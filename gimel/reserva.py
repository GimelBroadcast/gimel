# -*- coding: utf-8 -*-
"""
Redundancia: este equipo como playout ESPEJO de otro GIMEL.

La reserva mira cada dos segundos el panel web del principal. Si deja de
contestar, o contesta pero no esta emitiendo, durante el tiempo que se diga,
la reserva empieza a emitir ella (toma el relevo). Cuando el principal vuelve
a emitir, la reserva se aparta sola (si asi se quiere).

Mientras no emite, la reserva copia la programacion del principal (franjas,
senales, bloques, eventos...) para estar lista con lo mismo; lo que es de cada
equipo (su tarjeta, su panel web, sus servidores Icecast y esta misma
configuracion de reserva) no se copia. Las carpetas de musica tienen que
verse igual desde los dos equipos (un NAS, unidades mapeadas con la misma
letra).

Lo que no hace: conmutar la salida. Los dos playouts tienen que llegar al
emisor por caminos que se puedan juntar: un conmutador de audio con
deteccion de silencio, o un punto de montaje de reserva (fallback) en Icecast.
"""

import http.cookiejar
import json
import threading
import time
import urllib.error
import urllib.request

from . import config as modconfig
from .idioma import N_, tr

PROPIO = ("salida", "web", "icecast", "reserva", "idioma", "arranque_automatico")   # lo que no se copia


class Reserva:
    def __init__(self, nucleo):
        self.nucleo = nucleo
        self.vivo = None                       # el principal contesta (None: no se ha preguntado)
        self.emite = False
        self.relevo = False                    # esta reserva esta emitiendo en su lugar
        self.detalle = ""
        self._t_bien = time.monotonic()
        self._t_copia = 0.0
        self._abridor = None
        self._url = ""
        self._salir = False
        self._hilo = None

    def arrancar_hilo(self) -> None:
        if self._hilo is None:
            self._hilo = threading.Thread(target=self._bucle, daemon=True, name="reserva")
            self._hilo.start()

    def cerrar(self) -> None:
        self._salir = True

    def _bucle(self) -> None:
        while not self._salir:
            try:
                self.paso()
            except Exception as e:
                self.detalle = str(e)
            time.sleep(2.0)

    # ------------------------------------------------------------ http

    def _pedir(self, c, ruta: str, cuerpo=None):
        base = c.principal.strip().rstrip("/")
        if "://" not in base:
            base = "http://" + base
        if self._abridor is None or self._url != base:
            self._abridor = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            self._url = base
        datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
        pet = urllib.request.Request(base + ruta, data=datos, headers={
            "Content-Type": "application/json", "X-Gimel": "1"})
        try:
            with self._abridor.open(pet, timeout=3.0) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401 and ruta != "/api/login" and c.clave:
                self._pedir(c, "/api/login", {"clave": c.clave})
                with self._abridor.open(pet, timeout=3.0) as r:
                    return json.loads(r.read().decode("utf-8"))
            raise

    # ------------------------------------------------------------ el paso

    def paso(self) -> None:
        n = self.nucleo
        c = n.cfg.reserva
        ahora = time.monotonic()
        if not c.activa or not c.principal.strip():
            self.vivo = None
            self.relevo = False
            self._t_bien = ahora
            return
        try:
            e = self._pedir(c, "/api/estado")
            self.vivo, self.emite = True, bool(e.get("emitiendo"))
            self.detalle = ""
        except Exception as ex:
            self.vivo, self.emite = False, False
            self.detalle = str(getattr(ex, "reason", "") or ex)[:200]
        emito = n.emisor.emitiendo
        if self.vivo and self.emite:
            self._t_bien = ahora
            if self.relevo and c.devolver and emito:
                n.detener()
                self.relevo = False
                n.registro.escribir(time.time(), "sistema", N_("El principal vuelve a emitir: la reserva se aparta"))
            elif not emito:
                self.relevo = False
        elif not emito and ahora - self._t_bien >= max(2.0, c.espera):
            bien, mensaje = n.iniciar()
            if bien:
                self.relevo = True
                n.registro.escribir(time.time(), "sistema", N_("El principal no emite: la reserva toma el relevo"),
                                    nota=self.detalle)
            else:
                self.detalle = mensaje
        if c.copiar and self.vivo and not n.emisor.emitiendo and ahora - self._t_copia > 60.0:
            self._t_copia = ahora
            self._copiar(c)

    def _copiar(self, c) -> None:
        r = self._pedir(c, "/api/config")
        remota = r.get("config")
        if not isinstance(remota, dict):
            return
        local = modconfig.a_dict(self.nucleo.cfg)
        nueva = dict(remota)
        for k in PROPIO:
            nueva[k] = local[k]
        # una configuracion de otra version: lo que no conozca se queda como esta aqui
        nueva = {k: nueva.get(k, local[k]) for k in local}
        if json.dumps(nueva, sort_keys=True) != json.dumps(local, sort_keys=True):
            self.nucleo.guardar_config_dict(nueva)

    def estado(self) -> dict:
        c = self.nucleo.cfg.reserva
        if not c.activa:
            return {"activa": False}
        if self.vivo is None:
            texto = tr("preguntando al principal…")
        elif self.relevo:
            texto = tr("EN RELEVO: el principal no emite y esta reserva está en antena")
        elif self.vivo and self.emite:
            texto = tr("el principal emite; esta reserva espera")
        elif self.vivo:
            texto = tr("el principal contesta pero no emite")
        else:
            texto = tr("el principal no contesta") + (" (%s)" % self.detalle if self.detalle else "")
        return {"activa": True, "relevo": self.relevo, "vivo": bool(self.vivo), "emite": self.emite,
                "texto": texto}
