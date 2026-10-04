<p align="center"><img src="recursos/gimel-256.png" width="128" alt="GIMEL"></p>

# GIMEL

Radio playout for Windows built around **exact hourly rotations**.

Most playout programs play one song after another and hope the hour works out.
GIMEL plans each hour as a whole. The time signal goes on the hour, to the
sample. Ad and break blocks go at their minute with their exact length. The
music in between is chosen and crossfaded so that every segment lasts exactly
what it has to. Nothing is cut off abruptly to make room, and there are no
gaps to fill by hand.

It is meant for stations that run unattended: music radio, network affiliates
that have to break away and rejoin on a cue, and internet radio that wants the
discipline of a broadcast clock.

*Documentación en español: [LEEME.md](LEEME.md).*

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Install](#install)
- [First steps](#first-steps)
- [The window](#the-window)
- [Programming the station](#programming-the-station)
  - [Time slots](#time-slots)
  - [Songs](#songs)
  - [Jingles](#jingles)
  - [Time signals](#time-signals)
  - [Ad and break blocks](#ad-and-break-blocks)
  - [Fixed-minute events](#fixed-minute-events)
- [How the hour is fitted](#how-the-hour-is-fitted)
- [Mix settings](#mix-settings)
- [The library](#the-library)
- [Outputs](#outputs)
  - [Sound card](#sound-card)
  - [Icecast](#icecast)
- [CUE messages](#cue-messages)
- [Now playing title](#now-playing-title)
- [Broadcast log](#broadcast-log)
- [Web panel](#web-panel)
- [When something goes wrong](#when-something-goes-wrong)
- [Updates](#updates)
- [Command line](#command-line)
- [Where the data is kept](#where-the-data-is-kept)
- [Running from source](#running-from-source)
- [Building](#building)
- [Project layout](#project-layout)
- [Tests and tools](#tests-and-tools)
- [Languages](#languages)
- [Troubleshooting](#troubleshooting)
- [Licence](#licence)

## Features

- **Exact hourly rotation.** Songs are picked and crossfaded so each segment
  ends on its mark. The leftover is usually under a second and is spread over
  the transitions, where nobody hears it.
- **Sample-accurate timing.** Time signals, blocks and events start on the
  audio sample that corresponds to their clock time. The sound card latency is
  measured and compensated.
- **Shuffle that does not repeat.** Nothing plays again until the whole folder
  has played, two songs by the same artist are kept apart, and the rotation
  survives a restart.
- **Time slots** by day and hour, each with its own music, jingles and rules.
- **Jingles** over the transition or between songs, shuffled or in sequence,
  plus a station ID after the time signal.
- **Time signals**: one audio per hour, with the top of the hour falling where
  you say (start, end, or a given second of the audio).
- **Ad and break blocks** with an exact length, filled with spots or filler
  music, with opening and closing silences and intro and return jingles.
- **CUE messages** (`break` / `endbreak`) over HTTP, TCP, UDP, a file or DTMF
  tones, so other stations or systems can break away and rejoin.
- **Fixed-minute events**: bulletins, promos, half-hour signals.
- **Loudness levelling** to a target in LUFS (BS.1770), with a safety limiter.
- **Live library.** Folders and playlists are rescanned every minute: songs and
  jingles added or removed while GIMEL is running join or leave the rotation
  without a restart.
- **Outputs**: sound card (WASAPI, DirectSound, MME) and any number of Icecast
  servers (MP3, AAC, Ogg Vorbis, Opus), with the now playing title.
- **Now playing title** to a text file or a URL, for RDS encoders and websites.
- **Two interfaces** on the same engine: a desktop window and a web panel to
  run the station from another computer.
- **Spanish and English**, switchable without restarting.
- **Broadcast log** in CSV, one file per day, with the real time each audio
  went on air.
- **Self-update** from the releases of this repository, resuming the broadcast
  afterwards.
- **All the usual audio formats**, decoded by ffmpeg, each file by its own
  process: a corrupt file never takes the broadcast down.

## Requirements

- Windows 10 or later, 64-bit.
- A sound card, an Icecast server, or both.
- The PC clock synchronised by NTP. GIMEL trusts it for everything.

Nothing else has to be installed. The installer includes ffmpeg.

## Install

Download `gimel-setup.exe` from the
[latest release](https://github.com/GimelBroadcast/gimel/releases/latest) and
run it.

The installer is a single file with everything inside; it downloads nothing
else. It asks for administrator permission, shows the licence, installs to
`C:\Program Files\GIMEL`, adds the shortcuts and the uninstaller and, if you
tick the box, makes GIMEL start with Windows. To have it also go on air by
itself, enable *Settings > Station > Go on air when the program opens*.

It is not code-signed, so Windows SmartScreen may warn about it
(*More info > Run anyway*).

    gimel-setup.exe                     wizard
    gimel-setup.exe /S                  no questions: installs, or updates what is already there
    gimel-setup.exe /S /ARRANCAR        ...and opens GIMEL when done
    gimel-setup.exe /D=C:\Radio\GIMEL   into that folder (with or without /S)

With `/S` nothing is shown. What happened is left in `%TEMP%\gimel-setup.log`
and in the exit code:

| Exit code | Meaning |
|---|---|
| 0 | Installed or updated |
| 1 | Error |
| 2 | GIMEL was still open after 60 s; nothing was touched |

An update never leaves things half done. The new version is unpacked aside and
only replaces the previous one if it came out whole; if anything fails midway,
the previous version is put back.

To uninstall, use *Apps* in Windows settings, or run `desinstalar.exe` from the
program folder (`desinstalar.exe /S` for no questions). The configuration, the
rotation and the broadcast log are not deleted.

You can also use GIMEL without installing it: the program folder
(`GIMEL.exe`, `_internal\` and `ffmpeg.exe`) can be copied to another computer
as it is. A copied folder keeps its data next to the program and does not
update itself.

## First steps

1. Open GIMEL. The *On air* page says there is no schedule yet.
2. Go to **Time slots**, select *General programming* and, under *Songs*,
   press *Browse…* to choose the music folder (its subfolders are included) or
   an `.m3u` / `.pls` playlist.
3. Press **Save changes** (Ctrl+S).
4. GIMEL analyses the library. The status bar shows how many audios are left.
   It takes about half a second per song and is done only once.
5. The *On air* page now shows the *planned rotation*: what would air if you
   started right now.
6. Press **▶ GO ON AIR**.

From there, add what the station needs: jingles in the same time slot, the
hourly audio in **Time signals**, ad or break blocks in **Ads / break**, a
streaming server in **Icecast**.

To try GIMEL without your own music, see the demo library under
[Tests and tools](#tests-and-tools).

## The window

The window has nine pages, listed down the left side:

| Page | Shortcut | What it is for |
|---|---|---|
| On air | Ctrl+1 | What is playing, the countdown to the next anchor, and this hour's schedule |
| Time slots | Ctrl+2 | Which music and jingles play on which days and hours |
| Time signals | Ctrl+3 | The audio for each hour and how it is synchronised |
| Ads / break | Ctrl+4 | Blocks of spots or filler music, with their silences and CUE |
| Events | Ctrl+5 | Audios at a fixed minute of the hour |
| CUE and title | Ctrl+6 | Where the CUE messages and the now playing title are sent |
| Icecast | Ctrl+7 | Streaming servers |
| Settings | Ctrl+8 | Station, audio output, mix and web panel |
| Log | Ctrl+9 | What has been broadcast |

The menu bar:

- **File**: *Save changes* (Ctrl+S), *Discard changes*, *Import
  configuration…*, *Export configuration…*, *Open the data folder*, *Exit*
  (Ctrl+Q).
- **Broadcast**: *Go on air* / *Stop broadcasting*, *Skip song*, *Rebuild the
  schedule*.
- **View**: the nine pages, *Open the web panel in the browser*, *Full screen*
  (F11).
- **Language**: Español, English.
- **Help**: *Check for updates…*, *GIMEL page on GitHub*, *About GIMEL*.

The status bar at the bottom shows the audio output in use, the state of each
Icecast stream, the address of the web panel, how many audios are left to
analyse and, if there have been any, the number of audio dropouts.

**Saving.** The configuration pages work on a copy. Nothing reaches the
broadcast until you press *Save changes*; *Discard* goes back to what is in
use. Saving while on air is safe: what is already playing carries on and the
rest of the hour is planned again with the new settings.

**Importing and exporting.** An imported configuration comes in as unsaved
changes, so you can review it before saving or discard it. An exported one
contains the Icecast and web panel passwords, just like `config.json`.

**Skip song** fades out the song that is playing and brings in the next one;
the rest of the segment is chosen again so the hour still fits. **Rebuild the
schedule** plans the rest of the hour again, starting right now.

## Programming the station

### Time slots

A time slot says what plays on certain days between certain hours. The
*general programming* is the slot that applies when no other does; it always
exists and cannot be deleted.

Each hour is built with the **first time slot in the list that covers it**; if
none does, with the general programming. The order matters, so the list has ▲
and ▼ buttons. Slots go by whole hours because the rotation is hourly: each
hour is planned in one piece with the slot it belongs to.

If the end hour is not later than the start hour, the slot crosses midnight,
and the days ticked are those on which it *starts*: a slot from 22 to 6 ticked
for Friday covers Friday night and Saturday until 6.

If a slot's folder is empty or missing, the general programming's music is
used for that hour instead of going silent.

| Setting | What it does | Default |
|---|---|---|
| Time slot enabled | Turns the slot on or off without deleting it | On |
| Name, Days, From, To | When it applies | Every day, 0 to 24 |
| Folder or playlist | Where the songs come from | — |
| Order | *Shuffle* or *Sequential* | Shuffle |
| Skip those shorter than / longer than | Leaves out songs outside that length (0 = no limit) | 0 |
| Play jingles between songs | Turns jingles on for this slot | Off |
| Jingles folder or playlist | Where the jingles come from | — |
| Jingle order | *Shuffle* or *Sequential* | Shuffle |
| One jingle every … song changes | How often a jingle plays | 1 |
| Placement | *Over the transition between songs* or *Between one song and the next* | Over |
| Play the time signal | Whether this slot's hours start with the time signal | On |
| Station ID (a jingle) right after the signal | One of the slot's jingles after the time signal | Off |
| Allow ad / break blocks | Whether blocks are scheduled in this slot's hours | On |
| Allow fixed-minute events | Whether events are scheduled in this slot's hours | On |

### Songs

The source is a folder, with all its subfolders, or an `.m3u`, `.m3u8` or
`.pls` playlist. Internet streams inside a playlist are ignored.

- **Shuffle** is a deck of cards, not a dice roll. Every song plays once per
  round, and no song repeats until all of them have played. A new round never
  starts with the songs that closed the previous one, so between two plays of
  the same song there is always at least half the folder. Songs by the same
  artist are kept apart (three songs by default, see
  [Mix settings](#mix-settings)).
- **Sequential** follows the order of the playlist, or the natural order of
  the file names in a folder, and starts over at the end.

The rotation is saved to disk. Closing the program does not reset it, and what
is announced as coming up next does not change from one moment to the next.

To make an hour fit, the planner may take a song from further down the queue.
That only brings it forward; it does not repeat it.

### Jingles

Jingles come out of their own folder or playlist with their own rotation, in
the order the time slot says. In shuffle, every jingle in the folder plays
before any of them repeats.

- **Over the transition**: the jingle plays on top of the crossfade, over the
  end of one song and the start of the next. The incoming song is ducked while
  the jingle plays. If the jingle is longer than the allowed overlap, the song
  waits before coming in.
- **Between one song and the next**: song, jingle, song.

Blocks can use the slot's jingles as their intro and return jingles, and the
*station ID* after the time signal is taken from them too.

### Time signals

The **Time signals** page holds one audio for each of the 24 hours, plus a
generic one for the hours that have none. *Fill from a folder…* assigns them
all at once: each file goes to the hour of the number in its name (`07.mp3`,
`hora_14.wav`…).

| Setting | What it does | Default |
|---|---|---|
| Play time signals | Master switch | On |
| The top of the hour falls | *When the audio starts*, *when the audio ends*, or *at a given second of the audio* | When it starts |
| Second of the audio that falls on the hour | For the third option | 0 |
| Music fade-out before it | How long the music takes to fade when it has to be cut for a signal, a block or an event | 2 s |
| Signal for hours without their own audio | The generic one | — |

With pips, the last one normally starts exactly on the hour: choose *at a
given second of the audio* and say which.

The music before the signal is fitted so that it ends there by itself; the
fade-out is only what is left when the fit is not perfect. If no signal plays
in an hour, the last song of the hour simply crossfades into the first song of
the next one, on the hour.

### Ad and break blocks

    music (fades 2 s) → silence 5 s → intro jingle → spots or filler → silence 5 s → return jingle → music
                          ↑ break CUE at 2 s            (N s EXACTLY)     ↑ endbreak CUE at 2 s

A block is scheduled in every hour of its range. The music before and after it
adjusts itself so the hour still adds up.

| Setting | What it does | Default |
|---|---|---|
| Block enabled, Name, Days | — | On, every day |
| Only in the hours from … to | The range of hours in which it is scheduled | 0 to 24 |
| Minute of each hour, Second | When | 30:00 |
| At that time | What happens at that time: *the intro jingle starts*, *the opening silence starts*, or *the spots / the filler start* | The intro jingle starts |
| What plays | *Spots* or *Filler music* | Spots |
| Exact length | How long the content lasts, to the second | 60 s |
| Spots folder or playlist, Spot order | Where the spots come from | —, Shuffle |
| If the spots do not fill the time | *One more spot, cut when the time is up*, *Filler music until the time is up*, or *Silence until the time is up* | One more spot |
| Filler music | File, folder or playlist; it fades out when the time is up | — |
| Silence before the block | — | 5 s |
| Intro jingle | On or off, and a file or folder. Empty: one of the time slot's jingles | On |
| Silence at the end | — | 5 s |
| Return jingle, after the silence | On or off, and a file or folder | Off |
| Send break and endbreak CUE | — | On |
| Break CUE … s after the opening silence starts | — | 2 s |
| Endbreak CUE … s after the closing silence starts | — | 2 s |

**Spots.** In shuffle, GIMEL looks at the next spots in the rotation and plays
the combination that comes closest to the exact length without going over it.
In sequential, it plays them in order for as long as they fit. Whatever is
missing is handled like this: a gap shorter than 3 s is spread as pauses
between spots; a longer one is filled as the block says, with one more spot
cut when the time is up, with filler music, or with silence.

**Filler music** is for when the CUE makes the other stations break away and
all that is needed at this end is to cover the gap. Each break in the hour
gets different music.

**When a block does not fit.** A block that would run past the next hour is
shortened so it ends before the time signal, and a notice says so. If two
anchors overlap, the later one moves back to start when the earlier one ends.

### Fixed-minute events

An event is an audio that starts at an exact minute of the hour: a bulletin,
the half-hour signal, a promo. The music fades out first, as it does for the
time signal, and comes back when the audio ends.

The audio can be a single file, or a folder or playlist if you want several to
rotate, shuffled or in sequence. Like blocks, events have their days and their
range of hours.

## How the hour is fitted

- **Anchors** are what happens at an exact clock time: the time signal, the
  blocks, the fixed-minute events. They start on the sample they belong to.
- **Segments** are the music between two anchors.

For each segment, songs come out of the rotation in order, except the last two
or three, which are chosen so that the total lands just above the gap. What is
left over, usually under a second, is spread by bringing each song's
transition slightly forward, with a limit per song. If there is still excess,
the last song is faded out before the anchor.

Two clocks are at work, and each thing uses its own:

- Inside a segment, songs are **chained in audio frames**. The next one comes
  in when the one playing reaches its mix point, to the sample.
- Anchors follow the **wall clock**. The time signal starts on the frame that
  corresponds to the top of the hour, whatever the music is doing.

The sound card and the PC clock never run at exactly the same speed, so before
every transition the leftover is shared out again among the songs that remain.
The segment always ends on its anchor.

To know which clock time a frame corresponds to, the engine measures on every
audio callback when the audio it is delivering will actually leave the
speaker. That is how the sound card latency is compensated without having to
enter it. If something *after* the card delays the audio (a processor, an STL
link, an encoder), enter it in *Settings > Audio output > Chain delay to
compensate* and everything is brought forward by that much.

The next hour is planned five minutes before it starts. Each transition is
handed to the engine two seconds ahead, and the decoders of what is coming up
are started well before that.

## Mix settings

*Settings > Mix.*

| Setting | What it does | Default |
|---|---|---|
| **Fitting the hour** | | |
| Maximum trim per song | The most a song's transition can be brought forward to make the hour fit | 20 s |
| Fade-out of a trimmed song | How long the outgoing song takes to fade when it is crossed before its end | 4 s |
| A song plays for at least | A song that would play for less than this at the end of a segment is left out | 30 s |
| **Transitions** | | |
| Level at which the next one comes in | The next song starts when the one playing drops this many dB below its level. More negative means later transitions | −15 dB |
| Maximum overlap at the end of a song | The earliest the next song may come in before the end of the one playing | 8 s |
| Transition when a song is skipped by hand | Fade length when you press *Skip song* | 1 s |
| Separation between two by the same artist | Songs between two by the same artist | 3 |
| **Jingles over the transition** | | |
| Jingle playing over the incoming song, at most | With a longer jingle, the song waits before coming in | 15 s |
| Duck the incoming song while the jingle plays | How much the incoming song is lowered under the jingle | 6 dB |
| **Volume** | | |
| Level the volume of all audios | Loudness levelling | On |
| Target level | — | −14 LUFS |
| Song, jingle, spot, signal and event trim | Extra gain per type of audio | 0 dB |

**The mix point is taken from the audio itself.** A song that ends abruptly is
mixed at its very end. One that fades out is mixed earlier, when its level has
dropped by the amount set in *Level at which the next one comes in*. If your
songs have long fade-outs and the next one comes in too late for your taste,
raise the level (−9 dB, for example) and the *Maximum overlap*.

**Levelling** measures the loudness of each audio (BS.1770) and brings it to
the target. The gain never pushes an audio into clipping.

## The library

**Formats.** Files with these extensions are picked up and decoded by ffmpeg:
`.mp3` `.wav` `.flac` `.ogg` `.oga` `.opus` `.m4a` `.aac` `.wma` `.aif`
`.aiff` `.mp2` `.ac3` `.mka` `.wv` `.ape` `.mp4`. Playlists can be `.m3u`,
`.m3u8` or `.pls`.

**Analysis.** The first time a file is used, it is decoded once from start to
end to find out:

- its **real length**, counted in samples (the header of an MP3 can lie, and
  here a second of error is a second of silence before the time signal),
- where it **starts and stops sounding**, so leading and trailing silence are
  skipped,
- its **mix point**: how its level drops towards the end,
- its **loudness** in LUFS and its **peak**.

The result is stored and a file is only analysed again if its size or date
changes. Analysis runs in the background at low priority and takes about half
a second per song. Meanwhile, the broadcast carries on with what is already
analysed, so a folder on a slow network drive or a library of thousands of
songs does not hold anything up.

The title and artist come from the file's tags or, if it has none, from a file
name of the form `Artist - Title`.

**Live library.** Folders and playlists are looked at again every minute,
whether GIMEL is on air or not. A new audio joins the rotation as soon as it
has been analysed; one that has been removed leaves the schedule before it
gets to fail on air. In practice a change takes effect within a couple of
minutes, with no restart and no button to press.

Two details:

- An audio that is about to play (less than half a minute away) is not
  swapped. If you delete a file at that moment, it may play one last time.
- A folder that suddenly looks empty, as a network drive that stops answering
  does, is not believed until it is still empty a minute later.

## Outputs

The mix is made at 48 kHz in stereo. The sound card and every Icecast server
get exactly the same audio, after the limiter.

### Sound card

*Settings > Audio output.*

| Setting | What it does | Default |
|---|---|---|
| Audio system | WASAPI, DirectSound, MME, or *No sound card: Icecast only* | WASAPI |
| Audio output | Which sound card or virtual cable. It is remembered by name | System default |
| Buffer | If you hear dropouts, raise it. It does not affect how exact the hours are | 200 ms |
| Output volume | — | 0 dB |
| Safety limiter | Prevents clipping when two loud audios coincide | On |
| Chain delay to compensate | Delay of whatever comes after the sound card | 0 ms |

If the chosen output is not there when you go on air, GIMEL uses the system
default and says so. If the output stops asking for audio while on air (the
device was unplugged, for example), GIMEL tries to reopen it by itself.

### Icecast

*Icecast* page. The broadcast is sent to every active server, as well as to
the sound card. You can have several at once: the same programme in MP3 and in
AAC, or to two different servers. To broadcast through Icecast only, choose
*No sound card* as the audio system.

| Setting | What it does | Default |
|---|---|---|
| Send to this server | Turns the stream on or off | On |
| Name | Only to recognise it in the list | Icecast |
| Server, Port | Name or IP address, without `http://` | localhost, 8000 |
| Mount point | For example `/radio` or `/live.mp3` | /gimel |
| User, Password | The user is almost always `source` | source |
| Encrypted connection (TLS) | For servers behind HTTPS | Off |
| Format | MP3, AAC, Ogg Vorbis or Ogg Opus | MP3 |
| Quality | Bitrate, 16 to 320 kbps | 128 kbps |
| Sample rate | 48 000, 44 100, 32 000 or 22 050 Hz (Opus is always 48 000) | 44 100 Hz |
| Stereo | — | On |
| Send the title of each song | With MP3 and AAC | On |
| Stream name, Description, Genre, Website | What the listener sees. An empty stream name uses the station name | — |
| List it in public directories | — | Off |

The streams connect when you go on air. The audio thread never waits for the
network: if the connection stalls, the oldest audio waiting to be sent is
dropped, the listener hears a skip, and the sound card output is not affected.
If the connection is lost, it is retried every few seconds. The page shows the
state of each stream and why it failed: wrong password, mount point in use,
server not answering.

## CUE messages

A CUE is a message to another system: "I am going to a break and it lasts this
long" and "I am back". Affiliates use it to break away for their own ads and
rejoin on time.

CUE are off until you turn on *Send the CUE* on the *CUE and title* page. Then
each block sends two: the **break** CUE during the silence before the block
and the **endbreak** CUE during the silence at the end. How many seconds into
each silence is set in the block. They go to every active server on that
page:

| Type | What is sent | Destination |
|---|---|---|
| HTTP | A POST with the message to a URL (a GET if the message is empty) | `http://host:port/path` |
| TCP | The message, as one line | `host:port` |
| UDP | The message, in one datagram | `host:port` |
| Text file | The message, written to a file | A path |
| DTMF | The digits of the message as tones inside the audio itself | — |

The messages are templates. These variables are replaced:

| Variable | Value |
|---|---|
| `{evento}` | `break` or `endbreak`, whatever language the program is in |
| `{duracion}` | Seconds from the break CUE to the endbreak CUE |
| `{contenido}` | How long the spots or the filler last |
| `{silencio}` | The silence at the end of the block |
| `{bloque}` | The name of the block |
| `{emisora}` | The station name |
| `{hora}`, `{fecha}`, `{epoch}` | The time of the CUE: `HH:MM:SS.mmm`, `YYYY-MM-DD`, Unix time |

The default HTTP message is JSON:

    {"evento":"break","emisora":"My Radio","bloque":"Ads","duracion":68.5,"contenido":60,"hora":"10:29:57.000","epoch":1791102597.000}

DTMF messages are made of the keys `0`–`9`, `*`, `#` and `A`–`D`; the default
ones are `*1#` for the break and `*0#` for the endbreak.

Other settings: *Send the CUE early by* (positive: a little before their time;
negative: after) and *Retries if a server does not answer*, which applies to
HTTP and TCP. Each message is sent on its own thread at its exact clock time,
so a server that is down delays neither the others nor the broadcast.

The page has two test buttons, *Test: break* and *Test: endbreak*, and lists
the last CUE sent with their results. To try reception,
`python herramientas/servidor_cue.py` is a sample receiver on the ports the
program suggests.

## Now playing title

*CUE and title > Now playing title.* For an RDS encoder, the streaming
metadata or a website, GIMEL can publish what is playing. Turn on *Publish
what is playing* and it goes:

- to a **text file**, rewritten on every change, and
- to a **URL**, called with GET; `{texto}` is replaced by the title, already
  URL-encoded.

The text is a template, `{artista} - {titulo}` by default, and also accepts
`{emisora}`. With *Only songs change the text*, jingles, spots and signals
leave the last song's title in place; without it, you choose the text shown
for everything that is not a song.

The same text is what the Icecast servers receive as the title of each song.

## Broadcast log

Every audio that goes on air is written down with the **real** time it
started, one CSV file per day in `datos/registro/YYYY-MM-DD.csv`. It serves as
proof of the spots that were broadcast.

    fecha;hora;tipo;titulo;artista;segundos;nota;fichero
    2026-10-04;10:29:55.000;Jingle de bloque;Entrada a publicidad;;3.5;;D:\Radio\entrada.wav
    2026-10-04;10:29:58.500;Cuña;Spot 03;;15.0;;D:\Radio\ads\spot 03.mp3

The files are separated by semicolons and encoded in UTF-8 with a BOM, so they
open directly in Excel. They are always written in Spanish, whatever language
the program is in, so that a log is never half in one language and half in
another; the *Log* page translates it when showing it.

If the file cannot be written (the disk is full, or it is open in Excel), the
broadcast carries on.

## Web panel

The web panel does the same as the desktop window, against the same engine:
see what is playing and this hour's schedule, go on air, stop, skip, and
change the whole configuration. It is for running the station from another
computer, or on a machine with no screen. By default it is at
<http://127.0.0.1:8950>.

Who can get in:

- **Without a password, only the computer GIMEL runs on**, even if the panel
  is open to the network.
- **With a password**, anyone who knows it. The computer itself gets in
  without it.

To use it from another computer: *Settings > Web panel*, choose *Any computer
on the network* and set a password. Changes to the web panel settings take
effect when the program is restarted.

The panel can browse the disk and change the whole configuration, and it is
served over plain HTTP. **Do not expose it to the internet.** Use it on a
network you trust, or through a VPN or an HTTPS reverse proxy.

## When something goes wrong

GIMEL is built to stay on air:

- **A file that cannot be decoded** is left out when it is analysed. If it
  breaks later, a notice is shown, another audio is chosen in its place and
  the file is set aside for ten minutes.
- **A song shorter than its analysis said** (the file was changed): the next
  one comes in straight away.
- **An empty or missing folder in a time slot**: the general programming's
  music plays instead.
- **The PC clock jumps** (a time correction): the schedule is rebuilt from the
  new time.
- **The sound card stops responding**: GIMEL tries to reopen it.
- **The Icecast connection drops**: it reconnects by itself, and the sound
  card output is not affected.
- **A time signal that would start late**, because you went on air when it
  should already be playing, is skipped: a time signal off the hour is worse
  than none.
- **A damaged configuration file** is set aside as `config.json.roto` and the
  program starts with the default configuration.
- **An internal error** in the broadcast loop is shown as a notice and the
  loop carries on.

Notices appear on the *On air* page and in the web panel.

## Updates

*Help > Check for updates…* asks GitHub for the latest release. If it is newer
than the installed one, GIMEL downloads its installer, checks that it arrived
whole (its size and its SHA-256) and runs it: Windows asks for administrator
permission, GIMEL closes, the program is replaced and GIMEL opens again.

If you are on air, it warns first that the broadcast will stop for about a
minute, and it resumes by itself afterwards. The configuration and the data
are not touched.

The first time GIMEL opens after an update, it shows what is new in that
version.

Only a copy placed by the installer updates itself. Running from source, or
from a folder copied by hand, GIMEL tells you there is a new version and opens
its page.

> **Updating from 1.0.** On some computers, version 1.0 fails to check for
> updates with a certificate error. The fix is in 1.1, so 1.0 cannot download
> it by itself: download `gimel-setup.exe` from the releases page and run it
> once. It updates the installed copy and keeps your configuration.

## Command line

    GIMEL.exe                      desktop window (and web panel, if enabled)
    GIMEL.exe --emitir             go on air as soon as it opens
    GIMEL.exe --web                web panel only, no window
    GIMEL.exe --sin-web            do not open the web panel
    GIMEL.exe --host 0.0.0.0       address the web panel listens on
    GIMEL.exe --puerto 8950        port of the web panel
    GIMEL.exe --datos D:\Radio     folder for the configuration, the analysis and the log
    GIMEL.exe --actualizacion      say whether a newer version is published, and exit

From source, replace `GIMEL.exe` with `python main.py`.

`--actualizacion` exits with 0 if the installed version is the latest, 10 if
there is a newer one and 1 if it could not find out. The installed program has
no console, so redirect its output to read it:
`GIMEL.exe --actualizacion > result.txt`.

Only one GIMEL can run on a computer at a time: two would fight over the same
rotation and the same sound card.

## Where the data is kept

Installed under *Program Files*, GIMEL keeps its data in
`%LOCALAPPDATA%\GIMEL\datos`. A copy in a folder it can write to (a copied
program folder, or the source code) keeps it in `datos\` next to the program.
*File > Open the data folder* opens it.

| File | What it holds |
|---|---|
| `config.json` | The whole configuration. It contains the Icecast and web panel passwords |
| `rotacion.json` | The state of every rotation: what has played and what comes next |
| `analisis.db` | The analysis of each audio. It can be deleted; it is rebuilt |
| `registro\YYYY-MM-DD.csv` | The broadcast log |

Neither updating nor uninstalling touches this folder. To move a station to
another computer, export the configuration from the *File* menu, or copy the
whole folder with GIMEL closed.

## Running from source

    pip install -r requirements.txt        # plus ffmpeg on the PATH (winget install Gyan.FFmpeg)
    python main.py                         # desktop window + web panel
    python main.py --web                   # web panel only (http://127.0.0.1:8950)
    python main.py --emitir                # go on air as soon as it opens

Developed and tested with Python 3.11 on Windows. The dependencies degrade
gracefully:

| Package | Used for | Without it |
|---|---|---|
| numpy | The mixing engine and the analysis | Required |
| sounddevice | Output to the sound card | Icecast only |
| PyQt6 | The desktop window | Web panel only |
| flask | The web panel | Window only |
| certifi | Certificate authorities for the updater | Only those Windows already has |

ffmpeg is looked for next to `main.py` first and on the PATH after that.

On opening, GIMEL does **not** go on air, but it already generates the
rotation for the rest of the hour so you can see it.

The source code, its comments and the command-line options are in Spanish.

## Building

    pip install pyinstaller
    python herramientas/compilar.py                    # leaves dist/GIMEL/ and dist/gimel-setup.exe
    python herramientas/compilar.py --sin-instalador   # only the program folder
    python herramientas/compilar.py --sin-ffmpeg       # do not bundle ffmpeg.exe

- `dist/GIMEL/` is the program in a folder (`GIMEL.exe`, `_internal/`,
  `ffmpeg.exe` and `desinstalar.exe`).
- `dist/gimel-setup.exe` is the installer, written in Python
  (`instalador/instalador.py`), with that folder inside.
- ffmpeg is bundled: the `ffmpeg.exe` next to `main.py` or, if there is none,
  the one installed on the build machine, as long as it may be redistributed.
  A build configured with `--enable-nonfree` is refused.
- The icon (`recursos/gimel.ico` and `.png`) comes from
  `python herramientas/generar_icono.py`.

**To publish a version:**

1. Raise `__version__` in `gimel/__init__.py`.
2. List its changes in `gimel/novedades.py`, and their translation in
   `gimel/idiomas/en.py`. That is what the window shows after the update.
3. Build.
4. Create a release tagged `v` + that number (`v1.1`) with
   `dist/gimel-setup.exe` attached under that exact name.

The updater compares the release tag with the program's version, so a tag that
is not higher will not be offered to anyone.

## Project layout

    gimel/            the program
    herramientas/     demo, simulator, test battery, CUE receiver, build script
    instalador/       the Windows installer and uninstaller
    recursos/         the icon
    datos/            config.json, rotacion.json, analisis.db, registro/ (created on first run)
    demo/             demonstration library (created by generar_demo.py)

Inside `gimel/`:

| Module | What it does |
|---|---|
| `nucleo.py` | Puts everything together. It is the only thing the interfaces see, so the window and the web panel do exactly the same |
| `config.py` | The configuration: its data classes and its JSON |
| `esquema.py` | The description of every configuration form. Both interfaces draw their forms from it |
| `planificador.py` | Decides *what* plays and at what time: anchors, segments, which songs fit |
| `emisor.py` | Takes the schedule on air: hands each transition to the engine on the right frame |
| `motor.py` | The mixing engine and the sound card output. All time is counted in audio frames |
| `fuentes.py` | Audio sources: one ffmpeg process per file |
| `analisis.py` | The analysis of each audio and its cache |
| `biblioteca.py` | Which files are in each folder or playlist, and their analysis, without ever blocking |
| `rotacion.py` | The order in which the audios of each folder come out |
| `icecast.py` | Streaming to Icecast servers |
| `cue.py` | CUE messages and the now playing title |
| `registro.py` | The broadcast log |
| `actualizacion.py` | Updating from GitHub |
| `novedades.py` | What is new in each version |
| `idioma.py`, `idiomas/` | The languages |
| `ui/` | The desktop window (PyQt6) |
| `web/` | The web panel (Flask) |

Everything that changes the state of the broadcast happens on a single thread.
The interfaces leave orders in a queue and read a snapshot of the state; they
never touch anything directly. Only the audio thread touches the voices being
mixed.

## Tests and tools

GIMEL can be tested without a sound card and faster than real time. The
simulator uses the same engine, the same planner and the same broadcaster as
the real thing; the only difference is that the clock is driven by the audio
itself, so an hour is simulated in well under a minute and the result does not
depend on how fast the PC is.

    python herramientas/generar_demo.py --config               # a synthetic library, and a configuration that uses it
    python herramientas/simular.py --desde 10:52 --minutos 75  # simulated hours, checked to the sample
    python herramientas/pruebas.py                             # 17 edge-case scenarios
    python herramientas/pruebas.py jingles bloque              # only the scenarios whose name contains those words
    python herramientas/prueba_tarjeta.py                      # the engine against the real sound card, in silence
    python herramientas/servidor_cue.py                        # a receiver to test the CUE messages
    python herramientas/comprobar_idiomas.py                   # untranslated texts in each language

| Tool | What it does |
|---|---|
| `generar_demo.py` | Creates `demo/`: 36 songs, 8 jingles, 24 time signals, 10 spots, filler music and an intro jingle, all synthetic. Each song has its own melody, so transitions and cuts can be heard |
| `simular.py` | Simulates hours of broadcast and checks that every time signal starts on its exact frame, that every block lasts what it should, that the CUE go out on time and that there is no silence outside the schedule |
| `pruebas.py` | The test battery: starting inside a block, starting three seconds before the signal, a broken file, a file that disappears, a block that does not fit, changing the configuration while on air, audios added and removed while on air, and more |
| `prueba_tarjeta.py` | Runs the engine against the real sound card for a minute, in silence unless you pass `--sonar`. `--lista` shows the available outputs |
| `servidor_cue.py` | Receives CUE over HTTP (port 8951), TCP and UDP (8952) and prints them |
| `comprobar_idiomas.py` | Lists the texts each language table is missing |
| `compilar.py` | Builds the program and the installer |
| `generar_icono.py` | Draws the icon |

## Languages

The language is one for everything: the window, the web panel and the
broadcast notices. It is changed in the *Language* menu or in *Settings >
Station*, without restarting.

The program's texts are written in Spanish and each text is, at the same time,
the key of its translation. Each language is a table in `gimel/idiomas/`. To
add one:

1. Copy `gimel/idiomas/en.py` under the code of the new language and
   translate it.
2. Add it to `IDIOMAS` and `_TABLAS` in `gimel/idioma.py`.
3. Run `python herramientas/comprobar_idiomas.py`, which reports the texts
   that are missing, the ones no longer in use, and the ones whose `%s` or
   `%d` do not match the original.

## Troubleshooting

**"No schedule yet."** No songs folder has been chosen in *Time slots*, or the
library is still being analysed. The status bar shows how many audios are
left.

**The music does not start straight away the first time.** A new library has
to be analysed before it can be scheduled. The music starts as soon as there
are enough songs analysed.

**Audio dropouts.** Raise *Settings > Audio output > Buffer*. It does not
affect how exact the hours are. The status bar counts the dropouts.

**The time signal does not fall on the hour for the listener.** Check that the
PC clock is synchronised by NTP. If the audio is delayed after the sound card
(a processor, a link, an encoder), enter that delay in *Chain delay to
compensate*.

**The next song comes in too late, or too early.** Adjust *Level at which the
next one comes in* and *Maximum overlap at the end of a song* in
[Mix settings](#mix-settings).

**A new song does not show up.** Give it a couple of minutes: the folder is
looked at once a minute and the audio has to be analysed. In shuffle it then
takes its turn somewhere in the rotation, not necessarily next.

**"Check for updates" fails with a certificate error.** That is version 1.0 on
a computer whose Windows did not have the certificate authorities GitHub uses.
Install 1.1 or later by hand once; see [Updates](#updates).

**An Icecast stream does not connect.** The *Icecast* page says why: the
server rejects the user or the password, the mount point is already in use,
the server does not answer on that port, or the name cannot be found.

**The web panel cannot be reached from another computer.** It needs *Any
computer on the network* and a password, and a restart after changing either.
Check the Windows firewall too.

**Windows warns when running the installer.** It is not code-signed. Choose
*More info > Run anyway*.

**"ffmpeg not found"** (running from source). Install it with
`winget install Gyan.FFmpeg`, or put `ffmpeg.exe` next to `main.py`.

## Licence

GIMEL is free software under the **GNU GPL, version 3** (see `LICENSE`): you
can use, study, share and improve it under the terms of that licence.

The `ffmpeg.exe` that ships with the built program is FFmpeg, a separate
program with its own licence (also GPL v3 in the build used). It is included
unmodified; its source code is at <https://ffmpeg.org>.
