# -*- coding: utf-8 -*-
"""
Pagina de las listas auxiliares, la botonera y la preescucha (ver
gimel/auxiliares.py). Todo lo que se toca aqui va al momento al nucleo: no es
configuracion que espere a «Guardar cambios», es manejo en directo.
"""

import os

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
                             QInputDialog, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QStyle, QStyledItemDelegate, QVBoxLayout, QWidget)

from .. import auxiliares as modaux
from .. import rutas
from ..idioma import N_, tr
from . import estilo
from .paginas import Tarjeta, boton, en_scroll
from .widgets import BarraAvance, EtiquetaCorta, hms, mmss

COLOR_AUX = "#a855f7"


def filtro_audio() -> str:
    return "%s (%s);;%s (*.*)" % (tr("Audio"), " ".join("*" + e for e in rutas.EXT_AUDIO), tr("Todos"))


def _combo(opciones, valor, al_cambiar) -> QComboBox:
    w = QComboBox()
    w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    w.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    w.setMinimumContentsLength(7)                 # que encoja con la ventana en vez de empujar
    for v, texto in opciones:
        w.addItem(texto, v)
    i = w.findData(valor)
    w.setCurrentIndex(max(0, i))
    w.currentIndexChanged.connect(lambda _: al_cambiar(w.currentData()))
    return w


def _poner_combo(w: QComboBox, valor) -> None:
    i = w.findData(valor)
    if i >= 0 and i != w.currentIndex():
        w.blockSignals(True)
        w.setCurrentIndex(i)
        w.blockSignals(False)


def salidas_de_tarjeta(nucleo) -> list:
    return [("%s|%s" % (s["api"], s["nombre"]), "%s  ·  %s" % (s["api"].replace("Windows ", ""), s["nombre"]))
            for s in nucleo.salidas()]


# ================================================================ la lista

class Delegado(QStyledItemDelegate):
    """Una fila: numero, titulo y artista, intro, duracion; y las marcas de lo que suena y lo siguiente."""

    ALTO = 28

    def sizeHint(self, opcion, indice) -> QSize:
        return QSize(100, self.ALTO)

    def paint(self, p: QPainter, opcion, indice) -> None:
        d = indice.data(Qt.ItemDataRole.UserRole) or {}
        r = QRectF(opcion.rect).adjusted(1, 1, -1, -1)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if d.get("sonando"):
            fondo = QColor(COLOR_AUX)
            fondo.setAlpha(70)
        elif opcion.state & QStyle.StateFlag.State_Selected:
            fondo = QColor("#24303f")
        elif d.get("siguiente"):
            fondo = QColor("#1f2a1f")
        else:
            fondo = None
        if fondo is not None:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fondo)
            p.drawRoundedRect(r, 4, 4)
        if d.get("siguiente"):
            p.setPen(QPen(QColor(estilo.VERDE), 2))
            p.drawLine(int(r.left()) + 2, int(r.top()) + 4, int(r.left()) + 2, int(r.bottom()) - 4)
        tenue = QColor(estilo.TENUE)
        p.setFont(estilo.mono(8.5))
        p.setPen(QColor(COLOR_AUX) if d.get("sonando") else tenue)
        marca = "▶" if d.get("sonando") else ("›" if d.get("siguiente") else str(indice.row() + 1))
        p.drawText(r.adjusted(6, 0, 0, 0).toRect().adjusted(0, 0, 0, 0),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), marca)
        derecha = 8
        p.setFont(estilo.mono(9))
        p.setPen(QColor(estilo.TEXTO) if not d.get("pendiente") else tenue)
        dur = mmss(d["dur"]) if d.get("dur") else ("…" if d.get("pendiente") else "—")
        p.drawText(r.adjusted(0, 0, -derecha, 0).toRect(),
                   int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), dur)
        derecha += 46
        if d.get("intro"):
            p.setFont(estilo.mono(8))
            p.setPen(QColor("#fbbf24"))
            p.drawText(r.adjusted(0, 0, -derecha, 0).toRect(),
                       int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), "i%.0f" % d["intro"])
            derecha += 30
        if d.get("parar"):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(estilo.ROJO))
            p.drawRect(QRectF(r.right() - derecha - 10, r.center().y() - 4, 8, 8))
            derecha += 18
        texto = r.adjusted(30, 0, -derecha, 0)
        p.setFont(estilo.texto(9.5, bool(d.get("sonando"))))
        p.setPen(QColor("#f87171") if d.get("error") else QColor(estilo.TEXTO))
        fm = p.fontMetrics()
        titulo = d.get("titulo", "")
        if d.get("artista"):
            titulo += "  —  " + d["artista"]
        p.drawText(texto.toRect(), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                   fm.elidedText(titulo, Qt.TextElideMode.ElideRight, int(texto.width())))
        p.restore()


class VistaLista(QListWidget):
    """La lista de una auxiliar: se reordena arrastrando y admite audios soltados desde el Explorador."""

    soltados = pyqtSignal(list, int)          # rutas, fila donde se sueltan
    movido = pyqtSignal(int, int)             # de, a

    def __init__(self):
        super().__init__()
        self.setItemDelegate(Delegado(self))
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setAcceptDrops(True)
        self.setMinimumHeight(86)
        self.setStyleSheet("QListWidget::item { padding: 0; border: none; }")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            rutas_ = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
            it = self.itemAt(e.position().toPoint())
            self.soltados.emit(rutas_, self.row(it) if it is not None else self.count())
            e.acceptProposedAction()
            return
        de = self.currentRow()
        it = self.itemAt(e.position().toPoint())
        a = self.row(it) if it is not None else self.count() - 1
        e.ignore()                                        # el orden lo pone el nucleo: se repinta desde alli
        if de >= 0 and a >= 0 and de != a:
            self.movido.emit(de, a)


class PanelLista(Tarjeta):
    def __init__(self, pagina, n: int):
        super().__init__("")
        self.pagina = pagina
        self.n = n
        self.est = {}
        self.elementos = []
        self.caja.setContentsMargins(14, 10, 14, 10)
        self.caja.setSpacing(5)
        self.setMinimumHeight(330)
        cab = QHBoxLayout()
        cab.setSpacing(8)
        self.nombre = EtiquetaCorta(estilo.texto(8.5, True, 1.4), COLOR_AUX)
        cab.addWidget(self.nombre, 3)
        self.estado = EtiquetaCorta(estilo.texto(8.5), estilo.TENUE)
        cab.addWidget(self.estado, 2)
        self.b_opciones = boton(tr("Opciones") + "  ▾", "pequeno", self._opciones)
        cab.addWidget(self.b_opciones)
        self.caja.addLayout(cab)
        fila = QHBoxLayout()
        self.titulo = EtiquetaCorta(estilo.texto(12, True))
        fila.addWidget(self.titulo, 1)
        self.resta = QLabel("")
        self.resta.setFont(estilo.mono(15, True))
        fila.addWidget(self.resta)
        self.caja.addLayout(fila)
        fila = QHBoxLayout()
        self.artista = EtiquetaCorta(estilo.texto(9), estilo.TENUE)
        fila.addWidget(self.artista, 1)
        self.intro = QLabel("")
        self.intro.setFont(estilo.mono(10, True))
        self.intro.setStyleSheet("color: #fbbf24;")
        fila.addWidget(self.intro)
        fila.addSpacing(8)
        self.va = QLabel("")
        self.va.setFont(estilo.mono(8.5))
        self.va.setObjectName("tenue")
        fila.addWidget(self.va)
        self.caja.addLayout(fila)
        self.barra = BarraAvance()
        self.barra.setFixedHeight(7)
        self.caja.addWidget(self.barra)
        mandos = QHBoxLayout()
        mandos.setSpacing(5)
        self.b_play = boton("▶", "verde", lambda: self._accion("reproducir"))
        self.b_play.setToolTip(tr("Reproducir (o seguir tras la pausa)"))
        self.b_pausa = boton("❚❚", "", lambda: self._accion("pausa"))
        self.b_pausa.setToolTip(tr("Pausa"))
        self.b_parar = boton("■", "", lambda: self._accion("parar"))
        self.b_parar.setToolTip(tr("Parar"))
        self.b_sig = boton("⏭", "", lambda: self._accion("siguiente"))
        self.b_sig.setToolTip(tr("Saltar al siguiente"))
        for b in (self.b_play, self.b_pausa, self.b_parar, self.b_sig):
            b.setFixedHeight(30)
            b.setMinimumWidth(30)
            mandos.addWidget(b, 1)
        self.caja.addLayout(mandos)
        ajustes = QHBoxLayout()
        ajustes.setSpacing(5)
        self.modo = _combo([(m, tr(modaux.NOMBRE_MODO[m])) for m in modaux.MODOS], "asistido",
                           lambda v: self._ajuste(modo=v))
        self.modo.setToolTip(tr("Manual: cada audio se lanza a mano. Asistido: encadena hasta un punto de "
                                "parada. Automático: lo encadena todo."))
        ajustes.addWidget(self.modo, 1)
        self.principal = _combo([(m, tr(modaux.CORTO_PRINCIPAL[m])) for m in modaux.CON_PRINCIPAL], "encima",
                                lambda v: self._ajuste(principal=v))
        self.principal.setToolTip(tr("Qué le pasa a la emisión principal mientras suena esta lista. "
                                     "La principal nunca se para: sigue su hora por debajo."))
        ajustes.addWidget(self.principal, 1)
        self.caja.addLayout(ajustes)
        self.lista = VistaLista()
        self.lista.itemDoubleClicked.connect(lambda it: self._accion("reproducir", indice=self.lista.row(it)))
        self.lista.customContextMenuRequested.connect(self._menu)
        self.lista.soltados.connect(self._soltados)
        self.lista.movido.connect(lambda de, a: self._accion("mover", indice=de, destino=a))
        self.caja.addWidget(self.lista, 1)
        pie = QHBoxLayout()
        pie.setSpacing(5)
        pie.addWidget(boton("+ " + tr("Audios…"), "pequeno", self._anadir_ficheros))
        pie.addWidget(boton("+ " + tr("Carpeta o lista…"), "pequeno", self._anadir_carpeta))
        self.total = EtiquetaCorta(estilo.texto(8.5), estilo.TENUE)
        pie.addWidget(self.total, 1)
        self.caja.addLayout(pie)

    # ------------------------------------------------------------ ordenes

    def _accion(self, accion: str, **d) -> None:
        self.pagina.accion(dict(d, accion=accion, lista=self.n))

    def _ajuste(self, **campos) -> None:
        self._accion("ajustes", campos=campos)

    def _anadir_ficheros(self) -> None:
        r, _ = QFileDialog.getOpenFileNames(self, tr("Añadir audios a %s") % self.est.get("visible", ""), "",
                                            filtro_audio())
        if r:
            self._accion("anadir", rutas=r)

    def _anadir_carpeta(self) -> None:
        menu = QMenu(self)
        menu.addAction(tr("Una carpeta…"), lambda: self._elegir_carpeta())
        menu.addAction(tr("Una lista .m3u / .pls…"), lambda: self._elegir_lista())
        menu.exec(self.cursor().pos())

    def _elegir_carpeta(self) -> None:
        c = QFileDialog.getExistingDirectory(self, tr("Carpeta de audios"))
        if c:
            self._accion("anadir", rutas=[c])

    def _elegir_lista(self) -> None:
        r, _ = QFileDialog.getOpenFileName(self, tr("Lista"), "", tr("Listas (*.m3u *.m3u8 *.pls)"))
        if r:
            self._accion("anadir", rutas=[r])

    def _soltados(self, rutas_: list, fila: int) -> None:
        if rutas_:
            self._accion("anadir", rutas=rutas_, posicion=fila)

    def _elegidas(self) -> list:
        return sorted(self.lista.row(it) for it in self.lista.selectedItems())

    def _menu(self, pos) -> None:
        it = self.lista.itemAt(pos)
        menu = QMenu(self)
        if it is not None:
            i = self.lista.row(it)
            d = self.elementos[i] if i < len(self.elementos) else {}
            menu.addAction(tr("Reproducir ahora"), lambda: self._accion("reproducir", indice=i))
            menu.addAction(tr("Poner como siguiente"), lambda: self._accion("cue", indice=i))
            a = menu.addAction(tr("Punto de parada después de este"), lambda: self._accion("parada", indice=i))
            a.setCheckable(True)
            a.setChecked(bool(d.get("parar")))
            menu.addSeparator()
            menu.addAction(tr("Preescuchar"), lambda: self.pagina.accion({"accion": "preescuchar", "lista": self.n,
                                                                           "indice": i}))
            menu.addAction(tr("Preescuchar el final"), lambda: self.pagina.accion(
                {"accion": "preescuchar", "lista": self.n, "indice": i, "final": True}))
            menu.addAction(tr("Intro…"), lambda: self.pagina.intro_a_mano(d.get("ruta", ""), d.get("intro", 0.0)))
            menu.addSeparator()
            elegidas = self._elegidas() or [i]
            menu.addAction(tr("Quitar de la lista") + ("  (%d)" % len(elegidas) if len(elegidas) > 1 else ""),
                           lambda: self._accion("quitar", indices=elegidas))
        else:
            menu.addAction(tr("Añadir audios…"), self._anadir_ficheros)
        menu.exec(self.lista.viewport().mapToGlobal(pos))

    def _opciones(self) -> None:
        e = self.est
        menu = QMenu(self)
        menu.addAction(tr("Cambiar el nombre…"), self._renombrar)
        a = menu.addAction(tr("Bucle: al acabar, volver al principio"), lambda: self._ajuste(bucle=not e.get("bucle")))
        a.setCheckable(True)
        a.setChecked(bool(e.get("bucle")))
        a = menu.addAction(tr("Anunciar el título (RDS, Icecast) mientras suena"),
                           lambda: self._ajuste(titulo=not e.get("titulo")))
        a.setCheckable(True)
        a.setChecked(bool(e.get("titulo")))
        menu.addAction(tr("Cuánto baja la principal… (%g dB)") % e.get("bajada_db", 12), self._bajada)
        menu.addAction(tr("Volumen de esta lista… (%+g dB)") % e.get("ganancia_db", 0), self._ganancia)
        sub = menu.addMenu(tr("Salida"))
        grupo = []
        a = sub.addAction(tr("Con la emisión (misma salida y mezcla)"), lambda: self._ajuste(salida=""))
        a.setCheckable(True)
        a.setChecked(not e.get("salida"))
        grupo.append(a)
        sub.addSeparator()
        for valor, texto in salidas_de_tarjeta(self.pagina.ctx.nucleo):
            a = sub.addAction(texto, lambda v=valor: self._ajuste(salida=v))
            a.setCheckable(True)
            a.setChecked(e.get("salida") == valor)
        menu.addSeparator()
        menu.addAction(tr("Guardar la lista como…"), self._guardar)
        menu.addAction(tr("Vaciar la lista"), self._vaciar)
        menu.exec(self.b_opciones.mapToGlobal(self.b_opciones.rect().bottomLeft()))

    def _renombrar(self) -> None:
        t, ok = QInputDialog.getText(self, tr("Nombre"), tr("Nombre de la lista:"), text=self.est.get("nombre", ""))
        if ok:
            self._ajuste(nombre=t)

    def _bajada(self) -> None:
        v, ok = QInputDialog.getDouble(self, tr("Bajar la principal"), tr("dB que baja la principal:"),
                                       float(self.est.get("bajada_db", 12)), 0, 60, 1)
        if ok:
            self._ajuste(bajada_db=v)

    def _ganancia(self) -> None:
        v, ok = QInputDialog.getDouble(self, tr("Volumen"), tr("dB (sobre el volumen igualado):"),
                                       float(self.est.get("ganancia_db", 0)), -24, 12, 1)
        if ok:
            self._ajuste(ganancia_db=v)

    def _guardar(self) -> None:
        r, _ = QFileDialog.getSaveFileName(self, tr("Guardar la lista"), (self.est.get("visible") or "lista") + ".m3u8",
                                           tr("Lista (*.m3u8)"))
        if r:
            error = self.pagina.ctx.nucleo.aux.guardar_lista(self.n, r)
            self.pagina.ctx.avisar(error or tr("Lista guardada en %s") % os.path.normpath(r), bool(error))

    def _vaciar(self) -> None:
        if QMessageBox.question(self, tr("Vaciar"), tr("¿Quitar todos los audios de «%s»?") % self.est.get("visible", "")) \
                == QMessageBox.StandardButton.Yes:
            self._accion("vaciar")

    # ------------------------------------------------------------ pintar

    def actualizar(self, e: dict, ahora: float) -> None:
        self.est = e
        self.nombre.poner(e["visible"].upper())
        sal = e.get("salida")
        estados = {"sonando": tr("sonando"), "pausa": tr("en pausa"), "parado": tr("parada")}
        texto = estados.get(e["estado"], "")
        if sal:
            texto += "   ·   " + tr("por %s") % sal.split("|", 1)[-1]
        self.estado.poner(texto)
        _poner_combo(self.modo, e["modo"])
        _poner_combo(self.principal, e["principal"])
        if "elementos" in e:
            self._repoblar(e["elementos"])
        self._marcas(e)
        sonando = e["estado"] == "sonando"
        self.b_play.setEnabled(e.get("listo", True))
        if e["estado"] in ("sonando", "pausa"):
            self.titulo.poner(e["que"])
            self.artista.poner(e.get("quien") or "")
            va = e["va"] if e["estado"] == "pausa" else max(0.0, ahora - e["t_ini"])
            dur = e.get("dur") or 0.0
            self.barra.poner(va / dur if dur else 0.0, "jingle")
            self.va.setText(mmss(va) + (" / " + mmss(dur) if dur else ""))
            self.resta.setText("-" + mmss(dur - va) if dur and sonando else (tr("PAUSA") if not sonando else ""))
            intro = e.get("intro") or 0.0
            self.intro.setText(tr("INTRO %s") % mmss(intro - va) if sonando and intro > va else "")
        else:
            self.titulo.poner(tr("Lista vacía") if not e["n_elementos"] else
                              (tr("Siguiente: %s") % self.elementos[e["cursor"]]["titulo"]
                               if 0 <= e["cursor"] < len(self.elementos) else tr("Al final de la lista")))
            self.artista.poner("")
            self.barra.poner(0.0)
            self.va.setText("")
            self.resta.setText("")
            self.intro.setText("")
        partes = [tr("%d audios") % e["n_elementos"]] if e["n_elementos"] != 1 else [tr("1 audio")]
        if e.get("total"):
            partes.append(mmss(e["total"]))
        if e.get("resta") is not None and sonando:
            partes.append(tr("se para a las %s") % hms(e["fin"]))
        self.total.poner("  ·  ".join(partes))

    def _repoblar(self, elementos: list) -> None:
        self.elementos = elementos
        barra = self.lista.verticalScrollBar().value()
        elegidas = set(self._elegidas())
        self.lista.blockSignals(True)
        self.lista.clear()
        for i, d in enumerate(elementos):
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, dict(d))
            it.setToolTip(d["ruta"])
            self.lista.addItem(it)
            if i in elegidas:
                it.setSelected(True)
        self.lista.blockSignals(False)
        self.lista.verticalScrollBar().setValue(barra)

    def _marcas(self, e: dict) -> None:
        sonando = e["actual"] if e["estado"] == "sonando" else -1
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            d = it.data(Qt.ItemDataRole.UserRole)
            s, c = i == sonando, i == e["cursor"]
            if d.get("sonando") != s or d.get("siguiente") != c:
                d = dict(d, sonando=s, siguiente=c)
                it.setData(Qt.ItemDataRole.UserRole, d)


# ================================================================ botonera

class BotonCart(QWidget):
    def __init__(self, pagina, i: int):
        super().__init__()
        self.pagina = pagina
        self.i = i
        self.d = {}
        self.va = 0.0
        self.setMinimumSize(70, 58)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    def poner(self, d: dict, ahora: float) -> None:
        va = max(0.0, ahora - d["t_ini"]) if d.get("sonando") else 0.0
        if d != self.d or abs(va - self.va) > 0.15:
            self.d, self.va = d, va
            self.setToolTip(d.get("ruta") or tr("Sin audio: clic derecho para asignar uno, o suelta aquí un fichero"))
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.d.get("ruta"):
                self.pagina.accion({"accion": "disparar", "boton": self.i})
            else:
                self._asignar()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.pagina.accion({"accion": "asignar", "boton": self.i, "ruta": urls[0]})

    def _asignar(self) -> None:
        r, _ = QFileDialog.getOpenFileName(self, tr("Audio del botón %d") % (self.i + 1), "", filtro_audio())
        if r:
            self.pagina.accion({"accion": "asignar", "boton": self.i, "ruta": r})

    def _menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction(tr("Asignar un audio…"), self._asignar)
        if self.d.get("ruta"):
            menu.addAction(tr("Cambiar la etiqueta…"), self._etiqueta)
            a = menu.addAction(tr("En bucle (un colchón)"), lambda: self.pagina.accion(
                {"accion": "boton", "boton": self.i, "campos": {"bucle": not self.d.get("bucle")}}))
            a.setCheckable(True)
            a.setChecked(bool(self.d.get("bucle")))
            menu.addAction(tr("Preescuchar"), lambda: self.pagina.accion({"accion": "preescuchar", "boton": self.i}))
            menu.addSeparator()
            menu.addAction(tr("Quitar el audio"), lambda: self.pagina.accion({"accion": "asignar", "boton": self.i,
                                                                               "ruta": ""}))
        menu.exec(self.mapToGlobal(pos))

    def _etiqueta(self) -> None:
        t, ok = QInputDialog.getText(self, tr("Etiqueta"), tr("Texto del botón:"),
                                     text=self.d.get("etiqueta", "") if self.d.get("propia") else "")
        if ok:
            self.pagina.accion({"accion": "boton", "boton": self.i, "campos": {"etiqueta": t}})

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        d = self.d
        sonando = d.get("sonando")
        if not d.get("ruta"):
            p.setPen(QPen(QColor(estilo.BORDE), 1, Qt.PenStyle.DashLine))
            p.setBrush(QColor("#12161b"))
        else:
            p.setPen(QPen(QColor(COLOR_AUX if sonando else "#3b3150"), 1.5))
            p.setBrush(QColor("#2a1f3d" if not sonando else "#3d2a5c"))
        p.drawRoundedRect(r, 6, 6)
        if sonando and d.get("dur"):
            f = min(1.0, self.va / d["dur"])
            p.setPen(Qt.PenStyle.NoPen)
            c = QColor(COLOR_AUX)
            c.setAlpha(110)
            p.setBrush(c)
            p.setClipRect(QRectF(0, 0, self.width() * f, self.height()))
            p.drawRoundedRect(r, 6, 6)
            p.setClipping(False)
        p.setPen(QColor(estilo.TENUE))
        p.setFont(estilo.mono(7.5))
        p.drawText(r.adjusted(6, 3, -6, -3), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
                   str(self.i + 1) + ("  ∞" if d.get("bucle") else ""))
        if d.get("ruta"):
            p.setPen(QColor("#ffffff"))
            p.setFont(estilo.texto(8.5, True))
            p.drawText(r.adjusted(5, 12, -5, -12), int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
                       d.get("etiqueta", ""))
            if d.get("dur"):
                p.setPen(QColor("#ffffff" if sonando else estilo.TENUE))
                p.setFont(estilo.mono(7.5, bool(sonando)))
                t = ("-" + mmss(d["dur"] - self.va)) if sonando else mmss(d["dur"])
                p.drawText(r.adjusted(6, 3, -6, -3), int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom), t)


# ================================================================ la pagina

class PaginaAuxiliares(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._version = -1
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        raiz.setSpacing(14)

        listas = QWidget()
        rejilla = QGridLayout(listas)
        rejilla.setContentsMargins(0, 0, 0, 0)
        rejilla.setSpacing(14)
        self.paneles = []
        for n in range(modaux.N_LISTAS):
            p = PanelLista(self, n)
            rejilla.addWidget(p, n // 2, n % 2)
            self.paneles.append(p)
        raiz.addWidget(en_scroll(listas), 1)          # en una ventana pequena, antes desplazar que montar

        der = QVBoxLayout()
        der.setSpacing(14)
        self.b_todo = boton("■  " + tr("PARAR TODO"), "rojo", lambda: self.accion({"accion": "parar_todo"}))
        self.b_todo.setMinimumHeight(40)
        self.b_todo.setToolTip(tr("Para las cuatro listas y la botonera (la emisión principal sigue)"))
        der.addWidget(self.b_todo)
        self.aviso = QLabel("")
        self.aviso.setObjectName("aviso")
        self.aviso.setWordWrap(True)
        self.aviso.setVisible(False)
        der.addWidget(self.aviso)

        t = Tarjeta(N_("Botonera"))
        caja = QGridLayout()
        caja.setSpacing(6)
        self.botones = []
        for i in range(modaux.N_BOTONES):
            b = BotonCart(self, i)
            caja.addWidget(b, i // 4, i % 4)
            self.botones.append(b)
        t.caja.addLayout(caja)
        fila = QHBoxLayout()
        self.b_principal = _combo([(m, tr(modaux.CORTO_PRINCIPAL[m])) for m in modaux.CON_PRINCIPAL], "encima",
                                  lambda v: self.accion({"accion": "botonera", "campos": {"principal": v}}))
        fila.addWidget(self.b_principal, 1)
        fila.addWidget(boton(tr("Parar botonera"), "pequeno", lambda: self.accion({"accion": "parar_botonera"})))
        t.caja.addLayout(fila)
        n = QLabel(tr("Clic: lanzar o parar. Clic derecho: asignar, etiqueta, bucle. También se pueden soltar "
                      "ficheros encima."))
        n.setObjectName("ayuda")
        n.setWordWrap(True)
        t.caja.addWidget(n)
        der.addWidget(t)

        t2 = Tarjeta(N_("Preescucha"))
        self.pre_tarjeta = QComboBox()
        self.pre_tarjeta.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.pre_tarjeta.currentIndexChanged.connect(self._pre_tarjeta)
        self.pre_tarjeta.setToolTip(tr("Por qué tarjeta se preescucha (la de los cascos, no la de antena)"))
        self.pre_tarjeta.setMinimumContentsLength(18)
        self.pre_tarjeta.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        t2.caja.addWidget(self.pre_tarjeta)
        self.pre_misma = QLabel(tr("Ojo: es la misma tarjeta que la emisión, la preescucha se oiría en antena."))
        self.pre_misma.setObjectName("mal")
        self.pre_misma.setWordWrap(True)
        t2.caja.addWidget(self.pre_misma)
        self.pre_que = EtiquetaCorta(estilo.texto(10, True))
        t2.caja.addWidget(self.pre_que)
        self.pre_barra = BarraAvance()
        self.pre_barra.setFixedHeight(8)
        t2.caja.addWidget(self.pre_barra)
        fila = QHBoxLayout()
        self.pre_t = QLabel("")
        self.pre_t.setFont(estilo.mono(9))
        self.pre_t.setObjectName("tenue")
        fila.addWidget(self.pre_t, 1)
        b = boton(tr("Marcar intro aquí"), "pequeno", self._intro_pre)
        b.setToolTip(tr("Púlsalo justo cuando entra la voz: queda apuntado dónde acaba la intro"))
        fila.addWidget(b)
        fila.addWidget(boton("■", "pequeno", lambda: self.accion({"accion": "parar_preescucha"})))
        t2.caja.addLayout(fila)
        der.addWidget(t2)
        der.addStretch(1)
        lado = QWidget()
        lado.setLayout(der)
        lado.setFixedWidth(340)
        raiz.addWidget(lado)
        self._cargar_tarjetas()

    def cargar(self) -> None:
        self._version = -1
        self._cargar_tarjetas()

    def _cargar_tarjetas(self) -> None:
        e = self.ctx.nucleo.aux.estado(-2)["preescucha"]
        actual = "%s|%s" % (e["api"], e["dispositivo"]) if e["dispositivo"] else ""
        self.pre_tarjeta.blockSignals(True)
        self.pre_tarjeta.clear()
        self.pre_tarjeta.addItem(tr("Predeterminada del sistema"), "")
        for valor, texto in salidas_de_tarjeta(self.ctx.nucleo):
            self.pre_tarjeta.addItem(texto, valor)
        i = self.pre_tarjeta.findData(actual)
        self.pre_tarjeta.setCurrentIndex(max(0, i))
        self.pre_tarjeta.blockSignals(False)

    def _pre_tarjeta(self, _) -> None:
        v = self.pre_tarjeta.currentData() or ""
        api, _, nombre = v.partition("|")
        self.accion({"accion": "dispositivo_preescucha", "api": api, "dispositivo": nombre})

    def _intro_pre(self) -> None:
        bien, mensaje = self.ctx.nucleo.marcar_intro_preescucha()
        self.ctx.avisar(mensaje, not bien)

    def intro_a_mano(self, ruta: str, actual: float) -> None:
        v, ok = QInputDialog.getDouble(self, tr("Intro"), tr("Segundos de intro (0 = sin marca):"),
                                       float(actual or 0), 0, 600, 1)
        if ok and ruta:
            bien, mensaje = self.ctx.nucleo.marcar_intro(ruta, v)
            self.ctx.avisar(mensaje, not bien)

    def accion(self, d: dict) -> None:
        bien, mensaje = self.ctx.nucleo.aux.accion(d)
        if mensaje:
            self.ctx.avisar(mensaje, not bien)
        self.actualizar()

    def actualizar(self, _e=None) -> None:
        aux = self.ctx.nucleo.aux
        e = aux.estado(self._version)
        self._version = e["version"]
        import time
        ahora = time.time()
        for p, est in zip(self.paneles, e["listas"]):
            p.actualizar(est, ahora)
        for b, est in zip(self.botones, e["botonera"]["botones"]):
            b.poner(est, ahora)
        _poner_combo(self.b_principal, e["botonera"]["principal"])
        pre = e["preescucha"]
        self.pre_misma.setVisible(bool(pre.get("misma")))
        if pre["sonando"]:
            self.pre_que.poner(pre["que"])
            ofs = pre.get("ofs", 0.0)
            self.pre_barra.poner(pre["va"] / pre["dur"] if pre["dur"] else 0.0, "jingle")
            self.pre_t.setText(mmss(ofs + pre["va"]) + (" / " + mmss(ofs + pre["dur"]) if pre["dur"] else ""))
        else:
            self.pre_que.poner(tr("Nada en preescucha"))
            self.pre_barra.poner(0.0)
            self.pre_t.setText("")
        textos = []
        if not e["listo"]:
            textos.append(tr("No se está emitiendo: las listas que salen con la emisión y la botonera esperan "
                             "a que empiece. Las que tienen su propia tarjeta funcionan igual."))
        if e["emergencia"]["activa"]:
            textos.append(tr("LISTA DE EMERGENCIA EN ANTENA: la emisión principal está en silencio."))
        textos += [x["texto"] for x in e["avisos"][-2:]]
        self.aviso.setText("\n".join(textos))
        self.aviso.setVisible(bool(textos))
