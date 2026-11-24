# -*- coding: utf-8 -*-
"""
Pantalla de locutor: una ventana aparte, para el monitor del estudio, con lo
que hace falta mirar en directo y nada mas. La hora, lo que suena y cuanto le
queda, la cuenta atras de la intro (hasta que entra la voz), lo que falta para
el siguiente fijo (la senal, un bloque, un enlace), lo que viene despues y lo
que suena en las listas auxiliares. F11 la pone a pantalla completa.

No pregunta nada al nucleo por su cuenta: la ventana principal le pasa la
misma foto que pinta ella (si no, el vumetro de alli perderia picos).
"""

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import NOMBRE
from ..idioma import tr
from . import estilo
from .widgets import BarraAvance, Chip, EtiquetaCorta, Lampara, hms, mmss

AMBAR = "#fbbf24"


def _etq(puntos: float, negrita: bool = False, color: str = estilo.TEXTO, mono: bool = False) -> QLabel:
    w = QLabel("")
    w.setFont(estilo.mono(puntos, negrita) if mono else estilo.texto(puntos, negrita))
    w.setStyleSheet("color: %s;" % color)
    return w


class PantallaLocutor(QWidget):
    def __init__(self, icono=None):
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("%s · %s" % (NOMBRE, tr("Pantalla de locutor")))
        if icono is not None:
            self.setWindowIcon(icono)
        self.setObjectName("fondo")
        self.setStyleSheet("QWidget#fondo { background: #0b0d10; }")
        self.resize(1280, 720)
        QShortcut(QKeySequence("F11"), self, lambda: self.setWindowState(
            self.windowState() ^ Qt.WindowState.WindowFullScreen))
        QShortcut(QKeySequence("Esc"), self, lambda: self.setWindowState(
            self.windowState() & ~Qt.WindowState.WindowFullScreen))

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(36, 26, 36, 26)
        raiz.setSpacing(10)

        arriba = QHBoxLayout()
        self.emisora = _etq(16, True, estilo.ACENTO)
        arriba.addWidget(self.emisora)
        arriba.addStretch(1)
        self.lampara = Lampara()
        arriba.addWidget(self.lampara)
        arriba.addSpacing(26)
        self.reloj = _etq(54, True, mono=True)
        arriba.addWidget(self.reloj)
        raiz.addLayout(arriba)
        self.fecha = _etq(13, False, estilo.TENUE)
        self.fecha.setAlignment(Qt.AlignmentFlag.AlignRight)
        raiz.addWidget(self.fecha)
        raiz.addSpacing(10)

        self.chip = Chip()
        raiz.addWidget(self.chip)
        self.titulo = EtiquetaCorta(estilo.texto(38, True))
        raiz.addWidget(self.titulo)
        self.artista = EtiquetaCorta(estilo.texto(22), estilo.TENUE)
        raiz.addWidget(self.artista)
        self.barra = BarraAvance()
        self.barra.setFixedHeight(22)
        raiz.addWidget(self.barra)

        cuentas = QHBoxLayout()
        cuentas.setSpacing(40)
        col = QVBoxLayout()
        col.addWidget(_rotulo(tr("QUEDA")))
        self.resta = _etq(96, True, mono=True)
        col.addWidget(self.resta)
        cuentas.addLayout(col)
        col = QVBoxLayout()
        self.r_intro = _rotulo(tr("INTRO"))
        col.addWidget(self.r_intro)
        self.intro = _etq(96, True, AMBAR, mono=True)
        col.addWidget(self.intro)
        cuentas.addLayout(col)
        cuentas.addStretch(1)
        col = QVBoxLayout()
        self.r_ancla = _rotulo("")
        self.r_ancla.setAlignment(Qt.AlignmentFlag.AlignRight)
        col.addWidget(self.r_ancla)
        self.ancla = _etq(60, True, mono=True)
        self.ancla.setAlignment(Qt.AlignmentFlag.AlignRight)
        col.addWidget(self.ancla)
        cuentas.addLayout(col)
        raiz.addLayout(cuentas)

        raiz.addStretch(1)
        self.siguiente = EtiquetaCorta(estilo.texto(18), estilo.TEXTO)
        raiz.addWidget(self.siguiente)
        self.aux = QLabel("")
        self.aux.setFont(estilo.texto(15, True))
        self.aux.setStyleSheet("color: #c084fc;")
        raiz.addWidget(self.aux)
        self.alarma = QLabel("")
        self.alarma.setFont(estilo.texto(16, True))
        self.alarma.setStyleSheet("color: #ffffff; background: #7f1d1d; border: 1px solid #ef4444; "
                                  "border-radius: 8px; padding: 10px 16px;")
        self.alarma.setVisible(False)
        raiz.addWidget(self.alarma)

    def actualizar(self, e: dict) -> None:
        if not self.isVisible():
            return
        ahora = e["reloj"]
        self.reloj.setText(hms(ahora))
        d = datetime.fromtimestamp(ahora)
        self.fecha.setText(d.strftime("%d/%m/%Y"))
        self.emisora.setText(e.get("emisora", ""))
        emite = bool(e.get("emitiendo"))
        self.lampara.poner(emite)
        a = e.get("actual")
        self.chip.poner(a["tipo"] if a else "")
        if a and emite:
            va = max(0.0, ahora - a["t"])
            self.titulo.poner(a["titulo"])
            self.artista.poner(a.get("artista") or "")
            self.barra.poner(va / a["dur"] if a["dur"] else 0.0, a["tipo"])
            self.resta.setText(mmss(a["dur"] - va))
            intro = a.get("intro") or 0.0
            hay = intro > va
            self.intro.setText(mmss(intro - va) if hay else "")
            self.r_intro.setVisible(hay)
        else:
            self.titulo.poner(tr("Parado") if not emite else "…")
            self.artista.poner("")
            self.barra.poner(0.0)
            self.resta.setText("--:--")
            self.intro.setText("")
            self.r_intro.setVisible(False)
        an = e.get("ancla")
        if emite and an:
            self.r_ancla.setText((tr("SEÑAL HORARIA") if an["clase"] == "senal" else (an.get("nombre") or tr("BLOQUE")).upper()))
            self.ancla.setText(mmss(an["t"] - ahora))
        else:
            self.r_ancla.setText(tr("HORA EN PUNTO"))
            self.ancla.setText(mmss(3600 - (d.minute * 60 + d.second)))
        sig = e.get("siguiente")
        self.siguiente.poner(tr("Después:  %s%s   ·   %s") % (sig["titulo"], "  —  " + sig["artista"] if sig.get("artista") else "",
                                                             hms(sig["t"])) if sig and emite else "")
        aux = e.get("aux") or []
        self.aux.setText("    ".join("%s: %s%s" % (x["nombre"], x["titulo"], ("  -" + mmss(x["resta"])) if x.get("resta") else "")
                                   for x in aux if not x.get("emergencia")))
        alarmas = []
        if any(x.get("emergencia") for x in aux):
            alarmas.append(tr("LISTA DE EMERGENCIA EN ANTENA"))
        r = e.get("reserva") or {}
        if r.get("relevo"):
            alarmas.append(tr("ESTA ES LA RESERVA Y ESTÁ EN ANTENA"))
        if e.get("error"):
            alarmas.append(e["error"])
        self.alarma.setText("   ·   ".join(alarmas))
        self.alarma.setVisible(bool(alarmas))


def _rotulo(texto: str) -> QLabel:
    w = QLabel(texto)
    w.setFont(estilo.texto(11, True, 2.0))
    w.setStyleSheet("color: %s;" % estilo.TENUE)
    return w
