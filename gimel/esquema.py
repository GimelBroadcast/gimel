# -*- coding: utf-8 -*-
"""
Esquema de los formularios de configuracion.

Las dos interfaces (la de escritorio y el panel web) pintan sus formularios a
partir de estas listas, asi que tienen siempre las mismas opciones, con los
mismos nombres y las mismas ayudas, y anadir una opcion nueva es anadir una
linea aqui. Los textos van en español y se traducen al pintarlos (gimel/idioma.py).

Cada campo es un dict:
    clave      atributo de la dataclass de config
    etiqueta   lo que lee el usuario
    tipo       titulo | texto | parrafo | clave | bool | entero | decimal | opcion |
               origen | dias | hora | hora_fin | salida | entrada (de tarjeta: "API|nombre")
    ayuda      explicacion larga (opcional)
    min, max, paso, sufijo        para los numeros
    opciones   [(valor, texto)]   para tipo = opcion
    modo       carpeta | fichero | cualquiera | guardar   para tipo = origen
    si         (clave, [valores]): solo se ensena si otro campo vale eso
"""

from .config import CUE_INICIO, CUE_RETORNO
from .idioma import IDIOMAS, tr
from .motor import APIS, SIN_TARJETA


def c(clave, etiqueta, tipo, ayuda="", **mas) -> dict:
    d = {"clave": clave, "etiqueta": etiqueta, "tipo": tipo, "ayuda": ayuda}
    d.update(mas)
    return d


def t(texto, **mas) -> dict:
    d = {"clave": "", "etiqueta": texto, "tipo": "titulo", "ayuda": ""}
    d.update(mas)
    return d


ORDEN = [("aleatorio", "Aleatorio: no se repite nada hasta que haya sonado todo"),
         ("secuencial", "Secuencial: en el orden de la lista")]
ORDEN_PAUTA = ORDEN + [("pauta", "Pauta importada: la lista que toca a cada hora")]

_CUANDO = [
    c("nombre", "Nombre", "texto"),
    c("dias", "Días", "dias"),
    c("desde", "Desde las", "hora"),
    c("hasta", "Hasta las", "hora_fin",
      "Si la hora de fin no pasa de la de inicio, cruza la medianoche."),
]

FRANJA = [
    t("Cuándo", solo_franja=True),
    c("activa", "Franja activa", "bool", solo_franja=True),
    *[dict(x, solo_franja=True) for x in _CUANDO],
    t("Canciones"),
    c("canciones", "Carpeta o lista", "origen",
      "Carpeta (con sus subcarpetas) o lista .m3u / .pls de la que sale la música. Con «Pauta "
      "importada», la carpeta donde se importan las pautas (Archivo > Importar pauta).",
      modo="carpeta"),
    c("orden", "Orden", "opcion",
      "Pauta importada: cada hora suena la lista de esa hora que haya mandado el planificador "
      "de música (MusicMaster, Selector, Powergold…), en su orden; GIMEL la cuadra. Una hora sin "
      "pauta tira de la programación general.",
      opciones=ORDEN_PAUTA),
    c("dur_min", "Descartar las de menos de", "decimal", "0 = sin límite.",
      min=0, max=3600, paso=5, sufijo="s"),
    c("dur_max", "Descartar las de más de", "decimal", "0 = sin límite.",
      min=0, max=36000, paso=10, sufijo="s"),
    t("Jingles"),
    c("jingles", "Poner jingles entre canciones", "bool"),
    c("jingles_origen", "Carpeta o lista de jingles", "origen", modo="carpeta"),
    c("jingles_orden", "Orden de los jingles", "opcion", opciones=ORDEN),
    c("jingles_cada", "Un jingle cada", "entero", min=1, max=99, sufijo="cambios de canción"),
    c("jingles_modo", "Colocación", "opcion",
      "Encima: el jingle suena sobre el cruce, pisando el final de una canción y el "
      "principio de la otra. Entre: canción, jingle, canción.",
      opciones=[("encima", "Encima del cruce entre canciones"),
                ("entre", "Entre canción y canción")]),
    t("En las horas de esta programación"),
    c("senal", "Dar la señal horaria", "bool"),
    c("jingle_tras_senal", "Indicativo (un jingle) justo después de la señal", "bool"),
    c("publicidad", "Admitir bloques de publicidad / desconexión", "bool"),
    c("eventos", "Admitir eventos a minuto fijo", "bool"),
]

SENALES = [
    c("activas", "Dar señales horarias", "bool"),
    c("sincronia", "La hora en punto cae", "opcion",
      "Para unos pitos, lo normal es que el último empiece justo en punto: "
      "elige «en un segundo concreto» y di en cuál.",
      opciones=[("inicio", "cuando EMPIEZA el audio"),
                ("final", "cuando ACABA el audio"),
                ("segundo", "en un segundo concreto del audio")]),
    c("segundo", "Segundo del audio que cae en punto", "decimal",
      min=0, max=600, paso=0.1, decimales=3, sufijo="s", si=("sincronia", ["segundo"])),
    c("fundido", "Bajada de la música antes", "decimal",
      "Si hay que cortar lo que suena para dar la señal (o un bloque, o un evento), "
      "se le baja el volumen durante este tiempo.",
      min=0, max=20, paso=0.5, sufijo="s"),
    c("generica", "Señal para las horas sin audio propio", "origen", modo="fichero"),
]

BLOQUE = [
    t("Cuándo"),
    c("activo", "Bloque activo", "bool"),
    c("nombre", "Nombre", "texto"),
    c("dias", "Días", "dias"),
    c("desde", "Solo en las horas desde las", "hora"),
    c("hasta", "hasta las", "hora_fin"),
    c("minuto", "Minuto de cada hora", "entero", min=0, max=59),
    c("segundo", "Segundo", "entero", min=0, max=59),
    c("referencia", "A esa hora", "opcion",
      opciones=[("jingle", "empieza el jingle de entrada"),
                ("silencio", "empieza el silencio previo (calla la música)"),
                ("contenido", "empiezan las cuñas / el relleno")]),
    t("Contenido"),
    c("contenido", "Qué suena", "opcion",
      "Música de relleno: para cuando el CUE hace que los demás desconecten y por "
      "aquí solo hay que cubrir el hueco.",
      opciones=[("cunas", "Cuñas (sublista de publicidad)"),
                ("relleno", "Música de relleno")]),
    c("duracion", "Duración exacta", "decimal",
      "Lo que dura el contenido, clavado. La música se reajusta alrededor.",
      min=1, max=3000, paso=5, sufijo="s"),
    c("origen", "Carpeta o lista de cuñas", "origen",
      "Con «Pauta importada», la carpeta donde se importa la pauta de publicidad.",
      modo="carpeta", si=("contenido", ["cunas"])),
    c("orden", "Orden de las cuñas", "opcion",
      "Pauta importada: en cada corte, las cuñas que mande el programa de publicidad para esa "
      "hora y ese minuto, en su orden.",
      opciones=[(v, x.replace("a cada hora", "en cada corte")) for v, x in ORDEN_PAUTA],
      si=("contenido", ["cunas"])),
    c("sobrante", "Si las cuñas no llenan el tiempo", "opcion",
      "Huecos de menos de 3 s se reparten en respiros entre cuña y cuña.",
      opciones=[("cortar", "Otra cuña más, cortada al llegar al tiempo"),
                ("relleno", "Música de relleno hasta completar"),
                ("silencio", "Silencio hasta completar")],
      si=("contenido", ["cunas"])),
    c("relleno_origen", "Música de relleno", "origen",
      "Fichero, carpeta o lista. Se funde al acabar el tiempo.", modo="cualquiera"),
    t("Entrada y salida"),
    c("silencio_antes", "Silencio antes de entrar", "decimal", min=0, max=60, paso=0.5, sufijo="s"),
    c("jingle", "Jingle de entrada (ADS / desconexión)", "bool"),
    c("jingle_origen", "Jingle de entrada", "origen",
      "Fichero o carpeta. Vacío: uno de los jingles de la franja.", modo="cualquiera",
      si=("jingle", [True])),
    c("silencio_despues", "A negro al terminar", "decimal", min=0, max=60, paso=0.5, sufijo="s"),
    c("jingle_salida", "Jingle de vuelta, después del negro", "bool"),
    c("jingle_salida_origen", "Jingle de vuelta", "origen",
      "Fichero o carpeta. Vacío: uno de los jingles de la franja.", modo="cualquiera",
      si=("jingle_salida", [True])),
    t("CUE"),
    c("cue", "Emitir CUE de desconexión y de reconexión", "bool",
      "Los servidores a los que se mandan se configuran en la página CUE."),
    c("cue_tras", "CUE de desconexión", "decimal",
      min=0, max=60, paso=0.5, sufijo="s después de empezar el silencio previo", si=("cue", [True])),
    c("cue_retorno_tras", "CUE de reconexión", "decimal",
      min=0, max=60, paso=0.5, sufijo="s después de empezar el negro final", si=("cue", [True])),
]

EVENTO = [
    c("activo", "Evento activo", "bool"),
    c("nombre", "Nombre", "texto"),
    c("dias", "Días", "dias"),
    c("desde", "Solo en las horas desde las", "hora"),
    c("hasta", "hasta las", "hora_fin"),
    c("minuto", "Minuto de cada hora", "entero", min=0, max=59),
    c("segundo", "Segundo", "entero", min=0, max=59),
    c("tipo", "Qué suena", "opcion",
      "Enlace con la cadena (network join): a esa hora exacta la emisión se engancha al directo "
      "de la cadena, por un stream o por una entrada de la tarjeta, y lo da durante el tiempo "
      "que digas. Si el directo se corta, sale silencio y se reconecta; la hora sigue cuadrando.",
      opciones=[("audio", "Un audio"), ("enlace", "Enlace con la cadena (directo)")]),
    c("origen", "Audio", "origen",
      "Un fichero, o una carpeta o lista si quieres que vayan rotando.", modo="cualquiera",
      si=("tipo", ["audio"])),
    c("orden", "Si hay varios", "opcion", opciones=ORDEN, si=("tipo", ["audio"])),
    c("enlace", "Stream de la cadena", "texto",
      "URL del directo (http://…/cadena.mp3). Vacío: la entrada de tarjeta de abajo.",
      si=("tipo", ["enlace"])),
    c("entrada", "O entrada de tarjeta", "entrada",
      "La línea por la que llega la cadena (un receptor de satélite, un códec).", si=("tipo", ["enlace"])),
    c("duracion", "Duración exacta", "decimal", min=1, max=36000, paso=30, sufijo="s",
      si=("tipo", ["enlace"])),
]

MEZCLA = [
    t("Cuadrar la hora"),
    c("recorte_max", "Recorte máximo por canción", "decimal",
      "Para que las canciones entren en la hora se adelanta el cruce de cada una, "
      "repartiendo el recorte entre todas. Este es el tope por canción.",
      min=0, max=300, paso=1, sufijo="s"),
    c("crossfade", "Fundido de una canción recortada", "decimal",
      "Lo que tarda en desaparecer la canción que sale cuando se la cruza antes de su final.",
      min=0.2, max=30, paso=0.5, sufijo="s"),
    c("min_suena", "Una canción suena al menos", "decimal",
      "Si al final de un tramo una canción fuera a sonar menos que esto, no entra.",
      min=0, max=300, paso=5, sufijo="s"),
    t("Cruces"),
    c("umbral", "Nivel al que entra la siguiente", "decimal",
      "La siguiente canción arranca cuando la que suena cae estos dB por debajo de su "
      "nivel. Más negativo = cruces más tardíos.",
      min=-36, max=-3, paso=1, sufijo="dB"),
    c("solape_max", "Solape máximo al final de una canción", "decimal",
      min=0, max=30, paso=0.5, sufijo="s"),
    c("fundido_salto", "Cruce al saltar una canción a mano", "decimal",
      min=0.1, max=10, paso=0.1, sufijo="s"),
    c("separar_artista", "Separación entre dos del mismo artista", "entero",
      min=0, max=50, sufijo="canciones"),
    t("Jingles encima del cruce"),
    c("solape_jingle", "Jingle sonando sobre la canción que entra, como mucho", "decimal",
      "Con un jingle más largo que esto, la canción espera para entrar.",
      min=0, max=120, paso=1, sufijo="s"),
    c("atenuacion_jingle", "Bajar la canción que entra mientras suena el jingle", "decimal",
      min=0, max=30, paso=1, sufijo="dB"),
    t("Volumen"),
    c("normalizar", "Igualar el volumen de todos los audios", "bool"),
    c("objetivo_lufs", "Nivel objetivo", "decimal", min=-30, max=-8, paso=0.5, sufijo="LUFS",
      si=("normalizar", [True])),
    c("gan_canciones", "Retoque de las canciones", "decimal", min=-24, max=12, paso=0.5, sufijo="dB"),
    c("gan_jingles", "Retoque de los jingles", "decimal", min=-24, max=12, paso=0.5, sufijo="dB"),
    c("gan_cunas", "Retoque de las cuñas", "decimal", min=-24, max=12, paso=0.5, sufijo="dB"),
    c("gan_senales", "Retoque de señales y eventos", "decimal", min=-24, max=12, paso=0.5, sufijo="dB"),
]

SALIDA = [
    c("api", "Sistema de audio", "opcion",
      "«Sin tarjeta»: la emisión no sale por ningún altavoz, solo hacia los servidores "
      "Icecast (página Icecast). Sirve para un equipo sin sonido o para no ocupar la tarjeta.",
      opciones=[(a, a.replace("Windows ", "")) for a in APIS]
      + [(SIN_TARJETA, "Sin tarjeta: solo Icecast")]),
    c("dispositivo", "Salida de audio", "salida",
      "Por qué tarjeta (o cable virtual) sale la emisión.", si=("api", list(APIS))),
    c("latencia_ms", "Búfer", "entero",
      "Si se oyen cortes, súbelo. No afecta a la exactitud de las horas.",
      min=20, max=1000, paso=10, sufijo="ms", si=("api", list(APIS))),
    c("volumen_db", "Volumen de salida", "decimal", min=-60, max=12, paso=0.5, sufijo="dB"),
    c("limitador", "Limitador de seguridad", "bool",
      "Evita la saturación cuando coinciden dos audios fuertes."),
    c("retardo_ms", "Retardo de la cadena a compensar", "decimal",
      "Si detrás de la tarjeta hay algo que retrasa el audio (un procesador, el "
      "codificador), ponlo aquí y todo se adelanta para que la hora siga cayendo en punto.",
      min=-5000, max=30000, paso=10, sufijo="ms"),
]

ICECAST = [
    t("Servidor"),
    c("activo", "Enviar a este servidor", "bool"),
    c("nombre", "Nombre", "texto", "Solo para reconocerlo en esta lista."),
    c("servidor", "Servidor", "texto", "Nombre o dirección IP, sin http://."),
    c("puerto", "Puerto", "entero", min=1, max=65535),
    c("punto", "Punto de montaje", "texto", "Por ejemplo /radio o /directo.mp3."),
    c("usuario", "Usuario", "texto", "Casi siempre «source»."),
    c("clave", "Contraseña", "clave"),
    c("tls", "Conexión cifrada (TLS)", "bool"),
    t("Sonido"),
    c("formato", "Formato", "opcion",
      opciones=[("mp3", "MP3 (lo oye cualquier reproductor)"),
                ("aac", "AAC (mejor calidad a pocos kbps)"),
                ("ogg", "Ogg Vorbis"),
                ("opus", "Ogg Opus")]),
    c("bitrate", "Calidad", "entero", min=16, max=320, paso=16, sufijo="kbps"),
    c("frecuencia", "Frecuencia de muestreo", "opcion",
      opciones=[(48000, "48 000 Hz"), (44100, "44 100 Hz"), (32000, "32 000 Hz"),
                (22050, "22 050 Hz")],
      si=("formato", ["mp3", "aac", "ogg"])),
    c("estereo", "Estéreo", "bool"),
    t("Lo que ve el oyente"),
    c("metadatos", "Mandar el título de cada canción", "bool",
      "Con MP3 y AAC. El texto es el de la página «CUE y título» (Artista - Título)."),
    c("titulo", "Nombre del stream", "texto", "Vacío: el nombre de la emisora."),
    c("descripcion", "Descripción", "texto"),
    c("genero", "Género", "texto"),
    c("web", "Página web", "texto"),
    c("publico", "Anunciarlo en los directorios públicos", "bool"),
]

CUE = [
    c("activo", "Emitir los CUE", "bool"),
    c("adelanto_ms", "Adelantar los CUE", "decimal",
      "Positivo: salen un poco antes de su momento. Negativo: después.",
      min=-10000, max=10000, paso=50, sufijo="ms"),
    c("reintentos", "Reintentos si un servidor no contesta", "entero", min=0, max=5),
]

TIPOS_CUE = [("http", "HTTP (POST del mensaje a una URL)"),
             ("tcp", "TCP (una línea a host:puerto)"),
             ("udp", "UDP (un datagrama a host:puerto)"),
             ("archivo", "Fichero de texto"),
             ("dtmf", "Tonos DTMF dentro del audio")]

# lo que se propone al elegir cada tipo: (destino, CUE de desconexion, CUE de reconexion)
PLANTILLAS_CUE = {
    "http": ("http://127.0.0.1:8951/cue", CUE_INICIO, CUE_RETORNO),
    "tcp": ("127.0.0.1:8952", "break {duracion}", "endbreak"),
    "udp": ("127.0.0.1:8952", "break {duracion}", "endbreak"),
    "archivo": ("cue.txt", "break {duracion} {hora}", "endbreak {hora}"),
    "dtmf": ("", "*1#", "*0#"),
}

DESTINO_CUE = [
    c("activo", "Activo", "bool"),
    c("nombre", "Nombre", "texto"),
    c("tipo", "Tipo", "opcion", opciones=TIPOS_CUE),
    c("destino", "Servidor", "texto",
      "HTTP: la URL. TCP y UDP: host:puerto. Fichero: su ruta. DTMF: nada."),
    c("inicio", "CUE de desconexión", "parrafo",
      "Variables: {evento} (break o endbreak), {duracion} (segundos hasta la reconexión), "
      "{contenido} (lo que duran las cuñas), {bloque}, {emisora}, {hora}, {fecha}, {epoch}, "
      "{silencio}."),
    c("retorno", "CUE de reconexión", "parrafo"),
]

METADATOS = [
    c("activo", "Publicar lo que suena", "bool",
      "Para el RDS, el streaming o una web: el título en emisión, en un fichero o hacia una URL."),
    c("archivo", "Fichero de texto", "origen", modo="guardar"),
    c("url", "URL a la que avisar", "texto",
      "Se llama con GET; {texto} se sustituye por el título, ya codificado."),
    c("plantilla", "Texto", "texto", "Variables: {artista} {titulo} {emisora}."),
    c("solo_canciones", "Solo las canciones cambian el texto", "bool"),
    c("texto_resto", "Texto para lo demás (cuñas, señales…)", "texto",
      si=("solo_canciones", [False])),
]

WEB = [
    c("activa", "Panel de control por navegador", "bool"),
    c("host", "Quién puede entrar", "opcion",
      opciones=[("127.0.0.1", "Solo este equipo"), ("0.0.0.0", "Cualquier equipo de la red")]),
    c("puerto", "Puerto", "entero", min=1, max=65535),
    c("clave", "Contraseña", "clave",
      "Sin contraseña, el panel solo atiende a este mismo equipo aunque esté abierto a la red."),
]

SILENCIO = [
    c("activo", "Vigilar el silencio", "bool",
      "Si la emisión principal se queda muda (una carpeta que desaparece, un directo caído), entra "
      "sola una lista de emergencia, en bucle, encima de la principal. Cuando la principal vuelve "
      "a sonar, la de emergencia se retira con un fundido."),
    c("segundos", "Silencio que hace saltar la emergencia", "decimal",
      "Más que el negro de un bloque de publicidad, para que no salte en cada desconexión.",
      min=2, max=600, paso=1, sufijo="s"),
    c("umbral_db", "Por debajo de este nivel es silencio", "decimal", min=-80, max=-10, paso=1, sufijo="dBFS"),
    c("origen", "Lista de emergencia", "origen", "Carpeta o lista con la música de reserva.", modo="carpeta"),
    c("orden", "Orden", "opcion", opciones=ORDEN),
    c("vuelta", "Retirarla con la principal sonando", "decimal", min=1, max=120, paso=1, sufijo="s"),
]

GRABACION = [
    t("Cuándo"),
    c("activa", "Grabación activa", "bool"),
    c("nombre", "Nombre", "texto", "Va en el nombre del fichero, con la fecha y la hora."),
    c("dias", "Días", "dias"),
    c("hora", "Empieza a las", "hora"),
    c("minuto", "Minuto", "entero", min=0, max=59),
    c("segundo", "Segundo", "entero", min=0, max=59),
    c("duracion", "Duración", "decimal", min=0.1, max=1440, paso=1, sufijo="min"),
    t("Qué se graba"),
    c("fuente", "Fuente", "opcion",
      opciones=[("url", "Un stream (un corresponsal, otra emisora)"),
                ("entrada", "Una entrada de la tarjeta (una línea, un híbrido)"),
                ("antena", "Lo que sale al aire")]),
    c("url", "URL del stream", "texto", si=("fuente", ["url"])),
    c("entrada", "Entrada de tarjeta", "entrada", si=("fuente", ["entrada"])),
    t("Dónde"),
    c("carpeta", "Carpeta", "origen", modo="carpeta"),
    c("formato", "Formato", "opcion", opciones=[("mp3", "MP3"), ("wav", "WAV (sin pérdida)")]),
    c("bitrate", "Calidad", "entero", min=32, max=320, paso=32, sufijo="kbps", si=("formato", ["mp3"])),
    c("lista", "Al acabar, añadirla a", "opcion",
      "Ingesta: la grabación entra sola en una lista auxiliar, lista para lanzarla.",
      opciones=[(0, "Ninguna lista"), (1, "Lista auxiliar 1"), (2, "Lista auxiliar 2"),
                (3, "Lista auxiliar 3"), (4, "Lista auxiliar 4")]),
]

LOGGER = [
    c("activo", "Grabar todo lo que sale al aire", "bool",
      "La prueba de lo emitido: un MP3 por hora en una carpeta por día. Graba mientras se emite."),
    c("carpeta", "Carpeta", "origen", modo="carpeta"),
    c("bitrate", "Calidad", "entero", min=16, max=192, paso=16, sufijo="kbps"),
    c("dias", "Guardar", "entero", "Lo más viejo se borra solo. 0 = no borrar nunca.",
      min=0, max=3650, sufijo="días"),
]

RESERVA = [
    c("activa", "Este equipo es la reserva de otro GIMEL", "bool",
      "Playout espejo: este equipo vigila al principal y, si deja de emitir, empieza a emitir él. "
      "La salida de los dos tiene que poder juntarse fuera (un conmutador con detector de "
      "silencio, o un punto de montaje de reserva en Icecast)."),
    c("principal", "Panel web del principal", "texto",
      "Por ejemplo http://192.168.1.10:8950. El principal tiene que tener el panel abierto a la red "
      "y con contraseña."),
    c("clave", "Contraseña del panel del principal", "clave"),
    c("espera", "Tomar el relevo tras", "decimal",
      "Segundos sin saber del principal, o sin que emita.", min=2, max=600, paso=1, sufijo="s"),
    c("devolver", "Apartarse cuando el principal vuelva a emitir", "bool"),
    c("copiar", "Copiar la programación del principal", "bool",
      "Mientras no emite, cada minuto. No se copian la tarjeta, el panel web, Icecast ni esto. "
      "Las carpetas de música tienen que verse igual desde los dos equipos."),
]

SISTEMA = [
    c("emisora", "Nombre de la emisora", "texto"),
    c("arranque_automatico", "Empezar a emitir al abrir el programa", "bool",
      "Apagado: al abrir se genera la rotación y se espera a que pulses Emitir."),
    c("idioma", "Idioma", "opcion",
      "De la ventana, del panel web y de los avisos de la emisión.", opciones=list(IDIOMAS)),
]

ESQUEMA = {"franja": FRANJA, "senales": SENALES, "bloque": BLOQUE, "evento": EVENTO,
           "mezcla": MEZCLA, "salida": SALIDA, "icecast": ICECAST, "cue": CUE,
           "destino_cue": DESTINO_CUE, "metadatos": METADATOS, "web": WEB, "sistema": SISTEMA,
           "silencio": SILENCIO, "grabacion": GRABACION, "logger": LOGGER, "reserva": RESERVA}

TRADUCIBLE = ("etiqueta", "ayuda", "sufijo")      # lo que de un campo lee el usuario (y sus opciones)


def traducido() -> dict:
    """El esquema en el idioma de ahora, para quien no puede llamar a tr(): el panel web."""
    def campo(c: dict) -> dict:
        d = dict(c)
        for k in TRADUCIBLE:
            if d.get(k):
                d[k] = tr(d[k])
        if d.get("opciones"):
            d["opciones"] = [(v, tr(texto)) for v, texto in d["opciones"]]
        return d
    return {nombre: [campo(c) for c in campos] for nombre, campos in ESQUEMA.items()}
