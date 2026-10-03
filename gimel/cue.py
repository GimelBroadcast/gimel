# -*- coding: utf-8 -*-
"""
CUE de desconexion y de reconexion, y titulo en emision.

Un CUE es un aviso a otro sistema: "me voy a publicidad, dura tanto" y "ya
vuelvo". Se manda a tantos servidores como haya configurados, cada uno a su
manera:

    http      POST del mensaje a una URL (GET si el mensaje esta vacio)
    tcp       el mensaje, una linea, a host:puerto
    udp       el mensaje en un datagrama a host:puerto
    archivo   el mensaje escrito en un fichero
    dtmf      los digitos del mensaje como tonos dentro del propio audio

El emisor los programa con unos segundos de antelacion y con la hora de reloj
exacta a la que tocan; un hilo espera a esa hora y los lanza. Cada envio va en
su propio hilo: un servidor caido no retrasa a los demas ni a la emision.

Variables de los mensajes: {evento} {emisora} {bloque} {duracion} {contenido}
{silencio} {hora} {fecha} {epoch}. `evento` vale break en el CUE de desconexion
y endbreak en el de reconexion, este el programa en el idioma que este;
`duracion` es lo que va de uno a otro; `contenido`, lo que duran las cunas.
"""

import heapq
import itertools
import os
import re
import socket
import threading
import time
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime

import numpy as np

from .config import CUE_BREAK, CUE_ENDBREAK
from .idioma import tr

_RE_VAR = re.compile(r"\{(\w+)\}")
_ESCAPES = {"\\n": "\n", "\\r": "\r", "\\t": "\t"}


def numero(x: float) -> str:
    """60 -> '60', 63.364 -> '63.364'."""
    s = "%.3f" % x
    return s.rstrip("0").rstrip(".") if "." in s else s


def variables(evento: str, cuando: float, **mas) -> dict:
    d = datetime.fromtimestamp(cuando)
    v = {"evento": evento, "hora": d.strftime("%H:%M:%S.") + "%03d" % (d.microsecond // 1000),
         "fecha": d.strftime("%Y-%m-%d"), "epoch": "%.3f" % cuando}
    for k, x in mas.items():
        v[k] = numero(x) if isinstance(x, float) else str(x)
    return v


def componer(plantilla: str, datos: dict, url: bool = False) -> str:
    """Sustituye las {variables} conocidas; lo demas (las llaves de un JSON) se deja como esta."""
    def cambio(m):
        k = m.group(1)
        if k not in datos:
            return m.group(0)
        return urllib.parse.quote(datos[k], safe="") if url else datos[k]
    texto = _RE_VAR.sub(cambio, plantilla)
    if not url:
        for a, b in _ESCAPES.items():
            texto = texto.replace(a, b)
    return texto


def _host_puerto(destino: str):
    host, _, puerto = destino.strip().rpartition(":")
    return host.strip("[]") or "127.0.0.1", int(puerto)


def enviar(tipo: str, destino: str, texto: str, datos: dict) -> str:
    """Un envio. Devuelve un resumen del resultado; lanza excepcion si falla."""
    if tipo == "http":
        url = componer(destino, datos, url=True)
        if texto.strip():
            json_ = texto.lstrip()[:1] in "{["
            req = urllib.request.Request(
                url, data=texto.encode("utf-8"), method="POST",
                headers={"Content-Type": "application/json" if json_ else "text/plain; charset=utf-8"})
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as r:
            return "HTTP %d" % r.status
    if tipo == "tcp":
        with socket.create_connection(_host_puerto(destino), timeout=3) as s:
            s.sendall(texto.encode("utf-8") + (b"" if texto.endswith("\n") else b"\n"))
        return tr("enviado")
    if tipo == "udp":
        host, puerto = _host_puerto(destino)
        familia = socket.AF_INET6 if ":" in host else socket.AF_INET
        with socket.socket(familia, socket.SOCK_DGRAM) as s:
            s.sendto(texto.encode("utf-8"), (host, puerto))
        return tr("enviado")
    if tipo == "archivo":
        tmp = destino + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(texto)
        os.replace(tmp, destino)
        return tr("escrito")
    raise ValueError(tr("tipo de destino desconocido: %s") % tipo)


# ---------------------------------------------------------------- DTMF

_DTMF_FILAS = (697.0, 770.0, 852.0, 941.0)
_DTMF_COLS = (1209.0, 1336.0, 1477.0, 1633.0)
_DTMF_TECLAS = "123A456B789C*0#D"


def tonos_dtmf(texto: str, fs: int = 48000, nivel: float = 0.25,
               tono: float = 0.08, pausa: float = 0.06) -> np.ndarray:
    """Los digitos de `texto` como tonos DTMF (estereo). Lo que no sea tecla se ignora."""
    n_t, n_p = int(tono * fs), int(pausa * fs)
    t = np.arange(n_t) / float(fs)
    borde = np.minimum(1.0, np.minimum(np.arange(n_t), np.arange(n_t)[::-1]) / (0.004 * fs))
    trozos = []
    for ch in texto.upper():
        i = _DTMF_TECLAS.find(ch)
        if i < 0:
            continue
        s = (np.sin(2 * np.pi * _DTMF_FILAS[i // 4] * t)
             + np.sin(2 * np.pi * _DTMF_COLS[i % 4] * t)) * (nivel / 2.0) * borde
        trozos.append(s)
        trozos.append(np.zeros(n_p))
    if not trozos:
        return np.zeros((0, 2), dtype=np.float32)
    mono = np.concatenate(trozos).astype(np.float32)
    return np.stack([mono, mono], axis=1)


# ---------------------------------------------------------------- envio

class Cues:
    def __init__(self, cfg_cue, simulado: bool = False):
        self.cfg = cfg_cue
        self.simulado = simulado
        self.programados = []             # simulacion: (cuando, evento, datos)
        self.enviados = deque(maxlen=100)  # para la interfaz
        self._monton = []
        self._seq = itertools.count()
        self._cond = threading.Condition()
        self._salir = False
        if not simulado:
            threading.Thread(target=self._bucle, daemon=True, name="cues").start()

    def configurar(self, cfg_cue) -> None:
        self.cfg = cfg_cue

    def cerrar(self) -> None:
        with self._cond:
            self._salir = True
            self._cond.notify()

    def programar(self, cuando: float, evento: str, datos: dict) -> None:
        """Lanzar el CUE `evento` (inicio | retorno) a la hora de reloj `cuando`."""
        if self.simulado:
            self.programados.append((cuando, evento, datos))
            return
        with self._cond:
            heapq.heappush(self._monton, (cuando, next(self._seq), evento, datos))
            self._cond.notify()

    def _bucle(self) -> None:
        while True:
            with self._cond:
                while not self._monton and not self._salir:
                    self._cond.wait()
                if self._salir:
                    return
                cuando = self._monton[0][0]
                falta = cuando - time.time()
                if falta > 0.03:
                    self._cond.wait(min(falta - 0.03, 0.5))
                    continue
                _, _, evento, datos = heapq.heappop(self._monton)
            if falta > 0:
                time.sleep(falta)                         # los ultimos milisegundos, afinando
            self.emitir(evento, datos)

    def emitir(self, evento: str, datos: dict) -> None:
        for d in list(self.cfg.destinos):
            if d.activo and d.tipo != "dtmf":
                threading.Thread(target=self._enviar, args=(d, evento, datos),
                                 daemon=True, name="cue").start()

    def _enviar(self, d, evento: str, datos: dict) -> None:
        texto = componer(d.inicio if evento == "inicio" else d.retorno, datos)
        resultado = ""
        intentos = 1 + (max(0, int(self.cfg.reintentos)) if d.tipo in ("http", "tcp") else 0)
        for i in range(intentos):
            try:
                resultado = enviar(d.tipo, d.destino, texto, datos)
                break
            except Exception as e:
                resultado = "ERROR: %s" % e
                time.sleep(0.25)
        self.enviados.append({"hora": time.time(), "evento": evento, "nombre": d.nombre,
                              "destino": d.destino, "tipo": d.tipo, "texto": texto,
                              "resultado": resultado})

    def probar(self, d, evento: str = "inicio") -> str:
        """Envio de prueba a un destino, ahora mismo. Devuelve el resultado."""
        datos = variables(CUE_BREAK if evento == "inicio" else CUE_ENDBREAK, time.time(),
                          emisora="PRUEBA", bloque="Prueba", duracion=60.0, contenido=60.0,
                          silencio=5.0)
        if d.tipo == "dtmf":
            return tr("los tonos DTMF solo salen en emisión")
        try:
            texto = componer(d.inicio if evento == "inicio" else d.retorno, datos)
            return enviar(d.tipo, d.destino, texto, datos)
        except Exception as e:
            return "ERROR: %s" % e


class Titulo:
    """Lo que suena, a un fichero de texto o a una URL (para el RDS o el streaming)."""

    def __init__(self, cfg_meta):
        self.cfg = cfg_meta
        self.ultimo = ""
        self.extra = None                 # funcion(texto): Icecast tambien lo quiere

    def configurar(self, cfg_meta) -> None:
        self.cfg = cfg_meta

    def anunciar(self, tipo: str, titulo: str, artista: str, emisora: str) -> None:
        c = self.cfg
        datos = {"titulo": titulo, "artista": artista, "emisora": emisora, "tipo": tipo}
        if tipo == "cancion":
            texto = componer(c.plantilla or "{artista} - {titulo}", datos).strip(" -")
        elif c.solo_canciones or not c.texto_resto:
            return
        else:
            texto = componer(c.texto_resto, datos)
        if texto == self.ultimo:
            return
        self.ultimo = texto
        if self.extra is not None:
            try:
                self.extra(texto)
            except Exception:
                pass
        if c.activo:
            threading.Thread(target=self._sacar, args=(texto,), daemon=True, name="titulo").start()

    def _sacar(self, texto: str) -> None:
        c = self.cfg
        try:
            if c.archivo:
                enviar("archivo", c.archivo, texto, {})
        except Exception:
            pass
        try:
            if c.url:
                enviar("http", c.url, "", {"texto": texto})
        except Exception:
            pass
