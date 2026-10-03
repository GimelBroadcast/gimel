#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GIMEL: continuidad de radio por rotaciones horarias exactas.

    python main.py                 # ventana de escritorio (y panel web, si esta activado)
    python main.py --web           # solo el panel web, sin ventana
    python main.py --emitir        # empezar a emitir nada mas abrir
    python main.py --actualizacion # decir si hay una version nueva publicada, y salir

Cada hora se planifica de una pieza: la senal horaria en punto, los bloques de
publicidad o desconexion en su minuto y con su duracion exacta, y entre medias
la musica de la franja que toque, con las canciones elegidas y cruzadas de
forma que el tramo dure justo lo que tiene que durar.

Hay dos interfaces sobre el mismo nucleo: una de escritorio (PyQt6) y un panel
web (Flask). Si no esta PyQt6 se arranca solo con el panel web.
"""

import argparse
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def unica_instancia():
    """Dos GIMEL a la vez pisarian la misma rotacion y la misma tarjeta."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 48951))
        s.listen(1)
        return s
    except OSError:
        return None


def avisar(texto: str) -> None:
    """Por la consola; y si no la hay (el .exe no tiene), en una ventana, que si no nadie se entera."""
    print(texto)
    if sys.stdout is None and os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, texto, "GIMEL", 0x40)


def consultar_version() -> int:
    """--actualizacion: esta version y la ultima publicada. Sale con 0 si es la ultima, 10 si hay otra y 1 si no se sabe."""
    from gimel import __version__, actualizacion
    try:
        v = actualizacion.ultima()
    except actualizacion.Error as e:
        print("GIMEL %s. %s" % (__version__, e))
        return 1
    if v is None:
        print("GIMEL %s. Todavia no hay ninguna version publicada." % __version__)
    elif actualizacion.es_nueva(v):
        print("GIMEL %s. Hay una version nueva: %s (%s)" % (__version__, v.version, v.pagina))
        return 10
    else:
        print("GIMEL %s. Es la ultima version." % __version__)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="GIMEL: playout de radio por rotaciones horarias exactas")
    ap.add_argument("--web", action="store_true",
                    help="solo el panel web, sin ventana de escritorio")
    ap.add_argument("--sin-web", action="store_true", help="no abrir el panel web")
    ap.add_argument("--emitir", action="store_true", help="empezar a emitir al abrir")
    ap.add_argument("--host", default="", help="direccion en la que escucha el panel web")
    ap.add_argument("--puerto", type=int, default=0, help="puerto del panel web")
    ap.add_argument("--datos", default="",
                    help="carpeta de configuracion, analisis y registro (por defecto, ./datos)")
    ap.add_argument("--actualizacion", action="store_true",
                    help="decir si hay una version nueva publicada en GitHub, y salir")
    a = ap.parse_args()

    if a.actualizacion:
        return consultar_version()

    cerrojo = unica_instancia()
    if cerrojo is None:
        avisar("GIMEL ya esta abierto en este equipo.")
        return 1

    from gimel import actualizacion, rutas
    from gimel.nucleo import Nucleo

    rutas.subir_prioridad()
    nucleo = Nucleo(a.datos)
    if a.host:
        nucleo.cfg.web.host = a.host
    if a.puerto:
        nucleo.cfg.web.puerto = a.puerto

    web = None
    if (nucleo.cfg.web.activa or a.web) and not a.sin_web:
        try:
            from gimel.web.servidor import ServidorWeb
            web = ServidorWeb(nucleo)
            if web.arrancar():
                print("Panel web: %s" % web.url)
            else:
                print(web.error)
                web = None if not a.web else web
        except ImportError:
            print("No esta Flask (pip install flask): sin panel web.")
            web = None

    lanzar = None
    if not a.web:
        try:
            from gimel.ui.ventana import lanzar
        except ImportError as e:
            print("No esta PyQt6 (%s): se arranca solo con el panel web." % e)

    if lanzar is None and (web is None or not web.url):
        avisar("No hay ninguna interfaz disponible: instala PyQt6 o Flask "
               "(pip install -r requirements.txt).")
        nucleo.cerrar()
        return 1

    if nucleo.error:
        print(nucleo.error)
    # si se cerro emitiendo para actualizarse, al volver sigue emitiendo
    emitir = actualizacion.reanudar(nucleo.datos) or a.emitir or nucleo.cfg.arranque_automatico

    try:
        if lanzar is not None:
            return lanzar(nucleo, web, emitir)            # la ventana arranca la emision, ya montada
        if emitir:
            bien, mensaje = nucleo.iniciar()
            if mensaje:
                print(mensaje)
        print("GIMEL en marcha. Ctrl+C para salir.")
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        return 0
    finally:
        if web is not None:
            web.parar()
        nucleo.cerrar()
        cerrojo.close()


if __name__ == "__main__":
    sys.exit(main())
