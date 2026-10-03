# -*- coding: utf-8 -*-
"""
Idioma de las interfaces.

El programa esta escrito en español y sus textos son a la vez la clave de la
traduccion: todo lo que lee el usuario pasa por tr() y, si el idioma elegido
lo tiene en su tabla (gimel/idiomas/<codigo>.py), sale traducido; si no, sale
tal cual. Anadir un idioma es anadir su tabla y su linea en IDIOMAS;
herramientas/comprobar_idiomas.py dice que textos le faltan.

    tr("Guardar cambios")       el texto, en el idioma de ahora
    N_("Emisión")               el texto tal cual: solo lo marca para traducirlo
                                despues, con tr(), alli donde se pinte

N_() es para las constantes de modulo (los nombres de las paginas, los tipos de
audio): se quedan en español y se traducen al pintarlas, asi que cambiar de
idioma no obliga a reiniciar. El esquema de los formularios va igual.

El idioma es uno para todo el programa (se guarda en la configuracion): lo
siguen la ventana, el panel web y los avisos de la emision.
"""

from .idiomas import en

IDIOMAS = (("es", "Español"), ("en", "English"))      # (codigo, como se llama a si mismo)

_TABLAS = {"es": {}, "en": en.TEXTOS}
_actual = "es"
_tabla = _TABLAS["es"]


def poner(codigo: str) -> str:
    """Cambia el idioma. Un codigo desconocido deja el español. Devuelve el que queda."""
    global _actual, _tabla
    _actual = codigo if codigo in _TABLAS else "es"
    _tabla = _TABLAS[_actual]
    return _actual


def actual() -> str:
    return _actual


def tabla(codigo: str = "") -> dict:
    """Los textos de un idioma (del actual, si no se dice), para el panel web."""
    return _TABLAS.get(codigo or _actual, {})


def tr(texto: str) -> str:
    return _tabla.get(texto, texto)


def N_(texto: str) -> str:
    return texto


def dias_cortos() -> tuple:
    """Las iniciales de los dias, de lunes a domingo."""
    return tuple(tr("L M X J V S D").split())
