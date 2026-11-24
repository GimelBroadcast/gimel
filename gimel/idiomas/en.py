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
    # 1.2
    "Manual", "Intro", "INTRO", "INTRO %s", "dBFS", "min", "MP3", "Intro…",
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
    "&Buscar actualizaciones…": "Check for &updates…",
    "&Página de GIMEL en GitHub": "GIMEL &page on GitHub",
    "Todavía no hay ninguna versión publicada.\nTienes la %s.": "No version has been published yet.\nYou have %s.",
    "Tienes la última versión (%s).": "You have the latest version (%s).",
    "Hay una versión nueva: %s (tienes la %s).": "There is a new version: %s (you have %s).",
    "¿Abrir su página de descarga?": "Open its download page?",
    "Antes de actualizar, guarda o descarta los cambios de configuración que tienes a medias.":
        "Before updating, save or discard your pending configuration changes.",
    "¿Descargarla e instalarla ahora? GIMEL se cerrará, Windows pedirá permiso de administrador y, al acabar, GIMEL se abrirá otra vez.":
        "Download and install it now? GIMEL will close, Windows will ask for administrator "
        "permission and, when it is done, GIMEL will open again.",
    "Se está emitiendo: la emisión se cortará mientras se actualiza (cosa de un minuto) y después seguirá sola.":
        "You are on air: the broadcast will stop while updating (about a minute) and then resume "
        "by itself.",
    "Descargando GIMEL %s…": "Downloading GIMEL %s…",
    "Cancelar": "Cancel",
    "GitHub no admite más consultas por ahora. Prueba dentro de un rato.":
        "GitHub is not accepting more requests for now. Try again in a while.",
    "No se ha podido consultar GitHub: %s": "Could not reach GitHub: %s",
    "Esa versión no trae instalador.": "That version has no installer.",
    "La descarga no ha llegado entera. Vuelve a intentarlo.": "The download is incomplete. Try again.",
    "No se ha podido descargar: %s": "Could not download: %s",
    "Sin permiso de administrador no se puede actualizar. No se ha cambiado nada.":
        "Updating requires administrator permission. Nothing has been changed.",
    "No se ha podido lanzar el instalador (código %d).": "Could not start the installer (code %d).",
    "Novedades de %s": "What's new in %s",
    "%s se ha actualizado a la versión %s": "%s has been updated to version %s",
    "Versión %s": "Version %s",
    "Cerrar": "Close",
    "Los jingles se reparten bien: suenan todos los de la carpeta o la lista antes de que se repita ninguno. Antes unos pocos salían mucho más que el resto.":
        "Jingles are now spread evenly: every jingle in the folder or playlist plays before any of "
        "them repeats. Before, a few of them came up far more often than the rest.",
    "Cada franja elige el orden de sus jingles: aleatorio o secuencial.":
        "Each time slot chooses the order of its jingles: shuffle or sequential.",
    "Las canciones y los jingles que se añaden a una carpeta o a una lista, o se quitan de ella, entran en la rotación o salen de ella en un par de minutos, sin reiniciar el programa.":
        "Songs and jingles added to a folder or playlist, or removed from it, enter or leave the "
        "rotation within a couple of minutes, without restarting the program.",
    "«Buscar actualizaciones» ya no da error de certificado en los equipos en los que fallaba.":
        "“Check for updates” no longer fails with a certificate error on the computers where it did.",
    "Después de actualizar, GIMEL enseña las novedades de la versión la primera vez que se abre.":
        "After an update, GIMEL shows what is new in the version the first time it opens.",
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
    "Carpeta o lista de jingles": "Jingles folder or playlist",
    "Orden de los jingles": "Jingle order",
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

    # ---------------------------------------------------------------- 1.2: directo (auxiliares, botonera,
    # preescucha, intro, locutor), silencio, enlace con la cadena, grabaciones, pautas, certificado, reserva
    "Asistido":
        "Live assist",
    "Automático":
        "Automatic",
    "Encima de la principal":
        "Over the main playout",
    "Bajar la principal":
        "Duck the main playout",
    "Silenciar la principal":
        "Mute the main playout",
    "Principal: encima":
        "Main: over",
    "Principal: bajar":
        "Main: duck",
    "Principal: silenciar":
        "Main: mute",
    "Las listas auxiliares y la botonera suenan por la salida de la emisión: empieza a emitir primero.":
        "The aux lists and the cart wall play through the broadcast output: go on air first.",
    "Emergencia":
        "Emergency",
    "La lista está vacía.":
        "The list is empty.",
    "Ahí no hay audios que añadir.":
        "There is no audio there to add.",
    "Ese botón no tiene audio.":
        "That button has no audio.",
    "Eso no es un audio.":
        "That is not an audio file.",
    "No se encuentra ffmpeg.":
        "ffmpeg cannot be found.",
    "Auxiliar %d":
        "Aux %d",
    "La emisión lleva %d s en silencio: entra la lista de emergencia":
        "The broadcast has been silent for %d s: the emergency list goes on air",
    "orden ilegible":
        "unreadable command",
    "Silencio en la emisión: entra la lista de emergencia":
        "Silence on air: the emergency list goes on air",
    "%d audios añadidos.":
        "%d audio files added.",
    "Vuelve la emisión: se retira la lista de emergencia":
        "The broadcast is back: the emergency list is taken off",
    "No se puede abrir la salida de «%s»: %s":
        "Cannot open the output of “%s”: %s",
    "No se puede abrir la tarjeta de preescucha: %s":
        "Cannot open the preview sound card: %s",
    "Botonera":
        "Cart wall",
    "Botón %d":
        "Button %d",
    "%d botones sonando":
        "%d buttons playing",
    "Certificado de emisión":
        "Proof of play",
    "Periodo":
        "Period",
    "Pases emitidos":
        "Spots aired",
    "Resumen por cuña":
        "Summary by spot",
    "Pases":
        "Airings",
    "Detalle de pases":
        "Airing detail",
    "Generado el":
        "Generated on",
    "Ninguna":
        "None",
    "Filtro":
        "Filter",
    "Grabación":
        "Recording",
    "Carpeta (con sus subcarpetas) o lista .m3u / .pls de la que sale la música. Con «Pauta importada», la carpeta donde se importan las pautas (Archivo > Importar pauta).":
        "Folder (with its subfolders) or .m3u / .pls playlist the music comes from. With “Imported log”, the folder logs are imported into (File > Import a log).",
    "Pauta importada: cada hora suena la lista de esa hora que haya mandado el planificador de música (MusicMaster, Selector, Powergold…), en su orden; GIMEL la cuadra. Una hora sin pauta tira de la programación general.":
        "Imported log: each hour plays the list for that hour sent by the music scheduler (MusicMaster, Selector, Powergold…), in its order; GIMEL fits it to the hour. An hour without a log falls back to the general programming.",
    "Con «Pauta importada», la carpeta donde se importa la pauta de publicidad.":
        "With “Imported log”, the folder the traffic log is imported into.",
    "Pauta importada: en cada corte, las cuñas que mande el programa de publicidad para esa hora y ese minuto, en su orden.":
        "Imported log: in each break, the spots the traffic system sends for that hour and minute, in their order.",
    "Enlace con la cadena (network join): a esa hora exacta la emisión se engancha al directo de la cadena, por un stream o por una entrada de la tarjeta, y lo da durante el tiempo que digas. Si el directo se corta, sale silencio y se reconecta; la hora sigue cuadrando.":
        "Network join: at that exact time the broadcast joins the network feed, from a stream or a sound card input, and carries it for the time you set. If the feed drops, silence goes out and it reconnects; the hour stays exact.",
    "Un audio":
        "An audio file",
    "Enlace con la cadena (directo)":
        "Network join (live feed)",
    "Stream de la cadena":
        "Network stream",
    "URL del directo (http://…/cadena.mp3). Vacío: la entrada de tarjeta de abajo.":
        "URL of the live feed (http://…/network.mp3). Empty: the sound card input below.",
    "O entrada de tarjeta":
        "Or sound card input",
    "La línea por la que llega la cadena (un receptor de satélite, un códec).":
        "The line the network arrives on (a satellite receiver, a codec).",
    "Vigilar el silencio":
        "Watch for silence",
    "Si la emisión principal se queda muda (una carpeta que desaparece, un directo caído), entra sola una lista de emergencia, en bucle, encima de la principal. Cuando la principal vuelve a sonar, la de emergencia se retira con un fundido.":
        "If the main broadcast goes silent (a folder that disappears, a dropped feed), an emergency list goes on air by itself, looping, over the main playout. When the main playout sounds again, the emergency list fades out.",
    "Silencio que hace saltar la emergencia":
        "Silence that triggers the emergency list",
    "Más que el negro de un bloque de publicidad, para que no salte en cada desconexión.":
        "Longer than the dead air of an ad block, so it does not trigger on every break.",
    "Por debajo de este nivel es silencio":
        "Below this level counts as silence",
    "Lista de emergencia":
        "Emergency list",
    "Carpeta o lista con la música de reserva.":
        "Folder or playlist with the backup music.",
    "Retirarla con la principal sonando":
        "Take it off when the main playout has sounded for",
    "Grabación activa":
        "Recording enabled",
    "Va en el nombre del fichero, con la fecha y la hora.":
        "It goes in the file name, with the date and time.",
    "Empieza a las":
        "Starts at",
    "Minuto":
        "Minute",
    "Qué se graba":
        "What is recorded",
    "Fuente":
        "Source",
    "Un stream (un corresponsal, otra emisora)":
        "A stream (a correspondent, another station)",
    "Una entrada de la tarjeta (una línea, un híbrido)":
        "A sound card input (a line, a phone hybrid)",
    "Lo que sale al aire":
        "What goes on air",
    "URL del stream":
        "Stream URL",
    "Entrada de tarjeta":
        "Sound card input",
    "Dónde":
        "Where",
    "Carpeta":
        "Folder",
    "WAV (sin pérdida)":
        "WAV (lossless)",
    "Al acabar, añadirla a":
        "When finished, add it to",
    "Ingesta: la grabación entra sola en una lista auxiliar, lista para lanzarla.":
        "Ingest: the recording goes into an aux list by itself, ready to fire.",
    "Ninguna lista":
        "No list",
    "Lista auxiliar 1":
        "Aux list 1",
    "Lista auxiliar 2":
        "Aux list 2",
    "Lista auxiliar 3":
        "Aux list 3",
    "Lista auxiliar 4":
        "Aux list 4",
    "Grabar todo lo que sale al aire":
        "Record everything that goes on air",
    "La prueba de lo emitido: un MP3 por hora en una carpeta por día. Graba mientras se emite.":
        "Proof of what was broadcast: one MP3 per hour in one folder per day. It records while on air.",
    "Guardar":
        "Keep",
    "Lo más viejo se borra solo. 0 = no borrar nunca.":
        "Older files are deleted automatically. 0 = never delete.",
    "días":
        "days",
    "Este equipo es la reserva de otro GIMEL":
        "This computer is the backup of another GIMEL",
    "Playout espejo: este equipo vigila al principal y, si deja de emitir, empieza a emitir él. La salida de los dos tiene que poder juntarse fuera (un conmutador con detector de silencio, o un punto de montaje de reserva en Icecast).":
        "Mirror playout: this computer watches the main one and, if it stops broadcasting, goes on air itself. The outputs of both must be combined outside (a switcher with silence detection, or a fallback mount point in Icecast).",
    "Panel web del principal":
        "Web panel of the main playout",
    "Por ejemplo http://192.168.1.10:8950. El principal tiene que tener el panel abierto a la red y con contraseña.":
        "For example http://192.168.1.10:8950. The main playout must have its panel open to the network and with a password.",
    "Contraseña del panel del principal":
        "Password of the main playout's panel",
    "Tomar el relevo tras":
        "Take over after",
    "Segundos sin saber del principal, o sin que emita.":
        "Seconds without hearing from the main playout, or without it broadcasting.",
    "Apartarse cuando el principal vuelva a emitir":
        "Step aside when the main playout broadcasts again",
    "Copiar la programación del principal":
        "Copy the main playout's programming",
    "Mientras no emite, cada minuto. No se copian la tarjeta, el panel web, Icecast ni esto. Las carpetas de música tienen que verse igual desde los dos equipos.":
        "While not on air, every minute. The sound card, the web panel, Icecast and these settings are not copied. Music folders must look the same from both computers.",
    "no hay ninguna entrada de audio":
        "there is no audio input",
    "Empieza una grabación":
        "A recording starts",
    "no ha llegado audio":
        "no audio arrived",
    "Grabación cortada":
        "Recording cut short",
    "Grabación terminada":
        "Recording finished",
    "ffmpeg ha dejado de grabar":
        "ffmpeg stopped recording",
    "Intro quitada.":
        "Intro removed.",
    "Intro de %s: %.1f s":
        "Intro of %s: %.1f s",
    "Logger de antena":
        "Air logger",
    "Ahora no suena ninguna canción.":
        "No song is playing right now.",
    "No se está preescuchando nada.":
        "Nothing is being previewed.",
    "%d audios en %d listas (%s).":
        "%d audio files in %d lists (%s).",
    "En ese fichero no hay ninguna línea con hora y audio.":
        "That file has no line with a time and an audio file.",
    "una por hora":
        "one per hour",
    "una por corte":
        "one per break",
    "%d no están en el disco.":
        "%d are not on disk.",
    "%d líneas sin audio reconocible.":
        "%d lines without a recognizable audio file.",
    "Pauta importada de %s":
        "Log imported from %s",
    "«%s»: no hay pauta importada para este corte":
        "“%s”: there is no imported log for this break",
    "Auxiliar":
        "Aux",
    "Enlace con la cadena":
        "Network join",
    "preguntando al principal…":
        "asking the main playout…",
    "EN RELEVO: el principal no emite y esta reserva está en antena":
        "TAKEN OVER: the main playout is not broadcasting and this backup is on air",
    "El principal vuelve a emitir: la reserva se aparta":
        "The main playout is broadcasting again: the backup steps aside",
    "el principal emite; esta reserva espera":
        "the main playout is on air; this backup is waiting",
    "El principal no emite: la reserva toma el relevo":
        "The main playout is not broadcasting: the backup takes over",
    "el principal contesta pero no emite":
        "the main playout answers but is not broadcasting",
    "el principal no contesta":
        "the main playout does not answer",
    "Todos":
        "All",
    "Reproducir (o seguir tras la pausa)":
        "Play (or resume after pause)",
    "Pausa":
        "Pause",
    "Parar":
        "Stop",
    "Saltar al siguiente":
        "Skip to next",
    "Manual: cada audio se lanza a mano. Asistido: encadena hasta un punto de parada. Automático: lo encadena todo.":
        "Manual: each file is fired by hand. Live assist: segues up to a stop point. Automatic: segues everything.",
    "Qué le pasa a la emisión principal mientras suena esta lista. La principal nunca se para: sigue su hora por debajo.":
        "What happens to the main playout while this list plays. The main playout never stops: its hour keeps running underneath.",
    "Una carpeta…":
        "A folder…",
    "Una lista .m3u / .pls…":
        "An .m3u / .pls playlist…",
    "Carpeta de audios":
        "Audio folder",
    "Lista":
        "Playlist",
    "Listas (*.m3u *.m3u8 *.pls)":
        "Playlists (*.m3u *.m3u8 *.pls)",
    "Cambiar el nombre…":
        "Rename…",
    "Bucle: al acabar, volver al principio":
        "Loop: start over at the end",
    "Anunciar el título (RDS, Icecast) mientras suena":
        "Announce the title (RDS, Icecast) while playing",
    "Salida":
        "Output",
    "Con la emisión (misma salida y mezcla)":
        "With the broadcast (same output and mix)",
    "Guardar la lista como…":
        "Save the list as…",
    "Vaciar la lista":
        "Empty the list",
    "Nombre de la lista:":
        "List name:",
    "dB que baja la principal:":
        "dB the main playout is ducked:",
    "dB (sobre el volumen igualado):":
        "dB (on top of the normalized level):",
    "Guardar la lista":
        "Save the list",
    "Lista (*.m3u8)":
        "Playlist (*.m3u8)",
    "sonando":
        "playing",
    "en pausa":
        "paused",
    "parada":
        "stopped",
    "Asignar un audio…":
        "Assign an audio file…",
    "Etiqueta":
        "Label",
    "Texto del botón:":
        "Button text:",
    "Para las cuatro listas y la botonera (la emisión principal sigue)":
        "Stops the four lists and the cart wall (the main playout goes on)",
    "Clic: lanzar o parar. Clic derecho: asignar, etiqueta, bucle. También se pueden soltar ficheros encima.":
        "Click: fire or stop. Right click: assign, label, loop. You can also drop files on it.",
    "Preescucha":
        "Preview",
    "Por qué tarjeta se preescucha (la de los cascos, no la de antena)":
        "Sound card used for preview (the headphones one, not the on-air one)",
    "Ojo: es la misma tarjeta que la emisión, la preescucha se oiría en antena.":
        "Careful: it is the same sound card as the broadcast, the preview would be heard on air.",
    "Marcar intro aquí":
        "Mark intro here",
    "Púlsalo justo cuando entra la voz: queda apuntado dónde acaba la intro":
        "Press it right when the vocals come in: the end of the intro is noted",
    "Segundos de intro (0 = sin marca):":
        "Intro seconds (0 = no mark):",
    "Opciones":
        "Options",
    "Añadir audios a %s":
        "Add audio files to %s",
    "Reproducir ahora":
        "Play now",
    "Poner como siguiente":
        "Cue as next",
    "Punto de parada después de este":
        "Stop point after this one",
    "Preescuchar":
        "Preview",
    "Preescuchar el final":
        "Preview the ending",
    "Añadir audios…":
        "Add audio files…",
    "Cuánto baja la principal… (%g dB)":
        "How much the main playout is ducked… (%g dB)",
    "Volumen de esta lista… (%+g dB)":
        "Volume of this list… (%+g dB)",
    "Volumen de esta lista… (%g dB)":
        "Volume of this list… (%g dB)",
    "1 audio":
        "1 audio file",
    "Audio del botón %d":
        "Audio for button %d",
    "Cambiar la etiqueta…":
        "Change the label…",
    "En bucle (un colchón)":
        "Looped (a music bed)",
    "Quitar el audio":
        "Remove the audio",
    "PARAR TODO":
        "STOP ALL",
    "Parar botonera":
        "Stop cart wall",
    "Nada en preescucha":
        "Nothing in preview",
    "No se está emitiendo: las listas que salen con la emisión y la botonera esperan a que empiece. Las que tienen su propia tarjeta funcionan igual.":
        "Not on air: the lists that play with the broadcast and the cart wall wait for it to start. Lists with their own sound card work anyway.",
    "LISTA DE EMERGENCIA EN ANTENA: la emisión principal está en silencio.":
        "EMERGENCY LIST ON AIR: the main broadcast is silent.",
    "Audios…":
        "Audio files…",
    "Carpeta o lista…":
        "Folder or playlist…",
    "Quitar de la lista":
        "Remove from the list",
    "¿Quitar todos los audios de «%s»?":
        "Remove all audio files from “%s”?",
    "por %s":
        "via %s",
    "Lista vacía":
        "Empty list",
    "se para a las %s":
        "stops at %s",
    "Sin audio: clic derecho para asignar uno, o suelta aquí un fichero":
        "No audio: right click to assign one, or drop a file here",
    "Lista guardada en %s":
        "List saved to %s",
    "PAUSA":
        "PAUSED",
    "Al final de la lista":
        "At the end of the list",
    "Siguiente: %s":
        "Next: %s",
    "CADENA":
        "NETWORK",
    "QUEDA":
        "REMAINING",
    "HORA EN PUNTO":
        "TOP OF THE HOUR",
    "LISTA DE EMERGENCIA EN ANTENA":
        "EMERGENCY LIST ON AIR",
    "ESTA ES LA RESERVA Y ESTÁ EN ANTENA":
        "THIS IS THE BACKUP AND IT IS ON AIR",
    "Pantalla de locutor":
        "Presenter screen",
    "SEÑAL HORARIA":
        "TIME SIGNAL",
    "Después:  %s%s   ·   %s":
        "Next:  %s%s   ·   %s",
    "BLOQUE":
        "BLOCK",
    "Entra primero en el panel web (tiene contraseña).":
        "Log in to the web panel first (it has a password).",
    "Cuenta atrás de la intro: hasta que entra la voz":
        "Intro countdown: until the vocals come in",
    "Marcar intro":
        "Mark intro",
    "Púlsalo justo cuando entra la voz de la canción que suena: queda apuntado dónde acaba su intro, para la cuenta atrás":
        "Press it right when the vocals of the playing song come in: the end of its intro is noted, for the countdown",
    "Grabando ahora":
        "Recording now",
    "Nada.":
        "Nothing.",
    "Grabaciones programadas":
        "Scheduled recordings",
    "anunciante o campaña (opcional)":
        "advertiser or campaign (optional)",
    "Desde":
        "From",
    "Hasta":
        "To",
    "Guardar el certificado":
        "Save the proof of play",
    "Página web (*.html)":
        "Web page (*.html)",
    "Detector de silencio":
        "Silence detector",
    "Reserva (playout espejo)":
        "Backup (mirror playout)",
    "Líneas, corresponsales o conexiones que hay que grabar a una hora. Al acabar, la grabación puede entrar sola en una lista auxiliar.":
        "Lines, correspondents or remotes to record at a set time. When finished, the recording can go into an aux list by itself.",
    "No hay grabaciones programadas. Pulsa «Añadir».":
        "There are no scheduled recordings. Press “Add”.",
    "Certificado de emisión…":
        "Proof of play…",
    "Ahora: %s":
        "Now: %s",
    "Ahora: ":
        "Now: ",
    "quedan %s":
        "%s left",
    "ERROR: %s":
        "ERROR: %s",
    "Auxiliares y botonera":
        "Aux lists and cart wall",
    "Grabaciones":
        "Recordings",
    "Importar una &pauta (música o publicidad)…":
        "Import a &log (music or traffic)…",
    "Pantalla de &locutor":
        "&Presenter screen",
    "Importar una pauta":
        "Import a log",
    "Música: una lista por hora":
        "Music: one list per hour",
    "Publicidad: una lista por corte (hora y minuto del bloque)":
        "Traffic: one list per break (hour and minute of the block)",
    "La que traiga el fichero (o su nombre)":
        "The one in the file (or its name)",
    "Esta:":
        "This one:",
    "Fichero exportado":
        "Exported file",
    "Es de":
        "It is",
    "Fecha":
        "Date",
    "Dejar las listas en":
        "Put the lists in",
    "Carpeta de los audios":
        "Audio folder",
    "Vale casi cualquier exportación de texto (MusicMaster, Selector, Powergold, el programa de publicidad): de cada línea se saca la hora y el audio, como ruta, como nombre de fichero o como número de cartucho (el fichero de la carpeta de los audios cuyo nombre empieza por él). Luego pon «Pauta importada» en el orden de la franja o del bloque, con esa carpeta.":
        "Almost any text export works (MusicMaster, Selector, Powergold, the traffic system): from each line the time and the audio are taken, as a path, a file name or a cart number (the file in the audio folder whose name starts with it). Then set “Imported log” as the order of the time slot or block, with that folder.",
    "Falta el fichero o la carpeta donde dejar las listas.":
        "The file or the folder to put the lists in is missing.",
    "Pauta importada: %s":
        "Log imported: %s",
    "Fechas ilegibles.":
        "Unreadable dates.",
    "Pauta importada: la lista que toca a cada hora":
        "Imported log: the list for each hour",
    "Pauta importada: la lista que toca en cada corte":
        "Imported log: the list for each break",
    "Cadena":
        "Network",
    "Elegir un fichero":
        "Choose a file",
    "Salida: con la emisión":
        "Output: with the broadcast",
    "Audios, carpeta o lista…":
        "Audio files, folder or playlist…",
    "Subir":
        "Move up",
    "Bajar":
        "Move down",
    "Punto de parada":
        "Stop point",
    "Clic: lanzar o parar. Clic derecho: asignar, etiqueta, bucle.":
        "Click: fire or stop. Right click: assign, label, loop.",
    "Sin audio: clic para asignar uno":
        "No audio: click to assign one",
    "Pautas importadas":
        "Imported logs",
    "Importar una pauta (música o publicidad)…":
        "Import a log (music or traffic)…",
    "vacía: la que traiga el fichero (o su nombre)":
        "empty: the one in the file (or its name)",
    "Importar":
        "Import",
    "Abrir para imprimir":
        "Open to print",
    # novedades de la 1.2
    "Listas auxiliares: cuatro reproductores con su propia lista, en modo manual, asistido (encadena hasta un punto de parada) o automático. Mientras suenan, la emisión principal sigue igual, baja o se calla, sin perder nunca su hora.":
        "Aux lists: four players with their own list, in manual, live assist (segues up to a stop point) or automatic mode. While they play, the main broadcast stays as it is, ducks or mutes, without ever losing its timing.",
    "Botonera de 16 disparos para jingles, efectos y colchones, y preescucha por otra tarjeta.":
        "A 16-button cart wall for jingles, effects and music beds, and preview through another sound card.",
    "Intro de cada canción: se marca con un botón y sale su cuenta atrás para hablar encima.":
        "Song intros: mark them with a button and get a countdown to talk over.",
    "Pantalla de locutor (Ver > Pantalla de locutor, o /locutor en el panel web).":
        "Presenter screen (View > Presenter screen, or /locutor in the web panel).",
    "Detector de silencio: si la emisión se queda muda, entra sola una lista de emergencia.":
        "Silence detector: if the broadcast goes silent, an emergency list goes on air by itself.",
    "Enlace con la cadena: un evento puede engancharse a un stream o a una entrada de tarjeta durante un tiempo exacto.":
        "Network join: an event can join a stream or a sound card input for an exact length of time.",
    "Grabaciones programadas (líneas, corresponsales) que pueden entrar solas en una lista auxiliar, y logger de antena.":
        "Scheduled recordings (lines, correspondents) that can go into an aux list by themselves, and an air logger.",
    "Pautas importadas de los planificadores de música y de publicidad, y certificado de emisión de las cuñas.":
        "Logs imported from music and traffic schedulers, and proof of play for the spots.",
    "Reserva: un segundo GIMEL puede vigilar al principal y tomar el relevo si deja de emitir.":
        "Backup: a second GIMEL can watch the main one and take over if it stops broadcasting.",
}
