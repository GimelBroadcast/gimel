# -*- coding: utf-8 -*-
"""
Prueba de las listas auxiliares, la botonera y el nivel de la principal, con
el motor simulado (sin tarjeta, sin oir nada) y audios sinteticos.

Truco para medir: la "emision principal" suena solo por el canal IZQUIERDO y
todo lo auxiliar solo por el DERECHO. En la mezcla se ve por separado cuanto
baja la principal y cuando entra y sale cada auxiliar.

    python herramientas/prueba_auxiliares.py
"""

import os
import shutil
import sys
import tempfile
import time
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gimel import auxiliares as modaux                     # noqa: E402
from gimel import rutas                                    # noqa: E402
from gimel.auxiliares import Auxiliares                    # noqa: E402
from gimel.biblioteca import Biblioteca                    # noqa: E402
from gimel.config import Config                            # noqa: E402
from gimel.cue import Titulo                               # noqa: E402
from gimel.fuentes import FuenteMemoria                    # noqa: E402
from gimel.motor import PRINCIPAL, SISTEMA, Motor, Voz     # noqa: E402

FS = 48000
B = Motor.B
NIVEL_PRINCIPAL = 0.25
NIVEL_AUX = 0.5


def escribir_tono(ruta: str, segundos: float, hz: float, nivel: float = NIVEL_AUX) -> None:
    """Un tono solo por el canal derecho, con 20 ms de subida y final en seco."""
    n = int(segundos * FS)
    t = np.arange(n) / FS
    x = nivel * np.sin(2 * np.pi * hz * t)
    x[:960] *= np.linspace(0, 1, 960)
    est = np.zeros((n, 2))
    est[:, 1] = x
    with wave.open(ruta, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes((est * 32767).astype("<i2").tobytes())


class EmisorFalso:
    emitiendo = True
    actual = None


class Banco:
    """Motor simulado + auxiliares + una principal constante por el canal izquierdo."""

    def __init__(self, datos: str, bib):
        self.motor = Motor(FS, simulado=True, t0=1_700_000_000.0)
        self.picos = []                                   # (frame, pico izq, pico der) por bloque
        self.motor.sonda = lambda f, buf: self.picos.append((f, *np.abs(buf).max(axis=0)))
        principal = np.zeros((FS * 600, 2), dtype=np.float32)
        principal[:, 0] = NIVEL_PRINCIPAL
        self.voz_principal = Voz(FuenteMemoria(principal), 0)
        self.motor.orden("voz", self.voz_principal)
        cfg = Config()
        self.titulo = Titulo(cfg.metadatos)
        self.anuncios = []
        self.titulo.extra = self.anuncios.append
        self.emisor = EmisorFalso()
        self.aux = Auxiliares(datos, self.motor, bib, rutas.buscar_ffmpeg(), cfg=lambda: cfg,
                              titulo=self.titulo, emisor=self.emisor)

    def correr(self, segundos: float) -> None:
        for _ in range(int(segundos * FS / B)):
            self.aux.paso()
            self.motor.avanzar()

    def accion(self, **d):
        bien, mensaje = self.aux.accion(d)
        assert bien, mensaje
        return mensaje

    def tramo(self, t0: float, t1: float):
        """Picos (izq, der) entre dos instantes (s desde el arranque del motor)."""
        f0, f1 = t0 * FS, t1 * FS
        sel = [(l, r) for f, l, r in self.picos if f0 <= f < f1]
        return np.array(sel) if sel else np.zeros((0, 2))

    def ahora(self) -> float:
        return self.motor.m / FS


FALLOS = []


def comprobar(cond: bool, texto: str) -> None:
    print(("  ok    " if cond else "  FALLO ") + texto)
    if not cond:
        FALLOS.append(texto)


def main() -> int:
    ffmpeg = rutas.buscar_ffmpeg()
    if not ffmpeg:
        print("Hace falta ffmpeg en el PATH.")
        return 2
    base = tempfile.mkdtemp(prefix="gimel-aux-")
    try:
        audios = os.path.join(base, "audios")
        os.makedirs(audios)
        a = os.path.join(audios, "01 A.wav")
        b = os.path.join(audios, "02 B.wav")
        c = os.path.join(audios, "03 C.wav")
        largo = os.path.join(audios, "04 largo.wav")
        corto = os.path.join(audios, "05 corto.wav")
        escribir_tono(a, 4.0, 440)
        escribir_tono(b, 4.0, 660)
        escribir_tono(c, 3.0, 880)
        escribir_tono(largo, 10.0, 330)
        escribir_tono(corto, 1.5, 990)
        datos = os.path.join(base, "datos")
        os.makedirs(datos)
        bib = Biblioteca(datos, ffmpeg)
        for r in (a, b, c, largo, corto):
            bib.pista(r, urgente=True)
        limite = time.monotonic() + 60
        while any(bib.conocida(r) is None for r in (a, b, c, largo, corto)) and time.monotonic() < limite:
            time.sleep(0.05)
        print("Análisis: A %.2f s, B %.2f s, C %.2f s" % tuple(bib.conocida(r).largo for r in (a, b, c)))

        # ------------------------------------------------------------------ 1
        print("\n1. Automático, bajando la principal 12 dB: A, B y C seguidos")
        k = Banco(datos, bib)
        k.accion(accion="anadir", lista=0, rutas=[a, b, c])
        k.accion(accion="ajustes", lista=0, campos={"modo": "automatico", "principal": "bajar",
                                                    "bajada_db": 12, "titulo": True})
        k.correr(1.0)
        antes = k.tramo(0.3, 1.0)
        comprobar(abs(antes[:, 0].max() - NIVEL_PRINCIPAL) < 1e-3 and antes[:, 1].max() < 1e-4,
                  "antes: la principal entera y nada por la derecha")
        t_play = k.ahora()
        k.accion(accion="reproducir", lista=0)
        k.correr(13.0)
        sonando = k.tramo(t_play + 0.3, t_play + 10.6)
        comprobar(sonando[:, 1].min() > 0.3 * NIVEL_AUX,
                  "las tres seguidas, sin hueco (pico mínimo por bloque %.3f)" % sonando[:, 1].min())
        bajada = NIVEL_PRINCIPAL * 10 ** (-12 / 20)
        durante = k.tramo(t_play + 0.6, t_play + 10.0)
        comprobar(np.allclose(durante[:, 0], bajada, atol=2e-3),
                  "la principal, 12 dB abajo mientras suena (%.4f, esperado %.4f)" % (durante[:, 0].mean(), bajada))
        inicio = next(f for f, l, r in k.picos if r > 0.01 and f >= t_play * FS) / FS - t_play
        comprobar(abs(inicio - modaux.ARRANQUE) < B / FS + 0.03,
                  "entra %.0f ms después de pulsar" % (inicio * 1000))
        fin_aux = max(f for f, l, r in k.picos if r > 0.01) / FS
        comprobar(abs((fin_aux - t_play) - (modaux.ARRANQUE + 11.0)) < 0.15,
                  "acaba a los %.2f s (A+B+C = 11 s)" % (fin_aux - t_play - modaux.ARRANQUE))
        despues = k.tramo(fin_aux + 1.2, fin_aux + 2.0)
        comprobar(abs(despues[:, 0].min() - NIVEL_PRINCIPAL) < 1e-3, "después: la principal vuelve entera")
        L = k.aux.listas[0]
        comprobar(L.cabeza is None and not L.toques, "la lista queda parada")
        comprobar(k.voz_principal.pos == k.motor.m, "la principal no se ha detenido ni un frame")
        comprobar(any("A" in x for x in k.anuncios) and k.titulo.retenido is False,
                  "título anunciado y soltado (%s)" % k.anuncios)

        # ------------------------------------------------------------------ 2
        print("\n2. Asistido con punto de parada tras B; silenciando la principal")
        k = Banco(datos, bib)
        k.accion(accion="anadir", lista=1, rutas=[a, b, c])
        k.accion(accion="ajustes", lista=1, campos={"modo": "asistido", "principal": "silenciar"})
        k.accion(accion="parada", lista=1, indice=1)
        k.correr(0.5)
        t_play = k.ahora()
        k.accion(accion="reproducir", lista=1)
        k.correr(10.0)
        L = k.aux.listas[1]
        dentro = k.tramo(t_play + 0.5, t_play + 7.8)
        comprobar(dentro[:, 0].max() < 1e-3, "la principal, callada mientras suenan A y B")
        comprobar(dentro[:, 1].min() > 0.3 * NIVEL_AUX, "A y B seguidas")
        parado = k.tramo(t_play + 9.2, t_play + 10.0)
        comprobar(parado[:, 1].max() < 1e-4 and L.cabeza is None, "se para tras B (punto de parada)")
        comprobar(L.sig is L.elementos[2], "y deja C como siguiente")
        comprobar(abs(parado[:, 0].min() - NIVEL_PRINCIPAL) < 1e-3, "la principal ha vuelto")
        estado = k.aux.estado()["listas"][1]
        comprobar(estado["estado"] == "parado" and estado["cursor"] == 2, "la foto lo cuenta igual")
        k.accion(accion="reproducir", lista=1)
        k.correr(4.0)
        comprobar(k.tramo(k.ahora() - 3.0, k.ahora() - 1.0)[:, 1].min() > 0.3 * NIVEL_AUX,
                  "al pulsar otra vez sale C")

        # ------------------------------------------------------------------ 3
        print("\n3. Manual, pausa y seguir")
        k = Banco(datos, bib)
        k.accion(accion="anadir", lista=2, rutas=[largo, a])
        k.accion(accion="ajustes", lista=2, campos={"modo": "manual"})
        k.correr(0.5)
        k.accion(accion="reproducir", lista=2)
        k.correr(3.0)
        k.accion(accion="pausa", lista=2)
        k.correr(2.0)
        L = k.aux.listas[2]
        comprobar(L.pausa is not None and abs(L.pausa[1] - (3.0 - modaux.ARRANQUE)) < 0.1,
                  "en pausa a los %.2f s" % (L.pausa[1] if L.pausa else -1))
        comprobar(k.tramo(k.ahora() - 1.5, k.ahora())[:, 1].max() < 1e-4, "en pausa no suena")
        t_sigue = k.ahora()
        k.accion(accion="pausa", lista=2)
        k.correr(9.0)
        resto = [f for f, l, r in k.picos if r > 0.01 and f >= t_sigue * FS]
        sonado = (max(resto) - min(resto)) / FS
        comprobar(abs(sonado - (10.0 - L_pausa_s(3.0))) < 0.15,
                  "sigue por donde iba: suenan %.2f s más" % sonado)
        comprobar(L.cabeza is None and L.sig is L.elementos[1], "manual: se para al acabar, con A preparada")

        # ------------------------------------------------------------------ 4
        print("\n4. Botonera: dos botones a la vez, parar pulsando otra vez, bucle")
        k = Banco(datos, bib)
        k.accion(accion="asignar", boton=0, ruta=corto)
        k.accion(accion="asignar", boton=1, ruta=a)
        k.accion(accion="boton", boton=1, campos={"bucle": True})
        limite = time.monotonic() + 10
        while not (k.aux.botones[0].memoria is not None and k.aux.botones[1].memoria is not None) \
                and time.monotonic() < limite:
            k.aux.paso()
            time.sleep(0.05)
        comprobar(k.aux.botones[0].memoria is not None, "el botón corto, ya en memoria")
        k.accion(accion="disparar", boton=0)
        k.accion(accion="disparar", boton=1)
        k.correr(1.0)
        comprobar(sum(1 for b in k.aux.botones if b.cabeza is not None) == 2, "suenan los dos")
        k.correr(8.0)
        comprobar(k.aux.botones[1].cabeza is not None, "el de bucle sigue (va por la 3.ª vuelta)")
        comprobar(k.tramo(k.ahora() - 7.5, k.ahora())[:, 1].min() > 0.3 * NIVEL_AUX,
                  "el bucle no deja huecos entre vueltas")
        k.accion(accion="disparar", boton=1)
        k.correr(1.0)
        comprobar(k.aux.botones[1].cabeza is None and k.tramo(k.ahora() - 0.5, k.ahora())[:, 1].max() < 1e-4,
                  "pulsar otra vez lo para")

        # ------------------------------------------------------------------ 5
        print("\n5. Lo del grupo SISTEMA (los DTMF de los CUE) no se calla nunca")
        k = Banco(datos, bib)
        tono = np.zeros((FS * 5, 2), dtype=np.float32)
        tono[:, 0] = 0.1
        k.motor.orden("voz", Voz(FuenteMemoria(tono), k.motor.m + 10, grupo=SISTEMA))
        k.accion(accion="anadir", lista=3, rutas=[largo])
        k.accion(accion="ajustes", lista=3, campos={"principal": "silenciar"})
        k.accion(accion="reproducir", lista=3)
        k.correr(2.0)
        comprobar(abs(k.tramo(1.0, 2.0)[:, 0].mean() - 0.1) < 2e-3,
                  "con la principal silenciada, el DTMF sigue a su nivel")
        k.accion(accion="parar_todo")
        k.correr(1.5)
        comprobar(k.aux.listas[3].cabeza is None and k.motor.principal == 1.0, "parar todo")

        # ------------------------------------------------------------------ 6
        print("\n6. Sin emitir no suena, y al dejar de emitir se queda en pausa")
        k = Banco(datos, bib)
        k.accion(accion="anadir", lista=0, rutas=[largo])
        k.emisor.emitiendo = False
        bien, mensaje = k.aux.accion({"accion": "reproducir", "lista": 0})
        comprobar(not bien and mensaje, "parado: avisa en vez de sonar")
        k.emisor.emitiendo = True
        k.accion(accion="reproducir", lista=0)
        k.correr(4.0)
        k.emisor.emitiendo = False
        k.correr(1.0)
        L = k.aux.listas[0]
        comprobar(L.cabeza is None and L.pausa is not None and abs(L.pausa[1] - 3.9) < 0.2,
                  "al parar la emisión: en pausa a los %.1f s" % (L.pausa[1] if L.pausa else -1))

        # ------------------------------------------------------------------ 7
        print("\n7. Se guarda y se vuelve a leer")
        k = Banco(datos, bib)
        k.accion(accion="anadir", lista=0, rutas=[a, b])
        k.accion(accion="ajustes", lista=0, campos={"nombre": "Programa", "modo": "manual", "bucle": True})
        k.accion(accion="parada", lista=0, indice=0)
        k.accion(accion="asignar", boton=5, ruta=c, etiqueta="Efecto")
        k.aux.cerrar()
        k2 = Banco(datos, bib)
        L = k2.aux.listas[0]
        comprobar(L.nombre == "Programa" and L.modo == "manual" and L.bucle and len(L.elementos) == 2
                  and L.elementos[0].parar, "la lista, con sus ajustes y su punto de parada")
        comprobar(k2.aux.botones[5].ruta == c and k2.aux.botones[5].etiqueta == "Efecto", "el botón")
        e = k2.aux.estado()
        comprobar(e["listas"][0]["total"] > 7.9 and "elementos" in e["listas"][0], "la foto completa")
        comprobar("elementos" not in k2.aux.estado(e["version"])["listas"][0],
                  "sin cambios, la foto no repite los elementos")
        bib.cerrar()
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print("\n%s" % ("TODO BIEN" if not FALLOS else "%d FALLOS" % len(FALLOS)))
    return 1 if FALLOS else 0


def L_pausa_s(pulsado_a: float) -> float:
    """Lo que ya habia sonado al pausar (se pulso a los `pulsado_a` s de lanzar)."""
    return pulsado_a - modaux.ARRANQUE


if __name__ == "__main__":
    sys.exit(main())
