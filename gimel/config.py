# -*- coding: utf-8 -*-
"""
Configuracion de GIMEL. Todo vive en un unico JSON (datos/config.json):

    franjas      de tal hora a tal hora: que canciones y que jingles
    general      la programacion que rige cuando no toca ninguna franja
    senales      el audio de cada hora en punto
    publicidad   bloques de publicidad / desconexion, cada uno con sus horas
    eventos      audios a minuto fijo (boletines, senales de las medias...)
    mezcla       cruces, recortes y normalizado
    salida       tarjeta de sonido (o ninguna)
    icecast      servidores de streaming a los que se manda la emision
    cue          avisos de inicio y de retorno de las desconexiones
    metadatos    titulo en emision hacia un fichero o una URL
    web          panel de control por navegador
    idioma       en que idioma hablan la ventana, el panel web y los avisos

Las franjas van por horas enteras porque la rotacion es por horas: cada hora
se planifica de una pieza con la franja que le toque.
"""

import copy
import dataclasses
import json
import os
import typing
from dataclasses import dataclass, field
from datetime import datetime

from .idioma import N_, tr

DIAS = ("L", "M", "X", "J", "V", "S", "D")
GENERAL = N_("Programación general")          # el nombre de fabrica de la programacion general


def _todos() -> list:
    return [True] * 7


def cubre(dias, desde: int, hasta: int, dia: int, hora: int) -> bool:
    """
    Si un tramo horario [desde, hasta) alcanza a (dia, hora). dia: 0 = lunes.
    Si 'hasta' no pasa de 'desde' el tramo cruza la medianoche, y los dias
    marcados son los del dia en que EMPIEZA.
    """
    d, h = desde % 24, hasta
    if h > d:
        return d <= hora < h and bool(dias[dia])
    if h == d:
        return bool(dias[dia])
    if hora >= d:
        return bool(dias[dia])
    if hora < h:
        return bool(dias[(dia - 1) % 7])
    return False


@dataclass
class Franja:
    nombre: str = N_("Franja nueva")
    activa: bool = True
    dias: typing.List[bool] = field(default_factory=_todos)
    desde: int = 0                   # hora de inicio, 0..23
    hasta: int = 24                  # hora de fin, 1..24
    canciones: str = ""              # carpeta o lista
    orden: str = "aleatorio"         # aleatorio | secuencial
    dur_min: float = 0.0             # descartar canciones mas cortas (0 = sin limite)
    dur_max: float = 0.0             # descartar canciones mas largas (0 = sin limite)
    jingles: bool = False
    jingles_origen: str = ""
    jingles_cada: int = 1            # un jingle cada N cambios de cancion
    jingles_modo: str = "encima"     # encima (pisando el cruce) | entre (cancion, jingle, cancion)
    senal: bool = True               # dar la senal horaria en esta franja
    jingle_tras_senal: bool = False  # indicativo justo despues de la senal
    publicidad: bool = True          # admitir bloques de publicidad / desconexion
    eventos: bool = True             # admitir eventos a minuto fijo

    def cubre(self, dia: int, hora: int) -> bool:
        return self.activa and cubre(self.dias, self.desde, self.hasta, dia, hora)


@dataclass
class Senales:
    activas: bool = True
    archivos: typing.Dict[str, str] = field(default_factory=dict)   # "0".."23" -> fichero
    generica: str = ""               # para las horas sin audio propio
    sincronia: str = "inicio"        # la hora en punto cae en: inicio | final | segundo
    segundo: float = 0.0             # con sincronia = segundo
    fundido: float = 2.0             # bajada de la musica antes de senales, bloques y eventos

    def archivo_de(self, hora: int) -> str:
        return self.archivos.get(str(int(hora) % 24), "") or self.generica


@dataclass
class BloquePubli:
    nombre: str = N_("Publicidad")
    activo: bool = True
    dias: typing.List[bool] = field(default_factory=_todos)
    desde: int = 0                   # horas en las que se programa
    hasta: int = 24
    minuto: int = 30                 # cuando, dentro de cada hora
    segundo: int = 0
    referencia: str = "jingle"       # a esa hora empieza: silencio | jingle | contenido
    contenido: str = "cunas"         # cunas | relleno (musica de relleno todo el bloque)
    duracion: float = 60.0           # lo que dura el contenido: EXACTO
    origen: str = ""                 # carpeta o lista con las cunas
    orden: str = "aleatorio"         # aleatorio | secuencial
    sobrante: str = "cortar"         # si las cunas no llenan: cortar | relleno | silencio
    relleno_origen: str = ""         # musica de relleno (fichero, carpeta o lista)
    silencio_antes: float = 5.0      # silencio antes del jingle de entrada
    jingle: bool = True              # jingle de entrada (ADS / desconexion)
    jingle_origen: str = ""          # fichero o carpeta; vacio = jingles de la franja
    silencio_despues: float = 5.0    # negro al acabar el contenido
    jingle_salida: bool = False      # jingle de vuelta, tras el negro
    jingle_salida_origen: str = ""
    cue: bool = True                 # emitir CUE de desconexion y de reconexion
    cue_tras: float = 2.0            # el de desconexion sale a los N s de empezar el silencio previo
    cue_retorno_tras: float = 2.0    # el de reconexion, a los N s de empezar el negro final

    def cubre(self, dia: int, hora: int) -> bool:
        return self.activo and cubre(self.dias, self.desde, self.hasta, dia, hora)

    def desfase(self) -> float:
        return self.minuto * 60.0 + self.segundo


@dataclass
class EventoFijo:
    nombre: str = N_("Evento")
    activo: bool = True
    dias: typing.List[bool] = field(default_factory=_todos)
    desde: int = 0
    hasta: int = 24
    minuto: int = 30
    segundo: int = 0
    origen: str = ""                 # fichero, carpeta o lista (si hay varios, rotan)
    orden: str = "aleatorio"

    def cubre(self, dia: int, hora: int) -> bool:
        return self.activo and cubre(self.dias, self.desde, self.hasta, dia, hora)

    def desfase(self) -> float:
        return self.minuto * 60.0 + self.segundo


@dataclass
class Mezcla:
    crossfade: float = 4.0           # fundido de la cancion que sale cuando se la corta antes de hora
    recorte_max: float = 20.0        # lo mas que se le quita a una cancion para cuadrar la hora
    min_suena: float = 30.0          # una cancion que fuera a sonar menos que esto no entra
    umbral: float = -15.0            # dB bajo el nivel de la cancion en que entra la siguiente
    solape_max: float = 8.0          # tope del solape natural al final de una cancion
    solape_jingle: float = 15.0      # tope de jingle sonando sobre la cancion que entra
    atenuacion_jingle: float = 6.0   # dB que baja la cancion que entra mientras suena el jingle
    fundido_salto: float = 1.0       # cruce al saltar una cancion a mano
    separar_artista: int = 3         # canciones entre dos del mismo artista
    normalizar: bool = True
    objetivo_lufs: float = -14.0
    gan_canciones: float = 0.0       # retoque por tipo, en dB
    gan_jingles: float = 0.0
    gan_cunas: float = 0.0
    gan_senales: float = 0.0


@dataclass
class Salida:
    api: str = "Windows WASAPI"
    dispositivo: str = ""            # vacio = la predeterminada del sistema
    latencia_ms: int = 200           # colchon: da igual para la hora (se compensa) y evita cortes
    volumen_db: float = 0.0
    retardo_ms: float = 0.0          # retardo de lo que cuelga detras (procesador...), a compensar
    limitador: bool = True


# Lo que viaja en un CUE no depende del idioma del programa: quien lo recibe
# espera siempre las mismas palabras, break (desconexion) y endbreak (reconexion).
CUE_BREAK, CUE_ENDBREAK = "break", "endbreak"
CUE_INICIO = ('{"evento":"break","emisora":"{emisora}","bloque":"{bloque}",'
              '"duracion":{duracion},"contenido":{contenido},"hora":"{hora}","epoch":{epoch}}')
CUE_RETORNO = ('{"evento":"endbreak","emisora":"{emisora}","bloque":"{bloque}",'
               '"hora":"{hora}","epoch":{epoch}}')

# los mensajes de fabrica de antes de break / endbreak: al cargar una
# configuracion que aun los tenga, se ponen al dia (lo escrito a mano no se toca)
_CUE_ANTES = {
    CUE_INICIO.replace('"break"', '"desconexion"'): CUE_INICIO,
    CUE_RETORNO.replace('"endbreak"', '"reconexion"'): CUE_RETORNO,
    "CUE-OUT {duracion}": "break {duracion}",
    "CUE-IN": "endbreak",
    "DESCONEXION {duracion} {hora}": "break {duracion} {hora}",
    "RECONEXION {hora}": "endbreak {hora}",
}


@dataclass
class DestinoCue:
    nombre: str = N_("Servidor")
    activo: bool = True
    tipo: str = "http"               # http | tcp | udp | archivo | dtmf
    destino: str = "http://127.0.0.1:8951/cue"   # URL, host:puerto o fichero (dtmf no lo usa)
    inicio: str = CUE_INICIO         # mensaje del CUE de desconexion
    retorno: str = CUE_RETORNO       # mensaje del CUE de reconexion


@dataclass
class Cue:
    activo: bool = False
    adelanto_ms: float = 0.0         # mandar los CUE un poco antes (+) o despues (-)
    reintentos: int = 2              # si el servidor no contesta
    destinos: typing.List[DestinoCue] = field(default_factory=list)


@dataclass
class Icecast:
    nombre: str = "Icecast"
    activo: bool = True
    servidor: str = "localhost"
    puerto: int = 8000
    punto: str = "/gimel"            # punto de montaje
    usuario: str = "source"
    clave: str = "hackme"
    tls: bool = False                # conexion cifrada (servidores con https)
    formato: str = "mp3"             # mp3 | aac | ogg | opus
    bitrate: int = 128               # kbps
    frecuencia: int = 44100          # Hz (Opus va siempre a 48000)
    estereo: bool = True
    metadatos: bool = True           # mandar el titulo de cada cancion (MP3 y AAC)
    titulo: str = ""                 # nombre del stream; vacio = el de la emisora
    descripcion: str = ""
    genero: str = ""
    web: str = ""
    publico: bool = False            # anunciarlo en los directorios


@dataclass
class Metadatos:
    activo: bool = False
    archivo: str = ""                # fichero de texto con lo que suena
    url: str = ""                    # o una URL a la que avisar ({texto} va codificado)
    plantilla: str = "{artista} - {titulo}"
    solo_canciones: bool = True      # jingles, cunas y senales no cambian el texto
    texto_resto: str = ""            # con solo_canciones apagado: texto para lo que no es cancion


@dataclass
class Web:
    activa: bool = True
    host: str = "127.0.0.1"          # 0.0.0.0 para entrar desde otros equipos
    puerto: int = 8950
    clave: str = ""                  # sin clave solo se atiende a este mismo equipo


@dataclass
class Config:
    emisora: str = "GIMEL"
    franjas: typing.List[Franja] = field(default_factory=list)
    general: Franja = field(default_factory=lambda: Franja(nombre=GENERAL))
    senales: Senales = field(default_factory=Senales)
    publicidad: typing.List[BloquePubli] = field(default_factory=list)
    eventos: typing.List[EventoFijo] = field(default_factory=list)
    mezcla: Mezcla = field(default_factory=Mezcla)
    salida: Salida = field(default_factory=Salida)
    icecast: typing.List[Icecast] = field(default_factory=list)
    cue: Cue = field(default_factory=Cue)
    metadatos: Metadatos = field(default_factory=Metadatos)
    web: Web = field(default_factory=Web)
    arranque_automatico: bool = False
    idioma: str = "es"               # de las interfaces y de los avisos (gimel/idioma.py)

    def franja_de(self, momento: datetime) -> Franja:
        """La primera franja de la lista que cubra ese momento; si no, la general."""
        for f in self.franjas:
            if f.cubre(momento.weekday(), momento.hour):
                return f
        return self.general

    def copia(self) -> "Config":
        return copy.deepcopy(self)


def nuevo(clase):
    """Un objeto recien anadido desde una interfaz: su nombre de fabrica, en el idioma de ahora."""
    obj = clase()
    obj.nombre = tr(obj.nombre)
    return obj


def nombre_franja(nombre: str) -> str:
    """El nombre de una franja para ensenarlo: el de fabrica de la general se traduce."""
    return tr(nombre) if nombre == GENERAL else nombre


# ---------------------------------------------------------------- JSON

def _convertir(tipo, valor):
    origen = typing.get_origin(tipo)
    if dataclasses.is_dataclass(tipo):
        return de_dict(tipo, valor) if isinstance(valor, dict) else tipo()
    if origen is list:
        (t,) = typing.get_args(tipo)
        return [_convertir(t, v) for v in valor]
    if origen is dict:
        _, t = typing.get_args(tipo)
        return {str(k): _convertir(t, v) for k, v in valor.items()}
    if tipo is bool:
        return bool(valor)
    if tipo is int:
        return int(valor)
    if tipo is float:
        return float(valor)
    if tipo is str:
        return str(valor)
    return valor


def de_dict(clase, d: dict):
    """Lo que falte se queda con su valor por defecto; lo que sobre se ignora."""
    tipos = typing.get_type_hints(clase)
    args = {}
    for f in dataclasses.fields(clase):
        if f.name in d:
            try:
                args[f.name] = _convertir(tipos[f.name], d[f.name])
            except Exception:
                pass
    obj = clase(**args)
    if hasattr(obj, "dias"):
        obj.dias = ([bool(x) for x in obj.dias] + [True] * 7)[:7]
    return obj


def a_dict(cfg) -> dict:
    return dataclasses.asdict(cfg)


def origenes(cfg: Config) -> list:
    """Todas las carpetas, listas y ficheros de audio que nombra una configuracion."""
    res = []
    for f in cfg.franjas + [cfg.general]:
        res += [f.canciones, f.jingles_origen]
    for b in cfg.publicidad:
        res += [b.origen, b.relleno_origen, b.jingle_origen, b.jingle_salida_origen]
    for e in cfg.eventos:
        res.append(e.origen)
    res += list(cfg.senales.archivos.values()) + [cfg.senales.generica]
    return [o for o in dict.fromkeys(res) if o]


def al_dia(cfg: Config) -> Config:
    """Lo que una configuracion guardada por una version anterior trae de otra manera."""
    for d in cfg.cue.destinos:
        d.inicio = _CUE_ANTES.get(d.inicio, d.inicio)
        d.retorno = _CUE_ANTES.get(d.retorno, d.retorno)
    return cfg


def importar(ruta: str) -> Config:
    """La configuracion de un fichero cualquiera; lanza excepcion si no lo es."""
    with open(ruta, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    if not isinstance(d, dict) or not set(d) & {f.name for f in dataclasses.fields(Config)}:
        raise ValueError(tr("no es una configuración de GIMEL"))
    return al_dia(de_dict(Config, d))


def cargar(ruta: str) -> Config:
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            return al_dia(de_dict(Config, json.load(fh)))
    except FileNotFoundError:
        return Config()
    except Exception:
        # un JSON roto no puede dejar la emisora sin arrancar: se aparta y se sigue
        try:
            os.replace(ruta, ruta + ".roto")
        except OSError:
            pass
        return Config()


def guardar(cfg: Config, ruta: str) -> None:
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(a_dict(cfg), fh, ensure_ascii=False, indent=2)
    os.replace(tmp, ruta)
