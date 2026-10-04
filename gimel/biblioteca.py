# -*- coding: utf-8 -*-
"""
Biblioteca: que ficheros hay en cada carpeta o lista, y su analisis.

Nada de aqui bloquea a quien pregunta. `listar` y `pista` contestan al momento
con lo que ya se sabe (o None si aun no se sabe) y dejan el trabajo encargado:
las carpetas las recorre un hilo y los analisis los hacen otros, con ffmpeg a
prioridad baja para no molestar a la emision. Una carpeta en un NAS lento o
una biblioteca de miles de canciones sin analizar no paran nada: simplemente
van entrando en juego segun estan listas.
"""

import itertools
import os
import queue
import re
import threading
import time

from .analisis import CacheAnalisis, Pista, analizar
from .rutas import es_audio, es_lista


def _natural(ruta: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", ruta)]


def leer_lista(ruta: str) -> list:
    """Entradas de una lista .m3u/.m3u8/.pls, en su orden."""
    base = os.path.dirname(os.path.abspath(ruta))
    with open(ruta, "rb") as fh:
        crudo = fh.read()
    try:
        texto = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = crudo.decode("cp1252", "replace")
    pls = ruta.lower().endswith(".pls")
    res = []
    for linea in texto.splitlines():
        l = linea.strip()
        if not l or l.startswith("#"):
            continue
        if pls:
            if not (l.lower().startswith("file") and "=" in l):
                continue
            l = l.split("=", 1)[1].strip()
        if "://" in l[:12]:                               # emisoras por internet: no
            continue
        if not os.path.isabs(l):
            l = os.path.join(base, l)
        l = os.path.normpath(l)
        if es_audio(l):
            res.append(l)
    return res


class Biblioteca:
    REFRESCO = 60.0               # cada cuanto se vuelve a mirar una carpeta

    def __init__(self, carpeta_datos: str, ffmpeg: str, hilos: int = 0):
        self.ffmpeg = ffmpeg
        self.cache = CacheAnalisis(os.path.join(carpeta_datos, "analisis.db"))
        self.cambios = 0              # sube cuando un origen gana o pierde ficheros y cuando acaba un analisis
        self._dudosos = set()         # origenes que tenian audios y en la ultima pasada han salido vacios
        self._listas = {}             # clave del origen -> (momento, [rutas])
        self._stat = {}               # ruta -> (tamano, fecha)
        self._mem = {}                # ruta -> Pista, ya contrastada con el fichero
        self._neg = {}                # ruta -> (momento, Pista con error): ficheros que no estan
        self._cola = queue.PriorityQueue()
        self._pend = {}               # ruta -> prioridad encargada
        self._seq = itertools.count()
        self._lock = threading.Lock()
        self._escaneos = queue.Queue()
        self._escaneando = set()
        self._salir = False
        self.hechas = 0               # analisis terminados en esta sesion
        n = hilos or max(1, min(4, (os.cpu_count() or 2) // 2))
        self._hilos = [threading.Thread(target=self._analizador, daemon=True,
                                        name="analisis-%d" % i) for i in range(n)]
        self._hilos.append(threading.Thread(target=self._escaner, daemon=True,
                                            name="escaner"))
        for h in self._hilos:
            h.start()

    def cerrar(self) -> None:
        self._salir = True
        self._escaneos.put(None)
        for _ in self._hilos:
            self._cola.put((-1, next(self._seq), None))
        self.cache.cerrar()

    # ------------------------------------------------------------ ficheros

    @staticmethod
    def clave(origen: str) -> str:
        return os.path.normcase(os.path.abspath(origen))

    def listar(self, origen: str, esperar: float = 0.0):
        """
        Ficheros de una carpeta (con subcarpetas), una lista o un fichero
        suelto. None si aun no se ha podido mirar.
        """
        if not origen:
            return []
        clave = self.clave(origen)
        e = self._listas.get(clave)
        if e is None or time.monotonic() - e[0] > self.REFRESCO:
            with self._lock:
                if clave not in self._escaneando:
                    self._escaneando.add(clave)
                    self._escaneos.put((clave, origen))
        if e is None and esperar > 0:
            limite = time.monotonic() + esperar
            while clave not in self._listas and time.monotonic() < limite:
                time.sleep(0.02)
            e = self._listas.get(clave)
        return e[1] if e else None

    def _escaner(self) -> None:
        while not self._salir:
            trabajo = self._escaneos.get()
            if trabajo is None:
                return
            clave, origen = trabajo
            viejo = self._listas.get(clave)
            try:
                rutas = self._recorrer(origen)
            except Exception:
                rutas = []
            if viejo is not None and viejo[1] and not rutas and clave not in self._dudosos:
                # tenia audios y de pronto ninguno: puede ser un disco de red que no
                # contesta. No se da por vacio hasta que lo este dos pasadas seguidas
                self._dudosos.add(clave)
                rutas = viejo[1]
            else:
                self._dudosos.discard(clave)
            self._listas[clave] = (time.monotonic(), rutas)
            with self._lock:
                self._escaneando.discard(clave)
                if viejo is not None and viejo[1] != rutas:
                    self.cambios += 1                     # han anadido o quitado ficheros
            for r in rutas:                               # lo que falte por analizar, sin prisa
                if r not in self._mem:
                    self.pista(r)

    def _recorrer(self, origen: str) -> list:
        rutas = []
        if os.path.isdir(origen):
            pila = [origen]
            while pila:
                carpeta = pila.pop()
                try:
                    with os.scandir(carpeta) as it:
                        for ent in it:
                            if ent.is_dir():
                                pila.append(ent.path)
                            elif es_audio(ent.name):
                                try:
                                    st = ent.stat()
                                except OSError:
                                    continue
                                self._anotar(ent.path, st.st_size, st.st_mtime_ns)
                                rutas.append(ent.path)
                except OSError:
                    continue
            rutas.sort(key=_natural)
        elif es_lista(origen) and os.path.isfile(origen):
            for r in leer_lista(origen):
                try:
                    st = os.stat(r)
                except OSError:
                    continue
                self._anotar(r, st.st_size, st.st_mtime_ns)
                rutas.append(r)
        elif es_audio(origen) and os.path.isfile(origen):
            st = os.stat(origen)
            self._anotar(origen, st.st_size, st.st_mtime_ns)
            rutas.append(origen)
        return rutas

    def _anotar(self, ruta: str, tam: int, fecha: int) -> None:
        viejo = self._stat.get(ruta)
        if viejo is not None and viejo != (tam, fecha):
            self._mem.pop(ruta, None)                     # lo han cambiado: a reanalizar
        self._stat[ruta] = (tam, fecha)

    # ------------------------------------------------------------ analisis

    def pista(self, ruta: str, urgente: bool = False):
        """La Pista de un fichero, o None si aun se esta analizando."""
        p = self._mem.get(ruta)
        if p is not None:
            return p
        st = self._stat.get(ruta)
        if st is None:                                    # fichero suelto que nadie ha listado
            neg = self._neg.get(ruta)
            if neg is not None and time.monotonic() - neg[0] < 5.0:
                return neg[1]
            try:
                s = os.stat(ruta)
            except OSError:
                p = Pista(ruta=ruta, error="no existe el fichero")
                self._neg[ruta] = (time.monotonic(), p)
                return p
            st = (s.st_size, s.st_mtime_ns)
            self._stat[ruta] = st
        p = self.cache.buscar(ruta, st[0], st[1])
        if p is not None:
            self._mem[ruta] = p
            return p
        self._encargar(ruta, 0 if urgente else 5)
        return None

    def _encargar(self, ruta: str, prioridad: int) -> None:
        with self._lock:
            ya = self._pend.get(ruta)
            if ya is not None and ya <= prioridad:
                return
            self._pend[ruta] = prioridad
        self._cola.put((prioridad, next(self._seq), ruta))

    def _analizador(self) -> None:
        while not self._salir:
            prioridad, _, ruta = self._cola.get()
            if ruta is None:
                return
            with self._lock:
                if self._pend.get(ruta) != prioridad:     # ya hecha, o reencargada con mas prisa
                    continue
            try:
                p = analizar(self.ffmpeg, ruta)
            except Exception as e:
                p = Pista(ruta=ruta, error=str(e)[:300])
            if self._salir:
                return
            st = self._stat.get(ruta)
            if st is None:
                try:
                    s = os.stat(ruta)
                    st = (s.st_size, s.st_mtime_ns)
                except OSError:
                    st = (0, 0)
            try:
                self.cache.guardar(p, st[0], st[1])
            except Exception:
                pass
            self._mem[ruta] = p
            with self._lock:
                self._pend.pop(ruta, None)
                self.cambios += 1                         # ya se puede contar con el
            self.hechas += 1

    def pendientes(self) -> int:
        return len(self._pend)

    def pendiente(self, origen: str) -> bool:
        """Aun no se sabe lo que hay en ese origen, o esta a medio analizar."""
        if not origen:
            return False
        rutas = self.listar(origen)
        if rutas is None:
            return True
        return any(r not in self._mem for r in rutas[:60])

    def conocida(self, ruta: str):
        """La Pista si ya esta analizada; no encarga nada."""
        return self._mem.get(ruta)

    def resumen(self, origen: str) -> dict:
        """Para la interfaz: cuantos ficheros hay, cuantos analizados y cuanto duran."""
        rutas = self.listar(origen)
        if rutas is None:
            return {"leyendo": True, "ficheros": 0, "analizados": 0, "errores": 0, "segundos": 0.0}
        hechos = errores = 0
        total = 0.0
        for r in rutas:
            p = self._mem.get(r)
            if p is None:
                continue
            if p.error:
                errores += 1
            else:
                hechos += 1
                total += p.largo
        return {"leyendo": False, "ficheros": len(rutas), "analizados": hechos,
                "errores": errores, "segundos": total}
