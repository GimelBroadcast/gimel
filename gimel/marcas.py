# -*- coding: utf-8 -*-
"""
Marcas de intro: hasta que segundo de cada cancion se puede hablar encima
antes de que entre la voz (el "talk-over" de los automatizadores).

No hay forma fiable de saberlo escuchando el audio, asi que se marca a mano:
pulsando «Marcar intro» justo cuando entra la voz, con la cancion en antena o
en la preescucha, o escribiendo los segundos. Se guardan en datos/marcas.json
y valen para todo el programa: la pagina de emision, las listas auxiliares y
la pantalla de locutor ensenan la cuenta atras de la intro.
"""

import json
import os
import threading


class Marcas:
    def __init__(self, ruta: str = ""):
        self.ruta = ruta
        self._d = {}
        self._lock = threading.Lock()
        if ruta:
            try:
                with open(ruta, "r", encoding="utf-8") as fh:
                    d = json.load(fh)
                if isinstance(d, dict):
                    self._d = {str(k): v for k, v in d.items() if isinstance(v, dict)}
            except (OSError, ValueError):
                pass

    @staticmethod
    def _clave(ruta: str) -> str:
        return os.path.normcase(os.path.abspath(ruta)) if ruta and "://" not in ruta else ruta

    def intro(self, ruta: str) -> float:
        """Segundos de intro (desde el principio de lo que suena), o 0 si no esta marcada."""
        if not ruta:
            return 0.0
        m = self._d.get(self._clave(ruta))
        try:
            return float(m.get("intro", 0.0)) if m else 0.0
        except (TypeError, ValueError):
            return 0.0

    def poner_intro(self, ruta: str, segundos: float) -> None:
        segundos = max(0.0, round(float(segundos), 1))
        with self._lock:
            k = self._clave(ruta)
            if segundos <= 0.05:
                self._d.get(k, {}).pop("intro", None)
                if k in self._d and not self._d[k]:
                    del self._d[k]
            else:
                self._d.setdefault(k, {})["intro"] = segundos
            self._guardar()

    def _guardar(self) -> None:
        if not self.ruta:
            return
        tmp = self.ruta + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._d, fh, ensure_ascii=False, indent=0)
            os.replace(tmp, self.ruta)
        except OSError:
            pass
