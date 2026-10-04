# -*- coding: utf-8 -*-
"""
Novedades de cada version: lo que la ventana ensena la primera vez que se abre
despues de actualizar.

Para contar un cambio se anade una linea a su version en CAMBIOS, en español y
dentro de N_(), y su traduccion en gimel/idiomas/en.py
(herramientas/comprobar_idiomas.py dice si falta). Una version nueva es una
entrada nueva, encima de las demas.

Que version se abrio la ultima vez queda apuntado en la carpeta de datos. Si es
anterior a la de ahora, se viene de actualizar: se cuentan las novedades de
todas las versiones que hay entre las dos (quien salta de la 1.0 a la 1.2 ve
tambien las de la 1.1) y se apunta la de ahora, asi que salen una sola vez.
"""

import os

from . import __version__
from .actualizacion import numeros
from .idioma import N_

MARCA = "version"                     # en la carpeta de datos: la ultima version que se abrio

CAMBIOS = (                           # de la mas nueva a la mas vieja
    ("1.1", (
        N_("Los jingles se reparten bien: suenan todos los de la carpeta o la lista antes de que "
           "se repita ninguno. Antes unos pocos salían mucho más que el resto."),
        N_("Cada franja elige el orden de sus jingles: aleatorio o secuencial."),
        N_("Las canciones y los jingles que se añaden a una carpeta o a una lista, o se quitan de "
           "ella, entran en la rotación o salen de ella en un par de minutos, sin reiniciar el "
           "programa."),
        N_("«Buscar actualizaciones» ya no da error de certificado en los equipos en los que fallaba."),
        N_("Después de actualizar, GIMEL enseña las novedades de la versión la primera vez que se abre."),
    )),
)


def pendientes(datos: str) -> list:
    """
    [(version, cambios)] que ensenar, de la mas nueva a la mas vieja; vacio si
    no se viene de una actualizacion. Deja apuntada la version de ahora.
    """
    ruta = os.path.join(datos, MARCA)
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            antes = fh.read().strip()
    except OSError:
        antes = ""
    if antes != __version__:
        try:
            with open(ruta, "w", encoding="utf-8") as fh:
                fh.write(__version__)
        except OSError:
            pass
    if not antes:
        # la 1.0 no apuntaba nada. Con una configuracion ya guardada se viene de ella;
        # sin configuracion, el programa esta recien instalado y no hay nada que contar
        antes = "1.0" if os.path.isfile(os.path.join(datos, "config.json")) else __version__
    return [(v, c) for v, c in CAMBIOS if numeros(antes) < numeros(v) <= numeros(__version__)]
