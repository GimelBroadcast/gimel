# -*- coding: utf-8 -*-
"""
Las paginas de la ventana: la de emision y las de configuracion.

Las de configuracion trabajan sobre una copia de la configuracion (ctx.cfg)
que la ventana guarda o descarta entera; ninguna toca el nucleo por su cuenta
salvo para preguntar (que hay en una carpeta, que tarjetas hay).
"""

import copy
import os
import time
from datetime import datetime

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QPainter
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QFrame, QGridLayout,
                             QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
                             QMessageBox, QPushButton, QScrollArea, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from .. import config as modconfig
from ..config import CUE_BREAK, CUE_ENDBREAK
from ..esquema import ESQUEMA, PLANTILLAS_CUE
from ..idioma import N_, tr
from ..registro import NOMBRES as NOMBRES_REGISTRO
from . import estilo
from .formulario import Formulario
from .widgets import (BarraAvance, CampoRuta, Chip, EtiquetaCorta, ListaPauta, RelojHora,
                      Vumetro, hms, mmss)


def boton(texto: str, clase: str = "", al_pulsar=None) -> QPushButton:
    b = QPushButton(texto)
    if clase:
        b.setProperty("clase", clase)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if al_pulsar is not None:
        b.clicked.connect(al_pulsar)
    return b


def reestilar(w) -> None:
    """Tras cambiar una propiedad de la que depende el estilo."""
    w.style().unpolish(w)
    w.style().polish(w)


class Tarjeta(QFrame):
    def __init__(self, titulo: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("tarjeta")
        self.caja = QVBoxLayout(self)
        self.caja.setContentsMargins(18, 14, 18, 16)
        self.caja.setSpacing(8)
        self.rotulo = None
        if titulo:
            self.rotulo = QLabel(tr(titulo).upper())
            self.rotulo.setObjectName("rotulo")
            self.rotulo.setFont(estilo.texto(8, True, 1.6))
            self.caja.addWidget(self.rotulo)


def en_scroll(contenido: QWidget) -> QScrollArea:
    s = QScrollArea()
    s.setWidgetResizable(True)
    s.setFrameShape(QFrame.Shape.NoFrame)
    s.setWidget(contenido)
    # despues de setWidget, que es quien se lo pone: sin esto pinta el fondo de
    # la ventana encima del de la tarjeta
    contenido.setAutoFillBackground(False)
    s.viewport().setAutoFillBackground(False)
    return s


def horario(x) -> str:
    return "%02d–%02d" % (x.desde, x.hasta)


# ================================================================ emision

class PaginaEmision(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._t_usuario = 0.0
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        raiz.setSpacing(14)

        self.error = QLabel("")
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.error.setVisible(False)
        raiz.addWidget(self.error)

        arriba = QHBoxLayout()
        arriba.setSpacing(14)

        # ---- lo que suena
        t = Tarjeta(N_("En emisión"))
        self.chip = Chip()
        t.caja.addWidget(self.chip)
        self.titulo = EtiquetaCorta(estilo.texto(23, True))
        t.caja.addWidget(self.titulo)
        self.artista = EtiquetaCorta(estilo.texto(13), estilo.TENUE)
        t.caja.addWidget(self.artista)
        t.caja.addSpacing(6)
        self.barra = BarraAvance()
        t.caja.addWidget(self.barra)
        tiempos = QHBoxLayout()
        self.va = QLabel("")
        self.va.setFont(estilo.mono(11))
        self.va.setObjectName("tenue")
        self.resta = QLabel("")
        self.resta.setFont(estilo.mono(24, True))
        tiempos.addWidget(self.va, 0, Qt.AlignmentFlag.AlignTop)
        tiempos.addStretch(1)
        tiempos.addWidget(self.resta)
        t.caja.addLayout(tiempos)
        self.encima = EtiquetaCorta(estilo.texto(10.5, True), estilo.COLOR_TIPO["jingle"])
        t.caja.addWidget(self.encima)
        self.despues = EtiquetaCorta(estilo.texto(10.5), estilo.TENUE)
        t.caja.addWidget(self.despues)
        self.aviso = EtiquetaCorta(estilo.texto(9.5), "#fbbf24")
        t.caja.addWidget(self.aviso)
        t.caja.addStretch(1)
        mandos = QHBoxLayout()
        mandos.setSpacing(10)
        self.b_emitir = boton(tr("▶  EMITIR"), "verde", self.conmutar)
        self.b_emitir.setMinimumWidth(170)
        self.b_emitir.setMinimumHeight(46)
        self.b_emitir.setFont(estilo.texto(11.5, True, 1.0))
        self.b_saltar = boton("»  " + tr("Saltar canción"), "", lambda: ctx.nucleo.saltar())
        self.b_saltar.setMinimumHeight(46)
        self.b_rehacer = boton("↻  " + tr("Rehacer la pauta"), "", lambda: ctx.nucleo.replanificar())
        self.b_rehacer.setMinimumHeight(46)
        self.b_rehacer.setToolTip(tr("Volver a planificar lo que queda de hora desde ahora mismo"))
        mandos.addWidget(self.b_emitir)
        mandos.addWidget(self.b_saltar)
        mandos.addWidget(self.b_rehacer)
        mandos.addStretch(1)
        t.caja.addLayout(mandos)
        arriba.addWidget(t, 5)

        # ---- la hora
        t2 = Tarjeta(N_("La hora"))
        self.reloj = RelojHora()
        t2.caja.addWidget(self.reloj, 1)
        self.vu = Vumetro()
        t2.caja.addWidget(self.vu)
        arriba.addWidget(t2, 3)
        raiz.addLayout(arriba, 5)

        # ---- la pauta
        t3 = Tarjeta(N_("Pauta de la hora"))
        self.rot_pauta = t3.rotulo
        self.lista = ListaPauta()
        self.scroll = en_scroll(self.lista)
        self.scroll.verticalScrollBar().actionTriggered.connect(self._tocado)
        t3.caja.addWidget(self.scroll, 1)
        raiz.addWidget(t3, 6)
        self._emitiendo = None

    def _tocado(self, *_):
        self._t_usuario = time.monotonic()

    def emitir(self) -> None:
        bien, mensaje = self.ctx.nucleo.iniciar()
        if mensaje:
            self.ctx.avisar(mensaje, not bien)

    def conmutar(self) -> None:
        if self.ctx.nucleo.emisor.emitiendo:
            self.ctx.nucleo.detener()
        else:
            self.emitir()

    def actualizar(self, e: dict) -> None:
        emite = bool(e.get("emitiendo"))
        ahora = e["reloj"]
        if e.get("error"):
            self.error.setText(e["error"])
        self.error.setVisible(bool(e.get("error")))

        if emite != self._emitiendo:
            self._emitiendo = emite
            self.b_emitir.setText(tr("■  DETENER") if emite else tr("▶  EMITIR"))
            self.b_emitir.setProperty("clase", "rojo" if emite else "verde")
            reestilar(self.b_emitir)
            self.b_saltar.setEnabled(emite)
            self.b_rehacer.setEnabled(emite)

        a = e.get("actual")
        self.chip.poner(a["tipo"] if a else "")
        if a:
            self.titulo.poner(a["titulo"])
            self.artista.poner(a.get("artista") or "")
        else:
            self.titulo.poner("…" if emite else tr("Parado"))
            self.artista.poner("" if emite else tr("Abajo, la rotación que saldría si empezaras a emitir ahora"))
        if a and emite and a["dur"] > 0:
            va = max(0.0, ahora - a["t"])
            self.barra.poner(va / a["dur"], a["tipo"])
            self.va.setText(mmss(min(va, a["dur"])))
            self.resta.setText("-" + mmss(a["dur"] - va))
        else:
            self.barra.poner(0.0)
            self.va.setText("")
            self.resta.setText("")
        j = e.get("jingle")
        self.encima.poner("♪  " + tr("encima: ") + j["titulo"] if j else "")

        pauta = e.get("pauta") or []
        sig = next((f for f in pauta if f["estado"] in ("plan", "prep", "prog")
                    and f["tipo"] not in ("silencio", "cue", "jingle")), None)
        if sig:
            self.despues.poner(tr("A continuación:   %s%s   ·   %s") % (
                sig["titulo"], "  —  " + sig["artista"] if sig.get("artista") else "", hms(sig["t"])))
        else:
            self.despues.poner("")
        avisos = e.get("avisos") or []
        if e.get("aviso_salida"):
            self.aviso.poner(e["aviso_salida"])
        elif avisos and time.time() - avisos[-1]["t"] < 90:
            self.aviso.poner("%s   %s" % (hms(avisos[-1]["t"]), avisos[-1]["texto"]))
        else:
            self.aviso.poner("")

        ancla = e.get("ancla")
        if emite and ancla:
            cuenta = mmss(ancla["t"] - ahora)
            rotulo = tr("señal horaria") if ancla["clase"] == "senal" else (ancla.get("nombre") or tr("bloque"))
        else:
            d = datetime.fromtimestamp(ahora)
            cuenta = mmss(3600 - (d.minute * 60 + d.second))
            rotulo = tr("hora en punto")
        firma = tuple((round(f["t"]), f["tipo"], f["titulo"], f["estado"], f["nota"], round(f["dur"]))
                      for f in pauta)
        self.reloj.poner(e.get("h0", 0.0), pauta, firma, ahora, cuenta, rotulo, e.get("franja", ""))
        vu = e.get("vu") or (0.0, 0.0)
        self.vu.poner(vu[0], vu[1], bool(e.get("limitando")))
        if self.lista.poner(pauta, firma):
            h0 = e.get("h0", 0.0)
            self.rot_pauta.setText((tr("PAUTA DE LA HORA") if emite else tr("ROTACIÓN PREVISTA (SIN EMITIR)"))
                                   + "   ·   %s – %s" % (hms(h0)[:5], hms(h0 + 3600)[:5]))
            if time.monotonic() - self._t_usuario > 8.0:  # sigue a lo que suena, si no la estan mirando
                y = self.lista.y_actual()
                if y is not None:
                    self.scroll.verticalScrollBar().setValue(max(0, y - 2 * ListaPauta.ALTO))


# ================================================================ lista + formulario

class FilaLista(QWidget):
    """Una entrada de la lista: nombre a la izquierda, detalle a la derecha."""

    def __init__(self):
        super().__init__()
        f = QHBoxLayout(self)
        f.setContentsMargins(2, 0, 2, 0)
        self.nombre = QLabel("")
        self.detalle = QLabel("")
        self.detalle.setObjectName("ayuda")
        f.addWidget(self.nombre, 1)
        f.addWidget(self.detalle)

    def poner(self, nombre: str, detalle: str, activo: bool) -> None:
        self.nombre.setText(nombre or tr("(sin nombre)"))
        fuente = QFont(self.nombre.font())
        fuente.setStrikeOut(not activo)
        self.nombre.setFont(fuente)
        self.nombre.setStyleSheet("color: %s;" % (estilo.TEXTO if activo else estilo.TENUE))
        self.detalle.setText(detalle)


class PaginaLista(QWidget):
    """
    Lista de cosas a la izquierda (franjas, bloques, eventos, servidores) y el
    formulario de la elegida a la derecha.
    """

    def __init__(self, ctx, titulo: str, esquema: list, lista, nuevo, detalle, activo,
                 fijo=None, nota: str = "", vacio: str = "", cabecera=None, pie=None,
                 al_cambiar=None, incrustada: bool = False):
        super().__init__()
        self.ctx = ctx
        self._lista = lista               # funcion -> la lista de objetos de ctx.cfg
        self._nuevo = nuevo               # funcion -> objeto nuevo
        self._detalle = detalle
        self._activo = activo
        self._fijo = fijo                 # funcion -> objeto fijo que va el primero (la programacion general)
        self._al_cambiar = al_cambiar
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(*((0, 0, 0, 0) if incrustada else (18, 16, 18, 16)))
        raiz.setSpacing(14)

        izq = Tarjeta(titulo)
        izq.setFixedWidth(300)
        self.lw = QListWidget()
        self.lw.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lw.currentRowChanged.connect(self._elegir)
        izq.caja.addWidget(self.lw, 1)
        botones = QGridLayout()
        botones.setSpacing(6)
        self.b_anadir = boton("+ " + tr("Añadir"), "pequeno", self._anadir)
        self.b_dup = boton(tr("Duplicar"), "pequeno", self._duplicar)
        self.b_sube = boton("▲", "pequeno", lambda: self._mover(-1))
        self.b_baja = boton("▼", "pequeno", lambda: self._mover(1))
        self.b_quita = boton(tr("Eliminar"), "pequeno", self._eliminar)
        botones.addWidget(self.b_anadir, 0, 0)
        botones.addWidget(self.b_dup, 0, 1)
        botones.addWidget(self.b_sube, 0, 2)
        botones.addWidget(self.b_baja, 0, 3)
        botones.addWidget(self.b_quita, 1, 0, 1, 2)
        izq.caja.addLayout(botones)
        if nota:
            n = QLabel(tr(nota))
            n.setObjectName("ayuda")
            n.setWordWrap(True)
            izq.caja.addWidget(n)
        raiz.addWidget(izq)

        der = Tarjeta()
        dentro = QWidget()
        col = QVBoxLayout(dentro)
        col.setContentsMargins(0, 0, 10, 0)
        self.cabecera = cabecera
        if cabecera is not None:
            col.addWidget(cabecera)
        self.form = Formulario(esquema, ctx.nucleo, lambda c: bool(c.get("solo_franja")) and self._es_fijo())
        self.form.cambiado.connect(self._cambio)
        col.addWidget(self.form)
        if pie is not None:
            col.addWidget(pie)
        col.addStretch(1)
        self.vacio = QLabel(tr(vacio or N_("No hay nada todavía. Pulsa «Añadir».")))
        self.vacio.setObjectName("tenue")
        self.vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dentro = dentro
        if incrustada:
            der.caja.addWidget(dentro)
        else:
            der.caja.addWidget(en_scroll(dentro), 1)
        der.caja.addWidget(self.vacio)
        raiz.addWidget(der, 1)

    # los objetos, con el fijo (si lo hay) delante
    def _todos(self) -> list:
        items = list(self._lista())
        return ([self._fijo()] if self._fijo else []) + items

    def _es_fijo(self) -> bool:
        return self._fijo is not None and self.lw.currentRow() == 0

    def actual(self):
        todos = self._todos()
        i = self.lw.currentRow()
        return todos[i] if 0 <= i < len(todos) else None

    def cargar(self, fila=None) -> None:
        todos = self._todos()
        if fila is None:
            fila = max(0, self.lw.currentRow())
        self.lw.blockSignals(True)
        self.lw.clear()
        for i, obj in enumerate(todos):
            it = QListWidgetItem()
            w = FilaLista()
            self._pintar_fila(w, obj, self._fijo is not None and i == 0)
            it.setSizeHint(QSize(10, 42))                 # el relleno de la hoja de estilo se come 16
            self.lw.addItem(it)
            self.lw.setItemWidget(it, w)
        self.lw.blockSignals(False)
        fila = min(fila, len(todos) - 1)
        self.lw.setCurrentRow(fila)
        self._elegir(fila)

    def _pintar_fila(self, w: FilaLista, obj, fijo: bool) -> None:
        if fijo:
            w.poner(modconfig.nombre_franja(obj.nombre), tr("el resto"), True)
        else:
            w.poner(obj.nombre, self._detalle(obj), bool(self._activo(obj)))

    def _elegir(self, fila: int) -> None:
        obj = self.actual()
        hay = obj is not None
        self._dentro.setVisible(hay)
        self.vacio.setVisible(not hay)
        fijo = self._es_fijo()
        for b in (self.b_dup, self.b_sube, self.b_baja, self.b_quita):
            b.setEnabled(hay and not fijo)
        self.form.poner(obj)
        if self._al_cambiar is not None:
            self._al_cambiar(obj)

    def _cambio(self) -> None:
        i = self.lw.currentRow()
        obj = self.actual()
        if obj is not None:
            w = self.lw.itemWidget(self.lw.item(i))
            if w is not None:
                self._pintar_fila(w, obj, self._es_fijo())
        if self._al_cambiar is not None:
            self._al_cambiar(obj)
        self.ctx.cambiado()

    def _indice(self) -> int:
        """Posicion de la fila elegida dentro de la lista de verdad (sin el fijo)."""
        return self.lw.currentRow() - (1 if self._fijo else 0)

    def _anadir(self) -> None:
        self._lista().append(self._nuevo())
        self.ctx.cambiado()
        self.cargar(len(self._todos()) - 1)

    def _duplicar(self) -> None:
        obj = self.actual()
        if obj is None or self._es_fijo():
            return
        copia = copy.deepcopy(obj)
        copia.nombre = (copia.nombre or "") + " " + tr("(copia)")
        self._lista().insert(self._indice() + 1, copia)
        self.ctx.cambiado()
        self.cargar(self.lw.currentRow() + 1)

    def _mover(self, d: int) -> None:
        lista = self._lista()
        k = self._indice()
        j = k + d
        if k < 0 or not 0 <= j < len(lista):
            return
        lista[k], lista[j] = lista[j], lista[k]
        self.ctx.cambiado()
        self.cargar(self.lw.currentRow() + d)

    def _eliminar(self) -> None:
        obj = self.actual()
        if obj is None or self._es_fijo():
            return
        r = QMessageBox.question(self, tr("Eliminar"), tr("¿Eliminar «%s»?") % (obj.nombre or ""))
        if r != QMessageBox.StandardButton.Yes:
            return
        del self._lista()[self._indice()]
        self.ctx.cambiado()
        self.cargar(max(0, self.lw.currentRow() - 1))


class EsquemaBloque(QWidget):
    """El bloque de publicidad dibujado: que va detras de que, y cuanto dura."""

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.b = None
        self.setFixedHeight(46)

    def poner(self, b) -> None:
        self.b = b
        self.update()

    def paintEvent(self, _):
        b = self.b
        if b is None:
            return
        fundido = self.ctx.cfg.senales.fundido
        trozos = [("cancion", tr("música"), tr("baja %g s") % fundido)]
        if b.silencio_antes > 0:
            trozos.append(("silencio", tr("silencio %g s") % b.silencio_antes,
                           tr("CUE a los %g s") % b.cue_tras if b.cue else ""))
        if b.jingle:
            trozos.append(("jingle_publi", tr("jingle"), tr("entrada")))
        if b.contenido == "relleno":
            trozos.append(("relleno", tr("relleno"), tr("%g s exactos") % b.duracion))
        else:
            trozos.append(("cuna", tr("cuñas"), tr("%g s exactos") % b.duracion))
        if b.silencio_despues > 0:
            trozos.append(("silencio", tr("a negro %g s") % b.silencio_despues,
                           tr("CUE a los %g s") % b.cue_retorno_tras if b.cue else ""))
        if b.jingle_salida:
            trozos.append(("jingle_publi", tr("jingle"), tr("vuelta")))
        trozos.append(("cancion", tr("música"), ""))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ancho = (self.width() - 3 * (len(trozos) - 1)) / len(trozos)
        for i, (tipo, arriba, abajo) in enumerate(trozos):
            r = QRectF(i * (ancho + 3), 0, ancho, self.height() - 6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(estilo.color(tipo))
            p.drawRoundedRect(r, 4, 4)
            p.setPen(QColor("#111111" if tipo in estilo.TEXTO_OSCURO else "#ffffff"))
            p.setFont(estilo.texto(8.5, True))
            p.drawText(r.adjusted(2, 4, -2, -r.height() / 2), int(Qt.AlignmentFlag.AlignCenter), arriba)
            p.setFont(estilo.texto(7.5))
            p.drawText(r.adjusted(2, r.height() / 2 - 2, -2, -4), int(Qt.AlignmentFlag.AlignCenter), abajo)


def pagina_franjas(ctx) -> PaginaLista:
    return PaginaLista(
        ctx, N_("Programación"), ESQUEMA["franja"], lambda: ctx.cfg.franjas, modconfig.Franja,
        horario, lambda f: f.activa, fijo=lambda: ctx.cfg.general,
        nota=N_("Cada hora se hace con la primera franja de la lista que la cubra; si no la cubre "
                "ninguna, con la programación general. El orden importa: usa ▲ y ▼."))


def pagina_publicidad(ctx) -> PaginaLista:
    esquema = EsquemaBloque(ctx)
    return PaginaLista(
        ctx, N_("Bloques"), ESQUEMA["bloque"], lambda: ctx.cfg.publicidad, modconfig.BloquePubli,
        lambda b: "min %02d · %s" % (b.minuto, horario(b)), lambda b: b.activo,
        nota=N_("Un bloque se programa en todas las horas de su rango. La música de antes y de "
                "después se reajusta sola para que la hora siga cuadrando."),
        vacio=N_("No hay bloques de publicidad ni de desconexión. Pulsa «Añadir»."),
        cabecera=esquema, al_cambiar=esquema.poner)


def pagina_eventos(ctx) -> PaginaLista:
    return PaginaLista(
        ctx, N_("Eventos a minuto fijo"), ESQUEMA["evento"], lambda: ctx.cfg.eventos,
        modconfig.EventoFijo, lambda x: "min %02d · %s" % (x.minuto, horario(x)),
        lambda x: x.activo,
        nota=N_("Un audio que arranca en un minuto exacto de la hora: un boletín, la señal de las "
                "medias, una promo. La música calla antes, igual que con la señal horaria."),
        vacio=N_("No hay eventos. Pulsa «Añadir»."))


ESTADOS_ICECAST = {"emitiendo": N_("emitiendo"), "conectando": N_("conectando…"),
                   "error": N_("sin conexión"), "parado": N_("parado")}


def texto_icecast(flujos: list, largo: bool = False) -> str:
    """El estado de los envios a Icecast, en una linea (o una por servidor)."""
    partes = []
    for f in flujos:
        t = "%s: %s" % (f["nombre"], tr(ESTADOS_ICECAST.get(f["estado"], f["estado"])))
        if f["estado"] == "emitiendo":
            t += " (%s)" % mmss(f["segundos"])
        elif f.get("detalle"):
            t += " — " + f["detalle"]
        if largo:
            t += "   ·   " + f["destino"]
            if f.get("perdidos"):
                t += "   ·   " + tr("%d bloques perdidos por atasco de red") % f["perdidos"]
        partes.append(t)
    return ("\n" if largo else "   |   ").join(partes)


def pagina_icecast(ctx) -> PaginaLista:
    estado = QLabel(tr("Los envíos se conectan al empezar a emitir."))
    estado.setObjectName("ayuda")
    estado.setWordWrap(True)
    return PaginaLista(
        ctx, N_("Servidores Icecast"), ESQUEMA["icecast"], lambda: ctx.cfg.icecast, modconfig.Icecast,
        lambda x: "%s %dk" % (x.formato, x.bitrate), lambda x: x.activo,
        nota=N_("La emisión se manda a todos los servidores activos, además de salir por la tarjeta. "
                "Para emitir solo por Icecast, elige «Sin tarjeta» en Ajustes > Salida de audio."),
        vacio=N_("No hay ningún servidor Icecast. Pulsa «Añadir»."), cabecera=estado)


# ================================================================ senales horarias

class PaginaSenales(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        dentro = QWidget()
        col = QVBoxLayout(dentro)
        col.setContentsMargins(18, 16, 18, 16)
        col.setSpacing(14)

        t = Tarjeta(N_("Señales horarias"))
        self.form = Formulario(ESQUEMA["senales"], ctx.nucleo)
        self.form.cambiado.connect(ctx.cambiado)
        t.caja.addWidget(self.form)
        col.addWidget(t)

        t2 = Tarjeta(N_("El audio de cada hora"))
        fila = QHBoxLayout()
        fila.addWidget(boton(tr("Rellenar desde una carpeta…"), "pequeno", self._rellenar))
        fila.addWidget(boton(tr("Vaciar"), "pequeno", self._vaciar))
        nota = QLabel(tr("Al rellenar, cada audio va a la hora del número que lleve en el nombre "
                         "(07.mp3, hora_14.wav…)."))
        nota.setObjectName("ayuda")
        fila.addWidget(nota)
        fila.addStretch(1)
        t2.caja.addLayout(fila)
        rej = QGridLayout()
        rej.setHorizontalSpacing(12)
        rej.setVerticalSpacing(6)
        self.campos = []
        for h in range(24):
            et = QLabel("%02d:00" % h)
            et.setFont(estilo.mono(10.5, True))
            rej.addWidget(et, h, 0, Qt.AlignmentFlag.AlignTop)
            c = CampoRuta("fichero", ctx.nucleo.resumen)
            c.cambiado.connect(lambda ruta, h=h: self._puesta(h, ruta))
            rej.addWidget(c, h, 1)
            self.campos.append(c)
        rej.setColumnStretch(1, 1)
        t2.caja.addLayout(rej)
        col.addWidget(t2)
        col.addStretch(1)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(en_scroll(dentro))

    def cargar(self) -> None:
        s = self.ctx.cfg.senales
        self.form.poner(s)
        for h, c in enumerate(self.campos):
            c.poner(s.archivos.get(str(h), ""))

    def _puesta(self, h: int, ruta: str) -> None:
        s = self.ctx.cfg.senales
        if ruta:
            s.archivos[str(h)] = ruta
        else:
            s.archivos.pop(str(h), None)
        self.ctx.cambiado()

    def _rellenar(self) -> None:
        carpeta = QFileDialog.getExistingDirectory(self, tr("Carpeta con las señales horarias"))
        if not carpeta:
            return
        encontradas = self.ctx.nucleo.autosenales(carpeta)
        if not encontradas:
            self.ctx.avisar(tr("En esa carpeta no hay audios con un número de hora en el nombre."), True)
            return
        self.ctx.cfg.senales.archivos.update(encontradas)
        self.ctx.cambiado()
        self.cargar()
        self.ctx.avisar(tr("%d horas asignadas por el número del nombre de cada fichero.") % len(encontradas))

    def _vaciar(self) -> None:
        if QMessageBox.question(self, tr("Vaciar"), tr("¿Quitar el audio de las 24 horas?")) \
                != QMessageBox.StandardButton.Yes:
            return
        self.ctx.cfg.senales.archivos.clear()
        self.ctx.cambiado()
        self.cargar()


# ================================================================ CUE y titulo

class PaginaCue(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._tipo_visto = {}
        dentro = QWidget()
        col = QVBoxLayout(dentro)
        col.setContentsMargins(18, 16, 18, 16)
        col.setSpacing(14)

        t = Tarjeta(N_("CUE de desconexión y de reconexión"))
        self.form_cue = Formulario(ESQUEMA["cue"], ctx.nucleo)
        self.form_cue.cambiado.connect(ctx.cambiado)
        t.caja.addWidget(self.form_cue)
        n = QLabel(tr("El de desconexión sale durante el silencio previo a cada bloque y el de reconexión "
                      "durante el negro final (los segundos se ponen en cada bloque). Se mandan a todos "
                      "los servidores activos de abajo.") + " " +
                   tr("Para probar la recepción hay un servidor de ejemplo en herramientas/servidor_cue.py."))
        n.setObjectName("ayuda")
        n.setWordWrap(True)
        t.caja.addWidget(n)
        col.addWidget(t)

        pie = QWidget()
        fp = QHBoxLayout(pie)
        fp.setContentsMargins(0, 8, 0, 0)
        fp.addWidget(boton(tr("Probar: desconexión"), "pequeno", lambda: self._probar("inicio")))
        fp.addWidget(boton(tr("Probar: reconexión"), "pequeno", lambda: self._probar("retorno")))
        self.resultado = QLabel("")
        self.resultado.setObjectName("ayuda")
        fp.addWidget(self.resultado, 1)
        self.destinos = PaginaLista(
            ctx, N_("Servidores"), ESQUEMA["destino_cue"], lambda: ctx.cfg.cue.destinos,
            modconfig.DestinoCue, lambda d: d.tipo, lambda d: d.activo,
            vacio=N_("No hay ningún servidor al que mandar los CUE. Pulsa «Añadir»."),
            pie=pie, al_cambiar=self._tipo, incrustada=True)
        self.destinos.setMinimumHeight(560)
        col.addWidget(self.destinos)

        t3 = Tarjeta(N_("Título en emisión"))
        self.form_meta = Formulario(ESQUEMA["metadatos"], ctx.nucleo)
        self.form_meta.cambiado.connect(ctx.cambiado)
        t3.caja.addWidget(self.form_meta)
        col.addWidget(t3)

        t4 = Tarjeta(N_("Últimos CUE enviados"))
        self.enviados = QLabel(tr("Ninguno todavía."))
        self.enviados.setObjectName("ayuda")
        self.enviados.setFont(estilo.mono(9))
        self.enviados.setTextFormat(Qt.TextFormat.PlainText)
        self.enviados.setWordWrap(True)
        t4.caja.addWidget(self.enviados)
        col.addWidget(t4)
        col.addStretch(1)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(en_scroll(dentro))

    def cargar(self) -> None:
        self._tipo_visto = {}
        self.form_cue.poner(self.ctx.cfg.cue)
        self.form_meta.poner(self.ctx.cfg.metadatos)
        self.destinos.cargar()

    def _tipo(self, d) -> None:
        """Al cambiar el tipo de un servidor se proponen el destino y los mensajes de ese tipo."""
        if d is None:
            return
        antes = self._tipo_visto.get(id(d))
        self._tipo_visto[id(d)] = d.tipo
        if antes is None or antes == d.tipo or d.tipo not in PLANTILLAS_CUE:
            return
        viejo, nuevo = PLANTILLAS_CUE.get(antes), PLANTILLAS_CUE[d.tipo]
        if viejo is None or d.destino == viejo[0]:
            d.destino = nuevo[0]
        if viejo is None or d.inicio == viejo[1]:
            d.inicio = nuevo[1]
        if viejo is None or d.retorno == viejo[2]:
            d.retorno = nuevo[2]
        QTimer.singleShot(0, lambda: self.destinos.form.poner(d))

    def _probar(self, evento: str) -> None:
        d = self.destinos.actual()
        if d is None:
            return
        self.resultado.setText(tr("Enviando…"))
        self.resultado.repaint()
        r = self.ctx.nucleo.probar_cue(d, evento)
        self.resultado.setObjectName("mal" if r.startswith("ERROR") else "ayuda")
        reestilar(self.resultado)
        self.resultado.setText(r)

    def actualizar(self, e: dict) -> None:
        cues = e.get("cues") or []
        if not cues:
            return
        self.enviados.setText("\n".join(
            "%s  %-9s  %-18s %s" % (hms(c["hora"]), CUE_BREAK if c["evento"] == "inicio" else CUE_ENDBREAK,
                                    c["nombre"][:18], c["resultado"]) for c in reversed(cues)))


# ================================================================ ajustes

class PaginaAjustes(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        dentro = QWidget()
        col = QVBoxLayout(dentro)
        col.setContentsMargins(18, 16, 18, 16)
        col.setSpacing(14)
        self.formularios = []
        for titulo, clave, obj in ((N_("Emisora"), "sistema", lambda: ctx.cfg),
                                   (N_("Salida de audio"), "salida", lambda: ctx.cfg.salida),
                                   (N_("Mezcla"), "mezcla", lambda: ctx.cfg.mezcla),
                                   (N_("Panel web"), "web", lambda: ctx.cfg.web)):
            t = Tarjeta(titulo)
            f = Formulario(ESQUEMA[clave], ctx.nucleo)
            f.cambiado.connect(ctx.cambiado)
            t.caja.addWidget(f)
            if clave == "web":
                self.url = QLabel("")
                self.url.setObjectName("ayuda")
                self.url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                t.caja.addWidget(self.url)
            col.addWidget(t)
            self.formularios.append((f, obj))
        col.addStretch(1)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(en_scroll(dentro))

    def cargar(self) -> None:
        for f, obj in self.formularios:
            f.poner(obj())
        web = self.ctx.web
        self.url.setText(tr("Ahora mismo: %s") % web.url if web is not None and web.url
                         else tr("Ahora mismo el panel web no está en marcha."))


# ================================================================ registro

class PaginaRegistro(QWidget):
    COLUMNAS = (N_("Hora"), N_("Tipo"), N_("Título"), N_("Artista"), N_("Segundos"), N_("Nota"))

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        t = Tarjeta(N_("Registro de emisión"))
        fila = QHBoxLayout()
        self.dia = QComboBox()
        self.dia.setMinimumWidth(140)
        self.dia.currentIndexChanged.connect(lambda _: self._leer())
        fila.addWidget(self.dia)
        fila.addWidget(boton(tr("Actualizar"), "pequeno", self.cargar))
        fila.addWidget(boton(tr("Abrir la carpeta"), "pequeno", self._abrir))
        self.cuenta = QLabel("")
        self.cuenta.setObjectName("ayuda")
        fila.addWidget(self.cuenta)
        fila.addStretch(1)
        t.caja.addLayout(fila)
        self.tabla = QTableWidget(0, len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels([tr(x) for x in self.COLUMNAS])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setShowGrid(False)
        cab = self.tabla.horizontalHeader()
        cab.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        cab.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        t.caja.addWidget(self.tabla, 1)
        raiz.addWidget(t)

    def cargar(self) -> None:
        dias = self.ctx.nucleo.registro.dias()
        elegido = self.dia.currentText()
        self.dia.blockSignals(True)
        self.dia.clear()
        self.dia.addItems(dias)
        if elegido in dias:
            self.dia.setCurrentText(elegido)
        self.dia.blockSignals(False)
        self._leer()

    def _leer(self) -> None:
        filas = self.ctx.nucleo.registro.leer(self.dia.currentText()) if self.dia.count() else []
        filas = list(reversed(filas))
        self.tabla.setRowCount(len(filas))
        for i, f in enumerate(filas):
            sistema = f.get("tipo") == NOMBRES_REGISTRO["sistema"]
            for j, clave in enumerate(("hora", "tipo", "titulo", "artista", "segundos", "nota")):
                texto = f.get(clave, "")
                if clave == "tipo" or (clave == "titulo" and sistema):
                    texto = tr(texto)                     # el fichero se escribe siempre en español
                self.tabla.setItem(i, j, QTableWidgetItem(texto))
        self.cuenta.setText(tr("%d líneas") % len(filas) if filas else tr("Todavía no se ha emitido nada."))

    def _abrir(self) -> None:
        carpeta = self.ctx.nucleo.registro.carpeta
        if carpeta and os.path.isdir(carpeta):
            QDesktopServices.openUrl(QUrl.fromLocalFile(carpeta))
