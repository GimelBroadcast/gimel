#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compila GIMEL para Windows con PyInstaller.

    python herramientas/compilar.py                    # dist/GIMEL/ y dist/gimel-setup.exe
    python herramientas/compilar.py --sin-instalador   # solo la carpeta del programa
    python herramientas/compilar.py --sin-ffmpeg       # sin ffmpeg.exe dentro

dist/GIMEL/ es el programa en una carpeta: GIMEL.exe, _internal/, ffmpeg.exe
y desinstalar.exe. dist/gimel-setup.exe es el instalador
(instalador/instalador.py) con esa carpeta dentro, en carga.zip.

El ffmpeg que se mete es el que haya junto a main.py o, si no, el del PATH
(siguiendo el enlace si es el de WinGet), siempre que se pueda redistribuir:
uno compilado con --enable-nonfree se rechaza.

El instalador y el desinstalador son el mismo programa: con carga.zip dentro
instala y sin ella desinstala. Los dos llevan en su manifiesto que piden
permiso de administrador.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(RAIZ, "dist")
OBRA = os.path.join(RAIZ, "build")
ICONO = os.path.join(RAIZ, "recursos", "gimel.ico")
INSTALADOR = os.path.join(RAIZ, "instalador", "instalador.py")


def paso(texto: str) -> None:
    print("\n== %s" % texto, flush=True)


def pyinstaller(args: list) -> None:
    orden = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
             "--distpath", DIST, "--workpath", OBRA, "--specpath", OBRA] + args
    subprocess.run(orden, check=True, cwd=RAIZ)


def buscar_ffmpeg() -> str:
    junto = os.path.join(RAIZ, "ffmpeg.exe")
    if os.path.isfile(junto):
        return junto
    r = shutil.which("ffmpeg")
    return os.path.realpath(r) if r else ""


def redistribuible(ffmpeg: str) -> None:
    r = subprocess.run([ffmpeg, "-hide_banner", "-buildconf"], capture_output=True, text=True, errors="replace")
    if "--enable-nonfree" in r.stdout:
        raise SystemExit("Ese ffmpeg esta compilado con --enable-nonfree: no se puede redistribuir.")


def comprimir(carpeta: str, destino: str) -> None:
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for raiz, _, ficheros in os.walk(carpeta):
            for f in ficheros:
                ruta = os.path.join(raiz, f)
                z.write(ruta, os.path.relpath(ruta, carpeta))


def tamano(ruta: str) -> str:
    if os.path.isfile(ruta):
        n = os.path.getsize(ruta)
    else:
        n = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(ruta) for f in fs)
    return "%.1f MB" % (n / 1048576)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compila GIMEL (PyInstaller)")
    ap.add_argument("--sin-instalador", action="store_true", help="solo dist/GIMEL/")
    ap.add_argument("--sin-ffmpeg", action="store_true", help="no meter ffmpeg.exe")
    a = ap.parse_args()

    sys.path.insert(0, RAIZ)
    from gimel import __version__
    t0 = time.monotonic()
    ffmpeg = ""
    if not a.sin_ffmpeg:
        ffmpeg = buscar_ffmpeg()
        if not ffmpeg:
            raise SystemExit("No se encuentra ffmpeg (o usa --sin-ffmpeg).")
        redistribuible(ffmpeg)

    programa = os.path.join(DIST, "GIMEL")
    for d in (programa, OBRA):
        shutil.rmtree(d, ignore_errors=True)
    for f in ("gimel-setup.exe", "desinstalar.exe"):
        if os.path.exists(os.path.join(DIST, f)):
            os.remove(os.path.join(DIST, f))

    paso("GIMEL %s: el programa" % __version__)
    pyinstaller(["--name", "GIMEL", "--onedir", "--windowed", "--icon", ICONO,
                 "--add-data", "%s%s%s" % (os.path.join(RAIZ, "gimel", "web", "estatico"), os.pathsep,
                                           "gimel/web/estatico"),
                 "--hidden-import", "gimel.ui.ventana", "--hidden-import", "gimel.web.servidor",
                 "--exclude-module", "tkinter", "--exclude-module", "matplotlib",
                 os.path.join(RAIZ, "main.py")])
    if ffmpeg:
        shutil.copy2(ffmpeg, os.path.join(programa, "ffmpeg.exe"))

    paso("El desinstalador")
    pyinstaller(["--name", "desinstalar", "--onefile", "--windowed", "--uac-admin", "--icon", ICONO, INSTALADOR])
    os.replace(os.path.join(DIST, "desinstalar.exe"), os.path.join(programa, "desinstalar.exe"))
    print("dist/GIMEL: %s" % tamano(programa))

    if not a.sin_instalador:
        paso("El instalador")
        os.makedirs(OBRA, exist_ok=True)
        carga = os.path.join(OBRA, "carga.zip")
        version = os.path.join(OBRA, "version.txt")
        comprimir(programa, carga)
        with open(version, "w", encoding="utf-8") as fh:
            fh.write(__version__)
        print("carga.zip: %s" % tamano(carga))
        pyinstaller(["--name", "gimel-setup", "--onefile", "--windowed", "--uac-admin", "--icon", ICONO,
                     "--add-data", "%s%s." % (carga, os.pathsep),
                     "--add-data", "%s%s." % (version, os.pathsep),
                     "--add-data", "%s%s." % (os.path.join(RAIZ, "LICENSE"), os.pathsep),
                     INSTALADOR])
        print("dist/gimel-setup.exe: %s" % tamano(os.path.join(DIST, "gimel-setup.exe")))
    shutil.rmtree(OBRA, ignore_errors=True)
    print("\nHecho en %.0f s." % (time.monotonic() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
