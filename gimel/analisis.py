# -*- coding: utf-8 -*-
"""
Analisis de un audio: lo que hace falta saber de el para cuadrar una hora.

De cada fichero se saca, decodificandolo entero una sola vez con ffmpeg:

    dur         duracion real, contada en muestras (la de la cabecera de un
                MP3 puede mentir y aqui un segundo de error es un segundo de
                silencio antes de la senal horaria)
    cue_in      donde empieza a sonar de verdad (se salta el silencio inicial)
    cue_out     donde deja de sonar
    perfil      a que altura del final cae el nivel -3, -6 ... -36 dB por debajo
                del de la cancion: de ahi sale el punto de mezcla, que es donde
                puede entrar lo siguiente sin que se pisen
    lufs        sonoridad (BS.1770) para igualar el volumen de unas y otras
    pico        pico de muestra, para no saturar al normalizar

El resultado se guarda en SQLite; un fichero solo se vuelve a analizar si
cambia de tamano o de fecha.
"""

import json
import os
import re
import sqlite3
import subprocess
import threading
from dataclasses import dataclass

import numpy as np

from .rutas import PRIORIDAD_BAJA, SIN_VENTANA

VERSION = 2                    # subirla obliga a reanalizar toda la biblioteca
FS = 24_000                    # basta para medir niveles y es el doble de rapido
VENTANA = 240                  # 10 ms
SUB = 2400                     # 100 ms: subbloque de la medida de sonoridad
UMBRALES = (-3.0, -6.0, -9.0, -12.0, -15.0, -18.0, -21.0, -24.0, -30.0, -36.0)
NIVEL_INICIO = 10 ** (-48 / 20)
NIVEL_FINAL = 10 ** (-50 / 20)


@dataclass(frozen=True)
class Pista:
    ruta: str
    dur: float = 0.0
    cue_in: float = 0.0
    cue_out: float = 0.0
    perfil: tuple = ()
    lufs: float = -70.0
    pico: float = 0.0
    artista: str = ""
    titulo: str = ""
    error: str = ""

    @property
    def largo(self) -> float:
        """Lo que suena, de cue_in a cue_out."""
        return max(0.0, self.cue_out - self.cue_in)

    def mezcla(self, umbral: float = -15.0, solape_max: float = 8.0) -> float:
        """
        Punto del fichero (s) en que puede arrancar lo siguiente: la ultima
        vez que el nivel estuvo a 'umbral' dB del de la cancion. Una que acaba
        en seco da practicamente cue_out; una que se va apagando, bastante antes.
        """
        if not self.perfil:
            return self.cue_out
        xs = UMBRALES[::-1]                               # crecientes para interp
        ys = self.perfil[::-1]
        t = float(np.interp(umbral, xs, ys))
        t = min(t, self.cue_out)
        t = max(t, self.cue_out - max(0.0, solape_max))
        return max(t, self.cue_in + min(5.0, self.largo / 2.0))

    def nombre(self) -> str:
        if self.artista and self.titulo:
            return "%s - %s" % (self.artista, self.titulo)
        return self.titulo or os.path.splitext(os.path.basename(self.ruta))[0]

    def ganancia_db(self, objetivo: float) -> float:
        """dB que hay que darle para dejarla en 'objetivo' LUFS sin saturar."""
        if self.lufs <= -60.0:
            return 0.0
        g = objetivo - self.lufs
        if self.pico > 1e-4:
            g = min(g, -20.0 * np.log10(self.pico) - 0.5)
        return float(max(-24.0, min(12.0, g)))


# ---------------------------------------------------------------- sonoridad

def _pesos_k(n: int, fs: int) -> np.ndarray:
    """
    Ponderacion K de BS.1770 aplicada en frecuencia: |H(f)|^2 de los dos
    filtros de la norma, mas el factor de Parseval para que la suma sobre los
    bins de una rfft de n puntos de directamente la potencia media.
    """
    f = np.fft.rfftfreq(n, 1.0 / fs)
    w = 2.0 * np.pi * f / 48000.0                 # la norma da los coeficientes a 48 kHz
    z1 = np.exp(-1j * w)
    z2 = z1 * z1
    h1 = ((1.53512485958697 - 2.69169618940638 * z1 + 1.19839281085285 * z2)
          / (1.0 - 1.69065929318241 * z1 + 0.73248077421585 * z2))
    h2 = ((1.0 - 2.0 * z1 + z2)
          / (1.0 - 1.99004745483398 * z1 + 0.99007225036621 * z2))
    p = np.abs(h1 * h2) ** 2
    c = np.full(len(f), 2.0)
    c[0] = 1.0
    if n % 2 == 0:
        c[-1] = 1.0
    return (p * c / float(n) ** 2).astype(np.float32)


_PESOS = _pesos_k(SUB, FS)


def _lufs(z: np.ndarray) -> float:
    """Sonoridad integrada con las dos puertas de la norma. z: potencia K por subbloque de 100 ms."""
    if len(z) < 4:
        m = float(z.mean()) if len(z) else 0.0
        return -0.691 + 10.0 * np.log10(m) if m > 1e-12 else -70.0
    c = np.cumsum(np.concatenate(([0.0], z.astype(np.float64))))
    bloques = (c[4:] - c[:-4]) / 4.0                      # 400 ms, solapados al 75 %
    vivos = bloques[bloques > 10 ** ((-70.0 + 0.691) / 10.0)]
    if not len(vivos):
        return -70.0
    relativa = vivos.mean() * 0.1                         # -10 LU
    vivos = vivos[vivos > relativa]
    if not len(vivos):
        return -70.0
    return float(-0.691 + 10.0 * np.log10(vivos.mean()))


# ---------------------------------------------------------------- etiquetas

_RE_ETIQUETA = re.compile(r"^\s{4,}([A-Za-z_][\w\- ]*?)\s*:\s(.*)$")


def _etiquetas(texto: str):
    """Titulo y artista del volcado que ffmpeg hace de la entrada."""
    titulo = artista = ""
    dentro = False
    for linea in texto.splitlines():
        if linea.startswith("Input #0"):
            dentro = True
            continue
        if linea.startswith(("Output #0", "Stream mapping")):
            break
        if not dentro:
            continue
        m = _RE_ETIQUETA.match(linea)
        if not m:
            continue
        clave, valor = m.group(1).strip().lower(), m.group(2).strip()
        if clave == "title" and not titulo:
            titulo = valor
        elif clave == "artist" and not artista:
            artista = valor
    return titulo, artista


def _del_nombre(ruta: str):
    """'Artista - Titulo.mp3' cuando el fichero no trae etiquetas."""
    base = os.path.splitext(os.path.basename(ruta))[0]
    if " - " in base:
        a, t = base.split(" - ", 1)
        a = re.sub(r"^\d+[\s.\-_]+", "", a).strip()       # numero de pista delante
        return t.strip(), a
    return base, ""


# ---------------------------------------------------------------- analisis

def analizar(ffmpeg: str, ruta: str, baja_prioridad: bool = True) -> Pista:
    """Decodifica el fichero entero y devuelve su Pista (con .error si no se pudo)."""
    orden = [ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-i", ruta,
             "-map", "0:a:0", "-vn", "-sn", "-dn",
             "-ac", "2", "-ar", str(FS), "-f", "s16le", "pipe:1"]
    try:
        proc = subprocess.Popen(
            orden, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            creationflags=SIN_VENTANA | (PRIORIDAD_BAJA if baja_prioridad else 0))
    except OSError as e:
        return Pista(ruta=ruta, error="no se pudo lanzar ffmpeg: %s" % e)

    # stderr se vacia aparte: si se llena su tuberia, ffmpeg se queda parado
    errores = []
    hilo = threading.Thread(target=lambda: errores.append(proc.stderr.read()), daemon=True)
    hilo.start()

    picos, medias, zs = [], [], []
    total = 0
    pend = np.zeros((0, 2), dtype=np.float32)
    resto = b""
    try:
        while True:
            b = proc.stdout.read(FS * 4)                  # 1 s de audio
            if not b:
                break
            if resto:
                b = resto + b
            sobra = len(b) % 4
            resto = b[len(b) - sobra:] if sobra else b""
            x = np.frombuffer(b, dtype="<i2", count=(len(b) - sobra) // 2)
            x = x.reshape(-1, 2).astype(np.float32) * (1.0 / 32768.0)
            total += len(x)
            if len(pend):
                x = np.concatenate([pend, x])
            nb = len(x) // SUB
            if nb:
                trozo = x[:nb * SUB]
                v = trozo.reshape(nb * (SUB // VENTANA), VENTANA, 2)
                picos.append(np.abs(v).max(axis=(1, 2)))
                medias.append((v * v).mean(axis=(1, 2)))
                esp = np.fft.rfft(trozo.reshape(nb, SUB, 2), axis=1)
                pot = esp.real ** 2 + esp.imag ** 2
                zs.append((pot * _PESOS[None, :, None]).sum(axis=(1, 2)))
            pend = x[nb * SUB:]
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        hilo.join(timeout=5)

    texto = (errores[0] if errores else b"").decode("utf-8", "replace")
    if total == 0:
        motivo = [l for l in texto.splitlines() if l.strip()]
        return Pista(ruta=ruta, error=(motivo[-1].strip() if motivo else "sin audio")[:300])

    if len(pend):                                         # el pico final, de menos de 100 ms
        falta = (-len(pend)) % VENTANA
        if falta:
            pend = np.concatenate([pend, np.zeros((falta, 2), dtype=np.float32)])
        v = pend.reshape(-1, VENTANA, 2)
        picos.append(np.abs(v).max(axis=(1, 2)))
        medias.append((v * v).mean(axis=(1, 2)))

    picos = np.concatenate(picos)
    medias = np.concatenate(medias)
    z = np.concatenate(zs) if zs else np.zeros(0, dtype=np.float32)
    dur = total / float(FS)
    paso = VENTANA / float(FS)

    titulo, artista = _etiquetas(texto)
    if not titulo:
        titulo, a2 = _del_nombre(ruta)
        artista = artista or a2

    suena = np.flatnonzero(picos > NIVEL_INICIO)
    if not len(suena):                                    # fichero mudo
        return Pista(ruta=ruta, dur=dur, cue_in=0.0, cue_out=dur,
                     perfil=tuple(dur for _ in UMBRALES), lufs=-70.0, pico=0.0,
                     artista=artista, titulo=titulo)
    cue_in = max(0.0, suena[0] * paso - paso)
    acaba = np.flatnonzero(picos > NIVEL_FINAL)
    cue_out = min(dur, (acaba[-1] + 1) * paso + 0.04)

    # nivel suavizado a 300 ms y, de referencia, el de los pasajes fuertes
    n_suave = 30
    suave = np.convolve(medias, np.ones(n_suave) / n_suave, mode="same")
    db = 10.0 * np.log10(np.maximum(suave, 1e-10))
    i0, i1 = int(cue_in / paso), max(int(cue_in / paso) + 1, int(cue_out / paso))
    ref = float(np.percentile(db[i0:i1], 90))
    perfil = []
    for u in UMBRALES:
        sobre = np.flatnonzero(db >= ref + u)
        t = (sobre[-1] + 1) * paso if len(sobre) else cue_out
        perfil.append(float(min(max(t, cue_in), cue_out)))

    return Pista(ruta=ruta, dur=dur, cue_in=float(cue_in), cue_out=float(cue_out),
                 perfil=tuple(perfil), lufs=_lufs(z), pico=float(picos.max()),
                 artista=artista, titulo=titulo)


# ---------------------------------------------------------------- cache

class CacheAnalisis:
    """Los analisis ya hechos, en SQLite. Se carga entera en memoria al abrir."""

    def __init__(self, ruta_db: str):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(ruta_db, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS pistas ("
                         "ruta TEXT PRIMARY KEY, tam INTEGER, fecha INTEGER, "
                         "version INTEGER, datos TEXT)")
        self._db.commit()
        self.mem = {}                 # ruta -> (tam, fecha, Pista)
        for ruta, tam, fecha, version, datos in self._db.execute(
                "SELECT ruta, tam, fecha, version, datos FROM pistas"):
            if version != VERSION:
                continue
            try:
                d = json.loads(datos)
                d["perfil"] = tuple(d.get("perfil", ()))
                self.mem[ruta] = (tam, fecha, Pista(ruta=ruta, **d))
            except Exception:
                continue

    def buscar(self, ruta: str, tam: int, fecha: int):
        e = self.mem.get(ruta)
        if e is not None and e[0] == tam and e[1] == fecha:
            return e[2]
        return None

    def guardar(self, p: Pista, tam: int, fecha: int) -> None:
        d = {"dur": p.dur, "cue_in": p.cue_in, "cue_out": p.cue_out,
             "perfil": list(p.perfil), "lufs": p.lufs, "pico": p.pico,
             "artista": p.artista, "titulo": p.titulo, "error": p.error}
        self.mem[p.ruta] = (tam, fecha, p)
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO pistas VALUES (?,?,?,?,?)",
                             (p.ruta, tam, fecha, VERSION, json.dumps(d, ensure_ascii=False)))
            self._db.commit()

    def cerrar(self) -> None:
        with self._lock:
            try:
                self._db.close()
            except Exception:
                pass
