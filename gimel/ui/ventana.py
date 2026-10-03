# -*- coding: utf-8 -*-
"""
Ventana principal de GIMEL (PyQt6).

    menus      archivo, emision, ver, idioma y ayuda
    cabecera   marca, emisora, piloto de emision y reloj
    lateral    las paginas, y guardar / descartar los cambios de configuracion
    centro     la pagina elegida
    pie        salida de audio, panel web, analisis de la biblioteca

La ventana no sabe nada de audio: cada decima de segundo le pide al nucleo una
foto del estado y la pinta. Las paginas de configuracion trabajan sobre una
copia (self.cfg) que solo llega al nucleo al pulsar Guardar.

Cambiar de idioma no reinicia nada: se vuelve a montar lo que se ve (menus,
armazon y paginas) con los textos nuevos, y la configuracion a medio tocar
sigue donde estaba.
"""

import ctypes
import os
import sys
from datetime import datetime

from PyQt6.QtCore import QLibraryInfo, QLocale, QRectF, Qt, QTimer, QTranslator, QUrl
from PyQt6.QtGui import (QActionGroup, QColor, QDesktopServices, QIcon, QKeySequence, QPainter,
                         QPalette, QPen, QPixmap)
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QHBoxLayout, QLabel,
                             QMainWindow, QMenuBar, QMessageBox, QStackedWidget, QVBoxLayout,
                             QWidget)

from .. import NOMBRE, __version__
from .. import config as modconfig
from .. import idioma
from ..idioma import N_, tr
from . import estilo
from .paginas import (PaginaAjustes, PaginaCue, PaginaEmision, PaginaRegistro, PaginaSenales,
                      boton, pagina_eventos, pagina_franjas, pagina_icecast, pagina_publicidad,
                      reestilar, texto_icecast)
from .widgets import Lampara, hms

DIAS = (N_("lunes"), N_("martes"), N_("miércoles"), N_("jueves"), N_("viernes"), N_("sábado"),
        N_("domingo"))
MESES = (N_("enero"), N_("febrero"), N_("marzo"), N_("abril"), N_("mayo"), N_("junio"),
         N_("julio"), N_("agosto"), N_("septiembre"), N_("octubre"), N_("noviembre"),
         N_("diciembre"))


def pintar_logo(p: QPainter, r: QRectF) -> None:
    """La guimel: la letra que da nombre al programa."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(estilo.ACENTO), max(1.5, r.width() * 0.045)))
    p.setBrush(QColor("#1b2028"))
    m = r.width() * 0.05
    p.drawRoundedRect(r.adjusted(m, m, -m, -m), r.width() * 0.2, r.width() * 0.2)
    p.setPen(QColor(estilo.ACENTO))
    f = estilo.texto(1, True)
    f.setPixelSize(int(r.height() * 0.66))
    p.setFont(f)
    p.drawText(r.adjusted(0, -r.height() * 0.05, 0, 0), int(Qt.AlignmentFlag.AlignCenter), "ג")


def icono() -> QIcon:
    pm = QPixmap(256, 256)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    pintar_logo(p, QRectF(0, 0, 256, 256))
    p.end()
    return QIcon(pm)


class Logo(QWidget):
    def __init__(self, lado: int = 40):
        super().__init__()
        self.setFixedSize(lado, lado)

    def paintEvent(self, _):
        pintar_logo(QPainter(self), QRectF(0, 0, self.width(), self.height()))


class Contexto:
    """Lo que las paginas necesitan de la ventana."""

    def __init__(self, ventana, nucleo, web):
        self._v = ventana
        self.nucleo = nucleo
        self.web = web

    @property
    def cfg(self):
        return self._v.cfg

    def cambiado(self) -> None:
        self._v.marcar(True)

    def avisar(self, texto: str, malo: bool = False) -> None:
        self._v.avisar(texto, malo)


class Ventana(QMainWindow):
    PAGINAS = (("emision", N_("Emisión")), ("franjas", N_("Franjas")),
               ("senales", N_("Señales horarias")),
               ("publicidad", N_("Publicidad / desconexión")), ("eventos", N_("Eventos")),
               ("cue", N_("CUE y título")), ("icecast", N_("Icecast")), ("ajustes", N_("Ajustes")),
               ("registro", N_("Registro")))

    def __init__(self, nucleo, web=None):
        super().__init__()
        self.nucleo = nucleo
        self.web = web
        self.cfg = nucleo.config()
        self._origen = nucleo.cfg             # para saber si la han cambiado desde el panel web
        self._sucio = False
        self._oscura = False
        self.ctx = Contexto(self, nucleo, web)
        self.setWindowTitle("%s %s" % (NOMBRE, __version__))
        self.setWindowIcon(icono())
        self.resize(1340, 880)
        self.setMinimumSize(1080, 700)

        self._t_flotante = QTimer(self)
        self._t_flotante.setSingleShot(True)
        self._t_flotante.timeout.connect(lambda: self.flotante.setVisible(False))
        self._reloj_ui = QTimer(self)
        self._reloj_ui.timeout.connect(self._tic)
        self._montar()
        self._reloj_ui.start(100)
        self._tic()

    # ------------------------------------------------------------ armazon

    def _montar(self, pagina: int = 0) -> None:
        """
        Los menus, el armazon y las paginas, con los textos del idioma de
        ahora. Se llama al abrir y cada vez que cambia el idioma: lo que hay
        que conservar (la configuracion a medio tocar) vive en la ventana.
        """
        self._idioma = idioma.actual()
        self._fecha = ""
        self._emite = None
        self.setLocale(QLocale())             # los numeros de los campos, como en ese idioma
        self._menus()
        centro = QWidget()
        centro.setObjectName("fondo")
        raiz = QVBoxLayout(centro)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self._cabecera())
        medio = QHBoxLayout()
        medio.setSpacing(0)
        medio.addWidget(self._lateral())
        self.pila = QStackedWidget()
        medio.addWidget(self.pila, 1)
        raiz.addLayout(medio, 1)
        raiz.addWidget(self._pie())

        # Las paginas de configuracion se montan la primera vez que se abren:
        # montarlas todas al arrancar tenia la ventana varios segundos en blanco.
        self._fabricas = {"franjas": pagina_franjas, "senales": PaginaSenales,
                          "publicidad": pagina_publicidad, "eventos": pagina_eventos,
                          "cue": PaginaCue, "icecast": pagina_icecast, "ajustes": PaginaAjustes,
                          "registro": PaginaRegistro}
        self._montadas = {}               # nombre -> pagina
        self._por_cargar = set()          # montadas cuyo formulario se ha quedado viejo
        self.p_emision = PaginaEmision(self.ctx)
        self.pila.addWidget(self.p_emision)
        for _ in self.PAGINAS[1:]:
            self.pila.addWidget(QWidget())

        self.flotante = QLabel("", centro)
        self.flotante.setWordWrap(True)
        self.flotante.setVisible(False)
        self.setCentralWidget(centro)         # la anterior, si la habia, se destruye con todo lo suyo
        self._ir(pagina)

    def _menus(self) -> None:
        barra = QMenuBar()

        m = barra.addMenu(tr("&Archivo"))
        self.a_guardar = m.addAction(tr("&Guardar cambios"), self.guardar)
        self.a_guardar.setShortcut(QKeySequence.StandardKey.Save)
        self.a_descartar = m.addAction(tr("&Descartar cambios"), self.descartar)
        m.addSeparator()
        m.addAction(tr("&Importar configuración…"), self._importar)
        m.addAction(tr("&Exportar configuración…"), self._exportar)
        m.addSeparator()
        m.addAction(tr("Abrir la &carpeta de datos"), self._abrir_datos)
        m.addSeparator()
        m.addAction(tr("&Salir"), self.close).setShortcut("Ctrl+Q")

        m = barra.addMenu(tr("&Emisión"))
        self.a_emitir = m.addAction(tr("&Emitir"), lambda: self.p_emision.conmutar())
        m.addSeparator()
        self.a_saltar = m.addAction(tr("&Saltar canción"), self.nucleo.saltar)
        self.a_rehacer = m.addAction(tr("&Rehacer la pauta"), self.nucleo.replanificar)

        m = barra.addMenu(tr("&Ver"))
        self.a_paginas = QActionGroup(m)
        for i, (_, texto) in enumerate(self.PAGINAS):
            # triggered manda un bool: sin el primer argumento, caeria en i
            a = m.addAction(tr(texto), lambda marcada=False, i=i: self._ir(i))
            a.setCheckable(True)
            a.setShortcut("Ctrl+%d" % (i + 1))
            self.a_paginas.addAction(a)
        m.addSeparator()
        a = m.addAction(tr("Abrir el panel &web en el navegador"), self._abrir_web)
        a.setEnabled(self.web is not None and bool(self.web.url))
        a = m.addAction(tr("&Pantalla completa"), self._pantalla_completa)
        a.setCheckable(True)
        a.setChecked(self.isFullScreen())
        a.setShortcut("F11")

        m = barra.addMenu(tr("&Idioma"))
        grupo = QActionGroup(m)
        for codigo, nombre in idioma.IDIOMAS:
            a = m.addAction(nombre, lambda marcada=False, c=codigo: self.nucleo.poner_idioma(c))
            a.setCheckable(True)
            a.setChecked(codigo == idioma.actual())
            grupo.addAction(a)

        m = barra.addMenu(tr("A&yuda"))
        # aqui ira «Buscar actualizaciones» cuando el programa tenga repositorio
        m.addAction(tr("&Acerca de %s") % NOMBRE, self._acerca)
        self.setMenuBar(barra)                # la anterior, si la habia, se destruye

    def _cabecera(self) -> QWidget:
        w = QWidget()
        w.setObjectName("cabecera")
        w.setFixedHeight(68)
        f = QHBoxLayout(w)
        f.setContentsMargins(18, 0, 20, 0)
        f.setSpacing(14)
        f.addWidget(Logo(40))
        marca = QLabel(NOMBRE)
        marca.setFont(estilo.texto(16, True, 6.0))
        marca.setStyleSheet("color: %s;" % estilo.ACENTO)
        f.addWidget(marca)
        self.emisora = QLabel("")
        self.emisora.setFont(estilo.texto(12))
        self.emisora.setObjectName("tenue")
        f.addWidget(self.emisora)
        f.addStretch(1)
        self.lampara = Lampara()
        f.addWidget(self.lampara)
        f.addSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.setContentsMargins(0, 6, 0, 6)
        self.reloj = QLabel("--:--:--")
        self.reloj.setFont(estilo.mono(24, True))
        self.reloj.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.fecha = QLabel("")
        self.fecha.setObjectName("tenue")
        self.fecha.setFont(estilo.texto(8.5))
        self.fecha.setAlignment(Qt.AlignmentFlag.AlignRight)
        col.addWidget(self.reloj)
        col.addWidget(self.fecha)
        f.addLayout(col)
        return w

    def _lateral(self) -> QWidget:
        w = QWidget()
        w.setObjectName("lateral")
        w.setFixedWidth(232)
        col = QVBoxLayout(w)
        col.setContentsMargins(0, 12, 0, 14)
        col.setSpacing(2)
        self.grupo = QButtonGroup(w)
        self.grupo.setExclusive(True)
        for i, (_, texto) in enumerate(self.PAGINAS):
            b = boton(tr(texto), "nav")
            b.setCheckable(True)
            self.grupo.addButton(b, i)
            col.addWidget(b)
        self.grupo.idClicked.connect(self._pagina)
        col.addStretch(1)
        caja = QVBoxLayout()
        caja.setContentsMargins(14, 0, 14, 0)
        caja.setSpacing(6)
        self.b_guardar = boton(tr("Guardar cambios"), "", self.guardar)
        self.b_guardar.setMinimumHeight(38)
        self.b_descartar = boton(tr("Descartar"), "pequeno", self.descartar)
        caja.addWidget(self.b_guardar)
        caja.addWidget(self.b_descartar)
        col.addLayout(caja)
        self.marcar(self._sucio)
        return w

    def _pie(self) -> QWidget:
        w = QWidget()
        w.setObjectName("pie")
        w.setFixedHeight(28)
        f = QHBoxLayout(w)
        f.setContentsMargins(14, 0, 14, 0)
        f.setSpacing(22)
        self.pie_salida = QLabel("")
        self.pie_web = QLabel("")
        self.pie_web.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.pie_analisis = QLabel("")
        self.pie_cortes = QLabel("")
        f.addWidget(self.pie_salida)
        f.addWidget(self.pie_web)
        f.addStretch(1)
        f.addWidget(self.pie_cortes)
        f.addWidget(self.pie_analisis)
        return w

    def showEvent(self, ev):
        super().showEvent(ev)
        if not self._oscura and os.name == "nt":
            # barra de titulo oscura (aqui y no en __init__: la ventana nativa ya existe)
            self._oscura = True
            try:
                valor = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(int(self.winId()), 20, ctypes.byref(valor), 4)
            except Exception:
                pass

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._colocar_flotante()

    # ------------------------------------------------------------ paginas y configuracion

    def _ir(self, i: int) -> None:
        """A una pagina sin pasar por su boton del lateral (desde el menu, o al montar)."""
        self.grupo.button(i).setChecked(True)
        self._pagina(i)

    def _pagina(self, i: int) -> None:
        nombre = self.PAGINAS[i][0]
        if nombre != "emision":
            p = self._montadas.get(nombre)
            if p is None:
                p = self._fabricas[nombre](self.ctx)
                self._montadas[nombre] = p
                hueco = self.pila.widget(i)
                self.pila.removeWidget(hueco)
                hueco.deleteLater()
                self.pila.insertWidget(i, p)
                self._por_cargar.add(nombre)
            if nombre in self._por_cargar or nombre == "registro":
                self._por_cargar.discard(nombre)
                p.cargar()
        self.pila.setCurrentIndex(i)
        self.a_paginas.actions()[i].setChecked(True)

    def _recargar(self) -> None:
        """Los formularios, enlazados de nuevo a self.cfg: el que se ve, ya; los demas, al abrirlos."""
        self._por_cargar = set(self._montadas)
        self._pagina(self.pila.currentIndex())

    def marcar(self, sucio: bool) -> None:
        if sucio == self._sucio and self.b_guardar.property("clase") is not None:
            return
        self._sucio = sucio
        for x in (self.b_guardar, self.b_descartar, self.a_guardar, self.a_descartar):
            x.setEnabled(sucio)
        self.b_guardar.setProperty("clase", "acento" if sucio else "")
        reestilar(self.b_guardar)

    def guardar(self) -> None:
        foco = QApplication.focusWidget()
        if foco is not None:
            foco.clearFocus()                             # que el campo a medio escribir se de por acabado
        try:
            aviso = self.nucleo.guardar_config(self.cfg)
        except Exception as e:
            self.avisar(tr("No se ha podido guardar: %s") % e, True)
            return
        self.cfg = self.nucleo.config()
        self._origen = self.nucleo.cfg
        self.marcar(False)
        self._recargar()
        self.avisar(aviso or tr("Configuración guardada y aplicada."))

    def descartar(self) -> None:
        self.cfg = self.nucleo.config()
        self._origen = self.nucleo.cfg
        self.marcar(False)
        self._recargar()

    def avisar(self, texto: str, malo: bool = False) -> None:
        self.flotante.setText(texto)
        self.flotante.setStyleSheet(
            "background: %s; border: 1px solid %s; border-radius: 8px; padding: 12px 16px; font-size: 10pt;"
            % ("#7f1d1d" if malo else estilo.PANEL2, estilo.ROJO if malo else estilo.ACENTO))
        self.flotante.setVisible(True)
        self.flotante.raise_()
        self._colocar_flotante()
        self._t_flotante.start(9000 if malo else 5000)

    def _colocar_flotante(self) -> None:
        if not hasattr(self, "flotante") or not self.flotante.isVisible():
            return
        c = self.centralWidget()
        self.flotante.setFixedWidth(min(520, c.width() - 60))
        self.flotante.adjustSize()
        self.flotante.move(c.width() - self.flotante.width() - 24,
                           c.height() - self.flotante.height() - 46)

    # ------------------------------------------------------------ menus

    def _importar(self) -> None:
        """Otra configuracion entra como cambios sin guardar: se revisa y se guarda, o se descarta."""
        ruta, _ = QFileDialog.getOpenFileName(self, tr("Importar configuración"), "",
                                              tr("Configuración (*.json);;Todos (*.*)"))
        if not ruta:
            return
        try:
            nueva = modconfig.importar(ruta)
        except Exception as e:
            self.avisar(tr("No se ha podido importar: %s") % e, True)
            return
        nueva.idioma = self.cfg.idioma
        self.cfg = nueva
        self.marcar(True)
        self._recargar()
        self.avisar(tr("Configuración importada. Revísala y pulsa «Guardar cambios» para aplicarla."))

    def _exportar(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(self, tr("Exportar configuración"), "gimel-config.json",
                                              tr("Configuración (*.json);;Todos (*.*)"))
        if not ruta:
            return
        try:
            modconfig.guardar(self.cfg, ruta)
        except OSError as e:
            self.avisar(tr("No se ha podido exportar: %s") % e, True)
            return
        self.avisar(tr("Configuración exportada a %s") % os.path.normpath(ruta))

    def _abrir_datos(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.nucleo.datos))

    def _abrir_web(self) -> None:
        QDesktopServices.openUrl(QUrl(self.web.url))

    def _pantalla_completa(self) -> None:
        self.setWindowState(self.windowState() ^ Qt.WindowState.WindowFullScreen)

    def _acerca(self) -> None:
        QMessageBox.about(self, tr("Acerca de %s") % NOMBRE, "\n".join((
            "%s %s" % (NOMBRE, __version__),
            tr("Continuidad de radio por rotaciones horarias exactas."),
            "",
            tr("Carpeta de datos: %s") % self.nucleo.datos,
            "ffmpeg: %s" % (self.nucleo.ffmpeg or tr("no se encuentra")))))

    def _remontar(self) -> None:
        """Ha cambiado el idioma (desde el menu, desde Ajustes o desde el panel web)."""
        self.cfg.idioma = idioma.actual()     # que un Guardar posterior no vuelva al de antes
        idioma_qt(QApplication.instance())
        self._montar(self.pila.currentIndex())

    # ------------------------------------------------------------ el tic

    def _tic(self) -> None:
        if idioma.actual() != self._idioma and QApplication.activeModalWidget() is None:
            self._remontar()                              # con una pregunta abierta, cuando se cierre
        e = self.nucleo.estado()
        ahora = e["reloj"]
        self.reloj.setText(hms(ahora))
        d = datetime.fromtimestamp(ahora)
        fecha = tr("%(dia)s %(n)d de %(mes)s") % {"dia": tr(DIAS[d.weekday()]), "n": d.day,
                                                  "mes": tr(MESES[d.month - 1])}
        if fecha != self._fecha:
            self._fecha = fecha
            self.fecha.setText(fecha)
        emite = bool(e.get("emitiendo"))
        self.lampara.poner(emite)
        if emite != self._emite:
            self._emite = emite
            self.a_emitir.setText(tr("&Detener la emisión") if emite else tr("&Emitir"))
            self.a_saltar.setEnabled(emite)
            self.a_rehacer.setEnabled(emite)
        if self.emisora.text() != e.get("emisora", ""):
            self.emisora.setText(e.get("emisora", ""))
        actual = self.pila.currentWidget()
        if actual is self.p_emision:
            self.p_emision.actualizar(e)
        elif actual is self._montadas.get("cue"):
            actual.actualizar(e)
        flujos = e.get("icecast") or []
        if actual is self._montadas.get("icecast"):
            actual.cabecera.setText(texto_icecast(flujos, True) if flujos
                                    else tr("Los envíos se conectan al empezar a emitir."))
        salida = "  ·  ".join(tr(x) for x in e.get("salida", []) if x).replace("Windows ", "")
        if flujos:
            salida += "      Icecast → " + texto_icecast(flujos)
        self.pie_salida.setText(tr("Salida: ") + salida)
        web = self.web
        self.pie_web.setText(tr("Panel web: %s") % web.url if web is not None and web.url else "")
        n = e.get("analizando", 0)
        self.pie_analisis.setText(tr("Analizando la biblioteca: quedan %d") % n if n else "")
        cortes = e.get("cortes", 0)
        self.pie_cortes.setText(tr("Cortes de audio: %d") % cortes if cortes else "")
        if self.nucleo.cfg is not self._origen and not self._sucio:
            self.descartar()                              # la han cambiado desde el panel web

    def closeEvent(self, ev):
        if self.nucleo.emisor.emitiendo:
            r = QMessageBox.question(self, NOMBRE, tr("Se está emitiendo.\n¿Salir y parar la emisión?"))
            if r != QMessageBox.StandardButton.Yes:
                ev.ignore()
                return
        if self._sucio:
            r = QMessageBox.question(
                self, NOMBRE, tr("Hay cambios de configuración sin guardar.\n¿Guardarlos antes de salir?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel:
                ev.ignore()
                return
            if r == QMessageBox.StandardButton.Yes:
                self.guardar()
        self._reloj_ui.stop()
        ev.accept()


def paleta() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(estilo.FONDO))
    p.setColor(QPalette.ColorRole.WindowText, QColor(estilo.TEXTO))
    p.setColor(QPalette.ColorRole.Base, QColor("#0d1014"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(estilo.PANEL))
    p.setColor(QPalette.ColorRole.Text, QColor(estilo.TEXTO))
    p.setColor(QPalette.ColorRole.Button, QColor(estilo.PANEL2))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(estilo.TEXTO))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(estilo.PANEL2))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(estilo.TEXTO))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#3b82f6"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(estilo.TENUE))
    return p


_traductor_qt = None


def idioma_qt(app: QApplication) -> None:
    """Lo que escribe el propio Qt (el Sí / No de las preguntas, los menus de los campos) y sus numeros."""
    global _traductor_qt
    if _traductor_qt is not None:
        app.removeTranslator(_traductor_qt)
    codigo = idioma.actual()
    QLocale.setDefault(QLocale(codigo))
    t = QTranslator(app)
    if t.load("qtbase_" + codigo, QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(t)
        _traductor_qt = t
    else:
        _traductor_qt = None


def crear_app(datos: str) -> QApplication:
    if os.name == "nt":
        try:                                              # icono propio en la barra de tareas
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("gimel.playout")
        except Exception:
            pass
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(NOMBRE)
    app.setStyle("Fusion")
    app.setPalette(paleta())
    app.setFont(estilo.texto(10))
    app.setStyleSheet(estilo.hoja(os.path.join(datos, "ui")))
    app.setWindowIcon(icono())
    idioma_qt(app)
    return app


def lanzar(nucleo, web=None, emitir: bool = False) -> int:
    """
    Abre la ventana. Si hay que empezar emitiendo, se empieza con la ventana ya
    montada: construirla tiene ocupado al interprete un par de segundos y el
    hilo de audio se quedaria sin turno justo al arrancar.
    """
    app = crear_app(nucleo.datos)
    ventana = Ventana(nucleo, web)
    ventana.show()
    if emitir:
        QTimer.singleShot(700, ventana.p_emision.emitir)
    return app.exec()
