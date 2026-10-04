# -*- coding: utf-8 -*-
"""Colores, tipografias y hoja de estilo de la interfaz de escritorio."""

import os

from PyQt6.QtGui import QColor, QFont, QFontDatabase

from ..idioma import N_

FONDO = "#0f1216"
PANEL = "#171b21"
PANEL2 = "#1e242c"
BORDE = "#2a323d"
TEXTO = "#e6e9ee"
TENUE = "#8b96a5"
ACENTO = "#ffb000"
VERDE = "#22c55e"
ROJO = "#ef4444"

# un color por tipo de audio: los mismos en la pauta, en el reloj de la hora y en el panel web
COLOR_TIPO = {
    "cancion": "#3b82f6", "jingle": "#a855f7", "senal": "#f59e0b", "evento": "#14b8a6",
    "cuna": "#ef4444", "relleno": "#f97316", "jingle_publi": "#ec4899",
    "silencio": "#4b5563", "cue": "#22d3ee",
}
NOMBRE_TIPO = {
    "cancion": N_("CANCIÓN"), "jingle": N_("JINGLE"), "senal": N_("SEÑAL"), "evento": N_("EVENTO"),
    "cuna": N_("CUÑA"), "relleno": N_("RELLENO"), "jingle_publi": N_("JINGLE"),
    "silencio": N_("SILENCIO"), "cue": N_("CUE"),
}
TEXTO_OSCURO = ("senal", "cue")           # tipos cuyo color pide letra oscura encima


def color(tipo: str) -> QColor:
    return QColor(COLOR_TIPO.get(tipo, "#4b5563"))


_mono = None


def mono(puntos: float, negrita: bool = False) -> QFont:
    """Fuente de ancho fijo para horas y cuentas atras (que no bailen los digitos)."""
    global _mono
    if _mono is None:
        familias = set(QFontDatabase.families())
        _mono = next((f for f in ("Cascadia Mono", "Consolas", "Courier New") if f in familias),
                     "monospace")
    f = QFont(_mono)
    f.setPointSizeF(puntos)
    f.setBold(negrita)
    return f


def texto(puntos: float, negrita: bool = False, espaciado: float = 0.0) -> QFont:
    f = QFont("Segoe UI")
    f.setPointSizeF(puntos)
    f.setBold(negrita)
    if espaciado:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, espaciado)
    return f


# Ojo, dos cosas que no deben volver a esta hoja:
#  - font-family o font-size en una regla general: una hoja de estilo manda
#    sobre setFont(), y el reloj y las cuentas atras dejarian de verse grandes.
#  - reglas con el selector universal (*) o de descendientes (A > B > C): Qt las
#    comprueba contra cada control y montar un formulario se vuelve lentisimo.
#    El color del texto va por la paleta (ventana.paleta).
QSS = """
QMainWindow, QWidget#fondo { background: %(FONDO)s; }
QMenuBar { background: %(PANEL)s; border-bottom: 1px solid %(BORDE)s; padding: 2px 6px; }
QMenuBar::item { background: transparent; padding: 5px 11px; border-radius: 4px; }
QMenuBar::item:selected, QMenuBar::item:pressed { background: #2f3a48; }
QWidget#cabecera { background: #161a20; border-bottom: 1px solid %(BORDE)s; }
QWidget#lateral { background: %(PANEL)s; border-right: 1px solid %(BORDE)s; }
QWidget#pie { background: %(PANEL)s; border-top: 1px solid %(BORDE)s; }
QWidget#pie QLabel { color: %(TENUE)s; font-size: 9pt; }
QFrame#tarjeta { background: %(PANEL)s; border: 1px solid %(BORDE)s; border-radius: 8px; }
QLabel { background: transparent; }
QLabel#rotulo { color: %(TENUE)s; font-size: 8pt; font-weight: 700; }
QLabel#seccion { color: %(ACENTO)s; font-size: 8pt; font-weight: 700; padding-top: 10px;
                 border-bottom: 1px solid %(BORDE)s; padding-bottom: 4px; }
QLabel#ayuda { color: %(TENUE)s; font-size: 9pt; }
QLabel#tenue { color: %(TENUE)s; }
QLabel#mal { color: #f87171; font-size: 9pt; }
QLabel#aviso { color: #fbbf24; font-size: 9pt; }
QLabel#error { background: #7f1d1d; border: 1px solid %(ROJO)s; border-radius: 6px; padding: 8px 12px; }

QPushButton { background: %(PANEL2)s; border: 1px solid %(BORDE)s; border-radius: 6px; padding: 7px 14px; }
QPushButton:hover { border-color: #4b5766; }
QPushButton:pressed { background: #151a20; }
QPushButton:disabled { color: #56606d; border-color: #222830; }
QPushButton[clase="verde"] { background: #14532d; border-color: %(VERDE)s; font-weight: 700; }
QPushButton[clase="verde"]:hover { background: #166534; }
QPushButton[clase="rojo"] { background: #7f1d1d; border-color: %(ROJO)s; font-weight: 700; }
QPushButton[clase="rojo"]:hover { background: #991b1b; }
QPushButton[clase="mando"] { font-size: 11pt; padding: 10px 20px; }
QPushButton[clase="acento"] { background: %(ACENTO)s; color: #111; border-color: %(ACENTO)s; font-weight: 700; }
QPushButton[clase="pequeno"] { padding: 4px 10px; font-size: 9pt; }
QPushButton[clase="nav"] { background: transparent; border: none; border-left: 3px solid transparent;
                           border-radius: 0; text-align: left; padding: 11px 18px; color: %(TENUE)s; font-size: 10.5pt; }
QPushButton[clase="nav"]:hover { color: %(TEXTO)s; background: #1b2027; }
QPushButton[clase="nav"]:checked { color: %(TEXTO)s; background: %(PANEL2)s; border-left: 3px solid %(ACENTO)s; font-weight: 600; }
QPushButton[clase="dia"] { padding: 0; min-width: 30px; max-width: 30px; min-height: 28px; max-height: 28px;
                           background: #0d1014; color: %(TENUE)s; }
QPushButton[clase="dia"]:checked { background: %(ACENTO)s; color: #111; border-color: %(ACENTO)s; font-weight: 700; }

QLineEdit, QPlainTextEdit, QTextBrowser, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #0d1014; border: 1px solid %(BORDE)s; border-radius: 5px; padding: 5px 8px;
    selection-background-color: #3b82f6; }
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: %(ACENTO)s; }
QPlainTextEdit { font-family: "Cascadia Mono", Consolas; font-size: 9pt; }
QComboBox { padding-right: 26px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url(%(ICONOS)s/abajo.png); width: 10px; height: 6px; margin-right: 8px; }
QComboBox QAbstractItemView { background: %(PANEL2)s; border: 1px solid %(BORDE)s; selection-background-color: #2f3a48; outline: none; }
QSpinBox, QDoubleSpinBox { padding-right: 20px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 20px; border: none; margin-top: 3px; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border: none; margin-bottom: 3px; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url(%(ICONOS)s/arriba.png); width: 10px; height: 6px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url(%(ICONOS)s/abajo.png); width: 10px; height: 6px; }

QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 8px 10px; border-radius: 6px; border: 1px solid transparent; }
QListWidget::item:hover { background: %(PANEL2)s; }
QListWidget::item:selected { background: %(PANEL2)s; border: 1px solid %(ACENTO)s; color: %(TEXTO)s; }

QTableWidget { background: transparent; border: none; gridline-color: #20262e; outline: none; }
QTableWidget::item { padding: 4px 8px; border-bottom: 1px solid #20262e; }
QTableWidget::item:selected { background: #24303f; }
QHeaderView::section { background: transparent; border: none; border-bottom: 1px solid %(BORDE)s;
                       color: %(TENUE)s; font-size: 8pt; font-weight: 700; padding: 6px 8px; }

QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #2f3844; border-radius: 4px; min-height: 30px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #3d4857; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 12px; }
QScrollBar::handle:horizontal { background: #2f3844; border-radius: 4px; min-width: 30px; margin: 2px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QToolTip { background: %(PANEL2)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s; padding: 5px; }
QMenu { background: %(PANEL2)s; border: 1px solid %(BORDE)s; padding: 4px; }
QMenu::item { padding: 6px 26px; border-radius: 4px; }
QMenu::item:selected { background: #2f3a48; }
QMenu::item:disabled { color: #56606d; }
QMenu::separator { height: 1px; background: %(BORDE)s; margin: 4px 8px; }
QMenu::indicator { width: 8px; height: 8px; left: 9px; border-radius: 4px; }
QMenu::indicator:checked { background: %(ACENTO)s; }
QMessageBox, QDialog { background: %(PANEL)s; }
"""


def hoja(carpeta_iconos: str) -> str:
    """La hoja de estilo, con las flechas de desplegables y contadores ya dibujadas en disco."""
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtGui import QPainter, QPixmap, QPolygonF

    os.makedirs(carpeta_iconos, exist_ok=True)
    for nombre, puntos in (("abajo", ((1, 1), (19, 1), (10, 11))), ("arriba", ((1, 11), (19, 11), (10, 1)))):
        pm = QPixmap(20, 12)                              # al doble: se ve fino en pantallas densas
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(TENUE))
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in puntos]))
        p.end()
        pm.save(os.path.join(carpeta_iconos, nombre + ".png"))
    return QSS % {"FONDO": FONDO, "PANEL": PANEL, "PANEL2": PANEL2, "BORDE": BORDE, "TEXTO": TEXTO,
                  "TENUE": TENUE, "ACENTO": ACENTO, "VERDE": VERDE, "ROJO": ROJO,
                  "ICONOS": carpeta_iconos.replace("\\", "/")}
