# -*- coding: utf-8 -*-
"""
Panel web de GIMEL (Flask).

Hace lo mismo que la interfaz de escritorio y contra el mismo nucleo: ver lo
que suena, la pauta de la hora, arrancar, parar, saltar y tocar toda la
configuracion. Sirve para llevar la emisora desde otro equipo o para montarla
en una maquina sin pantalla.

Quien puede entrar:
  - Sin contrasena, SOLO este mismo equipo, este abierto a la red o no. Desde
    el panel se pueden ver las carpetas del disco y cambiar toda la
    configuracion: eso no se le deja a cualquiera que pase por la red.
  - Con contrasena, cualquiera que la sepa (este equipo entra sin ella).

Dos cerrojos mas, contra paginas maliciosas abiertas en el navegador de este
equipo: los POST exigen una cabecera propia (una pagina de otro sitio no puede
ponerla) y no se atiende a nombres de host que no sean una IP o este equipo.
"""

import hmac
import ipaddress
import logging
import os
import secrets
import socket
import threading

from flask import Flask, Response, jsonify, request, send_from_directory, session

from .. import config as modconfig
from .. import idioma
from ..esquema import PLANTILLAS_CUE, traducido
from ..idioma import tr

OCULTA = "********"


def crear_app(nucleo) -> Flask:
    aqui = os.path.dirname(os.path.abspath(__file__))
    estatico = os.path.join(aqui, "estatico")
    app = Flask(__name__, static_folder=estatico, static_url_path="/estatico")
    app.secret_key = secrets.token_hex(32)
    app.json.ensure_ascii = False
    equipo = socket.gethostname().lower()

    def es_local() -> bool:
        try:
            return ipaddress.ip_address(request.remote_addr or "").is_loopback
        except ValueError:
            return False

    def host_valido() -> bool:
        h = request.host.lower()
        if h.startswith("["):
            h = h[1:].split("]")[0]
        else:
            h = h.rsplit(":", 1)[0] if ":" in h else h
        if h in ("localhost", equipo):
            return True
        try:
            ipaddress.ip_address(h)
            return True
        except ValueError:
            return False

    @app.before_request
    def guardia():
        if not host_valido():
            return Response(tr("Host no admitido."), 403)
        clave = nucleo.cfg.web.clave
        if not es_local():
            if not clave:
                return Response(
                    tr("El panel de GIMEL no tiene contraseña y por eso solo atiende al propio "
                       "equipo. Ponle una en Ajustes > Panel web para entrar desde la red."), 403,
                    mimetype="text/plain; charset=utf-8")
            libre = request.path in ("/", "/api/login", "/api/textos", "/favicon.ico") or \
                request.path.startswith("/estatico/")
            if not libre and not session.get("dentro"):
                return jsonify(error="clave"), 401
        if request.method == "POST" and request.headers.get("X-Gimel") != "1":
            return Response(tr("Falta la cabecera X-Gimel."), 403)
        return None

    @app.after_request
    def cabeceras(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.get("/")
    def inicio():
        return send_from_directory(estatico, "index.html")

    @app.get("/favicon.ico")
    def icono():
        return Response(status=204)

    @app.post("/api/login")
    def login():
        clave = nucleo.cfg.web.clave
        dada = str((request.get_json(silent=True) or {}).get("clave", ""))
        if clave and hmac.compare_digest(dada.encode("utf-8"), clave.encode("utf-8")):
            session["dentro"] = True
            return jsonify(ok=True)
        return jsonify(ok=False), 401

    @app.get("/api/textos")
    def textos():
        return jsonify(idioma=idioma.actual(), textos=idioma.tabla())

    @app.get("/api/estado")
    def estado():
        return jsonify(nucleo.estado())

    @app.post("/api/emision")
    def emision():
        accion = str((request.get_json(silent=True) or {}).get("accion", ""))
        if accion == "iniciar":
            bien, mensaje = nucleo.iniciar()
            return jsonify(ok=bien, mensaje=mensaje)
        if accion == "detener":
            nucleo.detener()
        elif accion == "saltar":
            nucleo.saltar()
        elif accion == "replanificar":
            nucleo.replanificar()
        else:
            return jsonify(ok=False, mensaje=tr("acción desconocida")), 400
        return jsonify(ok=True, mensaje="")

    @app.get("/api/config")
    def leer_config():
        d = nucleo.config_dict()
        if d["web"]["clave"]:
            d["web"]["clave"] = OCULTA
        nuevo = lambda clase: modconfig.a_dict(modconfig.nuevo(clase))
        return jsonify(config=d, esquema=traducido(), plantillas_cue=PLANTILLAS_CUE,
                       salidas=nucleo.salidas(), dias=list(idioma.dias_cortos()),
                       nuevos={"franja": nuevo(modconfig.Franja),
                               "bloque": nuevo(modconfig.BloquePubli),
                               "evento": nuevo(modconfig.EventoFijo),
                               "destino_cue": nuevo(modconfig.DestinoCue),
                               "icecast": nuevo(modconfig.Icecast)})

    @app.post("/api/config")
    def guardar_config():
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            return jsonify(ok=False, mensaje=tr("configuración ilegible")), 400
        if isinstance(d.get("web"), dict) and d["web"].get("clave") == OCULTA:
            d["web"]["clave"] = nucleo.cfg.web.clave
        try:
            aviso = nucleo.guardar_config_dict(d)
        except Exception as e:
            return jsonify(ok=False, mensaje=str(e)), 400
        return jsonify(ok=True, mensaje=aviso)

    @app.get("/api/salidas")
    def salidas():
        refrescar = request.args.get("refrescar") == "1"
        return jsonify(salidas=nucleo.refrescar_salidas() if refrescar else nucleo.salidas())

    @app.get("/api/explorar")
    def explorar():
        return jsonify(nucleo.explorar(request.args.get("ruta", "")))

    @app.get("/api/origen")
    def origen():
        return jsonify(nucleo.resumen(request.args.get("ruta", "")))

    @app.post("/api/senales/auto")
    def senales_auto():
        carpeta = str((request.get_json(silent=True) or {}).get("carpeta", ""))
        return jsonify(archivos=nucleo.autosenales(carpeta))

    @app.get("/api/registro")
    def registro():
        dias = nucleo.registro.dias()
        fecha = request.args.get("fecha") or (dias[0] if dias else "")
        return jsonify(dias=dias, fecha=fecha, filas=nucleo.registro.leer(fecha) if fecha else [])

    @app.post("/api/cue/probar")
    def cue_probar():
        d = request.get_json(silent=True) or {}
        try:
            destino = modconfig.de_dict(modconfig.DestinoCue, d.get("destino") or {})
        except Exception as e:
            return jsonify(resultado="ERROR: %s" % e)
        return jsonify(resultado=nucleo.probar_cue(destino, str(d.get("evento", "inicio"))))

    return app


class ServidorWeb:
    """El panel, sirviendo en un hilo aparte."""

    def __init__(self, nucleo):
        self.nucleo = nucleo
        self._srv = None
        self.url = ""
        self.error = ""

    def arrancar(self) -> bool:
        from werkzeug.serving import make_server
        w = self.nucleo.cfg.web
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        try:
            self._srv = make_server(w.host, int(w.puerto), crear_app(self.nucleo), threaded=True)
        except Exception as e:
            self.error = tr("No se pudo abrir el panel web en %s:%s: %s") % (w.host, w.puerto, e)
            return False
        threading.Thread(target=self._srv.serve_forever, daemon=True, name="web").start()
        visible = "127.0.0.1" if w.host in ("0.0.0.0", "") else w.host
        self.url = "http://%s:%d/" % (visible, int(w.puerto))
        return True

    def parar(self) -> None:
        if self._srv is not None:
            try:
                self._srv.shutdown()
            except Exception:
                pass
            self._srv = None
