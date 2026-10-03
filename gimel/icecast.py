# -*- coding: utf-8 -*-
"""
Salida a Icecast.

Cada punto de montaje es un proceso ffmpeg que recibe por su entrada estandar
exactamente lo mismo que sale por la tarjeta (despues del limitador), lo
codifica y lo manda al servidor. Puede haber varios a la vez (el mismo
programa en MP3 y en AAC, o a dos servidores).

El hilo de audio no espera a nadie: deja cada bloque en una cola y sigue. Si
la red se atasca la cola se llena y se tira lo mas viejo (el oyente nota un
salto), pero la emision por la tarjeta ni se entera. Si ffmpeg se cae o el
servidor corta, se vuelve a conectar solo cada pocos segundos.

Con el formato MP3 o AAC se manda ademas el titulo de cada cancion por la
interfaz de administracion del servidor (/admin/metadata).
"""

import base64
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from collections import deque

from .idioma import tr
from .rutas import SIN_VENTANA

# formato -> (codec de ffmpeg, contenedor, tipo MIME)
FORMATOS = {
    "mp3": ("libmp3lame", "mp3", "audio/mpeg"),
    "aac": ("aac", "adts", "audio/aac"),
    "ogg": ("libvorbis", "ogg", "application/ogg"),
    "opus": ("libopus", "ogg", "application/ogg"),
}
CON_TITULO = ("mp3", "aac")       # los Ogg llevan el titulo dentro del propio flujo
REINTENTO = 5.0                   # segundos entre intentos de conexion


class Flujo:
    """Un punto de montaje."""

    COLA_MAX = 420                # bloques en espera, como mucho (~9 s)

    def __init__(self, ffmpeg: str, cfg, fs: int, emisora: str):
        self.ffmpeg = ffmpeg
        self.cfg = cfg
        self.fs = fs
        self.emisora = emisora
        self.estado = "parado"        # parado | conectando | emitiendo | error
        self.detalle = ""
        self.desde = 0.0              # cuando conecto (reloj monotono)
        self.perdidos = 0             # bloques tirados por atasco
        self.ultimo_titulo = ""
        self._cola = deque()
        self._fin = False
        self._proc = None
        self._hilo = None
        self._lleno_desde = 0.0

    # ------------------------------------------------------------ hilo de audio

    def poner(self, datos: bytes) -> None:
        cola = self._cola
        cola.append(datos)
        if len(cola) > self.COLA_MAX:
            try:
                cola.popleft()
            except IndexError:
                pass
            self.perdidos += 1
            ahora = time.monotonic()
            if not self._lleno_desde:
                self._lleno_desde = ahora
            elif ahora - self._lleno_desde > 15.0:        # atascado sin remedio: a reconectar
                self._lleno_desde = 0.0
                self._matar()
        else:
            self._lleno_desde = 0.0

    # ------------------------------------------------------------ control

    def arrancar(self) -> None:
        if self._hilo is not None:
            return
        self._fin = False
        self._hilo = threading.Thread(target=self._bucle, daemon=True, name="icecast")
        self._hilo.start()

    def parar(self) -> None:
        self._fin = True
        self._matar()
        self.estado = "parado"
        self.detalle = ""

    def _matar(self) -> None:
        p = self._proc
        if p is not None:
            try:
                if p.poll() is None:
                    p.kill()
            except Exception:
                pass

    def orden(self) -> list:
        c = self.cfg
        codec, contenedor, mime = FORMATOS.get(c.formato, FORMATOS["mp3"])
        frecuencia = 48000 if c.formato == "opus" else int(c.frecuencia)
        punto = c.punto if c.punto.startswith("/") else "/" + c.punto
        destino = "icecast://%s:%s@%s:%d%s" % (
            urllib.parse.quote(c.usuario or "source", safe=""),
            urllib.parse.quote(c.clave, safe=""), c.servidor.strip(), int(c.puerto),
            urllib.parse.quote(punto))
        o = [self.ffmpeg, "-hide_banner", "-loglevel", "info", "-nostats",
             "-probesize", "32", "-analyzeduration", "0",
             "-f", "f32le", "-ar", str(self.fs), "-ac", "2", "-i", "pipe:0",
             "-vn", "-c:a", codec, "-b:a", "%dk" % int(c.bitrate),
             "-ar", str(frecuencia), "-ac", "2" if c.estereo else "1",
             "-content_type", mime,
             "-ice_name", c.titulo or self.emisora or "GIMEL",
             "-ice_public", "1" if c.publico else "0"]
        if c.descripcion:
            o += ["-ice_description", c.descripcion]
        if c.genero:
            o += ["-ice_genre", c.genero]
        if c.web:
            o += ["-ice_url", c.web]
        if c.tls:
            o += ["-tls", "1"]
        o += ["-flush_packets", "1", "-f", contenedor, destino]
        return o

    def _bucle(self) -> None:
        while not self._fin:
            self.estado = "conectando"
            self.detalle = ""
            self._cola.clear()
            try:
                proc = subprocess.Popen(self.orden(), stdin=subprocess.PIPE,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                        creationflags=SIN_VENTANA)
            except OSError as e:
                self.estado, self.detalle = "error", tr("no se pudo lanzar ffmpeg: %s") % e
                self._esperar(REINTENTO)
                continue
            self._proc = proc
            lector = threading.Thread(target=self._leer_avisos, args=(proc,), daemon=True)
            lector.start()
            try:
                while not self._fin and proc.poll() is None:
                    try:
                        datos = self._cola.popleft()
                    except IndexError:
                        time.sleep(0.01)
                        continue
                    proc.stdin.write(datos)
            except (OSError, ValueError):
                pass                                      # tuberia rota: ffmpeg ha muerto
            finally:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
                self._matar()
                try:
                    proc.wait(timeout=3)
                except Exception:
                    pass
                lector.join(timeout=2)
            if self._fin:
                break
            self.estado = "error"
            if not self.detalle:
                self.detalle = tr("se ha cortado la conexión")
            self._esperar(REINTENTO)
        self.estado = "parado"
        self._hilo = None

    def _esperar(self, segundos: float) -> None:
        limite = time.monotonic() + segundos
        while not self._fin and time.monotonic() < limite:
            time.sleep(0.1)

    def _leer_avisos(self, proc) -> None:
        """Lo que va diciendo ffmpeg: de ahi se sabe si ha conectado y, si no, por que."""
        try:
            for cruda in proc.stderr:
                linea = cruda.decode("utf-8", "replace").strip()
                if not linea:
                    continue
                if linea.startswith("Output #0"):
                    self.estado = "emitiendo"             # cabecera enviada: el servidor ha aceptado
                    self.detalle = ""
                    self.desde = time.monotonic()
                    if self.ultimo_titulo:                # que el oyente no espere a la cancion siguiente
                        threading.Timer(2.5, self.titulo, args=(self.ultimo_titulo,)).start()
                    continue
                bajo = linea.lower()
                if any(x in bajo for x in ("error", "failed", "refused", "unauthorized", "forbidden",
                                           "timed out", "not found", "invalid")):
                    self.detalle = traducir(linea)
        except Exception:
            pass

    # ------------------------------------------------------------ titulo

    def titulo(self, texto: str) -> None:
        c = self.cfg
        self.ultimo_titulo = texto
        if not c.metadatos or c.formato not in CON_TITULO or self.estado != "emitiendo":
            return
        threading.Thread(target=self._mandar_titulo, args=(texto,), daemon=True,
                         name="icecast-titulo").start()

    def _mandar_titulo(self, texto: str) -> None:
        c = self.cfg
        punto = c.punto if c.punto.startswith("/") else "/" + c.punto
        url = "%s://%s:%d/admin/metadata?mount=%s&mode=updinfo&charset=UTF-8&song=%s" % (
            "https" if c.tls else "http", c.servidor.strip(), int(c.puerto),
            urllib.parse.quote(punto, safe=""), urllib.parse.quote(texto, safe=""))
        credencial = base64.b64encode(("%s:%s" % (c.usuario or "source", c.clave)).encode("utf-8"))
        req = urllib.request.Request(url, headers={"Authorization": "Basic " + credencial.decode("ascii"),
                                                   "User-Agent": "GIMEL"})
        try:
            urllib.request.urlopen(req, timeout=5).close()
        except Exception:
            pass                                          # un titulo perdido no es para avisar


def traducir(linea: str) -> str:
    """Los errores mas corrientes de ffmpeg, dichos en cristiano."""
    bajo = linea.lower()
    if "401" in bajo or "unauthorized" in bajo:
        return tr("el servidor rechaza el usuario o la contraseña")
    if "403" in bajo or "forbidden" in bajo:
        return tr("el servidor no admite ese punto de montaje (¿ya hay otra fuente en él?)")
    if "refused" in bajo:
        return tr("el servidor no contesta en ese puerto (conexión rechazada)")
    if "timed out" in bajo:
        return tr("el servidor no responde (tiempo agotado)")
    if "failed to resolve" in bajo or "name or service not known" in bajo or "no such host" in bajo:
        return tr("no se encuentra el servidor (nombre desconocido)")
    if "unknown encoder" in bajo or "encoder not found" in bajo:
        return tr("este ffmpeg no trae el codificador de ese formato")
    return linea[-160:]


class Emisiones:
    """Todos los puntos de montaje configurados."""

    def __init__(self, ffmpeg: str, motor):
        self.ffmpeg = ffmpeg
        self.motor = motor
        self.cfgs = []
        self.emisora = ""
        self.flujos = []
        self.en_marcha = False
        self.ultimo_titulo = ""

    def configurar(self, cfgs: list, emisora: str) -> None:
        """Cambia la configuracion; si se esta emitiendo, reconecta solo lo que haya cambiado."""
        self.cfgs = list(cfgs)
        self.emisora = emisora
        if self.en_marcha:
            self._sincronizar()

    def hay_activos(self) -> bool:
        return any(c.activo and c.servidor.strip() for c in self.cfgs)

    def arrancar(self) -> None:
        self.en_marcha = True
        self._sincronizar()

    def parar(self) -> None:
        self.en_marcha = False
        self.motor.toma = None
        for f in self.flujos:
            f.parar()
        self.flujos = []

    def _sincronizar(self) -> None:
        quiero = [c for c in self.cfgs if c.activo and c.servidor.strip()]
        sigue, nuevos = [], []
        for c in quiero:
            viejo = next((f for f in self.flujos if f.cfg == c and f not in sigue), None)
            if viejo is not None:
                sigue.append(viejo)
                nuevos.append(viejo)
            else:
                f = Flujo(self.ffmpeg, c, self.motor.fs, self.emisora)
                f.ultimo_titulo = self.ultimo_titulo
                f.arrancar()
                nuevos.append(f)
        for f in self.flujos:
            if f not in sigue:
                f.parar()
        self.flujos = nuevos
        self.motor.toma = self._toma if nuevos else None

    def _toma(self, bloque) -> None:
        """Lo llama el hilo de audio con cada bloque de salida."""
        datos = bloque.tobytes()
        for f in self.flujos:
            f.poner(datos)

    def titulo(self, texto: str) -> None:
        self.ultimo_titulo = texto
        for f in self.flujos:
            f.titulo(texto)

    def estado(self) -> list:
        ahora = time.monotonic()
        res = []
        for f in self.flujos:
            res.append({"nombre": f.cfg.nombre, "estado": f.estado, "detalle": f.detalle,
                        "segundos": ahora - f.desde if f.estado == "emitiendo" else 0.0,
                        "perdidos": f.perdidos,
                        "destino": "%s:%d%s" % (f.cfg.servidor, f.cfg.puerto, f.cfg.punto)})
        return res
