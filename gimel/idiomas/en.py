# -*- coding: utf-8 -*-
"""
English.

La clave es el texto en español tal como esta en el programa. Los %s, %d...
tienen que seguir en la traduccion (los que llevan nombre, %(dia)s, pueden
cambiar de orden). herramientas/comprobar_idiomas.py dice lo que falta.

Vocabulario: franja = time slot, pauta = schedule, cuña = spot, relleno =
filler, desconexión / reconexión = break / endbreak (como los CUE), señal
horaria = time signal, cruce = transition, registro = log.
"""

# se escriben igual que en español
IGUAL = (
    "CUE", "JINGLE", "Jingle", "Jingles", "jingle", "Icecast", "Audio", "Audio (%s)",
    "s", "ms", "dB", "LUFS", "kbps", "%d min", "%d h %d min", "%d audio",
    "WASAPI", "DirectSound", "MME", "Ogg Vorbis", "Ogg Opus",
    "48 000 Hz", "44 100 Hz", "32 000 Hz", "22 050 Hz", "Español", "English",
)

TEXTOS = {
    # ---------------------------------------------------------------- fechas y numeros
    ",": ".",                                             # la coma decimal
    "L M X J V S D": "M T W T F S S",
    "%(dia)s %(n)d de %(mes)s": "%(dia)s, %(mes)s %(n)d",
    "lunes": "Monday", "martes": "Tuesday", "miércoles": "Wednesday", "jueves": "Thursday",
    "viernes": "Friday", "sábado": "Saturday", "domingo": "Sunday",
    "enero": "January", "febrero": "February", "marzo": "March", "abril": "April",
    "mayo": "May", "junio": "June", "julio": "July", "agosto": "August",
    "septiembre": "September", "octubre": "October", "noviembre": "November",
    "diciembre": "December",

    # ---------------------------------------------------------------- menus
    "&Archivo": "&File",
    "&Guardar cambios": "&Save changes",
    "&Descartar cambios": "&Discard changes",
    "&Importar configuración…": "&Import configuration…",
    "&Exportar configuración…": "&Export configuration…",
    "Abrir la &carpeta de datos": "Open the data &folder",
    "&Salir": "E&xit",
    "&Emisión": "&Broadcast",
    "&Emitir": "&Go on air",
    "&Detener la emisión": "S&top broadcasting",
    "&Saltar canción": "&Skip song",
    "&Rehacer la pauta": "&Rebuild the schedule",
    "&Ver": "&View",
    "Abrir el panel &web en el navegador": "Open the &web panel in the browser",
    "&Pantalla completa": "&Full screen",
    "&Idioma": "&Language",
    "A&yuda": "&Help",
    "&Acerca de %s": "&About %s",
    "Acerca de %s": "About %s",
    "Continuidad de radio por rotaciones horarias exactas.":
        "Radio playout by exact hourly rotations.",
    "Carpeta de datos: %s": "Data folder: %s",
    "no se encuentra": "not found",
    "Importar configuración": "Import configuration",
    "Exportar configuración": "Export configuration",
    "Configuración (*.json);;Todos (*.*)": "Configuration (*.json);;All files (*.*)",
    "Configuración importada. Revísala y pulsa «Guardar cambios» para aplicarla.":
        "Configuration imported. Review it and press “Save changes” to apply it.",
    "Configuración exportada a %s": "Configuration exported to %s",
    "no es una configuración de GIMEL": "this is not a GIMEL configuration",
    "No se ha podido importar: %s": "Could not import: %s",
    "No se ha podido exportar: %s": "Could not export: %s",

    # ---------------------------------------------------------------- ventana
    "Emisión": "On air",
    "Franjas": "Time slots",
    "Señales horarias": "Time signals",
    "Publicidad / desconexión": "Ads / break",
    "Eventos": "Events",
    "CUE y título": "CUE and title",
    "Ajustes": "Settings",
    "Registro": "Log",
    "Guardar cambios": "Save changes",
    "Descartar": "Discard",
    "Configuración guardada y aplicada.": "Configuration saved and applied.",
    "No se ha podido guardar: %s": "Could not save: %s",
    "Salida: ": "Output: ",
    "Sin tarjeta": "No sound card",
    "solo Icecast": "Icecast only",
    "Predeterminada": "Default",
    "Panel web: %s": "Web panel: %s",
    "Analizando la biblioteca: quedan %d": "Analysing the library: %d left",
    "Cortes de audio: %d": "Audio dropouts: %d",
    "Se está emitiendo.\n¿Salir y parar la emisión?": "You are on air.\nQuit and stop the broadcast?",
    "Hay cambios de configuración sin guardar.\n¿Guardarlos antes de salir?":
        "There are unsaved configuration changes.\nSave them before quitting?",

    # ---------------------------------------------------------------- emision
    "En emisión": "On air",
    "en emisión": "on air",
    "EN EMISIÓN": "ON AIR",
    "PARADO": "OFF AIR",
    "Parado": "Off air",
    "SIN CONEXIÓN": "NO CONNECTION",
    "▶  EMITIR": "▶  GO ON AIR",
    "■  DETENER": "■  STOP",
    "Emitir": "Go on air",
    "Detener": "Stop",
    "Saltar canción": "Skip song",
    "Rehacer la pauta": "Rebuild the schedule",
    "Volver a planificar lo que queda de hora desde ahora mismo":
        "Plan the rest of the hour again, starting right now",
    "La hora": "The hour",
    "Pauta de la hora": "This hour's schedule",
    "PAUTA DE LA HORA": "THIS HOUR'S SCHEDULE",
    "Rotación prevista (sin emitir)": "Planned rotation (off air)",
    "ROTACIÓN PREVISTA (SIN EMITIR)": "PLANNED ROTATION (OFF AIR)",
    "Abajo, la rotación que saldría si empezaras a emitir ahora":
        "Below, the rotation that would air if you went on air now",
    "La pauta de abajo es la que saldría si empezaras ahora":
        "The schedule below is what would air if you started now",
    "encima: ": "on top: ",
    "A continuación:   %s%s   ·   %s": "Up next:   %s%s   ·   %s",
    "señal horaria": "time signal",
    "la señal horaria": "the time signal",
    "bloque": "block",
    "el siguiente bloque": "the next block",
    "hora en punto": "top of the hour",
    "Falta para: ": "Time to: ",
    "Falta para la hora en punto": "Time to the top of the hour",
    "Programación: ": "Programming: ",
    "LIMITADOR ACTUANDO": "LIMITER ACTIVE",
    "limitador": "limiter",
    "Aún no hay pauta: elige la carpeta de canciones en Franjas.":
        "No schedule yet: choose the songs folder in Time slots.",
    "Aún no hay pauta: falta elegir la carpeta de canciones o se está analizando la biblioteca.":
        "No schedule yet: the songs folder has not been chosen, or the library is being analysed.",
    "Hora": "Time",
    "Tipo": "Type",
    "Título": "Title",
    "Artista": "Artist",
    "Duración": "Length",
    "Segundos": "Seconds",
    "Nota": "Note",

    # ---------------------------------------------------------------- tipos de audio
    "CANCIÓN": "SONG", "SEÑAL": "SIGNAL", "EVENTO": "EVENT", "CUÑA": "SPOT",
    "RELLENO": "FILLER", "SILENCIO": "SILENCE",
    "Canción": "Song", "Señal": "Signal", "Señal horaria": "Time signal", "Evento": "Event",
    "Cuña": "Spot", "Relleno": "Filler", "Jingle de bloque": "Block jingle",
    "Silencio": "Silence", "Sistema": "System",
    "Comienza la emisión": "Broadcast started",
    "Emisión detenida": "Broadcast stopped",

    # ---------------------------------------------------------------- avisos de la emision
    "Error interno: ": "Internal error: ",
    "No se puede reproducir %s": "Cannot play %s",
    "No se ha podido reproducir %s": "Could not play %s",
    "No se puede reproducir el jingle %s": "Cannot play the jingle %s",
    "El reloj ha dado un salto: se rehace la pauta": "The clock has jumped: rebuilding the schedule",
    "La salida de audio no responde: se intenta reabrir":
        "The audio output is not responding: trying to reopen it",
    "No se pudo reabrir la salida: %s": "Could not reopen the output: %s",
    "Analizando la biblioteca: la música empezará enseguida":
        "Analysing the library: the music will start shortly",
    "No hay canciones que emitir en «%s»: revisa su carpeta o lista":
        "There are no songs to play in “%s”: check its folder or playlist",
    "%s omitida: llegaba %.1f s tarde": "%s skipped: it was %.1f s late",
    "«%s» no cabe antes de la hora siguiente": "“%s” does not fit before the next hour",
    "«%s» recortado a %.0f s: no cabe entero": "“%s” shortened to %.0f s: it does not fit whole",
    "saltada": "skipped",
    "cortada": "cut",
    "cortada %.1f s antes": "cut %.1f s early",
    "se cortará %.1f s antes": "will be cut %.1f s early",
    "cruce adelantado %.1f s": "transition %.1f s early",
    "jingle encima del cruce": "jingle over the transition",
    "CUE de desconexión": "Break CUE",
    "CUE de reconexión": "Endbreak CUE",
    "No se encuentra ffmpeg. Instálalo (winget install Gyan.FFmpeg) o deja ffmpeg.exe en la carpeta del programa.":
        "ffmpeg not found. Install it (winget install Gyan.FFmpeg) or put ffmpeg.exe in the program folder.",
    "No hay por dónde emitir: la salida es «Sin tarjeta» y no hay ningún servidor Icecast activo.":
        "Nowhere to broadcast: the output is “No sound card” and there is no active Icecast server.",
    "No se puede abrir la salida de audio: %s": "Cannot open the audio output: %s",
    "Los cambios del panel web se aplican al reiniciar el programa.":
        "Changes to the web panel take effect when the program is restarted.",
    "falta el paquete sounddevice (pip install sounddevice)":
        "the sounddevice package is missing (pip install sounddevice)",
    "no hay ninguna salida de audio": "there is no audio output",
    "No está la salida «%s»: se emite por «%s».": "Output “%s” is not available: broadcasting through “%s”.",

    # ---------------------------------------------------------------- CUE
    "enviado": "sent",
    "escrito": "written",
    "tipo de destino desconocido: %s": "unknown destination type: %s",
    "los tonos DTMF solo salen en emisión": "DTMF tones are only sent while on air",
    "CUE de desconexión y de reconexión": "Break and endbreak CUE",
    "El de desconexión sale durante el silencio previo a cada bloque y el de reconexión durante el negro final (los segundos se ponen en cada bloque). Se mandan a todos los servidores activos de abajo.":
        "The break CUE is sent during the silence before each block and the endbreak CUE during the "
        "closing silence (the seconds are set in each block). They go to every active server below.",
    "Para probar la recepción hay un servidor de ejemplo en herramientas/servidor_cue.py.":
        "To test reception there is a sample server in herramientas/servidor_cue.py.",
    "Probar: desconexión": "Test: break",
    "Probar: reconexión": "Test: endbreak",
    "Servidores": "Servers",
    "No hay ningún servidor al que mandar los CUE. Pulsa «Añadir».":
        "There is no server to send the CUE to. Press “Add”.",
    "Título en emisión": "Now playing title",
    "Últimos CUE enviados": "Last CUE sent",
    "Ninguno todavía.": "None yet.",
    "Enviando…": "Sending…",

    # ---------------------------------------------------------------- Icecast
    "emitiendo": "streaming",
    "conectando…": "connecting…",
    "sin conexión": "no connection",
    "parado": "stopped",
    "%d bloques perdidos por atasco de red": "%d blocks lost to network congestion",
    "Los envíos se conectan al empezar a emitir.": "The streams connect when you go on air.",
    "Servidores Icecast": "Icecast servers",
    "La emisión se manda a todos los servidores activos, además de salir por la tarjeta. Para emitir solo por Icecast, elige «Sin tarjeta» en Ajustes > Salida de audio.":
        "The broadcast is sent to every active server, as well as to the sound card. To broadcast "
        "through Icecast only, choose “No sound card” in Settings > Audio output.",
    "No hay ningún servidor Icecast. Pulsa «Añadir».": "There is no Icecast server. Press “Add”.",
    "el servidor rechaza el usuario o la contraseña": "the server rejects the user or the password",
    "el servidor no admite ese punto de montaje (¿ya hay otra fuente en él?)":
        "the server does not accept that mount point (is another source already on it?)",
    "el servidor no contesta en ese puerto (conexión rechazada)":
        "the server does not answer on that port (connection refused)",
    "el servidor no responde (tiempo agotado)": "the server does not respond (timed out)",
    "no se encuentra el servidor (nombre desconocido)": "server not found (unknown name)",
    "este ffmpeg no trae el codificador de ese formato":
        "this ffmpeg does not include the encoder for that format",
    "se ha cortado la conexión": "the connection was lost",
    "no se pudo lanzar ffmpeg: %s": "could not start ffmpeg: %s",

    # ---------------------------------------------------------------- listas
    "Añadir": "Add",
    "Duplicar": "Duplicate",
    "Eliminar": "Delete",
    "¿Eliminar «%s»?": "Delete “%s”?",
    "(copia)": "(copy)",
    "(sin nombre)": "(no name)",
    "el resto": "the rest",
    "No hay nada todavía. Pulsa «Añadir».": "Nothing here yet. Press “Add”.",
    "Programación": "Programming",
    "Programación general": "General programming",
    "Franja nueva": "New time slot",
    "Publicidad": "Ads",
    "Servidor": "Server",
    "Cada hora se hace con la primera franja de la lista que la cubra; si no la cubre ninguna, con la programación general. El orden importa: usa ▲ y ▼.":
        "Each hour is built with the first time slot in the list that covers it; if none does, with "
        "the general programming. The order matters: use ▲ and ▼.",
    "Bloques": "Blocks",
    "Un bloque se programa en todas las horas de su rango. La música de antes y de después se reajusta sola para que la hora siga cuadrando.":
        "A block is scheduled in every hour of its range. The music before and after it adjusts "
        "itself so the hour still adds up.",
    "No hay bloques de publicidad ni de desconexión. Pulsa «Añadir».":
        "There are no ad or break blocks. Press “Add”.",
    "Eventos a minuto fijo": "Fixed-minute events",
    "Un audio que arranca en un minuto exacto de la hora: un boletín, la señal de las medias, una promo. La música calla antes, igual que con la señal horaria.":
        "An audio that starts at an exact minute of the hour: a bulletin, the half-hour signal, a "
        "promo. The music fades out first, as it does for the time signal.",
    "No hay eventos. Pulsa «Añadir».": "There are no events. Press “Add”.",
    "música": "music",
    "baja %g s": "fades %g s",
    "silencio %g s": "silence %g s",
    "CUE a los %g s": "CUE at %g s",
    "entrada": "intro",
    "relleno": "filler",
    "cuñas": "spots",
    "%g s exactos": "%g s exactly",
    "a negro %g s": "silence %g s",
    "vuelta": "return",

    # ---------------------------------------------------------------- senales horarias
    "El audio de cada hora": "The audio for each hour",
    "Rellenar desde una carpeta…": "Fill from a folder…",
    "Vaciar": "Clear",
    "Al rellenar, cada audio va a la hora del número que lleve en el nombre (07.mp3, hora_14.wav…).":
        "When filling, each audio goes to the hour of the number in its name (07.mp3, hora_14.wav…).",
    "Carpeta con las señales horarias": "Folder with the time signals",
    "En esa carpeta no hay audios con un número de hora en el nombre.":
        "That folder has no audios with an hour number in their name.",
    "%d horas asignadas por el número del nombre de cada fichero.":
        "%d hours assigned by the number in each file name.",
    "¿Quitar el audio de las 24 horas?": "Remove the audio from all 24 hours?",

    # ---------------------------------------------------------------- ajustes y registro
    "Emisora": "Station",
    "Salida de audio": "Audio output",
    "Mezcla": "Mix",
    "Panel web": "Web panel",
    "Ahora mismo: %s": "Right now: %s",
    "Ahora mismo el panel web no está en marcha.": "The web panel is not running right now.",
    "Registro de emisión": "Broadcast log",
    "Actualizar": "Refresh",
    "Abrir la carpeta": "Open the folder",
    "%d líneas": "%d lines",
    "los ficheros están en datos/registro": "the files are in datos/registro",
    "Todavía no se ha emitido nada.": "Nothing has been broadcast yet.",

    # ---------------------------------------------------------------- campos
    "Examinar…": "Browse…",
    "Quitar": "Remove",
    "Listas (%s)": "Playlists (%s)",
    "Elegir carpeta": "Choose a folder",
    "Elegir fichero": "Choose a file",
    "Fichero de texto": "Text file",
    "Texto (*.txt);;Todos (*.*)": "Text (*.txt);;All files (*.*)",
    "Carpeta…": "Folder…",
    "Lista (.m3u, .pls)…": "Playlist (.m3u, .pls)…",
    "Un fichero de audio…": "An audio file…",
    "No existe": "Does not exist",
    "No se puede leer": "Cannot be read",
    "Leyendo…": "Reading…",
    "%d audios": "%d audios",
    "analizando (%d de %d)": "analysing (%d of %d)",
    "%d ilegibles": "%d unreadable",
    "Predeterminada del sistema": "System default",
    "(predeterminada)": "(default)",
    "(no está)": "(not available)",
    "Volver a mirar qué tarjetas hay (sin emitir)": "Look again for sound cards (while off air)",

    # ---------------------------------------------------------------- panel web
    "Host no admitido.": "Host not allowed.",
    "Falta la cabecera X-Gimel.": "The X-Gimel header is missing.",
    "El panel de GIMEL no tiene contraseña y por eso solo atiende al propio equipo. Ponle una en Ajustes > Panel web para entrar desde la red.":
        "The GIMEL panel has no password, so it only answers to this computer. Set one in "
        "Settings > Web panel to get in from the network.",
    "No se pudo abrir el panel web en %s:%s: %s": "Could not open the web panel on %s:%s: %s",
    "configuración ilegible": "unreadable configuration",
    "acción desconocida": "unknown action",
    "Contraseña": "Password",
    "Contraseña incorrecta": "Wrong password",
    "Entrar": "Log in",
    "Este equipo": "This computer",
    "subir": "up",
    "Elegir esta carpeta": "Choose this folder",
    "Elegir un audio": "Choose an audio",
    "Elegir una carpeta, una lista o un audio": "Choose a folder, a playlist or an audio",
    "Cancelar": "Cancel",
    "No se ha podido leer la configuración: %s": "Could not read the configuration: %s",

    # ---------------------------------------------------------------- esquema: franjas
    "Cuándo": "When",
    "Franja activa": "Time slot enabled",
    "Nombre": "Name",
    "Días": "Days",
    "Desde las": "From",
    "Hasta las": "To",
    "Si la hora de fin no pasa de la de inicio, cruza la medianoche.":
        "If the end hour is not later than the start hour, it crosses midnight.",
    "Canciones": "Songs",
    "Carpeta o lista": "Folder or playlist",
    "Carpeta (con sus subcarpetas) o lista .m3u / .pls de la que sale la música.":
        "Folder (with its subfolders) or .m3u / .pls playlist the music comes from.",
    "Orden": "Order",
    "Aleatorio: no se repite nada hasta que haya sonado todo":
        "Shuffle: nothing repeats until everything has played",
    "Secuencial: en el orden de la lista": "Sequential: in playlist order",
    "Descartar las de menos de": "Skip those shorter than",
    "Descartar las de más de": "Skip those longer than",
    "0 = sin límite.": "0 = no limit.",
    "Poner jingles entre canciones": "Play jingles between songs",
    "Carpeta de jingles": "Jingles folder",
    "Un jingle cada": "One jingle every",
    "cambios de canción": "song changes",
    "Colocación": "Placement",
    "Encima: el jingle suena sobre el cruce, pisando el final de una canción y el principio de la otra. Entre: canción, jingle, canción.":
        "Over: the jingle plays over the transition, on top of the end of one song and the start "
        "of the next. Between: song, jingle, song.",
    "Encima del cruce entre canciones": "Over the transition between songs",
    "Entre canción y canción": "Between one song and the next",
    "En las horas de esta programación": "During the hours of this programming",
    "Dar la señal horaria": "Play the time signal",
    "Indicativo (un jingle) justo después de la señal": "Station ID (a jingle) right after the signal",
    "Admitir bloques de publicidad / desconexión": "Allow ad / break blocks",
    "Admitir eventos a minuto fijo": "Allow fixed-minute events",

    # ---------------------------------------------------------------- esquema: senales
    "Dar señales horarias": "Play time signals",
    "La hora en punto cae": "The top of the hour falls",
    "Para unos pitos, lo normal es que el último empiece justo en punto: elige «en un segundo concreto» y di en cuál.":
        "With pips, the last one normally starts exactly on the hour: choose “at a given second” "
        "and say which.",
    "cuando EMPIEZA el audio": "when the audio STARTS",
    "cuando ACABA el audio": "when the audio ENDS",
    "en un segundo concreto del audio": "at a given second of the audio",
    "Segundo del audio que cae en punto": "Second of the audio that falls on the hour",
    "Bajada de la música antes": "Music fade-out before it",
    "Si hay que cortar lo que suena para dar la señal (o un bloque, o un evento), se le baja el volumen durante este tiempo.":
        "If what is playing has to be cut for the signal (or a block, or an event), its volume is "
        "faded down over this time.",
    "Señal para las horas sin audio propio": "Signal for hours without their own audio",

    # ---------------------------------------------------------------- esquema: bloques y eventos
    "Bloque activo": "Block enabled",
    "Solo en las horas desde las": "Only in the hours from",
    "hasta las": "to",
    "Minuto de cada hora": "Minute of each hour",
    "Segundo": "Second",
    "A esa hora": "At that time",
    "empieza el jingle de entrada": "the intro jingle starts",
    "empieza el silencio previo (calla la música)": "the opening silence starts (the music stops)",
    "empiezan las cuñas / el relleno": "the spots / the filler start",
    "Contenido": "Content",
    "Qué suena": "What plays",
    "Música de relleno: para cuando el CUE hace que los demás desconecten y por aquí solo hay que cubrir el hueco.":
        "Filler music: for when the CUE makes the others break away and all that is needed here "
        "is to fill the gap.",
    "Cuñas (sublista de publicidad)": "Spots (ad sublist)",
    "Música de relleno": "Filler music",
    "Duración exacta": "Exact length",
    "Lo que dura el contenido, clavado. La música se reajusta alrededor.":
        "How long the content lasts, to the second. The music adjusts around it.",
    "Carpeta o lista de cuñas": "Spots folder or playlist",
    "Orden de las cuñas": "Spot order",
    "Si las cuñas no llenan el tiempo": "If the spots do not fill the time",
    "Huecos de menos de 3 s se reparten en respiros entre cuña y cuña.":
        "Gaps shorter than 3 s are spread as pauses between spots.",
    "Otra cuña más, cortada al llegar al tiempo": "One more spot, cut when the time is up",
    "Música de relleno hasta completar": "Filler music until the time is up",
    "Silencio hasta completar": "Silence until the time is up",
    "Fichero, carpeta o lista. Se funde al acabar el tiempo.":
        "File, folder or playlist. It fades out when the time is up.",
    "Entrada y salida": "Intro and return",
    "Silencio antes de entrar": "Silence before the block",
    "Jingle de entrada (ADS / desconexión)": "Intro jingle (ADS / break)",
    "Jingle de entrada": "Intro jingle",
    "Fichero o carpeta. Vacío: uno de los jingles de la franja.":
        "File or folder. Empty: one of the time slot's jingles.",
    "A negro al terminar": "Silence at the end",
    "Jingle de vuelta, después del negro": "Return jingle, after the silence",
    "Jingle de vuelta": "Return jingle",
    "Emitir CUE de desconexión y de reconexión": "Send break and endbreak CUE",
    "Los servidores a los que se mandan se configuran en la página CUE.":
        "The servers they are sent to are set up on the CUE page.",
    "s después de empezar el silencio previo": "s after the opening silence starts",
    "s después de empezar el negro final": "s after the closing silence starts",
    "Evento activo": "Event enabled",
    "Un fichero, o una carpeta o lista si quieres que vayan rotando.":
        "A file, or a folder or playlist if you want them to rotate.",
    "Si hay varios": "If there are several",

    # ---------------------------------------------------------------- esquema: mezcla
    "Cuadrar la hora": "Fitting the hour",
    "Recorte máximo por canción": "Maximum trim per song",
    "Para que las canciones entren en la hora se adelanta el cruce de cada una, repartiendo el recorte entre todas. Este es el tope por canción.":
        "To make the songs fit in the hour, each transition is brought forward, sharing the trim "
        "among all of them. This is the limit per song.",
    "Fundido de una canción recortada": "Fade-out of a trimmed song",
    "Lo que tarda en desaparecer la canción que sale cuando se la cruza antes de su final.":
        "How long the outgoing song takes to fade when it is crossed before its end.",
    "Una canción suena al menos": "A song plays for at least",
    "Si al final de un tramo una canción fuera a sonar menos que esto, no entra.":
        "If a song at the end of a segment would play for less than this, it is left out.",
    "Cruces": "Transitions",
    "Nivel al que entra la siguiente": "Level at which the next one comes in",
    "La siguiente canción arranca cuando la que suena cae estos dB por debajo de su nivel. Más negativo = cruces más tardíos.":
        "The next song starts when the one playing drops this many dB below its level. More "
        "negative = later transitions.",
    "Solape máximo al final de una canción": "Maximum overlap at the end of a song",
    "Cruce al saltar una canción a mano": "Transition when a song is skipped by hand",
    "Separación entre dos del mismo artista": "Separation between two by the same artist",
    "canciones": "songs",
    "Jingles encima del cruce": "Jingles over the transition",
    "Jingle sonando sobre la canción que entra, como mucho": "Jingle playing over the incoming song, at most",
    "Con un jingle más largo que esto, la canción espera para entrar.":
        "With a jingle longer than this, the song waits before coming in.",
    "Bajar la canción que entra mientras suena el jingle": "Duck the incoming song while the jingle plays",
    "Volumen": "Volume",
    "Igualar el volumen de todos los audios": "Level the volume of all audios",
    "Nivel objetivo": "Target level",
    "Retoque de las canciones": "Song trim",
    "Retoque de los jingles": "Jingle trim",
    "Retoque de las cuñas": "Spot trim",
    "Retoque de señales y eventos": "Signal and event trim",

    # ---------------------------------------------------------------- esquema: salida
    "Sistema de audio": "Audio system",
    "«Sin tarjeta»: la emisión no sale por ningún altavoz, solo hacia los servidores Icecast (página Icecast). Sirve para un equipo sin sonido o para no ocupar la tarjeta.":
        "“No sound card”: the broadcast does not go to any speaker, only to the Icecast servers "
        "(Icecast page). Useful on a computer without sound, or to leave the sound card free.",
    "Sin tarjeta: solo Icecast": "No sound card: Icecast only",
    "Por qué tarjeta (o cable virtual) sale la emisión.":
        "Which sound card (or virtual cable) the broadcast goes out through.",
    "Búfer": "Buffer",
    "Si se oyen cortes, súbelo. No afecta a la exactitud de las horas.":
        "If you hear dropouts, raise it. It does not affect how exact the hours are.",
    "Volumen de salida": "Output volume",
    "Limitador de seguridad": "Safety limiter",
    "Evita la saturación cuando coinciden dos audios fuertes.":
        "Prevents clipping when two loud audios coincide.",
    "Retardo de la cadena a compensar": "Chain delay to compensate",
    "Si detrás de la tarjeta hay algo que retrasa el audio (un procesador, el codificador), ponlo aquí y todo se adelanta para que la hora siga cayendo en punto.":
        "If something after the sound card delays the audio (a processor, the encoder), enter it "
        "here and everything is brought forward so the hour still falls on time.",

    # ---------------------------------------------------------------- esquema: icecast
    "Enviar a este servidor": "Send to this server",
    "Solo para reconocerlo en esta lista.": "Only to recognise it in this list.",
    "Nombre o dirección IP, sin http://.": "Name or IP address, without http://.",
    "Puerto": "Port",
    "Punto de montaje": "Mount point",
    "Por ejemplo /radio o /directo.mp3.": "For example /radio or /live.mp3.",
    "Usuario": "User",
    "Casi siempre «source».": "Almost always “source”.",
    "Conexión cifrada (TLS)": "Encrypted connection (TLS)",
    "Sonido": "Sound",
    "Formato": "Format",
    "MP3 (lo oye cualquier reproductor)": "MP3 (any player can play it)",
    "AAC (mejor calidad a pocos kbps)": "AAC (better quality at low bitrates)",
    "Calidad": "Quality",
    "Frecuencia de muestreo": "Sample rate",
    "Estéreo": "Stereo",
    "Lo que ve el oyente": "What the listener sees",
    "Mandar el título de cada canción": "Send the title of each song",
    "Con MP3 y AAC. El texto es el de la página «CUE y título» (Artista - Título).":
        "With MP3 and AAC. The text is the one from the “CUE and title” page (Artist - Title).",
    "Nombre del stream": "Stream name",
    "Vacío: el nombre de la emisora.": "Empty: the station name.",
    "Descripción": "Description",
    "Género": "Genre",
    "Página web": "Website",
    "Anunciarlo en los directorios públicos": "List it in public directories",

    # ---------------------------------------------------------------- esquema: CUE y titulo
    "Emitir los CUE": "Send the CUE",
    "Adelantar los CUE": "Send the CUE early by",
    "Positivo: salen un poco antes de su momento. Negativo: después.":
        "Positive: they go out a little before their time. Negative: after.",
    "Reintentos si un servidor no contesta": "Retries if a server does not answer",
    "Activo": "Enabled",
    "HTTP (POST del mensaje a una URL)": "HTTP (POST of the message to a URL)",
    "TCP (una línea a host:puerto)": "TCP (one line to host:port)",
    "UDP (un datagrama a host:puerto)": "UDP (one datagram to host:port)",
    "Tonos DTMF dentro del audio": "DTMF tones inside the audio",
    "HTTP: la URL. TCP y UDP: host:puerto. Fichero: su ruta. DTMF: nada.":
        "HTTP: the URL. TCP and UDP: host:port. File: its path. DTMF: nothing.",
    "Variables: {evento} (break o endbreak), {duracion} (segundos hasta la reconexión), {contenido} (lo que duran las cuñas), {bloque}, {emisora}, {hora}, {fecha}, {epoch}, {silencio}.":
        "Variables: {evento} (break or endbreak), {duracion} (seconds until the endbreak), "
        "{contenido} (how long the spots last), {bloque}, {emisora}, {hora}, {fecha}, {epoch}, "
        "{silencio}.",
    "Publicar lo que suena": "Publish what is playing",
    "Para el RDS, el streaming o una web: el título en emisión, en un fichero o hacia una URL.":
        "For RDS, streaming or a website: the now playing title, to a file or to a URL.",
    "URL a la que avisar": "URL to notify",
    "Se llama con GET; {texto} se sustituye por el título, ya codificado.":
        "Called with GET; {texto} is replaced by the title, already encoded.",
    "Texto": "Text",
    "Variables: {artista} {titulo} {emisora}.": "Variables: {artista} {titulo} {emisora}.",
    "Solo las canciones cambian el texto": "Only songs change the text",
    "Texto para lo demás (cuñas, señales…)": "Text for everything else (spots, signals…)",

    # ---------------------------------------------------------------- esquema: web y sistema
    "Panel de control por navegador": "Browser control panel",
    "Quién puede entrar": "Who can get in",
    "Solo este equipo": "This computer only",
    "Cualquier equipo de la red": "Any computer on the network",
    "Sin contraseña, el panel solo atiende a este mismo equipo aunque esté abierto a la red.":
        "Without a password, the panel only answers to this computer even if it is open to the "
        "network.",
    "Nombre de la emisora": "Station name",
    "Empezar a emitir al abrir el programa": "Go on air when the program opens",
    "Apagado: al abrir se genera la rotación y se espera a que pulses Emitir.":
        "Off: on opening, the rotation is generated and the program waits for you to press Go on air.",
    "Idioma": "Language",
    "De la ventana, del panel web y de los avisos de la emisión.":
        "Of the window, the web panel and the broadcast notices.",
}
