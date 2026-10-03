# -*- coding: utf-8 -*-
"""Carpetas del programa, tipos de fichero y localizacion de ffmpeg."""

import os
import shutil
import subprocess
import sys
import tempfile

EXT_AUDIO = (".mp3", ".wav", ".flac", ".ogg", ".oga", ".opus", ".m4a", ".aac",
             ".wma", ".aif", ".aiff", ".mp2", ".ac3", ".mka", ".wv", ".ape",
             ".mp4")
EXT_LISTA = (".m3u", ".m3u8", ".pls")

# banderas de CreateProcess: que ffmpeg no abra una consola, y que el analisis
# de la biblioteca no le quite procesador a la emision
SIN_VENTANA = 0x08000000 if os.name == "nt" else 0
PRIORIDAD_BAJA = 0x00004000 if os.name == "nt" else 0


def raiz() -> str:
    """Carpeta del programa (tambien si va empaquetado con PyInstaller)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _protegida(carpeta: str) -> bool:
    """Si esta bajo Archivos de programa, donde solo escribe un administrador."""
    carpeta = os.path.normcase(os.path.abspath(carpeta)) + os.sep
    for variable in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        base = os.environ.get(variable)
        if base and carpeta.startswith(os.path.normcase(os.path.abspath(base)) + os.sep):
            return True
    return False


def carpeta_datos() -> str:
    """
    Junto al programa, salvo que alli no se pueda escribir: instalado en
    Archivos de programa los datos van a la carpeta del usuario
    (%LOCALAPPDATA%\\GIMEL\\datos), se abra el programa como se abra.
    """
    d = os.path.join(raiz(), "datos")
    if not _protegida(d):
        try:
            os.makedirs(d, exist_ok=True)
            tempfile.TemporaryFile(dir=d).close()
            return d
        except OSError:
            pass
    d = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "GIMEL", "datos")
    os.makedirs(d, exist_ok=True)
    return d


def es_audio(ruta: str) -> bool:
    return ruta.lower().endswith(EXT_AUDIO)


def es_lista(ruta: str) -> bool:
    return ruta.lower().endswith(EXT_LISTA)


def buscar_ffmpeg() -> str:
    """Primero el que venga junto al programa; si no, el del PATH."""
    nombre = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    for c in (os.path.join(raiz(), nombre), os.path.join(raiz(), "bin", nombre)):
        if os.path.isfile(c):
            return c
    return shutil.which("ffmpeg") or ""


def ffmpeg_tiene_soxr(ffmpeg: str) -> bool:
    """El remuestreador soxr suena mejor que el de serie, si esta compilado."""
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-buildconf"],
                           capture_output=True, timeout=15,
                           stdin=subprocess.DEVNULL, creationflags=SIN_VENTANA)
        return b"--enable-libsoxr" in r.stdout
    except Exception:
        return False


def subir_prioridad() -> None:
    """Prioridad 'por encima de lo normal' para que otro programa no nos corte."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x00008000)
    except Exception:
        pass
