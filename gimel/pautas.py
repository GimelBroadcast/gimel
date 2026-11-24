# -*- coding: utf-8 -*-
"""
Pautas importadas: la musica o la publicidad que manda un programa de
planificacion (MusicMaster, Selector, Powergold, el de trafico de la
publicidad) en vez de la rotacion de GIMEL.

Esos programas exportan la pauta del dia en un fichero de texto con una linea
por audio. Cada uno lo hace a su manera y casi todos dejan configurar las
columnas, asi que aqui no se espera un formato concreto: de cada linea se saca
la HORA (HH:MM o HH:MM:SS, si la trae; si no, vale la ultima vista), la FECHA
(si la trae) y el AUDIO, que puede ser

    una ruta completa             D:\\Musica\\Artista - Titulo.mp3
    un nombre de fichero          Artista - Titulo.mp3   (se busca en la carpeta de audios)
    un numero de cartucho         004512                 (el fichero cuyo nombre empieza por el)

Lo importado se deja en una carpeta, un .m3u8 por hora (musica) o por corte de
publicidad (hora y minuto del bloque):

    2026-11-24 14.m3u8          la musica de las 14 a las 15
    2026-11-24 14-30.m3u8       las cunas del bloque de las 14:30

Una franja con orden «Pauta importada» y esa carpeta como origen toca cada
hora la lista que le corresponde, en su orden (si no hay, tira de la
programacion general). Un bloque de publicidad con orden «Pauta importada»
hace lo mismo con su corte. GIMEL sigue cuadrando la hora: si la pauta trae
mas musica de la que cabe, las ultimas no entran; si trae menos, se completa
con la general.

El certificado de emision de lo importado sale del registro (ver
gimel/certificado.py): cada cuna emitida queda alli con su hora real.
"""

import os
import re
from datetime import date, datetime

from .biblioteca import _natural
from .idioma import tr
from .rutas import EXT_AUDIO, es_audio

_HORA = re.compile(r"(?<![\d:])([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?(?![\d:])")
_FECHAS = (
    (re.compile(r"(?<!\d)(20\d\d)[-/.](\d\d?)[-/.](\d\d?)(?!\d)"), "amd"),
    (re.compile(r"(?<!\d)(\d\d?)[-/.](\d\d?)[-/.](20\d\d)(?!\d)"), "dma"),
)
_FECHA_NOMBRE = (
    (re.compile(r"(?<!\d)(20\d\d)(\d\d)(\d\d)(?!\d)"), "amd"),
    (re.compile(r"(?<!\d)(\d\d)(\d\d)(\d\d)(?!\d)"), "amd2"),      # AAMMDD
)
_EXT = "|".join(e.lstrip(".") for e in EXT_AUDIO)
_RUTA = re.compile(r"((?:[A-Za-z]:|\\\\[^\\/;,\t|\"]+)[\\/][^;\t|\"]*?\.(?:%s))(?=$|[;,\t|\"\s])" % _EXT, re.I)
_NOMBRE = re.compile(r"([^;\t|\"\\/]+?\.(?:%s))(?=$|[;,\t|\"])" % _EXT, re.I)
_CARTUCHO = re.compile(r"(?<![\d:.\-/])(\d{3,8})(?![\d:.\-/])")


def nombre_hora(dia: date, hora: int) -> str:
    return "%s %02d.m3u8" % (dia.isoformat(), hora)


def nombre_corte(dia: date, hora: int, minuto: int) -> str:
    return "%s %02d-%02d.m3u8" % (dia.isoformat(), hora, minuto)


def archivo_hora(carpeta: str, h0: float) -> str:
    """La pauta importada de la hora que empieza en h0, o "" si no la hay."""
    d = datetime.fromtimestamp(h0 + 1)
    ruta = os.path.join(carpeta, nombre_hora(d.date(), d.hour))
    return ruta if os.path.isfile(ruta) else ""


def archivo_corte(carpeta: str, h0: float, minuto: int) -> str:
    d = datetime.fromtimestamp(h0 + 1)
    ruta = os.path.join(carpeta, nombre_corte(d.date(), d.hour, minuto))
    return ruta if os.path.isfile(ruta) else ""


def _fecha(texto: str, patrones):
    for rx, forma in patrones:
        m = rx.search(texto)
        if not m:
            continue
        try:
            a, b, c = (int(x) for x in m.groups())
            if forma == "amd":
                return date(a, b, c)
            if forma == "dma":
                return date(c, b, a)
            if forma == "amd2":
                return date(2000 + a, b, c)
        except ValueError:
            continue
    return None


class Cartuchos:
    """Los audios de una carpeta, por nombre de fichero y por el numero con que empieza."""

    def __init__(self, carpeta: str):
        self.por_nombre = {}
        self.por_numero = {}
        if not carpeta or not os.path.isdir(carpeta):
            return
        for raiz, _, ficheros in os.walk(carpeta):
            for f in sorted(ficheros, key=_natural):
                if not es_audio(f):
                    continue
                ruta = os.path.join(raiz, f)
                self.por_nombre.setdefault(f.lower(), ruta)
                m = re.match(r"\s*0*(\d+)", f)
                if m:
                    self.por_numero.setdefault(m.group(1), ruta)

    def buscar(self, linea: str) -> str:
        m = _RUTA.search(linea)
        if m:
            return os.path.normpath(m.group(1).strip())
        m = _NOMBRE.search(linea)
        if m:
            nombre = os.path.basename(m.group(1).strip())
            if nombre.lower() in self.por_nombre:
                return self.por_nombre[nombre.lower()]
        sin_horas = _HORA.sub(" ", linea)
        for m in _CARTUCHO.finditer(sin_horas):
            r = self.por_numero.get(m.group(1).lstrip("0") or "0")
            if r:
                return r
        return ""


def leer(ruta: str, fecha=None, carpeta_audios: str = ""):
    """
    Las entradas de un fichero de pauta: [(fecha, hora, minuto, segundo, ruta)].
    Devuelve tambien las lineas que traian audio pero no se ha encontrado.
    """
    with open(ruta, "rb") as fh:
        crudo = fh.read()
    try:
        texto = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = crudo.decode("cp1252", "replace")
    dia = fecha or _fecha(os.path.basename(ruta), _FECHA_NOMBRE) or date.today()
    cart = Cartuchos(carpeta_audios)
    entradas, perdidas = [], []
    h = m = s = None
    for linea in texto.splitlines():
        l = linea.strip()
        if not l or l.startswith("#"):
            continue
        f = _fecha(l, _FECHAS)
        if f is not None and fecha is None:
            dia = f
        mh = _HORA.search(l)
        if mh:
            h, m, s = int(mh.group(1)), int(mh.group(2)), int(mh.group(3) or 0)
        audio = cart.buscar(l)
        if not audio:
            if _NOMBRE.search(l) or (_CARTUCHO.search(_HORA.sub(" ", l)) and carpeta_audios):
                perdidas.append(l)
            continue
        if h is None:
            perdidas.append(l)
            continue
        entradas.append((dia, h, m, s, audio))
    return entradas, perdidas


def importar(ruta: str, destino: str, tipo: str = "musica", fecha=None, carpeta_audios: str = "") -> str:
    """
    Convierte un fichero de pauta en las listas por hora (musica) o por corte
    (publicidad) de `destino`. Devuelve un resumen para ensenar. Lanza
    excepcion si el fichero no se puede leer o no trae nada.
    """
    entradas, perdidas = leer(ruta, fecha, carpeta_audios)
    if not entradas:
        raise ValueError(tr("En ese fichero no hay ninguna línea con hora y audio."))
    os.makedirs(destino, exist_ok=True)
    grupos = {}
    for dia, h, m, s, audio in entradas:
        clave = nombre_hora(dia, h) if tipo == "musica" else nombre_corte(dia, h, m)
        grupos.setdefault(clave, []).append((h, m, s, audio))
    for nombre, filas in grupos.items():
        lineas = ["#EXTM3U", "# " + tr("Pauta importada de %s") % os.path.basename(ruta)]
        for h, m, s, audio in filas:
            lineas.append("#GIMEL-HORA:%02d:%02d:%02d" % (h, m, s))
            lineas.append(audio)
        tmp = os.path.join(destino, nombre + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lineas) + "\n")
        os.replace(tmp, os.path.join(destino, nombre))
    faltan = sum(1 for *_, a in entradas if not os.path.isfile(a))
    texto = tr("%d audios en %d listas (%s).") % (
        len(entradas), len(grupos), tr("una por hora") if tipo == "musica" else tr("una por corte"))
    if faltan:
        texto += " " + tr("%d no están en el disco.") % faltan
    if perdidas:
        texto += " " + tr("%d líneas sin audio reconocible.") % len(perdidas)
    return texto
