#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador de GIMEL (gimel-setup.exe) y su desinstalador (desinstalar.exe).

Es un solo programa, sin nada del propio GIMEL: compilado con el programa
dentro (carga.zip) instala; compilado sin el, desinstala. Los dos piden
permiso de administrador al arrancar (lo lleva su manifiesto: lo pone
herramientas/compilar.py).

    gimel-setup.exe                     asistente: la licencia, y carpeta, accesos directos y arranque con Windows
    gimel-setup.exe /S                  sin preguntar nada: instala, o actualiza lo que haya donde este
    gimel-setup.exe /S /ARRANCAR        ...y al acabar abre GIMEL (es lo que usa la actualizacion)
    gimel-setup.exe /D=C:\\Radio\\GIMEL   en esa carpeta (con /S o sin el)
    desinstalar.exe [/S]

Con /S no se ve nada: lo que pasa queda en %TEMP%\\gimel-setup.log y en el
codigo de salida (0 bien, 1 error, 2 GIMEL seguia abierto y no se ha tocado).

Instalar es: esperar a que GIMEL este cerrado, descomprimir la version nueva
en una carpeta aparte y, solo si ha salido entera, cambiarla por la anterior;
si algo falla a medias, la anterior sigue en su sitio. Lo que no ha puesto el
instalador (la carpeta datos, sobre todo) no se toca, ni al actualizar ni al
desinstalar.
"""

import ctypes
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import winreg
import zipfile

NOMBRE = "GIMEL"
EXE = "GIMEL.exe"
DESINSTALADOR = "desinstalar.exe"
LISTA = "instalado.json"              # lo que el instalador ha puesto en la carpeta, para saber que quitar
HIVE = winreg.HKEY_LOCAL_MACHINE
CLAVE = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\GIMEL"
# lo que Windows abre al iniciar sesion, para cualquier usuario (y sin elevar)
ARRANQUE = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
PUERTO = 48951                        # el cerrojo de instancia unica de GIMEL (main.py)
ESPERA = 60.0                         # con /S, lo que se espera a que GIMEL se cierre
SIN_VENTANA = 0x08000000


def aqui() -> str:
    """Donde estan los ficheros que acompanan al instalador (dentro del .exe, o junto al .py)."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def carga() -> str:
    return os.path.join(aqui(), "carga.zip")


def version() -> str:
    """La version de GIMEL que lleva dentro este instalador."""
    try:
        with open(os.path.join(aqui(), "version.txt"), "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def licencia() -> str:
    """El texto de la licencia (GNU GPL v3) que acompana al instalador."""
    try:
        with open(os.path.join(aqui(), "LICENSE"), "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------- idioma

EN = {
    "Instalar": "Install",
    "Actualizar": "Update",
    "Cancelar": "Cancel",
    "Cerrar": "Close",
    "Examinar…": "Browse…",
    "Instalación de %s": "%s setup",
    "Se va a instalar GIMEL %s.": "GIMEL %s will be installed.",
    "Se va a actualizar GIMEL %s a la versión %s.": "GIMEL %s will be updated to version %s.",
    "Carpeta": "Folder",
    "Acceso directo en el escritorio": "Desktop shortcut",
    "Abrir GIMEL al iniciar Windows": "Start GIMEL when Windows starts",
    "Siguiente": "Next",
    "Atrás": "Back",
    "GIMEL es software libre: puedes usarlo, estudiarlo, compartirlo y mejorarlo con las condiciones de la licencia GNU GPL, versión 3.":
        "GIMEL is free software: you can use, study, share and improve it under the terms of the "
        "GNU GPL, version 3.",
    "Abrir GIMEL al terminar": "Open GIMEL when finished",
    "Carpeta en la que instalar GIMEL": "Folder to install GIMEL in",
    "GIMEL está abierto. Ciérralo para seguir.": "GIMEL is open. Close it to continue.",
    "Esperando a que GIMEL se cierre…": "Waiting for GIMEL to close…",
    "Copiando ficheros…": "Copying files…",
    "GIMEL %s está instalado.": "GIMEL %s is installed.",
    "No se ha podido instalar: %s": "Could not install: %s",
    "Hace falta permiso de administrador.": "Administrator permission is required.",
    "Este instalador no lleva el programa dentro.": "This installer does not contain the program.",
    "¿Desinstalar GIMEL de este equipo?\n\nLa configuración y el registro de emisión no se borran.":
        "Uninstall GIMEL from this computer?\n\nThe configuration and the broadcast log are not deleted.",
    "GIMEL se ha desinstalado.": "GIMEL has been uninstalled.",
    "No se ha podido desinstalar: %s": "Could not uninstall: %s",
    "GIMEL no está instalado.": "GIMEL is not installed.",
}


def _espanol() -> bool:
    try:
        return ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x0A
    except Exception:
        return True


ESPANOL = _espanol()


def tr(texto: str) -> str:
    return texto if ESPANOL else EN.get(texto, texto)


# ---------------------------------------------------------------- el equipo

def registrar(texto: str) -> None:
    """Al registro del instalador (%TEMP%\\gimel-setup.log): con /S es lo unico que queda."""
    linea = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), texto)
    print(linea)
    try:
        with open(os.path.join(tempfile.gettempdir(), "gimel-setup.log"), "a", encoding="utf-8") as fh:
            fh.write(linea + "\n")
    except OSError:
        pass


def es_administrador() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def mensaje(texto: str, pregunta: bool = False, malo: bool = False) -> bool:
    """Una ventana de aviso de Windows. Con pregunta=True devuelve si han dicho que si."""
    estilo = (0x24 if pregunta else 0x10 if malo else 0x40) | 0x10000
    return ctypes.windll.user32.MessageBoxW(None, texto, NOMBRE, estilo) in (1, 6)


def _carpeta_comun(csidl: int) -> str:
    b = ctypes.create_unicode_buffer(520)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, b)
    return b.value


def carpeta_menu() -> str:
    """El menu Inicio de todos los usuarios."""
    return _carpeta_comun(0x17)


def carpeta_escritorio() -> str:
    """El escritorio de todos los usuarios."""
    return _carpeta_comun(0x19)


def carpeta_por_defecto() -> str:
    return os.path.join(os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles")
                        or r"C:\Program Files", NOMBRE)


def instalacion() -> dict:
    """Lo que el registro dice de la instalacion que hay: carpeta y version. Vacio si no hay ninguna."""
    try:
        with winreg.OpenKey(HIVE, CLAVE) as k:
            return {"carpeta": winreg.QueryValueEx(k, "InstallLocation")[0],
                    "version": winreg.QueryValueEx(k, "DisplayVersion")[0]}
    except OSError:
        return {}


def abierto(carpeta: str = "") -> bool:
    """Si GIMEL esta en marcha: tiene cogido su puerto de instancia unica, o su .exe no se deja abrir."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", PUERTO))
    except OSError:
        return True
    finally:
        s.close()
    exe = os.path.join(carpeta, EXE) if carpeta else ""
    if exe and os.path.exists(exe):
        try:
            with open(exe, "r+b"):
                pass
        except OSError:
            return True
    return False


def esperar_cierre(carpeta: str, segundos: float) -> bool:
    limite = time.monotonic() + segundos
    while abierto(carpeta):
        if time.monotonic() >= limite:
            return False
        time.sleep(0.5)
    return True


def abrir(carpeta: str) -> None:
    """
    Abre GIMEL como el usuario de la sesion, no como administrador: el
    instalador esta elevado, y lo que lanzara el directamente tambien lo
    estaria. Se lo encarga al Explorador, que no lo esta.
    """
    subprocess.Popen(["explorer.exe", os.path.join(carpeta, EXE)])


def borrar(ruta: str) -> None:
    if os.path.isdir(ruta) and not os.path.islink(ruta):
        shutil.rmtree(ruta)
    elif os.path.lexists(ruta):
        os.remove(ruta)


def acceso_directo(lnk: str, exe: str) -> None:
    """Un .lnk, hecho por el propio Windows (WScript.Shell). Las rutas viajan por el entorno: sin lios de comillas."""
    orden = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:GIMEL_LNK); "
             "$s.TargetPath = $env:GIMEL_EXE; $s.WorkingDirectory = $env:GIMEL_DIR; "
             "$s.IconLocation = $env:GIMEL_EXE + ',0'; $s.Save()")
    entorno = dict(os.environ, GIMEL_LNK=lnk, GIMEL_EXE=exe, GIMEL_DIR=os.path.dirname(exe))
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", orden], env=entorno,
                   check=True, capture_output=True, timeout=90, creationflags=SIN_VENTANA)


def apuntar(destino: str, tamano_kb: int) -> None:
    """La entrada de «Aplicaciones y caracteristicas» (y de donde /S saca la carpeta al actualizar)."""
    exe, quitar = os.path.join(destino, EXE), os.path.join(destino, DESINSTALADOR)
    with winreg.CreateKeyEx(HIVE, CLAVE, 0, winreg.KEY_WRITE) as k:
        for nombre, valor in (("DisplayName", NOMBRE), ("DisplayVersion", version()),
                              ("DisplayIcon", exe), ("InstallLocation", destino),
                              ("UninstallString", '"%s"' % quitar),
                              ("QuietUninstallString", '"%s" /S' % quitar),
                              ("InstallDate", time.strftime("%Y%m%d")),
                              ("EstimatedSize", tamano_kb), ("NoModify", 1), ("NoRepair", 1)):
            winreg.SetValueEx(k, nombre, 0, winreg.REG_DWORD if isinstance(valor, int) else winreg.REG_SZ, valor)


def en_el_arranque() -> bool:
    """Si GIMEL esta puesto para abrirse al iniciar sesion en Windows."""
    try:
        with winreg.OpenKey(HIVE, ARRANQUE) as k:
            winreg.QueryValueEx(k, NOMBRE)
        return True
    except OSError:
        return False


def poner_arranque(destino: str, si: bool) -> None:
    with winreg.CreateKeyEx(HIVE, ARRANQUE, 0, winreg.KEY_WRITE) as k:
        if si:
            winreg.SetValueEx(k, NOMBRE, 0, winreg.REG_SZ, '"%s"' % os.path.join(destino, EXE))
        else:
            try:
                winreg.DeleteValue(k, NOMBRE)
            except OSError:
                pass


# ---------------------------------------------------------------- instalar y desinstalar

def instalar(destino: str, escritorio=True, arranque=False, progreso=None) -> None:
    """
    Pone en `destino` el programa que lleva dentro el instalador. `escritorio`
    (el acceso directo) y `arranque` (abrirse al iniciar Windows): True lo
    pone, False lo quita y None lo deja como este, que es lo que toca al
    actualizar. `progreso` recibe de 0 a 1 segun se copia.
    """
    destino = os.path.abspath(destino)
    nuevo, viejo = os.path.join(destino, "_nuevo"), os.path.join(destino, "_viejo")
    os.makedirs(destino, exist_ok=True)
    for d in (nuevo, viejo):                              # restos de una instalacion que se quedo a medias
        borrar(d)
    tamano = 0
    with zipfile.ZipFile(carga()) as z:
        entradas = z.infolist()
        total = sum(e.file_size for e in entradas) or 1
        for e in entradas:
            z.extract(e, nuevo)
            tamano += e.file_size
            if progreso is not None:
                progreso(tamano / total)

    # ya esta entera: lo de antes se aparta y lo nuevo ocupa su sitio
    nombres = sorted(os.listdir(nuevo))
    os.makedirs(viejo)
    try:
        for n in nombres:
            if os.path.lexists(os.path.join(destino, n)):
                os.replace(os.path.join(destino, n), os.path.join(viejo, n))
            os.replace(os.path.join(nuevo, n), os.path.join(destino, n))
    except OSError:
        for n in nombres:                                 # no se ha podido: lo de antes, a su sitio
            if os.path.lexists(os.path.join(viejo, n)):
                borrar(os.path.join(destino, n))
                os.replace(os.path.join(viejo, n), os.path.join(destino, n))
        borrar(viejo)
        borrar(nuevo)
        raise
    borrar(viejo)
    borrar(nuevo)
    with open(os.path.join(destino, LISTA), "w", encoding="utf-8") as fh:
        json.dump({"version": version(), "ficheros": nombres}, fh)

    exe = os.path.join(destino, EXE)
    acceso_directo(os.path.join(carpeta_menu(), NOMBRE + ".lnk"), exe)
    lnk = os.path.join(carpeta_escritorio(), NOMBRE + ".lnk")
    if escritorio or (escritorio is None and os.path.exists(lnk)):
        acceso_directo(lnk, exe)
    elif escritorio is False:
        borrar(lnk)
    if arranque is None:
        arranque = en_el_arranque()                       # como estaba, pero apuntando a esta carpeta
    poner_arranque(destino, bool(arranque))
    apuntar(destino, tamano // 1024)


def desinstalar(destino: str) -> None:
    """Quita lo que puso el instalador. Lo demas que haya en la carpeta (los datos) se queda."""
    destino = os.path.abspath(destino)
    for carpeta in (carpeta_menu(), carpeta_escritorio()):
        borrar(os.path.join(carpeta, NOMBRE + ".lnk"))
    try:
        with open(os.path.join(destino, LISTA), "r", encoding="utf-8") as fh:
            nombres = [os.path.basename(str(n)) for n in json.load(fh)["ficheros"]]
    except (OSError, ValueError, KeyError, TypeError):
        nombres = ["_internal", EXE, DESINSTALADOR]
    for n in nombres + [LISTA, "_nuevo", "_viejo"]:
        if n not in ("", ".", ".."):
            borrar(os.path.join(destino, n))
    try:
        os.rmdir(destino)                                 # solo si se ha quedado vacia
    except OSError:
        pass
    poner_arranque(destino, False)
    try:
        winreg.DeleteKey(HIVE, CLAVE)
    except OSError:
        pass


# ---------------------------------------------------------------- sin preguntar (/S)

def en_silencio(destino: str, arrancar: bool) -> int:
    previa = instalacion()
    destino = destino or previa.get("carpeta") or carpeta_por_defecto()
    registrar("GIMEL %s -> %s (habia: %s)" % (version(), destino, previa.get("version") or "nada"))
    if not os.path.exists(carga()):
        registrar("ERROR: este instalador no lleva el programa dentro")
        return 1
    if not esperar_cierre(destino, ESPERA):
        registrar("GIMEL sigue abierto tras %.0f s: no se ha tocado nada" % ESPERA)
        return 2
    try:
        instalar(destino, escritorio=None if previa else True, arranque=None)
    except Exception as e:
        registrar("ERROR: %s" % e)
        return 1
    registrar("instalado")
    if arrancar:
        abrir(destino)
    return 0


# ---------------------------------------------------------------- asistente

FONDO, PANEL, BORDE, TEXTO, TENUE, ACENTO = "#0f1216", "#171b21", "#2a323d", "#e6e9ee", "#8b96a5", "#ffb000"


class Asistente:
    """Dos pasos: la licencia, y despues donde instalar y con que opciones."""

    def __init__(self, destino: str = ""):
        import tkinter as tk

        self.tk = tk
        self.previa = instalacion()
        self.hecho = False
        self.error = ""
        self._avance = 0.0
        self._instalando = False                          # desde que se pulsa Instalar hasta que la ventana lo da por acabado
        self._fin = None                                  # lo deja el hilo que instala: "" o el error
        v = self.v = tk.Tk()
        v.title(tr("Instalación de %s") % NOMBRE)
        v.configure(bg=FONDO)
        v.resizable(False, False)
        try:
            v.iconbitmap(os.path.join(aqui(), "gimel.ico"))
        except tk.TclError:
            pass
        caja = tk.Frame(v, bg=FONDO)                      # las dos paginas, una encima de otra
        caja.pack(fill="both", expand=True)
        caja.grid_rowconfigure(0, weight=1)
        caja.grid_columnconfigure(0, weight=1)
        self.p_opciones = self._opciones(caja, destino)
        self.p_licencia = self._licencia(caja)
        for p in (self.p_opciones, self.p_licencia):
            if p is not None:
                p.grid(row=0, column=0, sticky="nsew")
        (self.p_licencia or self.p_opciones).tkraise()    # se empieza por la licencia, si la hay
        v.protocol("WM_DELETE_WINDOW", self._cerrar)

    def _cabecera(self, marco, texto: str) -> None:
        tk = self.tk
        tk.Label(marco, text=NOMBRE, bg=FONDO, fg=ACENTO, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(marco, text=texto, bg=FONDO, fg=TEXTO, font=("Segoe UI", 10), wraplength=600,
                 justify="left").pack(anchor="w", pady=(2, 16))

    def _licencia(self, padre):
        """La GPL, para leerla antes de instalar. Si el instalador no la lleva, no hay pagina."""
        texto = licencia()
        if not texto:
            return None
        tk = self.tk
        marco = tk.Frame(padre, bg=FONDO, padx=26, pady=22)
        self._cabecera(marco, tr("GIMEL es software libre: puedes usarlo, estudiarlo, compartirlo y mejorarlo "
                                 "con las condiciones de la licencia GNU GPL, versión 3."))
        cuadro = tk.Frame(marco, bg=BORDE, padx=1, pady=1)
        cuadro.pack(fill="both", expand=True)
        barra = tk.Scrollbar(cuadro)
        self.t_licencia = tk.Text(cuadro, width=80, height=17, wrap="word", bg="#0d1014", fg=TEXTO,
                                  relief="flat", font=("Consolas", 9), padx=10, pady=8,
                                  yscrollcommand=barra.set)
        barra.configure(command=self.t_licencia.yview)
        barra.pack(side="right", fill="y")
        self.t_licencia.pack(side="left", fill="both", expand=True)
        self.t_licencia.insert("1.0", texto)
        self.t_licencia.configure(state="disabled")
        pie = tk.Frame(marco, bg=FONDO)
        pie.pack(fill="x", pady=(16, 0))
        self._boton(pie, tr("Cancelar"), self._cerrar).pack(side="right")
        self._boton(pie, tr("Siguiente"), self.p_opciones.tkraise, True).pack(side="right", padx=(0, 8))
        return marco

    def _opciones(self, padre, destino: str):
        from tkinter import ttk
        tk = self.tk
        marco = tk.Frame(padre, bg=FONDO, padx=26, pady=22)
        if self.previa and self.previa["version"] != version():
            texto = tr("Se va a actualizar GIMEL %s a la versión %s.") % (self.previa["version"], version())
        else:
            texto = tr("Se va a instalar GIMEL %s.") % version()
        self._cabecera(marco, texto)

        tk.Label(marco, text=tr("Carpeta"), bg=FONDO, fg=TENUE, font=("Segoe UI", 9)).pack(anchor="w")
        fila = tk.Frame(marco, bg=FONDO)
        fila.pack(fill="x", pady=(2, 12))
        self.carpeta = tk.StringVar(value=destino or self.previa.get("carpeta") or carpeta_por_defecto())
        self.campo = tk.Entry(fila, textvariable=self.carpeta, width=52, bg="#0d1014", fg=TEXTO,
                              insertbackground=TEXTO, relief="flat", highlightthickness=1,
                              disabledbackground="#0d1014", disabledforeground=TENUE,
                              highlightbackground=BORDE, highlightcolor=ACENTO, font=("Segoe UI", 10))
        self.campo.pack(side="left", fill="x", expand=True, ipady=4)
        self.b_examinar = self._boton(fila, tr("Examinar…"), self._examinar)
        self.b_examinar.pack(side="left", padx=(8, 0))

        lnk = os.path.join(carpeta_escritorio(), NOMBRE + ".lnk")
        self.escritorio = tk.BooleanVar(value=not self.previa or os.path.exists(lnk))
        self.arranque = tk.BooleanVar(value=en_el_arranque())
        self.arrancar = tk.BooleanVar(value=True)
        self.casillas = []
        for variable, rotulo in ((self.escritorio, tr("Acceso directo en el escritorio")),
                                 (self.arranque, tr("Abrir GIMEL al iniciar Windows")),
                                 (self.arrancar, tr("Abrir GIMEL al terminar"))):
            c = tk.Checkbutton(marco, text=rotulo, variable=variable, bg=FONDO, fg=TEXTO, selectcolor=PANEL,
                               activebackground=FONDO, activeforeground=TEXTO, font=("Segoe UI", 10),
                               highlightthickness=0, bd=0)
            c.pack(anchor="w")
            self.casillas.append(c)

        estilo = ttk.Style(self.v)
        estilo.theme_use("clam")
        estilo.configure("gimel.Horizontal.TProgressbar", troughcolor=PANEL, background=ACENTO,
                         bordercolor=BORDE, lightcolor=ACENTO, darkcolor=ACENTO)
        self.barra = ttk.Progressbar(marco, style="gimel.Horizontal.TProgressbar", maximum=1.0)
        self.barra.pack(fill="x", pady=(18, 4))
        self.estado = tk.Label(marco, text="", bg=FONDO, fg=TENUE, font=("Segoe UI", 9), anchor="w",
                               wraplength=600, justify="left")
        self.estado.pack(fill="x")

        pie = tk.Frame(marco, bg=FONDO)
        pie.pack(fill="x", side="bottom", pady=(16, 0))
        self.b_cerrar = self._boton(pie, tr("Cancelar"), self._cerrar)
        self.b_cerrar.pack(side="right")
        self.b_instalar = self._boton(pie, tr("Actualizar") if self.previa else tr("Instalar"), self._instalar, True)
        self.b_instalar.pack(side="right", padx=(0, 8))
        self.b_atras = self._boton(pie, tr("Atrás"), lambda: self.p_licencia.tkraise())
        if licencia():
            self.b_atras.pack(side="left")
        return marco

    def _boton(self, padre, texto: str, al_pulsar, principal: bool = False):
        tk = self.tk
        return tk.Button(padre, text=texto, command=al_pulsar, relief="flat", bd=0, padx=16, pady=6,
                         bg=ACENTO if principal else "#1e242c", fg="#111111" if principal else TEXTO,
                         activebackground="#ffc233" if principal else "#2f3a48",
                         activeforeground="#111111" if principal else TEXTO,
                         disabledforeground="#56606d", font=("Segoe UI", 10, "bold" if principal else "normal"))

    def _examinar(self) -> None:
        from tkinter import filedialog
        r = filedialog.askdirectory(parent=self.v, title=tr("Carpeta en la que instalar GIMEL"),
                                    initialdir=os.path.dirname(self.carpeta.get()) or None)
        if r:
            r = os.path.normpath(r)
            self.carpeta.set(r if os.path.basename(r).upper() == NOMBRE else os.path.join(r, NOMBRE))

    def _cerrar(self) -> None:
        if self._instalando:
            return                                        # a medio copiar no se cierra
        if self.hecho and self.arrancar.get():
            abrir(self.carpeta.get())
        self.v.destroy()

    def _instalar(self) -> None:
        from tkinter import messagebox
        destino = os.path.abspath(self.carpeta.get().strip() or carpeta_por_defecto())
        self.carpeta.set(destino)
        while abierto(destino):
            if not messagebox.askretrycancel(NOMBRE, tr("GIMEL está abierto. Ciérralo para seguir."), parent=self.v):
                return
        for w in [self.b_instalar, self.b_cerrar, self.b_atras, self.b_examinar, self.campo] + self.casillas:
            w.configure(state="disabled")
        self.estado.configure(text=tr("Copiando ficheros…"), fg=TENUE)
        self._fin = None
        self._instalando = True
        threading.Thread(target=self._trabajo, daemon=True,
                         args=(destino, self.escritorio.get(), self.arranque.get())).start()
        self._mirar()

    def _trabajo(self, destino: str, escritorio: bool, arranque: bool) -> None:
        try:
            instalar(destino, escritorio, arranque, self._progreso)
            self._fin = ""
        except Exception as e:
            registrar("ERROR: %s" % e)
            self._fin = str(e) or e.__class__.__name__

    def _progreso(self, fraccion: float) -> None:
        self._avance = fraccion                           # lo lee la ventana: Tk no se toca desde otro hilo

    def _mirar(self) -> None:
        self.barra.configure(value=self._avance)
        if self._fin is None:
            self.v.after(80, self._mirar)
            return
        self._instalando = False
        self.b_cerrar.configure(state="normal", text=tr("Cerrar"))
        if self._fin:
            self.error = self._fin
            self.estado.configure(text=tr("No se ha podido instalar: %s") % self._fin, fg="#f87171")
            for w in [self.b_instalar, self.b_atras, self.b_examinar, self.campo] + self.casillas:
                w.configure(state="normal")
        else:
            self.hecho = True
            self.b_instalar.pack_forget()                 # ya solo queda cerrar
            self.b_atras.pack_forget()
            self.barra.configure(value=1.0)
            self.estado.configure(text=tr("GIMEL %s está instalado.") % version(), fg="#22c55e")

    def ejecutar(self) -> int:
        self.v.update_idletasks()
        x = (self.v.winfo_screenwidth() - self.v.winfo_reqwidth()) // 2
        y = (self.v.winfo_screenheight() - self.v.winfo_reqheight()) // 3
        self.v.geometry("+%d+%d" % (x, y))
        self.v.mainloop()
        return 0 if self.hecho else 1


# ---------------------------------------------------------------- desinstalador

def quitar(args: list, silencio: bool) -> int:
    """
    Lo que hace desinstalar.exe. Un programa no puede borrar su propio .exe
    mientras corre: se copia a %TEMP% y sigue desde alli (/DE= le dice de
    donde venia); esa copia se borra sola en el proximo arranque de Windows.
    """
    yo = os.path.abspath(sys.executable)
    temporal = os.path.join(tempfile.gettempdir(), "gimel-desinstalar.exe")
    de = next((a[4:] for a in args if a.upper().startswith("/DE=")), "")
    if getattr(sys, "frozen", False) and not de:
        destino = os.path.dirname(yo)
        if not silencio and not mensaje(tr("¿Desinstalar GIMEL de este equipo?\n\nLa configuración y el "
                                           "registro de emisión no se borran."), pregunta=True):
            return 1
        shutil.copy2(yo, temporal)
        # la copia tiene que arrancar limpia, sin heredar la carpeta temporal de este .exe
        entorno = {k: v for k, v in os.environ.items() if not k.startswith(("_MEI", "_PYI"))}
        entorno["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        subprocess.Popen([temporal, "/DE=" + destino] + (["/S"] if silencio else []), env=entorno,
                         cwd=tempfile.gettempdir())
        return 0
    destino = de or instalacion().get("carpeta", "")
    if not destino:
        registrar("no hay nada que desinstalar")
        if not silencio:
            mensaje(tr("GIMEL no está instalado."))
        return 1
    registrar("desinstalar %s" % destino)
    if not esperar_cierre(destino, ESPERA if silencio else 0.0):
        if silencio:
            registrar("GIMEL sigue abierto: no se ha tocado nada")
            return 2
        while abierto(destino):
            if not mensaje(tr("GIMEL está abierto. Ciérralo para seguir."), pregunta=True):
                return 1
    time.sleep(0.6)                                       # que el desinstalador de la carpeta acabe de salir
    try:
        desinstalar(destino)
    except Exception as e:
        registrar("ERROR: %s" % e)
        if not silencio:
            mensaje(tr("No se ha podido desinstalar: %s") % e, malo=True)
        return 1
    registrar("desinstalado")
    if os.path.normcase(yo) == os.path.normcase(temporal):
        ctypes.windll.kernel32.MoveFileExW(temporal, None, 4)     # se borra al reiniciar Windows
    if not silencio:
        mensaje(tr("GIMEL se ha desinstalado."))
    return 0


# ---------------------------------------------------------------- principal

def main(args=None) -> int:
    args = list(sys.argv[1:] if args is None else args)
    mayus = [a.upper() for a in args]
    silencio = "/S" in mayus
    if not es_administrador():
        registrar("sin permiso de administrador")
        if not silencio:
            mensaje(tr("Hace falta permiso de administrador."), malo=True)
        return 1
    if not os.path.exists(carga()):                       # sin el programa dentro: es el desinstalador
        if os.path.basename(sys.executable).lower().startswith(("desinstalar", "gimel-desinstalar")):
            return quitar(args, silencio)
        registrar("este instalador no lleva el programa dentro")
        if not silencio:
            mensaje(tr("Este instalador no lleva el programa dentro."), malo=True)
        return 1
    destino = next((a[3:].strip('"') for a in args if a.upper().startswith("/D=")), "")
    if silencio:
        return en_silencio(destino, "/ARRANCAR" in mayus)
    return Asistente(destino).ejecutar()


if __name__ == "__main__":
    sys.exit(main())
