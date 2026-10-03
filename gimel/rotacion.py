# -*- coding: utf-8 -*-
"""
Rotacion: en que orden van saliendo los audios de cada carpeta o lista.

En aleatorio es una baraja: cada audio sale una vez por vuelta, y hasta que no
han salido todos no se repite ninguno. Las vueltas se barajan por adelantado
(siempre hay al menos dos preparadas) y se guardan en disco, asi que cerrar el
programa no reinicia la rotacion y lo que se anuncia como "a continuacion" no
cambia de un momento a otro.

El planificador puede sacar una cancion de mas adentro de la cola para cuadrar
la hora; eso solo la adelanta, no la repite: se quita de su vuelta y las demas
siguen en su sitio.

En secuencial se sigue el orden de la lista y solo se recuerda la ultima.
"""

import json
import os
import random
from collections import deque


class Rotacion:
    def __init__(self, ruta_json: str):
        self.ruta = ruta_json
        self.e = {}
        self._sucio = False
        try:
            with open(ruta_json, "r", encoding="utf-8") as fh:
                d = json.load(fh)
            if isinstance(d, dict):
                self.e = d
        except Exception:
            self.e = {}

    @staticmethod
    def clave(origen: str, orden: str) -> str:
        return os.path.normcase(os.path.abspath(origen)) + "|" + orden

    def _estado(self, clave: str) -> dict:
        st = self.e.get(clave)
        if not isinstance(st, dict):
            st = self.e[clave] = {}
        st.setdefault("ciclos", [])
        st.setdefault("conocidas", [])
        st.setdefault("rec", [])
        st.setdefault("ult", "")
        return st

    def cola(self, origen: str, orden: str, rutas: list, artista=None,
             separar: int = 3, minimo: int = 150) -> list:
        """El orden en que saldran los proximos audios (con repeticiones si hay pocos)."""
        if not rutas:
            return []
        clave = self.clave(origen, orden)
        st = self._estado(clave)
        if orden == "secuencial":
            try:
                i = rutas.index(st["ult"]) + 1
            except ValueError:
                i = 0
            vuelta = rutas[i:] + rutas[:i]
            res = list(vuelta)
            while len(res) < minimo:
                res += vuelta
            return res

        conj = set(rutas)
        if conj != set(st["conocidas"]):
            conocidas = set(st["conocidas"])
            ciclos = [[r for r in c if r in conj] for c in st["ciclos"]]
            ciclos = [c for c in ciclos if c]
            for r in rutas:                               # lo nuevo entra en todas las vueltas
                if r not in conocidas:
                    for c in ciclos:
                        c.insert(random.randint(0, len(c)), r)
            st["ciclos"] = ciclos
            st["conocidas"] = sorted(conj)
            self._sucio = True
        total = sum(len(c) for c in st["ciclos"])
        while (total < minimo or len(st["ciclos"]) < 2) and len(st["ciclos"]) < 400:
            previas = [r for c in st["ciclos"][-1:] for r in c] or st["rec"]
            c = self._barajar(rutas, previas, artista, separar)
            st["ciclos"].append(c)
            total += len(c)
            self._sucio = True
        return [r for c in st["ciclos"] for r in c]

    @staticmethod
    def _barajar(rutas: list, previas: list, artista, separar: int) -> list:
        """
        Una vuelta nueva. Las ultimas de la vuelta anterior no pueden caer al
        principio de esta, y se procura no juntar al mismo artista.
        """
        pend = list(rutas)
        random.shuffle(pend)
        # la segunda mitad de la vuelta anterior no cae en la primera de esta:
        # entre dos pases de un mismo audio hay como poco media carpeta
        k = len(rutas) // 2
        evitar = set(previas[-k:]) if k else set()
        ultimos = deque(maxlen=max(0, separar))
        if artista and separar > 0:
            for r in previas[-separar:]:
                ultimos.append(artista(r))
        res = []
        while pend:
            elegido = None
            respaldo = None
            for i, r in enumerate(pend[:40]):
                if len(res) < k and r in evitar:
                    continue
                if respaldo is None:
                    respaldo = i
                a = artista(r) if artista else ""
                if a and a in ultimos:
                    continue
                elegido = i
                break
            if elegido is None:
                elegido = respaldo if respaldo is not None else 0
            r = pend.pop(elegido)
            res.append(r)
            if artista and separar > 0:
                ultimos.append(artista(r))
        return res

    def consumir(self, origen: str, orden: str, ruta: str) -> None:
        """Este audio ya ha salido al aire."""
        st = self._estado(self.clave(origen, orden))
        if orden == "secuencial":
            st["ult"] = ruta
        else:
            for c in st["ciclos"]:
                if ruta in c:
                    c.remove(ruta)
                    break
            st["ciclos"] = [c for c in st["ciclos"] if c]
        st["rec"].append(ruta)
        del st["rec"][:-300]
        self._sucio = True

    def vuelta(self, origen: str, orden: str) -> list:
        """Lo que queda por salir de la vuelta en curso (vacio en secuencial)."""
        ciclos = self._estado(self.clave(origen, orden))["ciclos"]
        return list(ciclos[0]) if ciclos and orden != "secuencial" else []

    def recientes(self, origen: str, orden: str) -> list:
        return list(self._estado(self.clave(origen, orden))["rec"])

    def guardar(self) -> None:
        if not self._sucio:
            return
        self._sucio = False
        tmp = self.ruta + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.e, fh, ensure_ascii=False)
            os.replace(tmp, self.ruta)
        except OSError:
            self._sucio = True
