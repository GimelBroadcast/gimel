# -*- coding: utf-8 -*-
"""
Nucleo: junta biblioteca, rotacion, motor, emisor y CUE, y es lo unico que ven
las interfaces. La de escritorio y el panel web llaman a lo mismo, asi que
hacen exactamente lo mismo.
"""

import math
import os
import re
import string
import threading
import time

from . import NOMBRE, __version__
from . import config as modconfig
from . import idioma
from . import motor as modmotor
from . import rutas
from .biblioteca import Biblioteca
from .cue import Cues, Titulo
from .emisor import Emisor
from .icecast import Emisiones
from .idioma import N_, tr
from .registro import Registro
from .rotacion import Rotacion


class Nucleo:
    def __init__(self, datos: str = ""):
        self.datos = datos or rutas.carpeta_datos()
        os.makedirs(self.datos, exist_ok=True)            # con --datos puede ser una carpeta que aun no existe
        self.ruta_cfg = os.path.join(self.datos, "config.json")
        self.cfg = modconfig.cargar(self.ruta_cfg)
        self.cfg.idioma = idioma.poner(self.cfg.idioma)
        self.ffmpeg = rutas.buscar_ffmpeg()
        soxr = rutas.ffmpeg_tiene_soxr(self.ffmpeg) if self.ffmpeg else False
        self.bib = Biblioteca(self.datos, self.ffmpeg)
        self.rot = Rotacion(os.path.join(self.datos, "rotacion.json"))
        self.motor = modmotor.Motor(48000)
        self.registro = Registro(os.path.join(self.datos, "registro"))
        self.cues = Cues(self.cfg.cue)
        self.titulo = Titulo(self.cfg.metadatos)
        self.emisiones = Emisiones(self.ffmpeg, self.motor)
        self.emisiones.configurar(self.cfg.icecast, self.cfg.emisora)
        self.titulo.extra = self.emisiones.titulo
        self.emisor = Emisor(self.cfg, self.bib, self.rot, self.motor, self.ffmpeg, soxr,
                             self.registro, self.cues, self.titulo)
        self.emisor.reabrir = self._reabrir
        self._lock = threading.RLock()
        self._vu = [0.0, 0.0, 1.0]
        self._t_vu = time.monotonic()
        self.aviso_salida = ""
        self._aplicar_salida()
        self._calentar()
        self.emisor.arrancar_hilo()

    @property
    def error(self) -> str:
        """Lo que impide emitir, si hay algo."""
        return "" if self.ffmpeg else tr(
            "No se encuentra ffmpeg. Instálalo (winget install Gyan.FFmpeg) o deja "
            "ffmpeg.exe en la carpeta del programa.")

    def cerrar(self) -> None:
        self.emisor.detener()
        time.sleep(0.5)
        self.emisor.parar_hilo()
        self.emisiones.parar()
        self.motor.cerrar()
        self.cues.cerrar()
        self.rot.guardar()
        self.bib.cerrar()

    # ------------------------------------------------------------ emision

    def iniciar(self):
        """Abre la salida y empieza a emitir. Devuelve (bien, mensaje)."""
        with self._lock:
            if self.error:
                return False, self.error
            if self.emisor.emitiendo:
                return True, ""
            s = self.cfg.salida
            if s.api == modmotor.SIN_TARJETA and not self.emisiones.hay_activos():
                return False, tr("No hay por dónde emitir: la salida es «Sin tarjeta» y no hay "
                                 "ningún servidor Icecast activo.")
            try:
                self.aviso_salida = self.motor.abrir(s.api, s.dispositivo, s.latencia_ms / 1000.0)
            except Exception as e:
                return False, tr("No se puede abrir la salida de audio: %s") % e
            self.emisiones.arrancar()
            self.emisor.iniciar()
            return True, self.aviso_salida

    def detener(self) -> None:
        with self._lock:
            self.emisor.detener()
        threading.Timer(0.9, self._cerrar_salida).start()  # tras el fundido de salida

    def _cerrar_salida(self) -> None:
        with self._lock:
            if not self.emisor.emitiendo:
                self.emisiones.parar()
                self.motor.cerrar()

    def saltar(self) -> None:
        self.emisor.saltar()

    def replanificar(self) -> None:
        self.emisor.replanificar()

    def _reabrir(self) -> None:
        """La tarjeta ha dejado de pedir audio (desenchufada, driver caido): otra vez."""
        s = self.cfg.salida
        self.motor.cerrar()
        modmotor.dispositivos(refrescar=True)
        self.aviso_salida = self.motor.abrir(s.api, s.dispositivo, s.latencia_ms / 1000.0)

    def _aplicar_salida(self) -> None:
        s = self.cfg.salida
        self.motor.volumen = 10.0 ** (s.volumen_db / 20.0)
        self.motor.limitador = bool(s.limitador)
        self.motor.retardo = s.retardo_ms / 1000.0

    def _calentar(self) -> None:
        """Encarga el recorrido y el analisis de todo lo que nombra la configuracion."""
        for o in modconfig.origenes(self.cfg):
            if os.path.isfile(o) and rutas.es_audio(o):
                self.bib.pista(o, urgente=True)
            else:
                self.bib.listar(o)

    # ------------------------------------------------------------ estado

    def estado(self) -> dict:
        """La foto del emisor mas lo que anade el nucleo: vumetro, salida, version."""
        foto = dict(self.emisor.instantanea())
        with self._lock:
            ahora = time.monotonic()
            l, r, red = self.motor.niveles()
            cae = math.exp(-(ahora - self._t_vu) / 0.35)
            self._t_vu = ahora
            self._vu[0] = max(l, self._vu[0] * cae)
            self._vu[1] = max(r, self._vu[1] * cae)
            self._vu[2] = min(red, 1.0 - (1.0 - self._vu[2]) * cae)
            foto["vu"] = [self._vu[0], self._vu[1]]
            foto["limitando"] = self._vu[2] < 0.97
        foto["reloj"] = time.time()
        foto["tz"] = time.localtime().tm_gmtoff          # para que el panel web pinte la hora de aqui
        foto["emisora"] = self.cfg.emisora
        foto["idioma"] = idioma.actual()
        foto["nombre"] = NOMBRE
        foto["version"] = __version__
        foto["salida"] = list(self.motor.dispositivo) if self.motor.abierta() else \
            [self.cfg.salida.api, self.cfg.salida.dispositivo or N_("Predeterminada")]
        foto["aviso_salida"] = self.aviso_salida
        foto["icecast"] = self.emisiones.estado()
        foto["error"] = self.error
        return foto

    # ------------------------------------------------------------ configuracion

    def config(self) -> modconfig.Config:
        return self.cfg.copia()

    def guardar_config(self, cfg: modconfig.Config) -> str:
        """Guarda y aplica. Devuelve un aviso para ensenar (vacio si no hay nada que decir)."""
        aviso = ""
        with self._lock:
            vieja = self.cfg
            salida_cambia = (vieja.salida.api, vieja.salida.dispositivo, vieja.salida.latencia_ms) != \
                            (cfg.salida.api, cfg.salida.dispositivo, cfg.salida.latencia_ms)
            web_cambia = modconfig.a_dict(vieja.web) != modconfig.a_dict(cfg.web)
            self.cfg = cfg.copia()
            self.cfg.idioma = idioma.poner(self.cfg.idioma)
            modconfig.guardar(self.cfg, self.ruta_cfg)
            self._aplicar_salida()
            self.cues.configurar(self.cfg.cue)
            self.emisiones.configurar(self.cfg.icecast, self.cfg.emisora)
            self.emisor.aplicar_config(self.cfg)
            self._calentar()
            if salida_cambia and self.motor.abierta():
                s = self.cfg.salida
                try:
                    self.aviso_salida = self.motor.abrir(s.api, s.dispositivo, s.latencia_ms / 1000.0)
                    aviso = self.aviso_salida
                except Exception as e:
                    aviso = tr("No se puede abrir la salida de audio: %s") % e
            if web_cambia:
                aviso = (aviso + " " if aviso else "") + \
                    tr("Los cambios del panel web se aplican al reiniciar el programa.")
        return aviso

    def poner_idioma(self, codigo: str) -> None:
        """
        Cambia el idioma ya y lo deja guardado, sin pasar por Guardar: no es
        parte de la programacion, y no debe arrastrar cambios a medio hacer.
        """
        with self._lock:
            self.cfg.idioma = idioma.poner(codigo)
            modconfig.guardar(self.cfg, self.ruta_cfg)

    def config_dict(self) -> dict:
        return modconfig.a_dict(self.cfg)

    def guardar_config_dict(self, d: dict) -> str:
        return self.guardar_config(modconfig.de_dict(modconfig.Config, d))

    # ------------------------------------------------------------ ayudas para las interfaces

    @staticmethod
    def salidas(refrescar: bool = False) -> list:
        return modmotor.dispositivos(refrescar)

    def refrescar_salidas(self) -> list:
        """Vuelve a preguntar a Windows que tarjetas hay (solo se puede sin emitir)."""
        with self._lock:
            return modmotor.dispositivos(refrescar=not self.motor.abierta())

    def resumen(self, origen: str) -> dict:
        r = self.bib.resumen(origen) if origen else {"leyendo": False, "ficheros": 0,
                                                    "analizados": 0, "errores": 0, "segundos": 0.0}
        r["existe"] = bool(origen) and os.path.exists(origen)
        return r

    @staticmethod
    def explorar(ruta: str = "") -> dict:
        """Carpetas y audios de una ruta, para elegir desde el panel web."""
        if not ruta:
            if os.name == "nt":
                unidades = ["%s:\\" % u for u in string.ascii_uppercase if os.path.exists("%s:\\" % u)]
            else:
                unidades = ["/"]
            casa = os.path.expanduser("~")
            return {"ruta": "", "padre": None, "carpetas": unidades + [casa], "ficheros": []}
        ruta = os.path.abspath(ruta)
        carpetas, ficheros = [], []
        try:
            with os.scandir(ruta) as it:
                for e in it:
                    try:
                        if e.is_dir():
                            carpetas.append(e.path)
                        elif rutas.es_audio(e.name) or rutas.es_lista(e.name):
                            ficheros.append(e.path)
                    except OSError:
                        continue
        except OSError as e:
            return {"ruta": ruta, "padre": os.path.dirname(ruta), "carpetas": [], "ficheros": [],
                    "error": str(e)}
        padre = os.path.dirname(ruta)
        return {"ruta": ruta, "padre": "" if padre == ruta else padre,
                "carpetas": sorted(carpetas, key=str.lower), "ficheros": sorted(ficheros, key=str.lower)}

    @staticmethod
    def autosenales(carpeta: str) -> dict:
        """Reparte los audios de una carpeta entre las horas segun el numero de su nombre."""
        res = {}
        try:
            nombres = sorted(os.listdir(carpeta))
        except OSError:
            return res
        for nombre in nombres:
            if not rutas.es_audio(nombre):
                continue
            m = re.search(r"(?<!\d)(\d{1,2})(?!\d)", os.path.splitext(nombre)[0])
            if m and 0 <= int(m.group(1)) <= 24:
                res.setdefault(str(int(m.group(1)) % 24), os.path.join(carpeta, nombre))
        return res

    def probar_cue(self, destino, evento: str = "inicio") -> str:
        return self.cues.probar(destino, evento)
