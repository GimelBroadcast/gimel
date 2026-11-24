# -*- coding: utf-8 -*-
"""
Listas auxiliares, botonera y preescucha: lo que en un automatizador como
Dalet esta al lado de la playlist principal para llevar un programa en directo.

LISTAS AUXILIARES. Cuatro reproductores, cada uno con su lista, que suenan
por la misma salida que la emision (tarjeta e Icecast), encima de la pauta.
Tres modos, los de Dalet:

    manual       cada audio hay que lanzarlo; al acabar, la lista se para con
                 el siguiente ya cargado
    asistido     encadena uno tras otro hasta un PUNTO DE PARADA (se marca en
                 el audio tras el que hay que parar); alli espera a que lo
                 lancen
    automatico   lo encadena todo, sin hacer caso de los puntos de parada

Los audios se encadenan por su punto de mezcla, como en la pauta. Con bucle,
al acabar la lista se vuelve al principio. "Siguiente" es siempre el audio
marcado como tal (se puede cambiar a mano: es lo que entra al pulsar o al
encadenar).

Mientras suena una lista, la emision principal puede seguir igual (encima),
bajar unos dB (para hablar o pinchar encima) o callarse del todo. La
principal NUNCA se para: su hora sigue corriendo por debajo y, cuando la
auxiliar acaba, vuelve exactamente por donde va. Por eso las senales, los
bloques y los CUE siguen en su sitio pase lo que pase aqui.

BOTONERA (cart). Dieciseis botones con un audio cada uno: pulsar lo lanza y
volver a pulsar lo para. Pueden sonar varios a la vez. Los cortos se tienen
ya decodificados en memoria, asi que salen al instante.

PREESCUCHA. Por otra tarjeta, que no sale al aire: un audio entero o su final.

SALIDA PROPIA. Una lista puede sonar por su propia tarjeta en vez de por la
de la emision: es "un reproductor por canal de la mesa". Entonces no hace
falta estar emitiendo y quien mezcla es la mesa (bajar o silenciar la
principal sigue funcionando, si se quiere).

EMERGENCIA. Con el detector de silencio activo (Ajustes), si la principal se
queda muda mas de lo que dice la configuracion (y no esta sonando nada de
aqui), entra sola una lista de reserva, en bucle; cuando la principal vuelve
a sonar un rato, la reserva se retira con un fundido.

Todo esto es manejo en directo, no programacion: se aplica al momento (no
espera a "Guardar cambios") y se guarda solo en datos/auxiliares.json.

Hilos: las interfaces llaman a los metodos publicos, todos con el cerrojo. Un
hilo propio (`paso`) lee los eventos del motor, encadena y baja o sube la
principal. El hilo de audio no toca nada de aqui: recibe voces y ordenes por
la cola del motor y devuelve sus eventos por `eventos_aux`.
"""

import itertools
import json
import os
import threading
import time
import traceback
from collections import deque

import numpy as np

from . import rutas
from .biblioteca import _natural, leer_lista
from .fuentes import FuenteFFmpeg, FuenteMemoria
from .idioma import N_, tr
from .motor import SIN_TARJETA, Motor, Voz

N_LISTAS = 4
N_BOTONES = 16
GRUPO_BOTONERA = N_LISTAS + 1               # grupo de voces del motor (las listas van del 1 al 4)
GRUPO_EMERGENCIA = N_LISTAS + 2
ESPERA_CIERRE_SALIDA = 30.0                 # s sin usar tras los que se suelta la tarjeta propia de una lista

MODOS = ("manual", "asistido", "automatico")
CON_PRINCIPAL = ("encima", "bajar", "silenciar")
NOMBRE_MODO = {"manual": N_("Manual"), "asistido": N_("Asistido"), "automatico": N_("Automático")}
NOMBRE_PRINCIPAL = {"encima": N_("Encima de la principal"), "bajar": N_("Bajar la principal"),
                    "silenciar": N_("Silenciar la principal")}
CORTO_PRINCIPAL = {"encima": N_("Principal: encima"), "bajar": N_("Principal: bajar"),
                   "silenciar": N_("Principal: silenciar")}

AVANCE = 1.0              # s de antelacion con que se entrega al motor lo que entra encadenado
ARRANQUE = 0.12           # s entre pulsar y sonar: lo que necesita el motor para tenerlo a tiempo
FUNDIDO_PARAR = 0.35
FUNDIDO_SALTO = 0.6
FUNDIDO_PAUSA = 0.12
FUNDIDO_BOTON = 0.15
ENTRADA_REANUDAR = 0.06   # al reanudar una pausa: sin chasquido
MEMORIA_MAX = 30.0        # botones de hasta tantos s: enteros en memoria
FINAL_PREESCUCHA = 12.0   # "preescuchar el final": los ultimos tantos s
SIN_FIN = 1e7             # cue_out de un audio aun sin analizar: hasta donde llegue
ESPERA_CIERRE_PRE = 3.0   # s sin preescuchar nada tras los que se suelta esa tarjeta

_ids = itertools.count(1)


def _db(x: float) -> float:
    return 10.0 ** (x / 20.0)


def _num(v, defecto: float, lo: float, hi: float) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return defecto
    return max(lo, min(hi, v))


class Elemento:
    """Un audio de una lista auxiliar. Tiene identidad propia: moverlo no lo confunde con otro."""

    __slots__ = ("id", "ruta", "parar")

    def __init__(self, ruta: str, parar: bool = False):
        self.id = next(_ids)
        self.ruta = ruta
        self.parar = bool(parar)               # punto de parada: en asistido, la lista espera tras este


class Toque:
    """Un audio de una lista o de un boton ya entregado al motor."""

    __slots__ = ("voz", "fuente", "ruta", "pista", "el", "ofs", "f_ini", "t_ini", "dur",
                 "avance", "empezado", "parando", "encadenado", "motor")

    def __init__(self, voz, fuente, ruta, pista, el, ofs, frame, t_ini, dur, avance, motor=None):
        self.motor = motor                     # el de la emision, o el de la tarjeta propia de la lista
        self.voz = voz
        self.fuente = fuente
        self.ruta = ruta
        self.pista = pista
        self.el = el                           # Elemento (listas) o None (botones, preescucha)
        self.ofs = ofs                         # s del audio que se saltan (reanudar una pausa)
        self.f_ini = frame                     # frame de mezcla en que arranca (el real, al empezar)
        self.t_ini = t_ini
        self.dur = dur                         # s que va a sonar (None: sin analizar)
        self.avance = avance                   # s tras los que puede entrar el siguiente
        self.empezado = False
        self.parando = False
        self.encadenado = False                # ya se ha lanzado lo que va detras


class Lista:
    def __init__(self, n: int):
        self.n = n                             # 1..4: tambien su grupo de voces en el motor
        self.nombre = ""
        self.modo = "asistido"
        self.bucle = False
        self.principal = "encima"
        self.bajada_db = 12.0
        self.ganancia_db = 0.0
        self.titulo = False                    # anunciar lo que suena (RDS, Icecast) mientras suena
        self.salida = ""                       # "" = con la emision; "API|nombre" = su propia tarjeta
        self.elementos = []
        self.sig = None                        # el Elemento que entra al pulsar o al encadenar
        # en marcha
        self.toques = []
        self.cabeza = None                     # el ultimo Toque lanzado: el que manda
        self.pausa = None                      # (Elemento, segundos ya sonados)
        self.precarga = None                   # (id del elemento, ofs, fuente) lista para salir
        self.anunciado = False

    def visible(self) -> str:
        return self.nombre or tr("Auxiliar %d") % self.n

    def nivel(self) -> float:
        """A que nivel deja la principal mientras suena."""
        if self.principal == "silenciar":
            return 0.0
        if self.principal == "bajar":
            return _db(-abs(self.bajada_db))
        return 1.0

    def indice(self, el) -> int:
        try:
            return self.elementos.index(el)
        except ValueError:
            return -1

    def detras_de(self, el):
        """El que va detras de `el` en la lista (con bucle, tras el ultimo, el primero)."""
        i = self.indice(el)
        if i < 0:
            return None
        if i + 1 < len(self.elementos):
            return self.elementos[i + 1]
        if self.bucle and self.elementos:
            return self.elementos[0]
        return None

    def sigue(self, el) -> bool:
        """Si tras `el` se encadena el siguiente, segun el modo."""
        if self.modo == "automatico":
            return True
        if self.modo == "asistido":
            return not el.parar
        return False


class Boton:
    def __init__(self, i: int):
        self.i = i
        self.ruta = ""
        self.etiqueta = ""
        self.bucle = False
        self.toques = []
        self.cabeza = None
        self.memoria = None                    # el audio entero ya decodificado (los cortos)
        self.mem_ruta = ""
        self.cargando = False


class Auxiliares:
    def __init__(self, datos: str, motor, bib, ffmpeg: str, soxr: bool = False, cfg=None,
                 registro=None, titulo=None, emisor=None):
        self.ruta = os.path.join(datos, "auxiliares.json") if datos else ""
        self.motor = motor
        self.bib = bib
        self.ffmpeg = ffmpeg
        self.soxr = soxr
        self.cfg = cfg                         # funcion -> la Config de ahora (cambia al guardar)
        self.registro = registro
        self.titulo = titulo
        self.emisor = emisor
        self.marcas = None                     # las intros marcadas (gimel/marcas.py), las pone el nucleo
        self.listas = [Lista(n + 1) for n in range(N_LISTAS)]
        self.emergencia = Lista(GRUPO_EMERGENCIA)  # la de reserva del detector de silencio (no se ensena como las otras)
        self.emergencia.nombre = N_("Emergencia")
        self.emergencia.modo = "automatico"
        self.emergencia.bucle = True
        self._emergencia = False                   # la reserva esta en antena
        self._f_vuelve = None                      # frame desde el que la principal suena otra vez
        self._f_desde = 0                          # frame desde el que se cuenta el silencio (al empezar a emitir)
        self._listo_antes = False
        self._salidas = {}                         # "API|nombre" -> [Motor, ultimo uso]
        self.botones = [Boton(i) for i in range(N_BOTONES)]
        self.b_principal = "encima"
        self.b_bajada_db = 12.0
        self.b_ganancia_db = 0.0
        self.pre_api = ""
        self.pre_dispositivo = ""
        self.pre = None                        # Motor de la preescucha (otra tarjeta), al pedirlo
        self.pre_toque = None
        self._t_pre_libre = 0.0
        self.version = 1                       # sube cuando cambia algo de las listas que se pinta
        self.avisos = deque(maxlen=20)
        self._pistas = {}                      # ruta -> Pista ya analizada
        self._pedidas = set()
        self._t_pistas = 0.0
        self._por_voz = {}                     # id de voz -> (Lista | Boton, Toque)
        self._lock = threading.RLock()
        self._sucio = False
        self._t_sucio = 0.0
        self._hilo = None
        self._salir = False
        self._cargar()

    # ============================================================ hilo

    def arrancar_hilo(self) -> None:
        if self._hilo is None:
            self._salir = False
            self._hilo = threading.Thread(target=self._bucle, daemon=True, name="auxiliares")
            self._hilo.start()

    def _bucle(self) -> None:
        while not self._salir:
            try:
                self.paso()
            except Exception:
                traceback.print_exc()
                time.sleep(0.2)
            time.sleep(0.02)

    def cerrar(self) -> None:
        self._salir = True
        h, self._hilo = self._hilo, None
        if h is not None:
            h.join(timeout=1.0)
        with self._lock:
            self._reiniciar(todo=True)
            for L in self.todas():
                self._soltar_precarga(L)
            if self.pre is not None:
                self.pre.cerrar()
            for m, _ in self._salidas.values():
                m.cerrar()
            self._guardar()

    def todas(self) -> list:
        return self.listas + [self.emergencia]

    def paso(self) -> None:
        with self._lock:
            self._eventos()
            listo = self.listo()
            if listo and not self._listo_antes:
                self._f_desde = self.motor.m               # el silencio se cuenta desde que se emite
            self._listo_antes = listo
            for L in self.todas():
                if self._listo_lista(L):
                    self._encadenar(L)
            if listo:
                for b in self.botones:
                    self._repetir(b)
            elif any(t.motor is self.motor for _, t in self._por_voz.values()):
                self._reiniciar()                  # se ha dejado de emitir: lo que iba con ella se acaba
            for L in self.todas():
                self._precargar(L)
            self._vigilar_silencio(listo)
            self._nivel()
            self._paso_preescucha()
            self._paso_salidas()
            ahora = time.monotonic()
            if ahora - self._t_pistas > 1.5:
                self._t_pistas = ahora
                self._mirar_pistas()
            if self._sucio and ahora - self._t_sucio > 1.0:
                self._guardar()

    def listo(self) -> bool:
        """Se puede sonar: hay emision (las auxiliares salen por donde sale ella)."""
        if self.emisor is not None and not self.emisor.emitiendo:
            return False
        return self.motor.simulado or self.motor.abierta()

    def _listo_lista(self, L: Lista) -> bool:
        return True if L.salida else self.listo()

    def _motor_de(self, L: Lista):
        """El motor por el que sale la lista: el de la emision o el de su tarjeta, que se abre al pedirlo."""
        if not L.salida:
            return self.motor
        e = self._salidas.get(L.salida)
        if e is None:
            e = [Motor(self.motor.fs, simulado=self.motor.simulado, t0=self.motor.ahora()), 0.0]
            self._salidas[L.salida] = e
        m = e[0]
        e[1] = time.monotonic()
        if not m.simulado and not m.abierta():
            api, _, nombre = L.salida.partition("|")
            m.abrir(api, nombre, 0.15)
        return m

    def _paso_salidas(self) -> None:
        """Las tarjetas propias que llevan un rato sin usarse se sueltan."""
        if not self._salidas:
            return
        ahora = time.monotonic()
        usadas = {L.salida for L in self.todas() if L.toques}
        for clave, e in self._salidas.items():
            if clave in usadas:
                e[1] = ahora
            elif e[0].abierta() and ahora - e[1] > ESPERA_CIERRE_SALIDA:
                e[0].cerrar()

    def _vigilar_silencio(self, listo: bool) -> None:
        """Detector de silencio: si la principal se queda muda, entra la lista de emergencia."""
        c = self.cfg() if callable(self.cfg) else self.cfg
        s = getattr(c, "silencio", None)
        E = self.emergencia
        if s is None or not s.activo or not listo:
            if self._emergencia and (s is None or not s.activo):
                self._parar_lista(E, 2.0)
                self._emergencia = False
            return
        motor = self.motor
        fs = motor.fs
        motor.umbral_silencio = _db(s.umbral_db)
        mudo = (motor.m - max(motor.f_sonido, self._f_desde)) / float(fs)
        if not self._emergencia:
            otros = any(not t.parando for L in self.listas for t in L.toques) or \
                any(not t.parando for b in self.botones for t in b.toques)
            if mudo < max(2.0, s.segundos) or otros or not s.origen:
                return
            rutas_e = self.expandir([s.origen])
            if not rutas_e:
                return
            if s.orden == "aleatorio":
                import random
                random.Random(time.time()).shuffle(rutas_e)
            E.elementos = [Elemento(r) for r in rutas_e]
            for r in rutas_e[:20]:
                self._pedir(r)
            if self._lanzar(E, E.elementos[0]) is None:
                return
            self._emergencia = True
            self._f_vuelve = None
            texto = tr("La emisión lleva %d s en silencio: entra la lista de emergencia") % round(mudo)
            self._aviso(texto)
            if self.registro is not None:
                self.registro.escribir(time.time(), "sistema", N_("Silencio en la emisión: entra la lista de emergencia"))
            return
        if mudo < 1.0:                                    # la principal suena otra vez
            if self._f_vuelve is None:
                self._f_vuelve = motor.m
            elif (motor.m - self._f_vuelve) / float(fs) >= s.vuelta:
                self._parar_lista(E, 2.0)
                self._emergencia = False
                self._aviso(tr("Vuelve la emisión: se retira la lista de emergencia"))
                if self.registro is not None:
                    self.registro.escribir(time.time(), "sistema", N_("Vuelve la emisión: se retira la lista de emergencia"))
        else:
            self._f_vuelve = None
        if self._emergencia and E.cabeza is None and not E.toques and E.elementos:
            self._lanzar(E, E.sig or E.elementos[0])     # la de emergencia no se para nunca sola

    # ============================================================ audios

    def _pista(self, ruta: str):
        p = self._pistas.get(ruta)
        if p is None and self.bib is not None:
            p = self.bib.conocida(ruta)
            if p is not None:
                self._pistas[ruta] = p
        return p

    def _pedir(self, ruta: str) -> None:
        """Encarga el analisis (o lo saca de la cache) de un audio que acaba de entrar."""
        if ruta in self._pistas or ruta in self._pedidas or self.bib is None:
            return
        self._pedidas.add(ruta)
        p = self.bib.pista(ruta, urgente=True)
        if p is not None:
            self._pistas[ruta] = p

    def _mirar_pistas(self) -> None:
        nuevas = False
        for ruta in self._rutas():
            if ruta not in self._pistas:
                self._pedir(ruta)
                if self._pista(ruta) is not None:
                    nuevas = True
        if nuevas:
            self.version += 1
        for b in self.botones:
            self._a_memoria(b)

    def _rutas(self):
        for L in self.listas:
            for el in L.elementos:
                yield el.ruta
        for b in self.botones:
            if b.ruta:
                yield b.ruta

    def _mezcla(self):
        c = self.cfg() if callable(self.cfg) else self.cfg
        return getattr(c, "mezcla", None)

    def _ganancia(self, pista, extra_db: float) -> float:
        db = extra_db
        mz = self._mezcla()
        if pista is not None and not pista.error and mz is not None and mz.normalizar:
            db += pista.ganancia_db(mz.objetivo_lufs)
        return _db(db)

    def _avance(self, pista) -> float:
        """Segundos desde el principio del audio tras los que puede entrar lo siguiente."""
        if pista.largo > 20.0:
            mz = self._mezcla()
            umbral, solape = (mz.umbral, mz.solape_max) if mz is not None else (-15.0, 8.0)
        else:
            umbral, solape = -24.0, 1.5                   # un jingle, un efecto: casi al final
        return max(0.1, pista.mezcla(umbral, solape) - pista.cue_in)

    def _fuente(self, ruta: str, ofs: float, pista):
        if pista is not None and not pista.error:
            ci, co = pista.cue_in + ofs, pista.cue_out
        else:
            ci, co = ofs, SIN_FIN
        f = FuenteFFmpeg(self.ffmpeg, ruta, ci, co, self.motor.fs, self.soxr)
        f.preparar()
        return f

    def _toque(self, motor, fuente, ruta, pista, el, ofs, frame, ganancia, grupo, entrada=0.0):
        """Entrega un audio al motor y devuelve su Toque."""
        fs = motor.fs
        v = Voz(fuente, frame, ganancia, grupo)
        if entrada > 0:
            n = max(1, int(entrada * fs))
            v.duck = (frame - 2, frame - 1, frame, frame + n, 0.0)   # sube desde cero: fundido de entrada
        dur = avance = None
        if pista is not None and not pista.error:
            dur = max(0.05, pista.largo - ofs)
            avance = max(0.05, min(dur, self._avance(pista) - ofs))
        t = Toque(v, fuente, ruta, pista, el, ofs, frame, motor.wall_de(frame), dur, avance, motor)
        motor.orden("voz", v)
        return t

    def _fundir(self, t: Toque, segundos: float) -> None:
        if t.parando:
            return
        t.parando = True
        m = t.motor or self.motor
        fs = m.fs
        m.orden("fundir", t.voz.id, m.m + int(0.01 * fs), int(segundos * fs), 1.5)

    def _aviso(self, texto: str) -> None:
        self.avisos.append((time.time(), texto))

    # ============================================================ listas: en marcha

    def _lanzar(self, L: Lista, el: Elemento, ofs: float = 0.0, frame=None, entrada: float = 0.0):
        pista = self._pista(el.ruta)
        if pista is not None and pista.error:
            self._aviso(tr("No se puede reproducir %s") % os.path.basename(el.ruta))
            return None
        try:
            motor = self._motor_de(L)
        except Exception as e:
            self._aviso(tr("No se puede abrir la salida de «%s»: %s") % (L.visible(), e))
            return None
        if frame is None:
            frame = motor.m + int(ARRANQUE * motor.fs)
        fuente = self._tomar_precarga(L, el, ofs)
        if fuente is None:
            fuente = self._fuente(el.ruta, ofs, pista)
        t = self._toque(motor, fuente, el.ruta, pista, el, ofs, frame,
                        self._ganancia(pista, L.ganancia_db), L.n, entrada)
        self._por_voz[t.voz.id] = (L, t)
        L.toques.append(t)
        L.cabeza = t
        L.pausa = None
        L.sig = L.detras_de(el)
        return t

    def _encadenar(self, L: Lista) -> None:
        """Llega el punto de mezcla del que suena: entra el siguiente, al frame."""
        c = L.cabeza
        if c is None or c.encadenado or c.parando or c.avance is None:
            return
        if not L.sigue(c.el) or L.sig is None:
            return
        m = c.motor
        fs = m.fs
        f_mix = c.f_ini + int(round(c.avance * fs))
        if f_mix - m.m > AVANCE * fs:
            return
        if L.salida and m is not self._salidas.get(L.salida, [None])[0]:
            return                                        # le han cambiado la salida: lo siguiente, al pulsar
        c.encadenado = True
        self._lanzar(L, L.sig, frame=max(f_mix, m.m + 64))

    def _fin_lista(self, L: Lista, t: Toque) -> None:
        if t in L.toques:
            L.toques.remove(t)
        if L.cabeza is t:
            # se ha acabado sin que entrara nada detras: o no tocaba, o no se sabia cuando
            # (audio sin analizar), o ha durado menos de lo que decia su analisis
            if (not t.parando and not t.encadenado and t.el is not None and L.sigue(t.el)
                    and L.sig is not None and self._listo_lista(L)):
                self._lanzar(L, L.sig)
            else:
                L.cabeza = None
        if not L.toques and L.anunciado:
            L.anunciado = False
            self._soltar_titulo()

    def _precargar(self, L: Lista) -> None:
        """Lo que va a sonar al pulsar (o al encadenar) se tiene ya decodificandose."""
        if not self._listo_lista(L) or (L is self.emergencia and not self._emergencia):
            self._soltar_precarga(L)
            return
        if L.pausa is not None:
            el, ofs = L.pausa
        elif L.sig is not None:
            el, ofs = L.sig, 0.0
        else:
            self._soltar_precarga(L)
            return
        if L.precarga is not None and L.precarga[0] == el.id and abs(L.precarga[1] - ofs) < 1e-3:
            return
        pista = self._pista(el.ruta)
        if pista is not None and pista.error:
            self._soltar_precarga(L)
            return
        self._soltar_precarga(L)
        L.precarga = (el.id, ofs, self._fuente(el.ruta, ofs, pista))

    @staticmethod
    def _soltar_precarga(L: Lista) -> None:
        if L.precarga is not None:
            L.precarga[2].cerrar()
            L.precarga = None

    def _tomar_precarga(self, L: Lista, el: Elemento, ofs: float):
        p = L.precarga
        if p is not None and p[0] == el.id and abs(p[1] - ofs) < 1e-3 and not p[2].error:
            L.precarga = None
            return p[2]
        return None

    def _parar_lista(self, L: Lista, segundos: float = FUNDIDO_PARAR) -> None:
        for t in L.toques:
            self._fundir(t, segundos)
        L.cabeza = None

    # ============================================================ botonera: en marcha

    def _lanzar_boton(self, b: Boton, frame=None):
        pista = self._pista(b.ruta)
        if pista is not None and pista.error:
            self._aviso(tr("No se puede reproducir %s") % os.path.basename(b.ruta))
            return None
        motor = self.motor
        if frame is None:
            frame = motor.m + int(ARRANQUE * motor.fs)
        if b.memoria is not None and b.mem_ruta == b.ruta:
            fuente = FuenteMemoria(b.memoria)
        else:
            fuente = self._fuente(b.ruta, 0.0, pista)
        t = self._toque(motor, fuente, b.ruta, pista, None, 0.0, frame,
                        self._ganancia(pista, self.b_ganancia_db), GRUPO_BOTONERA)
        self._por_voz[t.voz.id] = (b, t)
        b.toques.append(t)
        b.cabeza = t
        return t

    def _repetir(self, b: Boton) -> None:
        """Boton en bucle: la vuelta siguiente entra justo donde acaba esta."""
        c = b.cabeza
        if not b.bucle or c is None or c.encadenado or c.parando or c.dur is None:
            return
        fs = self.motor.fs
        f_fin = c.f_ini + int(round(c.dur * fs))
        if f_fin - self.motor.m > AVANCE * fs:
            return
        c.encadenado = True
        self._lanzar_boton(b, max(f_fin, self.motor.m + 64))

    def _fin_boton(self, b: Boton, t: Toque) -> None:
        if t in b.toques:
            b.toques.remove(t)
        if b.cabeza is t:
            if b.bucle and not t.parando and not t.encadenado and t.empezado and self.listo():
                self._lanzar_boton(b)
            else:
                b.cabeza = None

    def _a_memoria(self, b: Boton) -> None:
        """Los botones cortos se decodifican enteros en otro hilo: luego salen al instante."""
        if not b.ruta or b.cargando or b.mem_ruta == b.ruta or not self.ffmpeg:
            return
        p = self._pista(b.ruta)
        if p is None or p.error or p.largo > MEMORIA_MAX:
            return
        b.cargando = True
        ruta = b.ruta
        threading.Thread(target=self._decodificar_boton, args=(b, ruta, p), daemon=True,
                         name="botonera").start()

    def _decodificar_boton(self, b: Boton, ruta: str, p) -> None:
        datos = None
        try:
            f = FuenteFFmpeg(self.ffmpeg, ruta, p.cue_in, p.cue_out, self.motor.fs, self.soxr)
            f.preparar()
            trozos = []
            limite = time.monotonic() + 60.0
            while not f.agotada and time.monotonic() < limite:
                d = f.leer(self.motor.fs, True)
                if len(d):
                    trozos.append(np.array(d, dtype=np.float32))
            f.cerrar()
            if trozos and not f.error:
                datos = np.ascontiguousarray(np.concatenate(trozos))
        except Exception:
            datos = None
        with self._lock:
            b.cargando = False
            if b.ruta == ruta:
                b.memoria = datos
                b.mem_ruta = ruta                  # aunque haya fallado: no se reintenta sin fin

    # ============================================================ eventos y nivel

    def _eventos(self) -> None:
        for m in [self.motor] + [e[0] for e in self._salidas.values()]:
            self._eventos_de(m)

    def _eventos_de(self, motor) -> None:
        ev = motor.eventos_aux
        while True:
            try:
                tipo, vid, f = ev.popleft()
            except IndexError:
                return
            d = self._por_voz.get(vid)
            if d is None:
                continue
            dueno, t = d
            if tipo == "inicio":
                t.f_ini = f
                t.t_ini = motor.wall_de(f)
                t.empezado = True
                self._al_aire(dueno, t)
                continue
            del self._por_voz[vid]
            t.fuente.cerrar()
            if not t.empezado and not t.parando:
                self._aviso(tr("No se ha podido reproducir %s") % os.path.basename(t.ruta))
            if isinstance(dueno, Lista):
                self._fin_lista(dueno, t)
            else:
                self._fin_boton(dueno, t)

    def _al_aire(self, dueno, t: Toque) -> None:
        p = t.pista
        titulo = (p.titulo or p.nombre()) if p is not None else os.path.splitext(os.path.basename(t.ruta))[0]
        artista = p.artista if p is not None else ""
        lista = isinstance(dueno, Lista)
        if self.registro is not None:
            if dueno is self.emergencia:
                tipo, nota = "emergencia", ""
            elif lista:
                tipo, nota = "auxiliar", dueno.visible()
            else:
                tipo, nota = "botonera", tr("Botón %d") % (dueno.i + 1)
            self.registro.escribir(t.t_ini, tipo, titulo, artista, t.dur or 0.0, nota, t.ruta)
        if lista and dueno.titulo and self.titulo is not None and t.ofs == 0.0:
            c = self.cfg() if callable(self.cfg) else self.cfg
            self.titulo.retenido = True
            self.titulo.anunciar("cancion", titulo, artista, getattr(c, "emisora", ""), aux=True)
            dueno.anunciado = True

    def _soltar_titulo(self) -> None:
        """Ya no suena ninguna lista con el titulo: vuelve el de la principal."""
        if self.titulo is None or any(L.anunciado for L in self.listas):
            return
        if not self.titulo.soltar() and self.emisor is not None:
            a = getattr(self.emisor, "actual", None)
            if a is not None and getattr(a, "estado", "") == "aire":
                c = self.cfg() if callable(self.cfg) else self.cfg
                self.titulo.anunciar(a.tipo, a.pista.titulo or a.pista.nombre(), a.pista.artista,
                                     getattr(c, "emisora", ""))

    def _nivel(self) -> None:
        """La principal, al nivel mas bajo que pida lo que este sonando aqui."""
        nivel = 1.0
        for L in self.listas:
            if any(not t.parando for t in L.toques):
                nivel = min(nivel, L.nivel())
        if any(not t.parando for b in self.botones for t in b.toques):
            nivel = min(nivel, self._nivel_botonera())
        self.motor.principal = nivel

    def _nivel_botonera(self) -> float:
        if self.b_principal == "silenciar":
            return 0.0
        if self.b_principal == "bajar":
            return _db(-abs(self.b_bajada_db))
        return 1.0

    def _reiniciar(self, todo: bool = False) -> None:
        """
        Se ha dejado de emitir: lo que sonaba con la emision se da por acabado
        (las listas con tarjeta propia siguen, salvo al cerrar el programa).
        """
        for vid, (dueno, t) in list(self._por_voz.items()):
            if todo or t.motor is self.motor:
                self._fundir(t, FUNDIDO_PARAR)
                t.fuente.cerrar()
                del self._por_voz[vid]
        for L in self.todas():
            c = L.cabeza
            if not (todo or (c is not None and c.motor is self.motor) or (c is None and not L.salida)):
                continue
            if c is not None and c.empezado and c.dur is not None and L is not self.emergencia:
                # que se pueda seguir por donde iba
                va = max(0.0, (c.motor.m - c.f_ini) / float(c.motor.fs))
                if va < c.dur - 1.0:
                    L.pausa = (c.el, c.ofs + va)
                    L.sig = c.el if c.el in L.elementos else L.sig
            L.toques = []
            L.cabeza = None
            L.anunciado = False
        self._emergencia = False
        for b in self.botones:
            b.toques = []
            b.cabeza = None
        self._soltar_titulo()
        self.motor.principal = 1.0

    # ============================================================ preescucha

    def _paso_preescucha(self) -> None:
        pre = self.pre
        if pre is None:
            return
        ev = pre.eventos
        while True:
            try:
                tipo, vid, f = ev.popleft()
            except IndexError:
                break
            t = self.pre_toque
            if t is None or t.voz.id != vid:
                continue
            if tipo == "inicio":
                t.f_ini = f
                t.t_ini = pre.wall_de(f)
                t.empezado = True
            else:
                t.fuente.cerrar()
                self.pre_toque = None
                self._t_pre_libre = time.monotonic()
        if self.pre_toque is None and pre.abierta() and \
                time.monotonic() - self._t_pre_libre > ESPERA_CIERRE_PRE and not pre.simulado:
            pre.cerrar()

    def _parar_pre(self) -> None:
        t = self.pre_toque
        if t is not None and self.pre is not None:
            fs = self.pre.fs
            self.pre.orden("fundir", t.voz.id, self.pre.m + int(0.01 * fs), int(0.08 * fs), 1.0)
            self.pre_toque = None
            self._t_pre_libre = time.monotonic()

    # ============================================================ ordenes (cualquier hilo)

    def accion(self, d: dict):
        """
        Punto de entrada unico para las dos interfaces. `d` trae "accion" y sus
        datos; devuelve (bien, mensaje).
        """
        if not isinstance(d, dict):
            return False, tr("orden ilegible")
        nombre = str(d.get("accion", ""))
        f = getattr(self, "_a_" + nombre, None)
        if f is None:
            return False, tr("acción desconocida")
        with self._lock:
            try:
                r = f(d)
            except (KeyError, IndexError, TypeError, ValueError) as e:
                return False, tr("orden ilegible") + " (%s)" % e
        if r is None:
            return True, ""
        if isinstance(r, str):
            return False, r
        return r

    def _lista(self, d: dict) -> Lista:
        n = int(d["lista"])
        if not 0 <= n < N_LISTAS:
            raise IndexError("lista")
        return self.listas[n]

    @staticmethod
    def _elemento(L: Lista, d: dict, clave: str = "indice") -> Elemento:
        i = int(d[clave])
        if not 0 <= i < len(L.elementos):
            raise IndexError(clave)
        return L.elementos[i]

    def _boton(self, d: dict) -> Boton:
        i = int(d["boton"])
        if not 0 <= i < N_BOTONES:
            raise IndexError("boton")
        return self.botones[i]

    def _cambiado(self, contenido: bool = True) -> None:
        self._sucio = True
        self._t_sucio = time.monotonic()
        if contenido:
            self.version += 1

    NO_EMITE = N_("Las listas auxiliares y la botonera suenan por la salida de la emisión: "
                  "empieza a emitir primero.")

    # --- transporte de las listas

    def _a_reproducir(self, d):
        L = self._lista(d)
        if not self._listo_lista(L):
            return tr(self.NO_EMITE)
        if d.get("indice") is not None:
            el = self._elemento(L, d)
            if L.cabeza is not None:
                self._parar_lista(L, FUNDIDO_SALTO)
            self._lanzar(L, el)
            self._cambiado(False)
            return None
        if L.cabeza is not None:
            return None                                   # ya suena
        if L.pausa is not None and L.pausa[0] in L.elementos:
            el, ofs = L.pausa
            self._lanzar(L, el, ofs, entrada=ENTRADA_REANUDAR)
            return None
        el = L.sig if L.sig in L.elementos else (L.elementos[0] if L.elementos else None)
        if el is None:
            return tr("La lista está vacía.")
        self._lanzar(L, el)
        self._cambiado(False)
        return None

    def _a_pausa(self, d):
        """Pausa y, si ya lo estaba, sigue por donde iba."""
        L = self._lista(d)
        c = L.cabeza
        if c is None:
            if L.pausa is not None:
                return self._a_reproducir({"lista": d["lista"]})
            return None
        m = c.motor
        va = max(0.0, (m.m - c.f_ini) / float(m.fs)) if c.empezado else 0.0
        self._parar_lista(L, FUNDIDO_PAUSA)
        L.pausa = (c.el, c.ofs + va)
        if c.el in L.elementos:
            L.sig = c.el
        return None

    def _a_parar(self, d):
        L = self._lista(d)
        self._parar_lista(L)
        L.pausa = None
        return None

    def _a_siguiente(self, d):
        """Salta al siguiente ya, con un fundido corto."""
        L = self._lista(d)
        if not self._listo_lista(L):
            return tr(self.NO_EMITE)
        L.pausa = None
        sig = L.sig
        self._parar_lista(L, FUNDIDO_SALTO)
        if sig is not None and sig in L.elementos:
            self._lanzar(L, sig)
        return None

    def _a_cue(self, d):
        """Marca el que entra al pulsar o al encadenar."""
        L = self._lista(d)
        L.sig = self._elemento(L, d)
        L.pausa = None
        self._cambiado(False)
        return None

    def _a_parada(self, d):
        """Pone o quita el punto de parada de un audio."""
        L = self._lista(d)
        el = self._elemento(L, d)
        el.parar = (not el.parar) if d.get("valor") is None else bool(d["valor"])
        self._cambiado()
        return None

    # --- contenido de las listas

    @staticmethod
    def expandir(rutas_dadas) -> list:
        """Ficheros, carpetas (con subcarpetas) y listas .m3u/.pls: los audios que hay, en orden."""
        res = []
        for r in rutas_dadas:
            r = str(r).strip().strip('"')
            if not r:
                continue
            if os.path.isdir(r):
                encontrados = []
                for raiz, carpetas, ficheros in os.walk(r):
                    carpetas.sort(key=_natural)
                    encontrados += [os.path.join(raiz, f) for f in ficheros if rutas.es_audio(f)]
                res += sorted(encontrados, key=_natural)
            elif rutas.es_lista(r) and os.path.isfile(r):
                try:
                    res += leer_lista(r)
                except OSError:
                    pass
            elif rutas.es_audio(r) and os.path.isfile(r):
                res.append(os.path.normpath(r))
        return res

    def _a_anadir(self, d):
        L = self._lista(d)
        nuevas = self.expandir(d.get("rutas") or [])
        if not nuevas:
            return tr("Ahí no hay audios que añadir.")
        pos = d.get("posicion")
        pos = len(L.elementos) if pos is None else max(0, min(len(L.elementos), int(pos)))
        els = [Elemento(r) for r in nuevas]
        L.elementos[pos:pos] = els
        if L.sig is None and L.cabeza is None and L.pausa is None:
            L.sig = els[0]
        elif L.sig is None and L.cabeza is not None:
            L.sig = L.detras_de(L.cabeza.el)              # lo que suena era el ultimo: ahora hay mas
        for r in nuevas:
            self._pedir(r)
        self._cambiado()
        return True, tr("%d audios añadidos.") % len(els) if len(els) != 1 else ""

    def _a_quitar(self, d):
        L = self._lista(d)
        quitar = sorted({int(i) for i in (d.get("indices") or []) if 0 <= int(i) < len(L.elementos)},
                        reverse=True)
        pos_sig = L.indice(L.sig) if L.sig is not None else -1
        for i in quitar:
            el = L.elementos[i]
            del L.elementos[i]
            if L.pausa is not None and L.pausa[0] is el:
                L.pausa = None
        if L.sig is not None and L.sig not in L.elementos:
            # se ha quitado el siguiente: pasa a serlo el que ha quedado en su sitio
            pos = pos_sig - sum(1 for i in quitar if i < pos_sig)
            if pos < len(L.elementos):
                L.sig = L.elementos[pos]
            else:
                L.sig = L.elementos[0] if L.bucle and L.elementos else None
        self._cambiado()
        return None

    def _a_mover(self, d):
        L = self._lista(d)
        el = self._elemento(L, d)
        destino = max(0, min(len(L.elementos) - 1, int(d["destino"])))
        L.elementos.remove(el)
        L.elementos.insert(destino, el)                   # el marcado como siguiente lo sigue siendo
        self._cambiado()
        return None

    def _a_vaciar(self, d):
        L = self._lista(d)
        L.elementos = []
        L.sig = None
        L.pausa = None
        self._cambiado()
        return None

    def _a_ajustes(self, d):
        L = self._lista(d)
        c = d.get("campos") or {}
        if "nombre" in c:
            L.nombre = str(c["nombre"]).strip()[:60]
        if c.get("modo") in MODOS:
            L.modo = c["modo"]
        if "bucle" in c:
            L.bucle = bool(c["bucle"])
            if L.cabeza is not None and L.sig is None:
                L.sig = L.detras_de(L.cabeza.el)
        if c.get("principal") in CON_PRINCIPAL:
            L.principal = c["principal"]
        if "bajada_db" in c:
            L.bajada_db = _num(c["bajada_db"], L.bajada_db, 0.0, 60.0)
        if "ganancia_db" in c:
            L.ganancia_db = _num(c["ganancia_db"], L.ganancia_db, -24.0, 12.0)
        if "titulo" in c:
            L.titulo = bool(c["titulo"])
            if not L.titulo and L.anunciado:
                L.anunciado = False
                self._soltar_titulo()
        if "salida" in c:
            L.salida = str(c["salida"] or "")             # lo que ya suena sigue por donde iba
            self._soltar_precarga(L)
        self._cambiado()
        return None

    def guardar_lista(self, n: int, ruta: str) -> str:
        """Escribe la lista auxiliar n como .m3u8. Devuelve un error, o "". (Solo la ventana de escritorio.)"""
        with self._lock:
            L = self.listas[n]
            lineas = ["#EXTM3U"]
            for el in L.elementos:
                p = self._pista(el.ruta)
                if p is not None and not p.error:
                    lineas.append("#EXTINF:%d,%s" % (round(p.largo), p.nombre()))
                lineas.append(el.ruta)
        try:
            with open(ruta, "w", encoding="utf-8", newline="\r\n") as fh:
                fh.write("\n".join(lineas) + "\n")
        except OSError as e:
            return str(e)
        return ""

    # --- botonera

    def _a_disparar(self, d):
        """Pulsar un boton: si no suena, sale; si suena, se para."""
        b = self._boton(d)
        if b.cabeza is not None and not b.cabeza.parando:
            for t in b.toques:
                self._fundir(t, FUNDIDO_BOTON)
            b.cabeza = None
            return None
        if not b.ruta:
            return tr("Ese botón no tiene audio.")
        if not self.listo():
            return tr(self.NO_EMITE)
        self._lanzar_boton(b)
        return None

    def _a_asignar(self, d):
        b = self._boton(d)
        ruta = str(d.get("ruta") or "")
        if ruta and not (rutas.es_audio(ruta) and os.path.isfile(ruta)):
            return tr("Eso no es un audio.")
        b.ruta = os.path.normpath(ruta) if ruta else ""
        if "etiqueta" in d:
            b.etiqueta = str(d.get("etiqueta") or "").strip()[:40]
        elif not ruta:
            b.etiqueta = ""
        b.memoria = None
        b.mem_ruta = ""
        if b.ruta:
            self._pedir(b.ruta)
            self._a_memoria(b)
        self._cambiado()
        return None

    def _a_boton(self, d):
        b = self._boton(d)
        c = d.get("campos") or {}
        if "etiqueta" in c:
            b.etiqueta = str(c["etiqueta"] or "").strip()[:40]
        if "bucle" in c:
            b.bucle = bool(c["bucle"])
        self._cambiado()
        return None

    def _a_botonera(self, d):
        c = d.get("campos") or {}
        if c.get("principal") in CON_PRINCIPAL:
            self.b_principal = c["principal"]
        if "bajada_db" in c:
            self.b_bajada_db = _num(c["bajada_db"], self.b_bajada_db, 0.0, 60.0)
        if "ganancia_db" in c:
            self.b_ganancia_db = _num(c["ganancia_db"], self.b_ganancia_db, -24.0, 12.0)
        self._cambiado()
        return None

    def _a_parar_botonera(self, d):
        for b in self.botones:
            for t in b.toques:
                self._fundir(t, FUNDIDO_BOTON)
            b.cabeza = None
        return None

    def _a_parar_todo(self, d):
        for L in self.listas:
            self._parar_lista(L)
            L.pausa = None
        self._a_parar_botonera(d)
        return None

    # --- preescucha

    def _a_preescuchar(self, d):
        if d.get("ruta"):
            ruta = str(d["ruta"])
        elif d.get("boton") is not None:
            ruta = self._boton(d).ruta
        else:
            ruta = self._elemento(self._lista(d), d).ruta
        if not ruta or not os.path.isfile(ruta):
            return tr("Eso no es un audio.")
        if not self.ffmpeg:
            return tr("No se encuentra ffmpeg.")
        if self.pre is None:
            self.pre = Motor(48000)
        pre = self.pre
        if not pre.abierta():
            try:
                pre.abrir(self.pre_api, self.pre_dispositivo, 0.15)
            except Exception as e:
                return tr("No se puede abrir la tarjeta de preescucha: %s") % e
        self._parar_pre()
        pista = self._pista(ruta)
        self._pedir(ruta)
        ofs = 0.0
        if d.get("final") and pista is not None and not pista.error:
            ofs = max(0.0, pista.largo - FINAL_PREESCUCHA)
        fuente = self._fuente(ruta, ofs, pista)
        self.pre_toque = self._toque(pre, fuente, ruta, pista, None, ofs, pre.m + int(0.08 * pre.fs),
                                     self._ganancia(pista, 0.0), 0)
        return None

    def _a_parar_preescucha(self, d):
        self._parar_pre()
        return None

    def _a_dispositivo_preescucha(self, d):
        self.pre_api = str(d.get("api") or "")
        self.pre_dispositivo = str(d.get("dispositivo") or "")
        self._parar_pre()
        if self.pre is not None and self.pre.abierta():
            self.pre.cerrar()
        self._cambiado(False)
        return None

    # ============================================================ foto para las interfaces

    def _texto(self, ruta: str):
        p = self._pista(ruta)
        if p is None or p.error:
            return os.path.splitext(os.path.basename(ruta))[0], "", p
        return p.titulo or os.path.splitext(os.path.basename(ruta))[0], p.artista, p

    def _intro(self, ruta: str) -> float:
        return self.marcas.intro(ruta) if self.marcas is not None else 0.0

    def _resta(self, L: Lista, ahora: float):
        """
        Backtiming: cuanto falta para que la lista se pare sola (por modo,
        punto de parada o final), contando con los cruces. None: no se sabe
        (audios sin analizar) o no se va a parar (automatico con bucle).
        """
        c = L.cabeza
        if c is None or c.dur is None:
            return None
        va = max(0.0, ahora - c.t_ini)
        if c.parando:
            return None
        if c.encadenado or not L.sigue(c.el) or L.sig is None:
            return max(0.0, c.dur - va) if not c.encadenado else None
        total = c.avance - va
        el, vistos = L.sig, set()
        while el is not None:
            if el.id in vistos:
                return None
            vistos.add(el.id)
            p = self._pista(el.ruta)
            if p is None or p.error:
                return None
            nxt = L.detras_de(el)
            if L.sigue(el) and nxt is not None:
                total += self._avance(p)
                el = nxt
            else:
                total += p.largo
                break
        return max(0.0, total)

    def estado(self, version: int = -1) -> dict:
        """Lo que pintan las interfaces. Los elementos de las listas solo van si han cambiado desde `version`."""
        with self._lock:
            listo = self.listo()
            ahora = self.motor.ahora() if listo else time.time()
            listas = []
            for L in self.listas:
                c = L.cabeza
                ahora_l = c.motor.ahora() if c is not None else ahora
                foto = {"n": L.n, "nombre": L.nombre, "visible": L.visible(), "modo": L.modo,
                        "bucle": L.bucle, "principal": L.principal, "bajada_db": L.bajada_db,
                        "ganancia_db": L.ganancia_db, "titulo": L.titulo, "salida": L.salida,
                        "listo": self._listo_lista(L),
                        "cursor": L.indice(L.sig) if L.sig is not None else -1,
                        "estado": "parado", "actual": -1, "t_ini": 0.0, "dur": 0.0, "va": 0.0,
                        "que": "", "quien": "", "resta": None, "fin": None,
                        "total": 0.0, "n_elementos": len(L.elementos)}
                if c is not None:
                    titulo, artista, _ = self._texto(c.ruta)
                    foto.update(estado="sonando", actual=L.indice(c.el), t_ini=c.t_ini,
                                dur=c.dur or 0.0, va=max(0.0, ahora_l - c.t_ini), que=titulo, quien=artista,
                                ruta=c.ruta, ofs=c.ofs, intro=max(0.0, self._intro(c.ruta) - c.ofs))
                    r = self._resta(L, ahora_l)
                    if r is not None:
                        foto["resta"] = r
                        foto["fin"] = time.time() + r
                elif L.pausa is not None:
                    el, pos = L.pausa
                    titulo, artista, p = self._texto(el.ruta)
                    foto.update(estado="pausa", actual=L.indice(el), va=pos, que=titulo, quien=artista,
                                dur=(p.largo if p is not None and not p.error else 0.0))
                total = 0.0
                elementos = []
                for el in L.elementos:
                    titulo, artista, p = self._texto(el.ruta)
                    dur = p.largo if p is not None and not p.error else 0.0
                    total += dur
                    if version != self.version:
                        elementos.append({"ruta": el.ruta, "titulo": titulo, "artista": artista,
                                          "dur": dur, "parar": el.parar, "pendiente": p is None,
                                          "error": bool(p is not None and p.error),
                                          "intro": self._intro(el.ruta)})
                foto["total"] = total
                if version != self.version:
                    foto["elementos"] = elementos
                listas.append(foto)
            botones = []
            for b in self.botones:
                c = b.cabeza
                titulo, _, p = self._texto(b.ruta) if b.ruta else ("", "", None)
                botones.append({"ruta": b.ruta, "etiqueta": b.etiqueta or titulo, "propia": bool(b.etiqueta),
                                "bucle": b.bucle, "dur": p.largo if p is not None and not p.error else 0.0,
                                "sonando": c is not None and not c.parando,
                                "t_ini": c.t_ini if c is not None else 0.0,
                                "va": max(0.0, ahora - c.t_ini) if c is not None else 0.0,
                                "lista": b.memoria is not None and b.mem_ruta == b.ruta})
            pre = {"api": self.pre_api, "dispositivo": self.pre_dispositivo, "sonando": False,
                   "que": "", "va": 0.0, "dur": 0.0, "misma": self._misma_tarjeta()}
            t = self.pre_toque
            if t is not None:
                pre.update(sonando=True, que=self._texto(t.ruta)[0], dur=(t.dur or 0.0) ,
                           va=max(0.0, time.time() - t.t_ini) if t.empezado else 0.0, ofs=t.ofs)
            avisos = [{"t": tt, "texto": x} for tt, x in self.avisos if time.time() - tt < 60.0]
            E = self.emergencia
            emergencia = {"activa": self._emergencia, "que": self._texto(E.cabeza.ruta)[0] if E.cabeza else ""}
            return {"version": self.version, "listo": listo, "ahora": ahora, "listas": listas,
                    "emergencia": emergencia,
                    "botonera": {"principal": self.b_principal, "bajada_db": self.b_bajada_db,
                                 "ganancia_db": self.b_ganancia_db, "botones": botones},
                    "preescucha": pre, "avisos": avisos, "nivel_principal": self.motor.principal}

    def _misma_tarjeta(self) -> bool:
        """La preescucha va por la misma tarjeta que la emision: se oiria en antena."""
        c = self.cfg() if callable(self.cfg) else self.cfg
        s = getattr(c, "salida", None)
        if s is None or s.api == SIN_TARJETA:
            return False
        return (self.pre_dispositivo or "") == (s.dispositivo or "") and \
            (not self.pre_dispositivo or (self.pre_api or s.api) == s.api)

    def resumen(self) -> list:
        """Para la pagina de emision: que suena ahora en las auxiliares y en la botonera."""
        with self._lock:
            if not self._por_voz:
                return []
            res = []
            for L in self.todas():
                c = L.cabeza
                if c is None:
                    continue
                res.append({"nombre": tr(L.visible()), "titulo": self._texto(c.ruta)[0],
                            "resta": (c.dur - max(0.0, c.motor.ahora() - c.t_ini)) if c.dur else None,
                            "principal": L.principal, "emergencia": L is self.emergencia})
            n = sum(1 for b in self.botones if b.cabeza is not None and not b.cabeza.parando)
            if n:
                res.append({"nombre": tr("Botonera"), "titulo": tr("%d botones sonando") % n if n > 1
                            else next(self._texto(b.ruta)[0] for b in self.botones
                                      if b.cabeza is not None and not b.cabeza.parando),
                            "resta": None, "principal": self.b_principal})
            return res

    # ============================================================ disco

    def _a_dict(self) -> dict:
        return {
            "listas": [{"nombre": L.nombre, "modo": L.modo, "bucle": L.bucle, "principal": L.principal,
                        "bajada_db": L.bajada_db, "ganancia_db": L.ganancia_db, "titulo": L.titulo,
                        "salida": L.salida,
                        "siguiente": L.indice(L.sig) if L.sig is not None else -1,
                        "elementos": [{"ruta": el.ruta, "parar": el.parar} for el in L.elementos]}
                       for L in self.listas],
            "botonera": {"principal": self.b_principal, "bajada_db": self.b_bajada_db,
                         "ganancia_db": self.b_ganancia_db,
                         "botones": [{"ruta": b.ruta, "etiqueta": b.etiqueta, "bucle": b.bucle}
                                     for b in self.botones]},
            "preescucha": {"api": self.pre_api, "dispositivo": self.pre_dispositivo},
        }

    def _cargar(self) -> None:
        if not self.ruta:
            return
        try:
            with open(self.ruta, "r", encoding="utf-8") as fh:
                d = json.load(fh)
        except FileNotFoundError:
            return
        except Exception:
            try:                                          # roto: se aparta y se empieza de cero
                os.replace(self.ruta, self.ruta + ".roto")
            except OSError:
                pass
            return
        for L, x in zip(self.listas, d.get("listas") or []):
            if not isinstance(x, dict):
                continue
            L.nombre = str(x.get("nombre") or "")[:60]
            L.modo = x.get("modo") if x.get("modo") in MODOS else L.modo
            L.bucle = bool(x.get("bucle"))
            L.principal = x.get("principal") if x.get("principal") in CON_PRINCIPAL else L.principal
            L.bajada_db = _num(x.get("bajada_db"), L.bajada_db, 0.0, 60.0)
            L.ganancia_db = _num(x.get("ganancia_db"), L.ganancia_db, -24.0, 12.0)
            L.titulo = bool(x.get("titulo"))
            L.salida = str(x.get("salida") or "")
            L.elementos = [Elemento(str(e.get("ruta", "")), bool(e.get("parar")))
                           for e in (x.get("elementos") or []) if isinstance(e, dict) and e.get("ruta")]
            i = x.get("siguiente", -1)
            if isinstance(i, int) and 0 <= i < len(L.elementos):
                L.sig = L.elementos[i]
            elif L.elementos:
                L.sig = L.elementos[0]
        bt = d.get("botonera") or {}
        self.b_principal = bt.get("principal") if bt.get("principal") in CON_PRINCIPAL else self.b_principal
        self.b_bajada_db = _num(bt.get("bajada_db"), self.b_bajada_db, 0.0, 60.0)
        self.b_ganancia_db = _num(bt.get("ganancia_db"), self.b_ganancia_db, -24.0, 12.0)
        for b, x in zip(self.botones, bt.get("botones") or []):
            if isinstance(x, dict):
                b.ruta = str(x.get("ruta") or "")
                b.etiqueta = str(x.get("etiqueta") or "")[:40]
                b.bucle = bool(x.get("bucle"))
        pre = d.get("preescucha") or {}
        self.pre_api = str(pre.get("api") or "")
        self.pre_dispositivo = str(pre.get("dispositivo") or "")
        for r in self._rutas():
            self._pedir(r)

    def _guardar(self) -> None:
        self._sucio = False
        if not self.ruta:
            return
        tmp = self.ruta + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._a_dict(), fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.ruta)
        except OSError:
            self._sucio = True                            # disco lleno, carpeta de solo lectura: luego
            self._t_sucio = time.monotonic() + 30.0
