# -*- coding: utf-8 -*-
"""
Controles propios de la interfaz: lo que Qt no trae y hace que esto parezca
un automatizador (el reloj de la hora, la pauta, el vumetro) y los campos de
los formularios (interruptor, dias, ruta con explorador).

Todo lo que se pinta a mano se repinta solo cuando cambia: el hilo de audio
compite por el interprete con este, y pintar de mas es quitarle tiempo.
"""

import math
import os
import time
from datetime import datetime

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (QAbstractButton, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMenu,
                             QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from .. import rutas
from ..idioma import tr
from . import estilo


def hms(t: float) -> str:
    return datetime.fromtimestamp(t).strftime("%H:%M:%S")


def mmss(s: float) -> str:
    s = max(0, int(round(s)))
    m = s // 60
    if m >= 60:
        return "%d:%02d:%02d" % (m // 60, m % 60, s % 60)
    return "%d:%02d" % (m, s % 60)


def duracion(s: float) -> str:
    if not s:
        return ""
    return ("%.1f s" % s).replace(".", tr(",")) if s < 10 else mmss(s)


def largo(s: float) -> str:
    h, m = int(s // 3600), int(round((s % 3600) / 60))
    return tr("%d h %d min") % (h, m) if h else tr("%d min") % m


# ---------------------------------------------------------------- formularios

class Interruptor(QAbstractButton):
    """Casilla de si/no con forma de interruptor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 24)

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        si = self.isChecked()
        p.setBrush(QColor(estilo.VERDE if si else "#2a323d"))
        p.drawRoundedRect(QRectF(0, 1, 44, 22), 11, 11)
        p.setBrush(QColor("#ffffff" if si else "#8b96a5"))
        p.drawEllipse(QRectF(23 if si else 3, 4, 16, 16))


class SelectorDias(QWidget):
    cambiado = pyqtSignal()

    def __init__(self, nombres, parent=None):
        super().__init__(parent)
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(4)
        self.botones = []
        for n in nombres:
            b = QPushButton(n)
            b.setCheckable(True)
            b.setProperty("clase", "dia")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(self.cambiado)
            fila.addWidget(b)
            self.botones.append(b)
        fila.addStretch(1)

    def poner(self, dias) -> None:
        for b, d in zip(self.botones, dias):
            b.setChecked(bool(d))

    def valor(self) -> list:
        return [b.isChecked() for b in self.botones]


class CampoRuta(QWidget):
    """Ruta de una carpeta, una lista o un audio, con explorador y resumen de lo que hay."""

    cambiado = pyqtSignal(str)

    def __init__(self, modo: str = "cualquiera", resumen=None, parent=None):
        super().__init__(parent)
        self.modo = modo
        self._resumen = resumen               # funcion ruta -> dict (Nucleo.resumen)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(2)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.editingFinished.connect(self._fijar)
        fila.addWidget(self.edit, 1)
        b = QPushButton(tr("Examinar…"))
        b.setProperty("clase", "pequeno")
        b.clicked.connect(self._examinar)
        fila.addWidget(b)
        self._boton = b
        q = QPushButton("✕")
        q.setProperty("clase", "pequeno")
        q.setToolTip(tr("Quitar"))
        q.clicked.connect(lambda: self._elegida(""))
        fila.addWidget(q)
        caja.addLayout(fila)
        self.info = QLabel("")
        self.info.setObjectName("ayuda")
        self.info.setVisible(False)
        caja.addWidget(self.info)
        self._reloj = QTimer(self)
        self._reloj.setSingleShot(True)
        self._reloj.timeout.connect(self._mirar)
        self._ultima = ""

    def poner(self, ruta: str) -> None:
        self._ultima = ruta or ""
        self.edit.setText(self._ultima)
        self._mirar()

    def valor(self) -> str:
        return self.edit.text().strip()

    def _fijar(self) -> None:
        ruta = self.valor()
        if ruta != self._ultima:
            self._ultima = ruta
            self.cambiado.emit(ruta)
            self._mirar()

    def _elegida(self, ruta: str) -> None:
        if ruta is None:
            return
        self.edit.setText(os.path.normpath(ruta) if ruta else "")
        self._fijar()

    def _donde(self) -> str:
        r = self.valor()
        while r and not os.path.isdir(r):
            nuevo = os.path.dirname(r)
            if nuevo == r:
                return ""
            r = nuevo
        return r

    def _examinar(self) -> None:
        audio = tr("Audio (%s)") % " ".join("*" + e for e in rutas.EXT_AUDIO)
        listas = tr("Listas (%s)") % " ".join("*" + e for e in rutas.EXT_LISTA)

        def carpeta():
            r = QFileDialog.getExistingDirectory(self, tr("Elegir carpeta"), self._donde())
            if r:
                self._elegida(r)

        def fichero(filtro):
            r, _ = QFileDialog.getOpenFileName(self, tr("Elegir fichero"), self._donde(), filtro)
            if r:
                self._elegida(r)

        if self.modo == "fichero":
            fichero(audio)
        elif self.modo == "guardar":
            r, _ = QFileDialog.getSaveFileName(self, tr("Fichero de texto"), self._donde() or self.valor(),
                                               tr("Texto (*.txt);;Todos (*.*)"))
            if r:
                self._elegida(r)
        else:
            menu = QMenu(self)
            menu.addAction(tr("Carpeta…"), carpeta)
            menu.addAction(tr("Lista (.m3u, .pls)…"), lambda: fichero(listas))
            if self.modo == "cualquiera":
                menu.addAction(tr("Un fichero de audio…"), lambda: fichero(audio))
            menu.exec(self._boton.mapToGlobal(self._boton.rect().bottomLeft()))

    def _mirar(self) -> None:
        ruta = self.valor()
        if not ruta or self._resumen is None or self.modo == "guardar":
            self.info.setVisible(False)
            return
        try:
            r = self._resumen(ruta)
        except Exception:
            self.info.setVisible(False)
            return
        self.info.setVisible(True)
        if not r.get("existe"):
            self.info.setObjectName("mal")
            self.info.setText(tr("No existe"))
        elif self.modo == "fichero":                      # un fichero suelto: solo se avisa si falla
            self.info.setObjectName("mal")
            self.info.setText(tr("No se puede leer") if r.get("errores") else "")
            self.info.setVisible(bool(r.get("errores")))
            if r.get("leyendo") or (not r.get("analizados") and not r.get("errores")):
                self._reloj.start(2000)
        elif r.get("leyendo"):
            self.info.setObjectName("ayuda")
            self.info.setText(tr("Leyendo…"))
            self._reloj.start(1200)
        else:
            self.info.setObjectName("ayuda")
            n, hechos, malos = r["ficheros"], r["analizados"], r["errores"]
            t = (tr("%d audio") if n == 1 else tr("%d audios")) % n
            if hechos:
                t += " · " + largo(r["segundos"])
            if hechos < n - malos:
                t += " · " + tr("analizando (%d de %d)") % (hechos, n)
                self._reloj.start(2500)
            if malos:
                t += " · " + tr("%d ilegibles") % malos
            self.info.setText(t)
        self.info.style().unpolish(self.info)
        self.info.style().polish(self.info)


class EtiquetaCorta(QLabel):
    """Etiqueta de una linea que, si no cabe, acaba en puntos suspensivos."""

    def __init__(self, fuente, color: str = estilo.TEXTO, parent=None):
        super().__init__(parent)
        self._texto = ""
        self._fuente = fuente
        self._color = QColor(color)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(QFontMetrics(fuente).height() + 4)

    def poner(self, texto: str) -> None:
        if texto != self._texto:
            self._texto = texto
            self.setToolTip(texto if len(texto) > 40 else "")
            self.update()

    def minimumSizeHint(self) -> QSize:
        return QSize(10, self.height())

    def sizeHint(self) -> QSize:
        return QSize(200, self.height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setPen(self._color)
        p.setFont(self._fuente)
        p.drawText(self.rect(), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                   QFontMetrics(self._fuente).elidedText(self._texto, Qt.TextElideMode.ElideRight,
                                                         self.width()))


# ---------------------------------------------------------------- emision

class Lampara(QWidget):
    """El piloto de EN EMISION."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._si = False
        self.setFixedSize(150, 34)

    def poner(self, si: bool) -> None:
        if si != self._si:
            self._si = si
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(4, 4, self.width() - 8, self.height() - 8)
        if self._si:
            for i, alfa in enumerate((28, 46, 70)):       # resplandor
                p.setPen(QPen(QColor(239, 68, 68, alfa), 8 - 2.5 * i))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(r, 5, 5)
            p.setPen(QPen(QColor(estilo.ROJO), 1))
            p.setBrush(QColor("#991b1b"))
        else:
            p.setPen(QPen(QColor(estilo.BORDE), 1))
            p.setBrush(QColor("#20262e"))
        p.drawRoundedRect(r, 5, 5)
        p.setPen(QColor("#ffffff" if self._si else estilo.TENUE))
        p.setFont(estilo.texto(8.5, True, 1.6))
        p.drawText(r, int(Qt.AlignmentFlag.AlignCenter), tr("EN EMISIÓN") if self._si else tr("PARADO"))


class Chip(QWidget):
    """Etiqueta de color con el tipo de audio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tipo = ""
        self.setFixedSize(92, 22)

    def poner(self, tipo: str) -> None:
        if tipo != self._tipo:
            self._tipo = tipo
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintar_chip(p, QRectF(0, 1, self.width(), 20), self._tipo or "silencio",
                    "—" if not self._tipo else None)


def pintar_chip(p: QPainter, r: QRectF, tipo: str, texto=None, alfa: int = 255) -> None:
    c = estilo.color(tipo)
    c.setAlpha(alfa)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawRoundedRect(r, 3, 3)
    tinta = QColor("#111111" if tipo in estilo.TEXTO_OSCURO else "#ffffff")
    tinta.setAlpha(alfa)
    p.setPen(tinta)
    p.setFont(estilo.texto(7.5, True, 0.6))
    p.drawText(r, int(Qt.AlignmentFlag.AlignCenter), texto or tr(estilo.NOMBRE_TIPO.get(tipo, tipo.upper())))


class BarraAvance(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._f = 0.0
        self._tipo = "cancion"
        self.setFixedHeight(16)

    def poner(self, fraccion: float, tipo: str = "cancion") -> None:
        fraccion = max(0.0, min(1.0, fraccion))
        if abs(fraccion - self._f) * max(1, self.width()) >= 0.5 or tipo != self._tipo:
            self._f = fraccion
            self._tipo = tipo
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(QColor(estilo.BORDE), 1))
        p.setBrush(QColor("#0b0d10"))
        p.drawRoundedRect(r, 7, 7)
        if self._f > 0.002:
            c = estilo.color(self._tipo)
            g = QLinearGradient(0, 0, self.width(), 0)
            g.setColorAt(0.0, c.darker(125))
            g.setColorAt(1.0, c.lighter(125))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.setClipRect(QRectF(0, 0, self.width() * self._f, self.height()))
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 6, 6)


class Vumetro(QWidget):
    """Dos barras de picos con escala en dB y testigo del limitador."""

    SUELO = -48.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = [self.SUELO, self.SUELO]
        self._pico = [self.SUELO, self.SUELO]
        self._t_pico = [0.0, 0.0]
        self._lim = False
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def poner(self, izq: float, der: float, limitando: bool) -> None:
        ahora = time.monotonic()
        cambia = limitando != self._lim
        self._lim = limitando
        for i, v in enumerate((izq, der)):
            db = max(self.SUELO, 20.0 * math.log10(max(v, 1e-6)))
            if abs(db - self._db[i]) > 0.4:
                self._db[i] = db
                cambia = True
            if db >= self._pico[i] or ahora - self._t_pico[i] > 1.5:
                if abs(db - self._pico[i]) > 0.4:
                    cambia = True
                self._pico[i] = db
                self._t_pico[i] = ahora
        if cambia:
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        x0, x1 = 20.0, self.width() - 50.0
        ancho = max(10.0, x1 - x0)
        pos = lambda db: x0 + ancho * (max(self.SUELO, min(0.0, db)) - self.SUELO) / -self.SUELO
        n = max(10, int(ancho // 6))
        for canal, y in enumerate((6.0, 26.0)):
            p.setPen(QColor(estilo.TENUE))
            p.setFont(estilo.texto(8, True))
            p.drawText(QRectF(0, y, 16, 14), int(Qt.AlignmentFlag.AlignCenter), "LR"[canal])
            p.setPen(Qt.PenStyle.NoPen)
            hasta = pos(self._db[canal])
            for k in range(n):
                sx = x0 + ancho * k / n
                db = self.SUELO + (-self.SUELO) * (k + 1) / n
                encendido = sx < hasta - 0.5 and self._db[canal] > self.SUELO
                if db > -3.0:
                    c = QColor("#ef4444")
                elif db > -12.0:
                    c = QColor("#eab308")
                else:
                    c = QColor("#22c55e")
                if not encendido:
                    c = QColor("#1b2028")
                p.setBrush(c)
                p.drawRect(QRectF(sx, y, ancho / n - 1.5, 14))
            if self._pico[canal] > self.SUELO + 1:
                p.setBrush(QColor("#ffffff"))
                p.drawRect(QRectF(pos(self._pico[canal]) - 1, y, 2, 14))
        p.setFont(estilo.texto(7))
        p.setPen(QColor(estilo.TENUE))
        for db in (-40, -30, -20, -12, -6, -3, 0):
            x = pos(db)
            p.drawText(QRectF(x - 14, 44, 28, 14), int(Qt.AlignmentFlag.AlignCenter), str(db))
        r = QRectF(self.width() - 42, 12, 40, 22)
        p.setPen(QPen(QColor(estilo.ROJO if self._lim else estilo.BORDE), 1))
        p.setBrush(QColor("#991b1b" if self._lim else "#14181d"))
        p.drawRoundedRect(r, 4, 4)
        p.setPen(QColor("#ffffff" if self._lim else "#56606d"))
        p.setFont(estilo.texto(7.5, True, 0.8))
        p.drawText(r, int(Qt.AlignmentFlag.AlignCenter), "LIM")


class RelojHora(QWidget):
    """
    La hora en curso como una esfera: cada audio de la pauta ocupa su arco, con
    el color de su tipo, y la aguja va por donde va la emision. En el centro,
    lo que falta para la proxima ancla.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._h0 = 0.0
        self._filas = []
        self._firma = None
        self._ahora = 0.0
        self._cuenta = ""
        self._rotulo = ""
        self._franja = ""

    def poner(self, h0: float, filas: list, firma, ahora: float, cuenta: str, rotulo: str,
              franja: str) -> None:
        cambia = (firma != self._firma or cuenta != self._cuenta or rotulo != self._rotulo
                  or franja != self._franja or abs(ahora - self._ahora) >= 1.0)
        if not cambia:
            return
        self._h0, self._filas, self._firma = h0, filas, firma
        self._ahora, self._cuenta, self._rotulo, self._franja = ahora, cuenta, rotulo, franja
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        lado = min(self.width(), self.height()) - 30.0
        cx, cy = self.width() / 2.0, self.height() / 2.0
        grosor = max(14.0, lado * 0.125)
        radio = lado / 2.0 - grosor / 2.0
        aro = QRectF(cx - radio, cy - radio, 2 * radio, 2 * radio)

        p.setPen(QPen(QColor("#1b2028"), grosor))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(aro)

        def angulo(t):                                    # grados desde las doce, en el sentido del reloj
            return (t - self._h0) / 3600.0 * 360.0

        plano = QPen()
        plano.setCapStyle(Qt.PenCapStyle.FlatCap)
        plano.setWidthF(grosor)
        for f in self._filas:
            dur = f.get("dur") or 0.0
            if dur <= 0 or f["tipo"] == "cue":
                continue
            a0 = angulo(max(f["t"], self._h0))
            a1 = angulo(min(f["t"] + dur, self._h0 + 3600.0))
            if a1 - a0 <= 0.05:
                continue
            c = estilo.color(f["tipo"])
            if f["estado"] == "fin":
                c.setAlpha(70)
            elif f["estado"] != "aire":
                c.setAlpha(185)
            plano.setColor(c)
            p.setPen(plano)
            hueco = 0.45 if a1 - a0 > 1.5 else 0.0        # una rendija entre audio y audio
            p.drawArc(aro, int(round((90.0 - a0) * 16)), int(round(-(a1 - a0 - hueco) * 16)))

        exterior = radio + grosor / 2.0
        for f in self._filas:                             # los CUE, un punto por fuera
            if f["tipo"] != "cue" or not (self._h0 <= f["t"] <= self._h0 + 3600):
                continue
            a = math.radians(angulo(f["t"]))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(estilo.color("cue"))
            p.drawEllipse(QPointF(cx + math.sin(a) * (exterior + 5), cy - math.cos(a) * (exterior + 5)), 3, 3)

        p.setFont(estilo.texto(7.5, True))
        for minuto in range(0, 60, 5):
            a = math.radians(minuto * 6.0)
            s, c_ = math.sin(a), -math.cos(a)
            interior = radio - grosor / 2.0
            p.setPen(QPen(QColor("#3a4452"), 1.4 if minuto % 15 else 2.2))
            p.drawLine(QPointF(cx + s * (interior - 3), cy + c_ * (interior - 3)),
                       QPointF(cx + s * (interior - (7 if minuto % 15 else 11)),
                               cy + c_ * (interior - (7 if minuto % 15 else 11))))
            if minuto % 15 == 0:
                p.setPen(QColor(estilo.TENUE))
                d = interior - 22
                p.drawText(QRectF(cx + s * d - 12, cy + c_ * d - 8, 24, 16),
                           int(Qt.AlignmentFlag.AlignCenter), "%02d" % minuto)

        if self._ahora and self._h0 <= self._ahora <= self._h0 + 3600.0:
            a = math.radians(angulo(self._ahora))
            s, c_ = math.sin(a), -math.cos(a)
            dentro, fuera = radio - grosor / 2.0 - 4, exterior + 3
            p.setPen(QPen(QColor("#ffffff"), 2.2))
            p.drawLine(QPointF(cx + s * dentro, cy + c_ * dentro), QPointF(cx + s * fuera, cy + c_ * fuera))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(estilo.ACENTO))
            punta = QPointF(cx + s * (fuera + 1), cy + c_ * (fuera + 1))
            ancho = 5.0
            p.drawPolygon(QPolygonF([
                punta,
                QPointF(punta.x() + s * 9 + c_ * ancho, punta.y() + c_ * 9 - s * ancho),
                QPointF(punta.x() + s * 9 - c_ * ancho, punta.y() + c_ * 9 + s * ancho)]))

        p.setPen(QColor(estilo.TEXTO))
        p.setFont(estilo.mono(max(14.0, lado * 0.105), True))
        p.drawText(QRectF(cx - radio, cy - lado * 0.10, 2 * radio, lado * 0.17),
                   int(Qt.AlignmentFlag.AlignCenter), self._cuenta)
        p.setPen(QColor(estilo.TENUE))
        p.setFont(estilo.texto(max(7.0, lado * 0.026), True, 0.6))
        ancho_txt = 2.0 * (radio - grosor / 2.0) - 64.0     # lo que cabe dentro del aro, sin pisar las marcas
        p.drawText(QRectF(cx - ancho_txt / 2, cy + lado * 0.07, ancho_txt, lado * 0.13),
                   int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
                   self._rotulo.upper())
        if self._franja:
            p.setFont(estilo.texto(max(7.0, lado * 0.026)))
            p.drawText(QRectF(cx - ancho_txt / 2, cy - lado * 0.155, ancho_txt, 18),
                       int(Qt.AlignmentFlag.AlignCenter),
                       QFontMetrics(p.font()).elidedText(self._franja, Qt.TextElideMode.ElideRight, int(ancho_txt)))


class ListaPauta(QWidget):
    """La pauta de la hora, pintada a mano: una franja de color por tipo y la que suena, resaltada."""

    ALTO = 34

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filas = []
        self._firma = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self.ALTO)

    def poner(self, filas: list, firma) -> bool:
        """Devuelve si ha cambiado algo."""
        if firma == self._firma:
            return False
        self._filas = filas
        self._firma = firma
        self.setFixedHeight(max(1, len(filas)) * self.ALTO)
        self.update()
        return True

    def y_actual(self):
        for i, f in enumerate(self._filas):
            if f["estado"] == "aire":
                return i * self.ALTO
        for i, f in enumerate(self._filas):
            if f["estado"] != "fin":
                return i * self.ALTO
        return None

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ancho = self.width()
        alto = self.ALTO
        f_hora, f_titulo, f_nota = estilo.mono(10), estilo.texto(10.5, True), estilo.texto(9)
        f_artista = estilo.texto(10)
        w_nota = int(min(310, ancho * 0.27))
        x_dur = ancho - w_nota - 78
        x_titulo = 204
        if not self._filas:
            p.setPen(QColor(estilo.TENUE))
            p.setFont(estilo.texto(10))
            p.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter),
                       tr("Aún no hay pauta: elige la carpeta de canciones en Franjas."))
            return
        primera = max(0, ev.rect().top() // alto)
        ultima = min(len(self._filas) - 1, ev.rect().bottom() // alto)
        for i in range(primera, ultima + 1):
            f = self._filas[i]
            y = i * alto
            aire = f["estado"] == "aire"
            pasada = f["estado"] == "fin"
            alfa = 105 if pasada else 255
            if aire:
                p.fillRect(QRectF(0, y, ancho, alto), QColor("#1d2a40"))
            p.fillRect(QRectF(0, y + 2, 4, alto - 4),
                       QColor(estilo.ACENTO) if aire else estilo.color(f["tipo"]).darker(100 if not pasada else 220))
            p.setPen(QPen(QColor("#20262e"), 1))
            p.drawLine(QPointF(0, y + alto - 0.5), QPointF(ancho, y + alto - 0.5))

            tinta = QColor(estilo.TEXTO)
            tinta.setAlpha(alfa)
            tenue = QColor(estilo.TENUE)
            tenue.setAlpha(alfa)
            p.setPen(tinta)
            p.setFont(f_hora)
            p.drawText(QRectF(16, y, 84, alto), int(Qt.AlignmentFlag.AlignVCenter), hms(f["t"]))
            pintar_chip(p, QRectF(108, y + 7, 82, alto - 14), f["tipo"], None, alfa)

            p.setFont(f_titulo)
            fm = QFontMetrics(f_titulo)
            hueco = max(40, x_dur - x_titulo - 12)
            titulo = fm.elidedText(f["titulo"], Qt.TextElideMode.ElideRight, hueco)
            p.setPen(tinta)
            p.drawText(QRectF(x_titulo, y, hueco, alto), int(Qt.AlignmentFlag.AlignVCenter), titulo)
            usado = fm.horizontalAdvance(titulo)
            if f.get("artista") and hueco - usado > 60:
                p.setFont(f_artista)
                p.setPen(tenue)
                fa = QFontMetrics(f_artista)
                p.drawText(QRectF(x_titulo + usado + 10, y, hueco - usado - 10, alto),
                           int(Qt.AlignmentFlag.AlignVCenter),
                           fa.elidedText("— " + f["artista"], Qt.TextElideMode.ElideRight, hueco - usado - 10))
            p.setFont(f_hora)
            p.setPen(tinta)
            p.drawText(QRectF(x_dur, y, 66, alto),
                       int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), duracion(f["dur"]))
            if f.get("nota"):
                p.setFont(f_nota)
                p.setPen(tenue)
                p.drawText(QRectF(ancho - w_nota, y, w_nota - 10, alto), int(Qt.AlignmentFlag.AlignVCenter),
                           QFontMetrics(f_nota).elidedText(f["nota"], Qt.TextElideMode.ElideRight, w_nota - 10))
