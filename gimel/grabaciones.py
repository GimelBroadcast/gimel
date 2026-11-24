# -*- coding: utf-8 -*-
"""
Grabaciones: lo que entra (lineas, corresponsales, conexiones) y lo que sale.

GRABACIONES PROGRAMADAS. Cada una tiene sus dias, su hora de empezar y su
duracion, y graba de:

    url       un stream (el de un corresponsal, el de otra emisora)
    entrada   una entrada de tarjeta (una linea, un hibrido telefonico)
    antena    lo que sale al aire

Al acabar, el fichero puede entrar solo en una lista auxiliar (ingesta): la
conexion grabada queda lista para lanzarla. Si el programa se abre a mitad de
una grabacion, graba lo que queda.

LOGGER DE ANTENA. Graba sin parar lo que sale al aire, un fichero por hora en
una carpeta por dia (carpeta/AAAA-MM-DD/HH.mp3), y borra lo que pase de los
dias que se quieran guardar. Es la prueba de lo emitido.

Lo que sale al aire se oye por las `tomas` del motor (como Icecast): el hilo
de audio solo copia el bloque a una cola, nunca espera a ffmpeg.
"""

import os
import queue
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta

import numpy as np

from .idioma import N_, tr
from .rutas import SIN_VENTANA


def _limpio(nombre: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", nombre).strip() or "grabacion"


class Grabador:
    """Un fichero que se va escribiendo con ffmpeg: de lo que le llega por `poner`, o de una URL."""

    def __init__(self, ffmpeg: str, destino: str, formato: str = "mp3", bitrate: int = 128,
                 fs: int = 48000, url: str = "", segundos: float = 0.0):
        self.ffmpeg = ffmpeg
        self.destino = destino
        self.formato = formato
        self.bitrate = int(bitrate)
        self.fs = fs
        self.url = url
        self.segundos = segundos
        self.error = ""
        self.perdidos = 0
        self._proc = None
        self._cola = queue.Queue(maxsize=400)             # ~8 s de bloques de 1024
        self._hilo = None
        self.empezo = time.time()

    def _codec(self) -> list:
        if self.formato == "wav":
            return ["-c:a", "pcm_s16le"]
        return ["-c:a", "libmp3lame", "-b:a", "%dk" % self.bitrate]

    def arrancar(self) -> None:
        os.makedirs(os.path.dirname(self.destino) or ".", exist_ok=True)
        if self.url:
            orden = [self.ffmpeg, "-y", "-v", "error", "-nostdin"]
            if self.url.lower().startswith(("http://", "https://")):
                orden += ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5"]
            orden += ["-i", self.url]
            if self.segundos:
                orden += ["-t", "%.1f" % self.segundos]
            orden += ["-vn", "-ac", "2"] + self._codec() + [self.destino]
            entrada = subprocess.DEVNULL
        else:
            orden = [self.ffmpeg, "-y", "-v", "error", "-f", "f32le", "-ar", str(self.fs), "-ac", "2",
                     "-i", "pipe:0"] + self._codec() + [self.destino]
            entrada = subprocess.PIPE
        try:
            self._proc = subprocess.Popen(orden, stdin=entrada, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL, creationflags=SIN_VENTANA)
        except OSError as e:
            self.error = str(e)
            return
        if not self.url:
            self._hilo = threading.Thread(target=self._escribir, daemon=True, name="grabador")
            self._hilo.start()

    def poner(self, datos: bytes) -> None:
        """Desde el hilo de audio: no espera nunca."""
        try:
            self._cola.put_nowait(datos)
        except queue.Full:
            self.perdidos += 1

    def _escribir(self) -> None:
        p = self._proc
        while True:
            d = self._cola.get()
            if d is None:
                break
            try:
                p.stdin.write(d)
            except (OSError, ValueError):
                self.error = self.error or tr("ffmpeg ha dejado de grabar")
                break
        try:
            p.stdin.close()
        except Exception:
            pass

    def vivo(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def parar(self, esperar: float = 5.0) -> None:
        p = self._proc
        if p is None:
            return
        if self.url:
            try:
                p.terminate()                             # ffmpeg cierra el fichero al recibirla
            except Exception:
                pass
        else:
            self._cola.put(None)
            if self._hilo is not None:
                self._hilo.join(timeout=esperar)
        try:
            p.wait(timeout=esperar)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


class _Entrada:
    """Una entrada de tarjeta que alimenta a un Grabador."""

    def __init__(self, quien: str, grabador: Grabador, fs: int):
        self.flujo = None
        try:
            import sounddevice as sd
            from .motor import buscar_entrada
            api, _, nombre = quien.partition("|")
            d = buscar_entrada(api, nombre)
            if d is None:
                grabador.error = tr("no hay ninguna entrada de audio")
                return
            canales = 2 if d["canales"] >= 2 else 1

            def cb(datos, frames, tinfo, estado):
                a = np.asarray(datos, dtype=np.float32)
                if canales == 1:
                    a = np.repeat(a, 2, axis=1)
                grabador.poner(np.ascontiguousarray(a[:, :2]).tobytes())

            self.flujo = sd.InputStream(samplerate=fs, device=d["indice"], channels=canales,
                                        dtype="float32", blocksize=1024, callback=cb)
            self.flujo.start()
        except Exception as e:
            grabador.error = str(e)

    def cerrar(self) -> None:
        f, self.flujo = self.flujo, None
        if f is not None:
            try:
                f.abort()
                f.close()
            except Exception:
                pass


class Grabaciones:
    def __init__(self, ffmpeg: str, motor, cfg, aux=None, registro=None):
        self.ffmpeg = ffmpeg
        self.motor = motor
        self.cfg = cfg                         # funcion -> Config
        self.aux = aux
        self.registro = registro
        self.en_curso = {}                     # clave -> (Grabacion, Grabador, _Entrada | None, fin)
        self.hechas = set()                    # claves ya grabadas (no se repiten al reabrir el hilo)
        self.terminadas = []                   # (hora, nombre, fichero, error) para ensenar
        self.logger = None                     # (hora en punto, Grabador)
        self._t_purga = 0.0
        self._lock = threading.Lock()
        self._salir = False
        self._hilo = None
        motor.tomas.append(self._toma)

    # ------------------------------------------------------------ hilo

    def arrancar_hilo(self) -> None:
        if self._hilo is None:
            self._hilo = threading.Thread(target=self._bucle, daemon=True, name="grabaciones")
            self._hilo.start()

    def cerrar(self) -> None:
        self._salir = True
        with self._lock:
            for clave in list(self.en_curso):
                self._acabar(clave, cortada=True)
            if self.logger is not None:
                self.logger[1].parar()
                self.logger = None

    def _bucle(self) -> None:
        while not self._salir:
            try:
                self.paso(time.time())
            except Exception:
                import traceback
                traceback.print_exc()
            time.sleep(1.0)

    def _toma(self, bloque) -> None:
        """Lo llama el hilo de audio con cada bloque de salida."""
        if not self.en_curso and self.logger is None:
            return
        datos = bloque.tobytes()
        lg = self.logger
        if lg is not None:
            lg[1].poner(datos)
        for g, gr, ent, fin in list(self.en_curso.values()):
            if g.fuente == "antena":
                gr.poner(datos)

    # ------------------------------------------------------------ el paso

    def paso(self, ahora: float) -> None:
        c = self.cfg() if callable(self.cfg) else self.cfg
        with self._lock:
            self._programadas(c, ahora)
            self._logger(c, ahora)

    @staticmethod
    def _inicios(g, ahora: float):
        """Los comienzos de `g` que pueden estar en marcha ahora (el de hoy y, si cruza la medianoche, el de ayer)."""
        hoy = datetime.fromtimestamp(ahora).replace(hour=0, minute=0, second=0, microsecond=0)
        for dia in (hoy - timedelta(days=1), hoy):
            if not g.dias[dia.weekday()]:
                continue
            t0 = (dia + timedelta(hours=g.hora, minutes=g.minuto, seconds=g.segundo)).timestamp()
            yield t0

    def _programadas(self, c, ahora: float) -> None:
        for clave, (g, gr, ent, fin) in list(self.en_curso.items()):
            if ahora >= fin or (gr.url and not gr.vivo()):
                self._acabar(clave)
        for i, g in enumerate(getattr(c, "grabaciones", []) or []):
            if not g.activa or g.duracion <= 0 or not g.carpeta:
                continue
            if g.fuente == "url" and not g.url:
                continue
            for t0 in self._inicios(g, ahora):
                fin = t0 + g.duracion * 60.0
                clave = "%d|%s|%d" % (i, g.nombre, int(t0))
                if t0 <= ahora < fin - 2.0 and clave not in self.en_curso and clave not in self.hechas:
                    self._empezar(clave, g, t0, fin, ahora)

    def _empezar(self, clave: str, g, t0: float, fin: float, ahora: float) -> None:
        d = datetime.fromtimestamp(t0)
        nombre = "%s %s.%s" % (_limpio(g.nombre), d.strftime("%Y-%m-%d %H-%M"), "wav" if g.formato == "wav" else "mp3")
        destino = os.path.join(g.carpeta, nombre)
        if os.path.exists(destino):                       # se reabre a mitad: lo que queda, en otro fichero
            destino = destino[:-4] + datetime.fromtimestamp(ahora).strftime(" (%H-%M-%S)") + destino[-4:]
        gr = Grabador(self.ffmpeg, destino, g.formato, g.bitrate, self.motor.fs,
                      url=g.url if g.fuente == "url" else "", segundos=fin - ahora if g.fuente == "url" else 0.0)
        gr.arrancar()
        ent = _Entrada(g.entrada, gr, self.motor.fs) if g.fuente == "entrada" else None
        self.en_curso[clave] = (g, gr, ent, fin)
        if self.registro is not None:
            self.registro.escribir(ahora, "sistema", N_("Empieza una grabación"), nota=g.nombre, fichero=destino)

    def _acabar(self, clave: str, cortada: bool = False) -> None:
        g, gr, ent, fin = self.en_curso.pop(clave)
        self.hechas.add(clave)
        if ent is not None:
            ent.cerrar()
        gr.parar()
        bien = os.path.isfile(gr.destino) and os.path.getsize(gr.destino) > 1024
        error = gr.error or ("" if bien else tr("no ha llegado audio"))
        self.terminadas.append((time.time(), g.nombre, gr.destino, error))
        del self.terminadas[:-20]
        if self.registro is not None:
            self.registro.escribir(time.time(), "sistema",
                                   N_("Grabación cortada") if cortada else N_("Grabación terminada"),
                                   nota=g.nombre + (" — " + error if error else ""), fichero=gr.destino)
        if bien and not cortada and g.lista and self.aux is not None:
            self.aux.accion({"accion": "anadir", "lista": int(g.lista) - 1, "rutas": [gr.destino]})

    def _logger(self, c, ahora: float) -> None:
        lg = getattr(c, "logger", None)
        quiere = lg is not None and lg.activo and lg.carpeta and self.motor.abierta()
        if not quiere:
            if self.logger is not None:
                self.logger[1].parar()
                self.logger = None
            return
        d = datetime.fromtimestamp(ahora)
        hora = d.replace(minute=0, second=0, microsecond=0)
        if self.logger is not None and self.logger[0] == hora:
            return
        viejo = self.logger
        carpeta = os.path.join(lg.carpeta, hora.strftime("%Y-%m-%d"))
        destino = os.path.join(carpeta, hora.strftime("%H") + ".mp3")
        n = 2
        while os.path.exists(destino):                    # el programa se ha reabierto en esta hora
            destino = os.path.join(carpeta, "%s (%d).mp3" % (hora.strftime("%H"), n))
            n += 1
        gr = Grabador(self.ffmpeg, destino, "mp3", lg.bitrate, self.motor.fs)
        gr.arrancar()
        self.logger = (hora, gr)                           # primero el nuevo: no se pierde ni un bloque
        if viejo is not None:
            threading.Thread(target=viejo[1].parar, daemon=True, name="logger").start()
        if ahora - self._t_purga > 3600.0:
            self._t_purga = ahora
            self._purgar(lg, d)

    @staticmethod
    def _purgar(lg, ahora: datetime) -> None:
        if lg.dias <= 0:
            return
        limite = (ahora - timedelta(days=int(lg.dias))).strftime("%Y-%m-%d")
        try:
            for nombre in os.listdir(lg.carpeta):
                if re.fullmatch(r"\d{4}-\d\d-\d\d", nombre) and nombre < limite:
                    shutil.rmtree(os.path.join(lg.carpeta, nombre), ignore_errors=True)
        except OSError:
            pass

    # ------------------------------------------------------------ estado

    def estado(self) -> dict:
        ahora = time.time()
        with self._lock:
            curso = [{"nombre": g.nombre, "fichero": gr.destino, "resta": max(0.0, fin - ahora),
                      "error": gr.error} for g, gr, ent, fin in self.en_curso.values()]
            lg = self.logger
            return {"en_curso": curso,
                    "logger": {"fichero": lg[1].destino, "error": lg[1].error} if lg else None,
                    "terminadas": [{"t": t, "nombre": n, "fichero": f, "error": e}
                                   for t, n, f, e in reversed(self.terminadas)]}
