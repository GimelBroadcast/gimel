# -*- coding: utf-8 -*-
"""
Motor de mezcla y salida de audio.

Todo el tiempo del playout se cuenta en FRAMES DE MEZCLA: el motor lleva un
contador `m` de frames generados desde que nacio, y cada voz (una cancion, un
jingle, una cuna...) tiene escrito en que frame arranca y en cual se funde.
Asi un cruce o una senal horaria caen en la muestra exacta, no "cuando el
temporizador se despierte".

Para saber a que hora de reloj corresponde un frame, el callback de la tarjeta
mide en cada vuelta a que hora va a salir por el altavoz lo que entrega, y de
ahi sale la correspondencia frame <-> reloj (frame_de / wall_de).

Solo el hilo de audio toca las voces. Los demas hilos dejan ordenes en una cola
(`orden`) y leen lo ocurrido de otra (`eventos`).

    ordenes   ("voz", Voz)
              ("fundir", id, frame, n, exponente)
              ("duck", id, fa, fb, fc, fd, nivel)
              ("vaciar", frame, n)        funde lo que suena y quita lo que no ha empezado
    eventos   ("inicio", id, frame)
              ("fin", id, frame)

Con `simulado=True` no hay tarjeta: se avanza a mano con `avanzar()` y el reloj
es exacto. Con eso se prueban horas enteras de emision en segundos.
"""

import itertools
import math
import threading
import time
import traceback
from collections import deque

import numpy as np

from .idioma import N_, tr

try:
    import sounddevice as sd
except Exception:                                         # sin tarjeta o sin el paquete
    sd = None

TECHO = 0.985                 # el limitador no deja pasar de aqui (-0,13 dBFS)


class Voz:
    """Un audio colocado en la linea de tiempo del motor."""

    _ids = itertools.count(1)
    __slots__ = ("id", "fuente", "inicio", "ganancia", "fundidos", "duck",
                 "pos", "activa")

    def __init__(self, fuente, inicio: int, ganancia: float = 1.0):
        self.id = next(Voz._ids)
        self.fuente = fuente
        self.inicio = int(inicio)        # frame de mezcla en que arranca
        self.ganancia = float(ganancia)
        self.fundidos = []               # [(frame, n, exponente)]: se multiplican
        self.duck = None                 # (fa, fb, fc, fd, nivel)
        self.pos = 0                     # frames ya sonados
        self.activa = False


class Motor:
    B = 1024                  # frames por bloque (21 ms a 48 kHz)

    def __init__(self, fs: int = 48000, simulado: bool = False, t0: float = 0.0):
        self.fs = int(fs)
        self.simulado = simulado
        self.bloqueante = simulado       # en simulacion se espera a ffmpeg
        self.m = 0                       # frames de mezcla generados
        self.voces = []                  # solo el hilo de audio
        self.ordenes = deque()
        self.eventos = deque()
        self.volumen = 1.0
        self.limitador = True
        self.mudo = False
        self.retardo = 0.0               # retardo de la cadena tras la tarjeta (s)
        self.sonda = None                # pruebas: sonda(frame, bloque_de_mezcla)

        B = self.B
        self._mix = np.zeros((B, 2), dtype=np.float32)
        self._a = np.zeros((B, 2), dtype=np.float32)      # bloque retenido por el limitador
        self._b = np.zeros((B, 2), dtype=np.float32)
        self._sal = np.zeros((B, 2), dtype=np.float32)
        self._idx = np.arange(B, dtype=np.float64)
        self._rampa = ((np.arange(B, dtype=np.float32) + 1.0) / B)[:, None]
        self._g = 1.0                    # ganancia del limitador al final del ultimo bloque
        self._t_prev = 1.0               # la que necesita el bloque retenido
        self._suelta = (B / float(self.fs)) / 0.8         # recuperacion: ~0,8 s
        self._resto = np.zeros((0, 2), dtype=np.float32)

        self._pico = [0.0, 0.0]
        self._reduccion = 1.0
        self.secos = 0                   # bloques en que una voz no tenia audio listo
        self.cortes = 0                  # veces que la tarjeta se quedo sin datos
        self.saltos = 0                  # veces que el reloj dio un brinco
        self.error_cb = ""
        self.t_ultimo_cb = 0.0

        self._flujo = None
        self._canales = 2
        self._lat = 0.1
        self.dispositivo = ("", "")
        self.toma = None                 # funcion(bloque de salida): por aqui escucha Icecast
        self._marcapasos_hilo = None     # salida "sin tarjeta": un hilo que hace de tarjeta
        self._fin_marcapasos = False
        self._off = t0 if simulado else time.time()
        self._reiniciar_reloj()

    # ------------------------------------------------------------ reloj

    def frame_de(self, t: float) -> int:
        """Frame de mezcla que sale al aire a la hora de reloj t."""
        return int(round((t - self._off - self.retardo) * self.fs))

    def wall_de(self, frame: int) -> float:
        """Hora de reloj a la que sale al aire el frame de mezcla."""
        return self._off + self.retardo + frame / float(self.fs)

    def ahora(self) -> float:
        """Hora de reloj del proximo frame que se va a generar."""
        return self.wall_de(self.m)

    DESCARTE = 3              # medidas del arranque que no valen

    def _reiniciar_reloj(self) -> None:
        self._nmed = 0
        self._min = math.inf
        self._vent = []
        self._por_vent = max(1, int(0.5 * self.fs / self.B))

    def _medir(self, med: float) -> None:
        """
        med: hora de reloj del frame 0 segun este callback. Las medidas solo
        pueden pecar de tardias (el callback espera turno, nunca se adelanta;
        en WASAPI y DirectSound bailan hasta 10-20 ms hacia arriba), asi que
        la buena es la minima de los ultimos dos segundos.

        Las primeras llamadas tras abrir la tarjeta no valen: llegan con su
        bufer aun vacio y la latencia que declaran no es la real (medido: la
        primera se va justo una latencia entera).
        """
        self._nmed += 1
        n = self._nmed - self.DESCARTE
        if n <= 0:
            return
        if med < self._min:
            self._min = med
        if not self._vent:
            self._off = self._min                         # aun asentandose: la mejor hasta ahora
        if n % self._por_vent == 0:
            asentado = bool(self._vent)
            self._vent.append(self._min)
            del self._vent[:-4]
            self._min = math.inf
            nuevo = min(self._vent)
            if asentado and abs(nuevo - self._off) > 0.5:
                self.saltos += 1                          # el reloj del PC ha dado un brinco
                self._vent = [self._vent[-1]]
                nuevo = self._vent[0]
            self._off = nuevo

    # ------------------------------------------------------------ ordenes

    def orden(self, *o) -> None:
        self.ordenes.append(o)

    def _ordenes(self) -> None:
        while True:
            try:
                o = self.ordenes.popleft()
            except IndexError:
                return
            tipo = o[0]
            if tipo == "voz":
                self.voces.append(o[1])
            elif tipo == "fundir":
                _, vid, f, n, ex = o
                for v in self.voces:
                    if v.id == vid:
                        v.fundidos.append((int(f), max(1, int(n)), float(ex)))
                        break
            elif tipo == "duck":
                _, vid, fa, fb, fc, fd, niv = o
                fb = max(fb, fa + 1)
                fc = max(fc, fb + 1)
                fd = max(fd, fc + 1)
                for v in self.voces:
                    if v.id == vid:
                        v.duck = (int(fa), int(fb), int(fc), int(fd), float(niv))
                        break
            elif tipo == "vaciar":
                _, f, n = o
                quedan = []
                for v in self.voces:
                    if v.activa or v.inicio < f:
                        v.fundidos.append((int(f), max(1, int(n)), 1.0))
                        quedan.append(v)
                    else:
                        self.eventos.append(("fin", v.id, self.m))
                self.voces = quedan

    # ------------------------------------------------------------ mezcla

    def _ganancia(self, v: Voz, f0: int, k: int):
        g = None
        for fi, n, ex in v.fundidos:
            if f0 + k <= fi:
                continue
            x = (self._idx[:k] + (f0 - fi)) * (1.0 / n)
            np.clip(x, 0.0, 1.0, out=x)
            c = 1.0 - x
            if ex != 1.0:
                c = c ** ex
            g = c if g is None else g * c
        d = v.duck
        if d is not None and f0 < d[3] and f0 + k > d[0]:
            fa, fb, fc, fd, niv = d
            t = self._idx[:k] + (f0 - fa)
            c = np.interp(t, (0.0, fb - fa, fc - fa, fd - fa), (1.0, niv, niv, 1.0))
            g = c if g is None else g * c
        if g is None:
            return v.ganancia
        return (g * v.ganancia).astype(np.float32)

    def _mezclar(self) -> np.ndarray:
        B = self.B
        m0 = self.m
        m1 = m0 + B
        self._ordenes()
        buf = self._mix
        buf.fill(0.0)
        vivas = []
        for v in self.voces:
            if v.inicio >= m1:
                vivas.append(v)
                continue
            a = v.inicio - m0 if v.inicio > m0 else 0
            f0 = m0 + a
            cnt = B - a
            fin = False
            for fi, n, _ in v.fundidos:                   # se acaba donde acabe su primer fundido
                tope = fi + n
                if tope <= f0:
                    cnt = 0
                    fin = True
                elif tope < f0 + cnt:
                    cnt = tope - f0
                    fin = True
            k = 0
            if cnt > 0:
                d = v.fuente.leer(cnt, self.bloqueante)
                k = len(d)
                if k:
                    if not v.activa:
                        v.activa = True
                        self.eventos.append(("inicio", v.id, f0))
                    g = self._ganancia(v, f0, k)
                    if isinstance(g, float):
                        if g == 1.0:
                            buf[a:a + k] += d
                        else:
                            buf[a:a + k] += d * np.float32(g)
                    else:
                        buf[a:a + k] += d * g[:, None]
                    v.pos += k
                if k < cnt:
                    if v.fuente.agotada:
                        fin = True
                    elif not fin:                         # aun decodificando: se espera
                        self.secos += 1
            if fin:
                self.eventos.append(("fin", v.id, f0 + k))
            else:
                vivas.append(v)
        self.voces = vivas
        if self.sonda is not None:
            self.sonda(m0, buf)
        self.m = m1
        return buf

    def _bloque(self) -> np.ndarray:
        """
        Un bloque de salida. El limitador mira un bloque por delante: lo que
        sale ahora es la mezcla ANTERIOR, con la ganancia ya bajando si la que
        acaba de mezclarse viene con un pico. Por eso la salida va B frames por
        detras de la mezcla (y el reloj lo descuenta).
        """
        mix = self._mezclar()
        nuevo, viejo = self._b, self._a
        np.multiply(mix, np.float32(self.volumen), out=nuevo)
        pico = float(np.abs(nuevo).max())
        t_nuevo = 1.0 if pico <= TECHO or not self.limitador else TECHO / pico
        g0 = self._g
        obj = min(self._t_prev, t_nuevo)
        g1 = obj if obj < g0 else min(obj, g0 + self._suelta)
        sal = self._sal
        if g0 == 1.0 and g1 == 1.0:
            sal[:] = viejo
        else:
            np.multiply(viejo, np.float32(g0) + np.float32(g1 - g0) * self._rampa, out=sal)
        if not self.limitador:
            np.clip(sal, -1.0, 1.0, out=sal)
        self._g = g1
        self._t_prev = t_nuevo
        self._a, self._b = nuevo, viejo
        p = np.abs(sal).max(axis=0)
        if p[0] > self._pico[0]:
            self._pico[0] = float(p[0])
        if p[1] > self._pico[1]:
            self._pico[1] = float(p[1])
        if g1 < self._reduccion:
            self._reduccion = g1
        toma = self.toma
        if toma is not None:
            toma(sal)
        return sal

    def niveles(self):
        """(pico izq, pico der, ganancia minima del limitador) desde la ultima consulta."""
        l, r = self._pico
        red = self._reduccion
        self._pico = [0.0, 0.0]
        self._reduccion = 1.0
        return l, r, red

    def avanzar(self, bloques: int = 1) -> None:
        """Simulacion: genera bloques sin tarjeta."""
        for _ in range(bloques):
            self._bloque()

    # ------------------------------------------------------------ tarjeta

    def _cb(self, salida, frames, tinfo, estado) -> None:
        try:
            ahora = time.time()
            self.t_ultimo_cb = time.monotonic()
            if estado and estado.output_underflow:
                self.cortes += 1
            lat = tinfo.outputBufferDacTime - tinfo.currentTime
            if not 0.001 < lat < 2.0:                     # DirectSound no lo informa
                lat = self._lat
            B = self.B
            r = len(self._resto)
            self._medir(ahora + lat - (self.m - B - r) / float(self.fs))
            n = 0
            if r:
                k = min(frames, r)
                self._volcar(salida, 0, self._resto[:k])
                self._resto = self._resto[k:]
                n = k
            while n < frames:
                blo = self._bloque()
                k = min(frames - n, B)
                self._volcar(salida, n, blo[:k])
                if k < B:
                    self._resto = blo[k:].copy()
                n += k
            if self.mudo:
                salida.fill(0.0)
        except Exception:
            salida.fill(0.0)
            if not self.error_cb:
                self.error_cb = traceback.format_exc()

    def _volcar(self, salida, n: int, trozo: np.ndarray) -> None:
        if self._canales >= 2:
            salida[n:n + len(trozo), :2] = trozo
            if self._canales > 2:
                salida[n:n + len(trozo), 2:] = 0.0
        else:
            salida[n:n + len(trozo), 0] = trozo.mean(axis=1)

    def abrir(self, api: str = "", nombre: str = "", latencia: float = 0.12) -> str:
        """
        Abre la salida. Devuelve un aviso si no se encontro la tarjeta pedida y
        se ha tirado de otra; lanza excepcion si no se puede abrir ninguna.
        """
        if api == SIN_TARJETA:
            self.cerrar()
            self._reiniciar_reloj()
            self._resto = self._resto[:0]
            self._lat = 0.0
            self._off = time.time() - (self.m - self.B) / float(self.fs)
            self._fin_marcapasos = False
            self.t_ultimo_cb = time.monotonic()
            self._marcapasos_hilo = threading.Thread(target=self._marcapasos, daemon=True,
                                                     name="marcapasos")
            self._marcapasos_hilo.start()
            self.dispositivo = (SIN_TARJETA, N_("solo Icecast"))
            return ""
        if sd is None:
            raise RuntimeError(tr("falta el paquete sounddevice (pip install sounddevice)"))
        self.cerrar()
        aviso = ""
        d = buscar_dispositivo(api, nombre)
        if d is None:
            raise RuntimeError(tr("no hay ninguna salida de audio"))
        if nombre and d["nombre"] != nombre:
            aviso = tr("No está la salida «%s»: se emite por «%s».") % (nombre, d["nombre"])
        extra = None
        if "WASAPI" in d["api"]:
            # que Windows convierta la frecuencia: el motor va siempre a 48 kHz
            extra = sd.WasapiSettings(auto_convert=True)
        self._canales = 2 if d["canales"] >= 2 else 1
        self._reiniciar_reloj()
        self._resto = self._resto[:0]
        flujo = sd.OutputStream(samplerate=self.fs, blocksize=self.B,
                                device=d["indice"], channels=self._canales,
                                dtype="float32", latency=latencia,
                                callback=self._cb, extra_settings=extra)
        self._lat = float(flujo.latency) if flujo.latency else float(latencia)
        self.t_ultimo_cb = time.monotonic()
        flujo.start()
        if self._nmed <= self.DESCARTE:
            # hasta que haya medidas: con el bufer de la tarjeta vacio, lo primero sale casi al momento
            self._off = time.time() + 0.02 - (self.m - self.B) / float(self.fs)
        self._flujo = flujo
        self.dispositivo = (d["api"], d["nombre"])
        return aviso

    def _marcapasos(self) -> None:
        """
        Salida sin tarjeta: este hilo genera los bloques al ritmo del reloj del
        PC, como haria una tarjeta de sonido. El audio no va a ningun altavoz;
        se lo lleva quien este escuchando en `toma` (Icecast).
        """
        fs, B = float(self.fs), self.B
        t0, m0 = time.perf_counter(), self.m
        while not self._fin_marcapasos:
            falta = t0 + (self.m - m0 + B) / fs - time.perf_counter()
            if falta > 0:
                time.sleep(falta)
            elif falta < -2.0:
                # el equipo ha estado parado un rato: no se recupera a toda prisa
                t0, m0 = time.perf_counter(), self.m
            self.t_ultimo_cb = time.monotonic()
            try:
                self._medir(time.time() - (self.m - B) / fs)
                self._bloque()
            except Exception:
                if not self.error_cb:
                    self.error_cb = traceback.format_exc()
                time.sleep(0.1)

    def cerrar(self) -> None:
        h = self._marcapasos_hilo
        if h is not None:
            self._fin_marcapasos = True
            self._marcapasos_hilo = None
            h.join(timeout=1.0)
        f = self._flujo
        self._flujo = None
        if f is not None:
            try:
                f.abort()
                f.close()
            except Exception:
                pass

    def abierta(self) -> bool:
        return self._flujo is not None or self._marcapasos_hilo is not None

    def viva(self) -> bool:
        """La tarjeta sigue pidiendo audio (si la desenchufan, deja de hacerlo)."""
        h = self._marcapasos_hilo
        if h is not None:
            return h.is_alive()
        f = self._flujo
        if f is None:
            return False
        try:
            if not f.active:
                return False
        except Exception:
            return False
        # con margen: un tiron del propio programa (el interprete ocupado) no es una tarjeta caida
        return time.monotonic() - self.t_ultimo_cb < 3.0

    def latencia(self) -> float:
        return self._lat


# ---------------------------------------------------------------- tarjetas

APIS = ("Windows WASAPI", "Windows DirectSound", "MME")
SIN_TARJETA = N_("Sin tarjeta")   # "sistema de audio" que no es ninguno: solo Icecast


def dispositivos(refrescar: bool = False) -> list:
    """
    Salidas de audio: [{api, nombre, indice, canales, defecto}]. Se deja fuera
    WDM-KS, que exige formato exacto y solo da problemas. Con `refrescar` se
    vuelve a preguntar a Windows (solo puede hacerse sin emitir).
    """
    if sd is None:
        return []
    if refrescar:
        try:
            sd._terminate()
            sd._initialize()
        except Exception:
            pass
    try:
        apis = sd.query_hostapis()
        todos = sd.query_devices()
    except Exception:
        return []
    res = []
    for i, d in enumerate(todos):
        if d["max_output_channels"] <= 0:
            continue
        a = apis[d["hostapi"]]
        if "WDM" in a["name"]:
            continue
        res.append({"api": a["name"], "nombre": d["name"], "indice": i,
                    "canales": int(d["max_output_channels"]),
                    "defecto": a["default_output_device"] == i})
    return res


def buscar_dispositivo(api: str, nombre: str):
    """
    La tarjeta por nombre (los indices de PortAudio bailan cada vez que se
    enchufa algo). Si no esta: la misma en otra API, la predeterminada de esa
    API o la que haya.
    """
    lista = dispositivos()
    if not lista:
        return None
    if nombre:
        for d in lista:
            if d["api"] == api and d["nombre"] == nombre:
                return d
        for d in lista:
            if d["nombre"] == nombre:
                return d
    for d in lista:
        if d["api"] == api and d["defecto"]:
            return d
    for pref in APIS:
        for d in lista:
            if d["api"] == pref and d["defecto"]:
                return d
    return lista[0]
