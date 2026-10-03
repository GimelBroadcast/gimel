# -*- coding: utf-8 -*-
"""
Formulario generico: pinta los campos de un esquema (gimel/esquema.py) y los
deja enlazados a un objeto de la configuracion. Cada cambio se escribe en el
objeto al momento; guardar o descartar es cosa de la ventana.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QWidget)

from ..idioma import dias_cortos, tr
from .widgets import CampoRuta, Interruptor, SelectorDias


class _SinRueda:
    """Que la rueda del raton, al pasar por encima haciendo scroll, no cambie valores."""

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class Entero(_SinRueda, QSpinBox):
    pass


class Decimal(_SinRueda, QDoubleSpinBox):
    pass


class Desplegable(_SinRueda, QComboBox):
    def poner_opciones(self, opciones, valor) -> None:
        self.blockSignals(True)
        self.clear()
        for v, texto in opciones:
            self.addItem(texto, v)
        i = self.findData(valor)
        self.setCurrentIndex(i if i >= 0 else 0)
        self.blockSignals(False)


class Formulario(QWidget):
    cambiado = pyqtSignal()

    def __init__(self, campos: list, nucleo, omitir=None, parent=None):
        super().__init__(parent)
        self.campos = campos
        self.nucleo = nucleo
        self.omitir = omitir                  # funcion campo -> bool: campos que no se ensenan
        self.obj = None
        # campos de los que depende que otros se vean: al cambiar, se repinta entero
        self._mandan = {c["si"][0] for c in campos if c.get("si")}
        if any(c["tipo"] == "salida" for c in campos):
            self._mandan.add("api")
        self._rejilla = QGridLayout(self)
        self._rejilla.setContentsMargins(0, 0, 0, 0)
        self._rejilla.setHorizontalSpacing(16)
        self._rejilla.setVerticalSpacing(7)
        self._rejilla.setColumnMinimumWidth(0, 270)
        self._rejilla.setColumnStretch(1, 1)

    def poner(self, obj) -> None:
        self.obj = obj
        self._construir()

    def _vaciar(self) -> None:
        while self._rejilla.count():
            it = self._rejilla.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _construir(self) -> None:
        self._vaciar()
        obj = self.obj
        if obj is None:
            return
        fila = 0
        for c in self.campos:
            if self.omitir is not None and self.omitir(c):
                continue
            si = c.get("si")
            if si and getattr(obj, si[0]) not in si[1]:
                continue
            if c["tipo"] == "titulo":
                rot = QLabel(tr(c["etiqueta"]).upper())
                rot.setObjectName("seccion")
                self._rejilla.addWidget(rot, fila, 0, 1, 2)
                fila += 1
                continue
            et = QLabel(tr(c["etiqueta"]))
            et.setWordWrap(True)
            et.setContentsMargins(0, 6, 0, 0)             # a la altura del texto del control
            self._rejilla.addWidget(et, fila, 0, Qt.AlignmentFlag.AlignTop)
            self._rejilla.addWidget(self._control(c, obj), fila, 1)
            fila += 1
            if c.get("ayuda"):
                ay = QLabel(tr(c["ayuda"]))
                ay.setObjectName("ayuda")
                ay.setWordWrap(True)
                self._rejilla.addWidget(ay, fila, 1)
                fila += 1
        self._rejilla.setRowStretch(fila, 1)

    def _escribir(self, clave: str, valor) -> None:
        setattr(self.obj, clave, valor)
        self.cambiado.emit()
        if clave in self._mandan:
            QTimer.singleShot(0, self._construir)         # fuera del manejador del propio control

    @staticmethod
    def _con_hueco(*widgets) -> QWidget:
        """Los controles pequenos, pegados a la izquierda en vez de estirados."""
        caja = QWidget()
        f = QHBoxLayout(caja)
        f.setContentsMargins(0, 0, 0, 0)
        f.setSpacing(8)
        for w in widgets:
            f.addWidget(w)
        f.addStretch(1)
        return caja

    def _control(self, c: dict, obj) -> QWidget:
        clave, tipo = c["clave"], c["tipo"]
        v = getattr(obj, clave)
        if tipo == "bool":
            w = Interruptor()
            w.setChecked(bool(v))
            w.toggled.connect(lambda x, k=clave: self._escribir(k, bool(x)))
            return self._con_hueco(w)
        if tipo in ("entero", "decimal"):
            if tipo == "entero":
                w = Entero()
                w.setRange(int(c.get("min", 0)), int(c.get("max", 999999)))
                w.setSingleStep(int(c.get("paso", 1)))
                w.setValue(int(v))
                w.valueChanged.connect(lambda x, k=clave: self._escribir(k, int(x)))
            else:
                w = Decimal()
                w.setDecimals(int(c.get("decimales", 1)))
                w.setRange(float(c.get("min", 0)), float(c.get("max", 999999)))
                w.setSingleStep(float(c.get("paso", 0.1)))
                w.setValue(float(v))
                w.valueChanged.connect(lambda x, k=clave: self._escribir(k, float(x)))
            w.setFixedWidth(110)
            w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            if c.get("sufijo"):
                s = QLabel(tr(c["sufijo"]))
                s.setObjectName("tenue")
                return self._con_hueco(w, s)
            return self._con_hueco(w)
        if tipo in ("opcion", "hora", "hora_fin"):
            if tipo == "hora":
                opciones = [(i, "%02d:00" % i) for i in range(24)]
            elif tipo == "hora_fin":
                opciones = [(i, "%02d:00" % i) for i in range(1, 25)]
            else:
                opciones = [(valor, tr(texto)) for valor, texto in c["opciones"]]
            w = Desplegable()
            w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            w.poner_opciones(opciones, v)
            w.currentIndexChanged.connect(lambda _, k=clave, w=w: self._escribir(k, w.currentData()))
            return self._con_hueco(w)
        if tipo == "dias":
            w = SelectorDias(dias_cortos())
            w.poner(v)
            w.cambiado.connect(lambda k=clave, w=w: self._escribir(k, w.valor()))
            return w
        if tipo == "origen":
            w = CampoRuta(c.get("modo", "cualquiera"), self.nucleo.resumen)
            w.poner(v)
            w.cambiado.connect(lambda x, k=clave: self._escribir(k, x))
            return w
        if tipo == "salida":
            return self._salida(clave, obj, v)
        if tipo == "parrafo":
            w = QPlainTextEdit()
            w.setPlainText(v)
            w.setFixedHeight(76)
            w.setTabChangesFocus(True)
            w.textChanged.connect(lambda k=clave, w=w: self._escribir(k, w.toPlainText()))
            return w
        w = QLineEdit(str(v))
        if tipo == "clave":
            w.setEchoMode(QLineEdit.EchoMode.Password)
        w.textEdited.connect(lambda x, k=clave: self._escribir(k, x))
        return w

    def _salida(self, clave: str, obj, v) -> QWidget:
        """Desplegable con las tarjetas del sistema de audio elegido."""
        api = getattr(obj, "api", "")
        salidas = [s for s in self.nucleo.salidas() if s["api"] == api]
        opciones = [("", tr("Predeterminada del sistema"))]
        opciones += [(s["nombre"], s["nombre"] + ("   " + tr("(predeterminada)") if s["defecto"] else ""))
                     for s in salidas]
        if v and all(s["nombre"] != v for s in salidas):
            opciones.append((v, v + "   " + tr("(no está)")))
        w = Desplegable()
        w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        w.setMinimumWidth(340)
        w.poner_opciones(opciones, v)
        w.currentIndexChanged.connect(lambda _, k=clave, w=w: self._escribir(k, w.currentData()))
        b = QPushButton(tr("Actualizar"))
        b.setProperty("clase", "pequeno")
        b.setToolTip(tr("Volver a mirar qué tarjetas hay (sin emitir)"))

        def refrescar():
            self.nucleo.refrescar_salidas()
            QTimer.singleShot(0, self._construir)

        b.clicked.connect(refrescar)
        return self._con_hueco(w, b)
