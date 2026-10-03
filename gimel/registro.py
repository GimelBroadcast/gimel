# -*- coding: utf-8 -*-
"""
Registro de emision: una linea por cada audio que sale al aire, con su hora
real. Un fichero CSV por dia en datos/registro (sirve de certificado de las
cunas emitidas). Las ultimas lineas se guardan tambien en memoria para la
interfaz.
"""

import csv
import os
import threading
from collections import deque
from datetime import datetime

from .idioma import N_

CABECERA = ("fecha", "hora", "tipo", "titulo", "artista", "segundos", "nota", "fichero")

# El fichero se escribe siempre en español, este el programa en el idioma que
# este: un registro con los tipos en dos idiomas no habria quien lo filtrara.
# Las interfaces traducen el tipo al ensenarlo.
NOMBRES = {"cancion": N_("Canción"), "jingle": N_("Jingle"), "senal": N_("Señal horaria"),
           "evento": N_("Evento"), "cuna": N_("Cuña"), "relleno": N_("Relleno"),
           "jingle_publi": N_("Jingle de bloque"), "cue": N_("CUE"), "silencio": N_("Silencio"),
           "sistema": N_("Sistema")}


class Registro:
    def __init__(self, carpeta: str = ""):
        self.carpeta = carpeta
        self.ultimas = deque(maxlen=500)
        self._lock = threading.Lock()
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

    def escribir(self, cuando: float, tipo: str, titulo: str = "", artista: str = "",
                 segundos: float = 0.0, nota: str = "", fichero: str = "") -> None:
        d = datetime.fromtimestamp(cuando)
        fila = (d.strftime("%Y-%m-%d"), d.strftime("%H:%M:%S.") + "%03d" % (d.microsecond // 1000),
                NOMBRES.get(tipo, tipo), titulo, artista, "%.1f" % segundos, nota, fichero)
        self.ultimas.append({"t": cuando, "tipo": tipo, "titulo": titulo, "artista": artista,
                             "dur": segundos, "nota": nota})
        if not self.carpeta:
            return
        ruta = os.path.join(self.carpeta, d.strftime("%Y-%m-%d") + ".csv")
        with self._lock:
            try:
                nuevo = not os.path.exists(ruta)
                with open(ruta, "a", encoding="utf-8-sig", newline="") as fh:
                    w = csv.writer(fh, delimiter=";")
                    if nuevo:
                        w.writerow(CABECERA)
                    w.writerow(fila)
            except OSError:
                pass                                      # disco lleno o fichero abierto en Excel: se sigue emitiendo

    def dias(self) -> list:
        """Fechas (AAAA-MM-DD) de las que hay registro, de la mas reciente a la mas antigua."""
        if not self.carpeta:
            return []
        try:
            return sorted((f[:-4] for f in os.listdir(self.carpeta) if f.endswith(".csv")),
                          reverse=True)
        except OSError:
            return []

    def leer(self, fecha: str, limite: int = 5000) -> list:
        """Las lineas de un dia, como dicts con las claves de CABECERA."""
        if not self.carpeta or not fecha.replace("-", "").isdigit():
            return []
        ruta = os.path.join(self.carpeta, fecha + ".csv")
        try:
            with open(ruta, "r", encoding="utf-8-sig", newline="") as fh:
                filas = list(csv.DictReader(fh, delimiter=";"))
        except OSError:
            return []
        return filas[-limite:]
