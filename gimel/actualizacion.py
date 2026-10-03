# -*- coding: utf-8 -*-
"""
Actualizacion desde GitHub.

Las versiones de GIMEL se publican como «releases» de su repositorio
(gimel.REPOSITORIO), cada una con su instalador, gimel-setup.exe. Actualizar es:

  1. ultima()     preguntar a GitHub cual es la ultima publicada
  2. descargar()  bajar su instalador, comprobando que llega entero (el tamano
                  y, cuando GitHub la da, su huella SHA-256)
  3. instalar()   lanzarlo con /S: Windows pide permiso de administrador y el
                  instalador espera a que GIMEL se cierre, cambia el programa
                  y lo vuelve a abrir

Aqui no hay ventanas ni audio: quien llama (el menu Ayuda de la ventana, o
`main.py --actualizacion`) decide cuando, y pregunta lo que haya que preguntar.

Para publicar una version: subir el numero en gimel/__init__.py, compilar
(herramientas/compilar.py) y crear en GitHub una release con la etiqueta
v<numero> y dist/gimel-setup.exe adjunto, con ese nombre.
"""

import ctypes
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import REPOSITORIO, __version__, rutas
from .idioma import tr

API = "https://api.github.com/repos/%s/releases/latest" % REPOSITORIO
DESCARGAS = "https://github.com/%s/releases/download/" % REPOSITORIO     # de ningun otro sitio se baja nada
INSTALADOR = "gimel-setup.exe"
LISTA = "instalado.json"              # lo deja el instalador junto al programa
MARCA = "reanudar_emision"            # en la carpeta de datos: se estaba emitiendo al actualizar
AGENTE = {"User-Agent": "GIMEL/%s" % __version__, "Accept": "application/vnd.github+json"}


class Error(Exception):
    """Algo que contarle al usuario tal cual."""


class Cancelada(Exception):
    pass


@dataclass
class Version:
    version: str                      # "1.2"
    pagina: str                       # la de la release, para verla en el navegador
    instalador: str = ""              # de donde bajar gimel-setup.exe ("" si la release no lo trae)
    tamano: int = 0
    sha256: str = ""                  # "" si GitHub no la da
    notas: str = ""


def numeros(version: str) -> tuple:
    """'v1.2.0' -> (1, 2): para comparar versiones (los ceros del final no cuentan)."""
    partes = []
    for trozo in version.strip().lstrip("vV").split("."):
        digitos = "".join(c for c in trozo if c.isdigit())
        if not digitos:
            break
        partes.append(int(digitos))
    while partes and partes[-1] == 0:
        partes.pop()
    return tuple(partes)


def es_nueva(v: Version) -> bool:
    return numeros(v.version) > numeros(__version__)


def ultima(espera: float = 15.0):
    """La ultima version publicada, o None si aun no hay ninguna. Lanza Error si no se puede saber."""
    try:
        with urllib.request.urlopen(urllib.request.Request(API, headers=AGENTE), timeout=espera) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code in (403, 429):
            raise Error(tr("GitHub no admite más consultas por ahora. Prueba dentro de un rato."))
        raise Error(tr("No se ha podido consultar GitHub: %s") % e)
    except (OSError, ValueError) as e:
        raise Error(tr("No se ha podido consultar GitHub: %s") % e)
    v = Version(version=str(d.get("tag_name") or "").strip().lstrip("vV"), pagina=str(d.get("html_url") or ""),
                notas=str(d.get("body") or ""))
    for a in d.get("assets") or []:
        url = str(a.get("browser_download_url") or "")
        if str(a.get("name") or "").lower() == INSTALADOR and url.startswith(DESCARGAS):
            v.instalador = url
            v.tamano = int(a.get("size") or 0)
            huella = str(a.get("digest") or "")
            v.sha256 = huella[7:].lower() if huella.lower().startswith("sha256:") else ""
    return v


def descargar(v: Version, carpeta: str, progreso=None, cancelar=None) -> str:
    """
    Baja el instalador de `v` a `carpeta` y devuelve su ruta. `progreso`
    recibe de 0 a 1; si `cancelar()` dice que si, se deja y lanza Cancelada.
    Lanza Error si no llega o no llega entero.
    """
    if not v.instalador.startswith(DESCARGAS):
        raise Error(tr("Esa versión no trae instalador."))
    destino = os.path.join(carpeta, "gimel-setup-%s.exe" % ".".join(str(n) for n in numeros(v.version)))
    parte = destino + ".parte"
    huella = hashlib.sha256()
    hecho = 0
    try:
        with urllib.request.urlopen(urllib.request.Request(v.instalador, headers={"User-Agent": AGENTE["User-Agent"]}),
                                    timeout=30) as r, open(parte, "wb") as fh:
            total = v.tamano or int(r.headers.get("Content-Length") or 0)
            while True:
                if cancelar is not None and cancelar():
                    raise Cancelada()
                trozo = r.read(262144)
                if not trozo:
                    break
                fh.write(trozo)
                huella.update(trozo)
                hecho += len(trozo)
                if progreso is not None and total:
                    progreso(min(1.0, hecho / total))
        if (v.tamano and hecho != v.tamano) or (v.sha256 and huella.hexdigest() != v.sha256):
            raise Error(tr("La descarga no ha llegado entera. Vuelve a intentarlo."))
        os.replace(parte, destino)
    except (OSError, ValueError) as e:
        raise Error(tr("No se ha podido descargar: %s") % e)
    finally:
        try:
            os.remove(parte)
        except OSError:
            pass
    return destino


def instalada() -> str:
    """
    La carpeta del programa, si esta copia la puso el instalador (que es
    quien sabe cambiarla por otra); si no (se usa desde el codigo, o es una
    carpeta copiada a mano), "".
    """
    if not getattr(sys, "frozen", False):
        return ""
    carpeta = rutas.raiz()
    return carpeta if os.path.isfile(os.path.join(carpeta, LISTA)) else ""


def _elevado(programa: str, argumentos: str) -> int:
    """Lanza un programa pidiendo permiso de administrador. Mas de 32 es que ha arrancado."""
    return ctypes.windll.shell32.ShellExecuteW(None, "runas", programa, argumentos, None, 1)


def instalar(instalador: str, carpeta: str) -> None:
    """
    Lanza el instalador descargado para que actualice `carpeta` sin preguntar
    y vuelva a abrir GIMEL. Vuelve en cuanto el instalador ha arrancado (se
    queda esperando a que GIMEL se cierre: hay que cerrarlo acto seguido).
    Lanza Error si no se le da el permiso de administrador.
    """
    r = _elevado(instalador, '/S /ARRANCAR "/D=%s"' % carpeta.rstrip("\\"))
    if r <= 32:
        if r == 5:
            raise Error(tr("Sin permiso de administrador no se puede actualizar. No se ha cambiado nada."))
        raise Error(tr("No se ha podido lanzar el instalador (código %d).") % r)


# ---------------------------------------------------------------- reanudar la emision

def marcar_reanudar(datos: str) -> None:
    """Se estaba emitiendo al actualizar: que al volver a abrirse, siga."""
    try:
        with open(os.path.join(datos, MARCA), "w", encoding="utf-8") as fh:
            fh.write("%.3f" % time.time())
    except OSError:
        pass


def reanudar(datos: str, vale: float = 600.0) -> bool:
    """
    Si hay que empezar emitiendo porque se cerro, emitiendo, para actualizar.
    La marca se gasta al leerla y caduca a los diez minutos: una actualizacion
    que no llego a acabar no pone la emisora en el aire dias despues.
    """
    ruta = os.path.join(datos, MARCA)
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            cuando = float(fh.read().strip() or 0)
        os.remove(ruta)
    except (OSError, ValueError):
        return False
    return -60.0 <= time.time() - cuando <= vale          # con holgura por si el reloj se ha ajustado entre medias

