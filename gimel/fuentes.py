# -*- coding: utf-8 -*-
"""
Fuentes de audio para el motor de mezcla.

FuenteFFmpeg decodifica un fichero con un proceso ffmpeg propio y lo va dejando
en una cola de bloques. Un proceso por audio tiene dos ventajas para una
emisora que no puede callarse: cualquier formato que ffmpeg entienda vale, y un
fichero corrupto solo tumba a su ffmpeg, nunca a la emision.

Dos hilos tocan cada fuente y ninguno pisa al otro: el lector solo anade a la
cola y cuenta lo producido; el hilo de audio solo saca y cuenta lo consumido.
"""

import subprocess
import threading
import time
from collections import deque

import numpy as np

from .rutas import SIN_VENTANA

VACIO = np.zeros((0, 2), dtype=np.float32)


class FuenteFFmpeg:
    BLOQUE = 8192            # frames por lectura de la tuberia
    COLCHON = 10.0           # segundos decodificados por delante, como mucho

    def __init__(self, ffmpeg: str, ruta: str, cue_in: float, cue_out: float,
                 fs: int = 48000, soxr: bool = False):
        self.ffmpeg = ffmpeg
        self.ruta = ruta
        self.fs = fs
        self.soxr = soxr
        self._saltar = max(0, int(round(cue_in * fs)))
        self.total = max(0, int(round((cue_out - cue_in) * fs)))   # frames que va a dar
        self._hasta = cue_out
        self._max = int(self.COLCHON * fs)
        self._cola = deque()
        self._cab = None             # bloque a medio consumir
        self._ic = 0
        self.producidos = 0
        self.consumidos = 0
        self.fin_lectura = False
        self.error = ""
        self._cerrar = False
        self._proc = None
        self._hilo = None

    # ------------------------------------------------ lado del lector

    def preparar(self) -> None:
        """Lanza ffmpeg y empieza a llenar el colchon."""
        if self._hilo is not None:
            return
        self._hilo = threading.Thread(target=self._leer, daemon=True,
                                      name="fuente")
        self._hilo.start()

    def _leer(self) -> None:
        orden = [self.ffmpeg, "-v", "error", "-nostdin", "-i", self.ruta,
                 "-map", "0:a:0", "-vn", "-sn", "-dn",
                 "-t", "%.3f" % (self._hasta + 0.5)]
        if self.soxr:
            orden += ["-af", "aresample=%d:resampler=soxr:precision=24" % self.fs]
        orden += ["-ac", "2", "-ar", str(self.fs), "-f", "f32le", "pipe:1"]
        try:
            # stderr va a la basura: un fichero danado puede escupir avisos sin
            # fin y, con su tuberia llena y nadie leyendola, ffmpeg se pararia
            self._proc = subprocess.Popen(
                orden, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, creationflags=SIN_VENTANA)
        except OSError as e:
            self.error = "no se pudo lanzar ffmpeg: %s" % e
            self.fin_lectura = True
            return
        salida = self._proc.stdout
        saltar = self._saltar
        quedan = self.total
        resto = b""
        try:
            while quedan > 0 and not self._cerrar:
                while self.producidos - self.consumidos >= self._max and not self._cerrar:
                    time.sleep(0.02)
                b = salida.read(self.BLOQUE * 8)
                if not b:
                    break
                if resto:
                    b = resto + b
                sobra = len(b) % 8
                resto = b[len(b) - sobra:] if sobra else b""
                a = np.frombuffer(b, dtype="<f4", count=(len(b) - sobra) // 4).reshape(-1, 2)
                if saltar:
                    k = min(saltar, len(a))
                    a = a[k:]
                    saltar -= k
                    if not len(a):
                        continue
                if len(a) > quedan:
                    a = a[:quedan]
                quedan -= len(a)
                self._cola.append(a)
                self.producidos += len(a)
        except Exception as e:                            # tuberia rota al cerrar, etc.
            if not self._cerrar:
                self.error = str(e)
        finally:
            if (self.producidos == 0 and self.total > 0 and not self._cerrar
                    and not self.error):
                self.error = "no se pudo decodificar"
            self.fin_lectura = True
            self._matar()
            try:
                salida.close()
                self._proc.wait(timeout=2)
            except Exception:
                pass

    def _matar(self) -> None:
        # solo matar: la tuberia la cierra el hilo lector, que es quien la lee
        p = self._proc
        if p is None:
            return
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass

    # ------------------------------------------------ lado del consumidor

    def lista(self) -> bool:
        """Hay audio suficiente para arrancar sin riesgo de quedarse seca."""
        return self.fin_lectura or self.producidos >= min(self.total, self.fs)

    @property
    def agotada(self) -> bool:
        return (self.fin_lectura and not self._cola
                and (self._cab is None or self._ic >= len(self._cab)))

    def leer(self, n: int, bloquear: bool = False) -> np.ndarray:
        """
        Hasta n frames (n x 2, float32). Devuelve menos si aun no hay mas
        decodificado, o si se acabo. Con bloquear (simulacion, donde el reloj
        corre mas que ffmpeg) espera a que los haya.
        """
        if self._hilo is None:                            # nadie la preparo: se prepara sola
            self.preparar()
        if bloquear:
            limite = time.monotonic() + 30.0
            while (self.producidos - self.consumidos < n and not self.fin_lectura
                   and time.monotonic() < limite):
                time.sleep(0.0005)
        salida = None
        k = 0
        while k < n:
            if self._cab is None or self._ic >= len(self._cab):
                try:
                    self._cab = self._cola.popleft()
                except IndexError:
                    self._cab = None
                    break
                self._ic = 0
            tomar = min(n - k, len(self._cab) - self._ic)
            trozo = self._cab[self._ic:self._ic + tomar]
            self._ic += tomar
            if salida is None:
                if tomar == n:                            # caso normal: sin copiar
                    self.consumidos += n
                    return trozo
                salida = np.empty((n, 2), dtype=np.float32)
            salida[k:k + tomar] = trozo
            k += tomar
        self.consumidos += k
        return VACIO if salida is None else salida[:k]

    def cerrar(self) -> None:
        self._cerrar = True
        self._matar()


class FuenteMemoria:
    """Audio ya sintetizado (los tonos DTMF de un CUE)."""

    def __init__(self, datos: np.ndarray):
        self._d = np.ascontiguousarray(datos, dtype=np.float32)
        self._i = 0
        self.total = len(self._d)
        self.error = ""
        self.fin_lectura = True

    def preparar(self) -> None:
        pass

    def lista(self) -> bool:
        return True

    @property
    def agotada(self) -> bool:
        return self._i >= len(self._d)

    def leer(self, n: int, bloquear: bool = False) -> np.ndarray:
        trozo = self._d[self._i:self._i + n]
        self._i += len(trozo)
        return trozo

    def cerrar(self) -> None:
        pass
