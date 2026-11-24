# -*- coding: utf-8 -*-
"""
Prueba de las funciones de directo que no son las listas auxiliares:
detector de silencio, salida propia de una lista, enlace con la cadena
(network join), pautas importadas, certificado de emision, grabaciones con
ingesta, logger de antena, reserva (playout espejo) y marcas de intro.

Todo sin tarjeta y sin oir nada (motor simulado, servidores falsos).

    python herramientas/prueba_funciones.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gimel import config as C                                # noqa: E402
from gimel import pautas, rutas                              # noqa: E402
from gimel.certificado import html_certificado               # noqa: E402
from gimel.fuentes import FuenteDirecto, FuenteMemoria       # noqa: E402
from gimel.grabaciones import Grabaciones                    # noqa: E402
from gimel.marcas import Marcas                              # noqa: E402
from gimel.motor import Voz                                  # noqa: E402
from gimel.planificador import AnclaAudio, Planificador, hora_en_punto   # noqa: E402
from gimel.registro import Registro                          # noqa: E402
from gimel.reserva import Reserva                            # noqa: E402
from prueba_auxiliares import FS, NIVEL_AUX, Banco, comprobar, escribir_tono, FALLOS   # noqa: E402

FFMPEG = rutas.buscar_ffmpeg()


def esperar(cond, segundos=20.0) -> bool:
    limite = time.monotonic() + segundos
    while not cond() and time.monotonic() < limite:
        time.sleep(0.05)
    return cond()


def duracion_de(ruta: str) -> float:
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", ruta, "-f", "null", "-"], capture_output=True, text=True,
                       errors="replace")
    import re
    t = re.findall(r"time=(\d+):(\d+):([\d.]+)", r.stderr)
    if not t:
        return 0.0
    h, m, s = t[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


class SurtidorVacio:
    def cola(self, *a, **k):
        return []

    def vuelta(self, *a):
        return []

    def pista(self, ruta):
        return None

    def pendiente(self, origen):
        return False


def main() -> int:
    from gimel.biblioteca import Biblioteca
    base = tempfile.mkdtemp(prefix="gimel-func-")
    try:
        audios = os.path.join(base, "audios")
        emergencia = os.path.join(base, "emergencia")
        os.makedirs(audios)
        os.makedirs(emergencia)
        for i in range(3):
            escribir_tono(os.path.join(emergencia, "reserva %d.wav" % i), 6.0, 300 + 100 * i)
        largo = os.path.join(audios, "largo.wav")
        escribir_tono(largo, 10.0, 440)
        datos = os.path.join(base, "datos")
        os.makedirs(datos)
        bib = Biblioteca(datos, FFMPEG)
        for r in [largo] + [os.path.join(emergencia, f) for f in os.listdir(emergencia)]:
            bib.pista(r, urgente=True)
        esperar(lambda: bib.pendientes() == 0, 60)

        # ------------------------------------------------------------------ 1
        print("\n1. Detector de silencio: la principal se calla, entra la emergencia, vuelve y se retira")
        k = Banco(datos, bib)
        cfg = C.Config()
        cfg.silencio.activo = True
        cfg.silencio.segundos = 4.0
        cfg.silencio.vuelta = 2.0
        cfg.silencio.origen = emergencia
        k.aux.cfg = lambda: cfg
        k.motor.ordenes.clear()                           # fuera la principal de 600 s del banco (aun en la cola)
        corta = np.zeros((FS * 3, 2), dtype=np.float32)
        corta[:, 0] = 0.25
        k.motor.orden("voz", Voz(FuenteMemoria(corta), k.motor.m))
        k.correr(6.0)
        comprobar(not k.aux._emergencia, "a los 3 s de silencio aún no salta")
        k.correr(2.5)
        comprobar(k.aux._emergencia, "a los ~4 s de silencio entra la lista de emergencia")
        comprobar(k.tramo(k.ahora() - 1.0, k.ahora())[:, 1].min() > 0.3 * NIVEL_AUX, "y suena")
        vuelta = np.zeros((FS * 30, 2), dtype=np.float32)
        vuelta[:, 0] = 0.25
        k.motor.orden("voz", Voz(FuenteMemoria(vuelta), k.motor.m))
        k.correr(1.0)
        comprobar(k.aux._emergencia, "con la principal de vuelta, espera un poco antes de retirarse")
        k.correr(5.0)                                     # 2 s de espera + 2 s de fundido, y margen
        comprobar(not k.aux._emergencia and k.tramo(k.ahora() - 1.0, k.ahora())[:, 1].max() < 1e-4,
                  "se retira con su fundido al volver la principal")

        # ------------------------------------------------------------------ 2
        print("\n2. Una lista por su propia tarjeta (canal de la mesa): no sale por la emisión")
        k = Banco(datos, bib)
        k.emisor.emitiendo = False
        k.accion(accion="anadir", lista=2, rutas=[largo])
        k.accion(accion="ajustes", lista=2, campos={"salida": "Windows WASAPI|Mesa canal 3"})
        k.accion(accion="reproducir", lista=2)
        propio = k.aux._salidas["Windows WASAPI|Mesa canal 3"][0]
        picos = []
        propio.sonda = lambda f, buf: picos.append(np.abs(buf).max(axis=0))
        for _ in range(int(3.0 * FS / 1024)):
            k.aux.paso()
            k.motor.avanzar()
            propio.avanzar()
        comprobar(max(p[1] for p in picos[20:]) > 0.3 * NIVEL_AUX, "suena por su tarjeta aunque no se emita")
        comprobar(k.tramo(0.0, k.ahora())[:, 1].max() < 1e-4, "y no por la de la emisión")

        # ------------------------------------------------------------------ 3
        print("\n3. Enlace con la cadena: el directo no se adelanta y dura exacto")
        rampa = os.path.join(audios, "rampa.wav")
        n = FS * 10
        import wave
        x = np.zeros((n, 2))
        x[:, 0] = x[:, 1] = np.linspace(0.0, 0.5, n)      # el nivel dice por que segundo va
        with wave.open(rampa, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(FS)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        f = FuenteDirecto(FFMPEG, rampa, 3.0, FS)
        f.preparar()
        esperar(lambda: f.recibidos >= n, 10)
        primero = f.leer(1024, True)
        comprobar(primero[:, 0].mean() > 0.4,
                  "preparado de antemano, entra lo último que ha llegado (nivel %.2f de 0,5)" % primero[:, 0].mean())
        total = len(primero)
        while not f.agotada:
            total += len(f.leer(4096, False))
        f.cerrar()
        comprobar(total == 3 * FS, "da exactamente 3 s (%d frames), aunque el directo se acabe antes" % total)
        cfg = C.Config()
        ev = C.EventoFijo(nombre="Informativo de la cadena", minuto=30, tipo="enlace",
                          enlace="http://cadena.example/directo", duracion=600.0)
        cfg.eventos = [ev]
        h0 = hora_en_punto(time.time()) + 3600
        plan = Planificador(cfg, SurtidorVacio()).planificar_hora(h0, llenar=False)
        a = next((b for b in plan.bloques if isinstance(b, AnclaAudio) and b.clase == "evento"), None)
        comprobar(a is not None and abs(a.t - (h0 + 1800)) < 1e-6 and abs(a.dur - 600) < 1e-6
                  and a.piezas[0].tipo == "enlace" and a.piezas[0].suena == 600.0,
                  "en la pauta: a las y media, 600 s exactos, cortado al acabar")

        # ------------------------------------------------------------------ 4
        print("\n4. Pautas importadas (música por hora, publicidad por corte)")
        cartuchos = os.path.join(base, "cartuchos")
        os.makedirs(cartuchos)
        for nombre in ("004512 Cuna Ferreteria.wav", "004513 Cuna Panaderia.wav", "Artista - Cancion.wav"):
            escribir_tono(os.path.join(cartuchos, nombre), 1.0, 500)
        hoy = date.today()
        export = os.path.join(base, "MM%s.TXT" % hoy.strftime("%Y%m%d"))
        with open(export, "w", encoding="cp1252") as fh:
            fh.write("; exportado por el planificador\n")
            fh.write("14:00:05;M;%s;Artista - Cancion;210\n" % os.path.join(cartuchos, "Artista - Cancion.wav"))
            fh.write("14:03:35;M;Artista - Cancion.wav;Otra vez por nombre\n")
            fh.write("15:00:00|004512|CUNA FERRETERIA|20\n")
            fh.write("15:00:20|004513|CUNA PANADERIA|20\n")
            fh.write("15:00:40|999999|NO EXISTE|20\n")
        destino = os.path.join(base, "pautas")
        texto = pautas.importar(export, destino, "musica", None, cartuchos)
        hora14 = os.path.join(destino, pautas.nombre_hora(hoy, 14))
        hora15 = os.path.join(destino, pautas.nombre_hora(hoy, 15))
        from gimel.biblioteca import leer_lista
        comprobar(os.path.isfile(hora14) and len(leer_lista(hora14)) == 2, "la hora 14: dos canciones (%s)" % texto)
        comprobar(os.path.isfile(hora15) and [os.path.basename(r)[:6] for r in leer_lista(hora15)] == ["004512", "004513"],
                  "la hora 15: los cartuchos 004512 y 004513 por su número")
        h14 = datetime.combine(hoy, datetime.min.time()).timestamp() + 14 * 3600
        fr = C.Franja(canciones=destino, orden="pauta")
        r = Planificador.franja_hora(fr, h14)
        comprobar(r.canciones == hora14 and r.orden == "secuencial", "una franja con pauta toca la lista de su hora")
        comprobar(Planificador.franja_hora(fr, h14 + 5 * 3600).canciones == "", "sin pauta para esa hora: vacía (tira de la general)")
        pautas.importar(export, destino, "publicidad", None, cartuchos)
        corte = os.path.join(destino, pautas.nombre_corte(hoy, 15, 0))
        comprobar(os.path.isfile(corte) and len(leer_lista(corte)) == 2, "publicidad: el corte de las 15:00 con sus dos cuñas")

        # ------------------------------------------------------------------ 5
        print("\n5. Certificado de emisión")
        reg = Registro(os.path.join(base, "registro"))
        ayer = datetime.now() - timedelta(days=1)
        for i in range(3):
            reg.escribir(ayer.timestamp() + i * 60, "cuna", "Cuña Ferretería", "", 20.0, "", "004512.wav")
        reg.escribir(time.time(), "cuna", "Cuña Panadería", "", 20.0, "", "004513.wav")
        reg.escribir(time.time(), "cancion", "Una canción", "Artista", 200.0, "", "c.mp3")
        h = html_certificado(reg, ayer.date(), date.today(), "", "Radio Prueba")
        comprobar(h.count("<tr><td>") == 4 + 2, "cuatro pases y dos cuñas en el resumen (sin la canción)")
        h = html_certificado(reg, ayer.date(), date.today(), "ferreter", "Radio Prueba")
        comprobar("Panader" not in h and h.count("Cuña Ferretería") == 4, "con filtro, solo la ferretería")

        # ------------------------------------------------------------------ 6
        print("\n6. Grabación programada de un corresponsal, con ingesta en una lista auxiliar")
        k = Banco(datos, bib)
        cfg = C.Config()
        ahora = datetime.now()
        g = C.Grabacion(nombre="Corresponsal", hora=ahora.hour, minuto=ahora.minute, segundo=0,
                        duracion=(ahora.second + 4) / 60.0, fuente="url", url=largo,
                        carpeta=os.path.join(base, "grabaciones"), lista=2)
        cfg.grabaciones = [g]
        gr = Grabaciones(FFMPEG, k.motor, lambda: cfg, k.aux, None)
        gr.paso(time.time())
        comprobar(len(gr.en_curso) == 1, "empieza sola a su hora (abierto a mitad: graba lo que queda)")
        esperar(lambda: (gr.paso(time.time()) or not gr.en_curso), 20)
        hecha = gr.terminadas[-1] if gr.terminadas else None
        comprobar(hecha is not None and not hecha[3] and os.path.getsize(hecha[2]) > 1024,
                  "fichero grabado: %s" % (os.path.basename(hecha[2]) if hecha else "-"))
        comprobar(len(k.aux.listas[1].elementos) == 1 and k.aux.listas[1].elementos[0].ruta == hecha[2],
                  "y ha entrado en la lista auxiliar 2")
        gr.paso(time.time())
        comprobar(not gr.en_curso, "no se repite en la misma hora")

        print("\n7. Logger de antena: lo que sale al aire, a un fichero por hora")
        cfg.grabaciones = []
        cfg.logger = C.Logger(activo=True, carpeta=os.path.join(base, "logger"), bitrate=64)
        k.motor.abierta = lambda: True
        gr.paso(time.time())
        comprobar(gr.logger is not None, "empieza a grabar")
        k.motor.avanzar(int(3.0 * FS / 1024))
        fichero = gr.logger[1].destino
        gr.cerrar()
        d = duracion_de(fichero)
        comprobar(abs(d - 3.0) < 0.2, "%s con %.2f s (los 3 s que han salido)" %
                  (os.path.relpath(fichero, cfg.logger.carpeta), d))
        k.motor.tomas.remove(gr._toma)

        # ------------------------------------------------------------------ 8
        print("\n8. Reserva (playout espejo) contra un principal falso")
        principal = {"emitiendo": True, "vivo": True, "config": C.a_dict(C.Config(emisora="Radio Principal"))}

        class Principal(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if not principal["vivo"]:
                    self.connection.close()
                    return
                d = {"emitiendo": principal["emitiendo"]} if self.path == "/api/estado" else {"config": principal["config"]}
                cuerpo = json.dumps(d).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

        srv = ThreadingHTTPServer(("127.0.0.1", 0), Principal)
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        class NucleoFalso:
            def __init__(self):
                self.cfg = C.Config(emisora="Reserva")
                self.cfg.reserva = C.Reserva(activa=True, principal="127.0.0.1:%d" % srv.server_port, espera=3.0)
                self.emisor = type("E", (), {"emitiendo": False})()
                self.registro = Registro("")
                self.guardadas = 0

            def iniciar(self):
                self.emisor.emitiendo = True
                return True, ""

            def detener(self):
                self.emisor.emitiendo = False

            def guardar_config_dict(self, d):
                self.cfg = C.de_dict(C.Config, d)
                self.guardadas += 1

        nf = NucleoFalso()
        rs = Reserva(nf)
        rs.paso()
        comprobar(rs.vivo and not nf.emisor.emitiendo, "el principal emite: la reserva espera")
        comprobar(nf.cfg.emisora == "Radio Principal" and nf.cfg.reserva.activa,
                  "y copia su programación (sin pisar su propia configuración de reserva)")
        principal["vivo"] = False
        rs.paso()
        comprobar(not nf.emisor.emitiendo, "el principal deja de contestar: aún espera")
        rs._t_bien -= 3.5
        rs.paso()
        comprobar(nf.emisor.emitiendo and rs.relevo, "pasado el tiempo de espera, toma el relevo")
        principal["vivo"] = True
        rs.paso()
        comprobar(not nf.emisor.emitiendo and not rs.relevo, "el principal vuelve: la reserva se aparta")
        srv.shutdown()

        # ------------------------------------------------------------------ 9
        print("\n9. Marcas de intro")
        m = Marcas(os.path.join(datos, "marcas.json"))
        m.poner_intro(largo, 7.34)
        comprobar(abs(Marcas(os.path.join(datos, "marcas.json")).intro(largo) - 7.3) < 1e-9, "se guarda y se vuelve a leer")
        m.poner_intro(largo, 0)
        comprobar(m.intro(largo) == 0.0, "y se quita")
        bib.cerrar()
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print("\n%s" % ("TODO BIEN" if not FALLOS else "%d FALLOS" % len(FALLOS)))
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
