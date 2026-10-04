# -*- coding: utf-8 -*-
"""
Emisor: lleva la pauta al aire.

El planificador dice QUE suena y a que hora; el motor sabe poner una voz en un
frame exacto. El emisor esta en medio: unas decimas de segundo antes de cada
cambio (un cruce entre canciones, una senal horaria, un bloque) calcula el
frame en que toca y le entrega al motor las voces y los fundidos.

Dos relojes conviven aqui y cada cosa va con el suyo:

  - Dentro de un tramo las canciones se ENCADENAN EN FRAMES: la siguiente
    entra cuando la que suena llega a su punto de mezcla, a la muestra.
  - Las anclas van con el RELOJ DE PARED: la senal horaria arranca en el frame
    que corresponde a las en punto, pase lo que pase con la musica.

Como la tarjeta de sonido y el reloj del PC no corren exactamente igual, antes
de cada cruce se vuelve a repartir lo que sobra o falta entre las canciones
que quedan (el "reajuste"): el tramo siempre acaba clavado en su ancla.

Todo lo que cambia el estado ocurre en un solo hilo (`paso`). La interfaz deja
ordenes en un buzon y lee una foto del estado; nunca toca nada.
"""

import queue
import threading
import time
import traceback
from collections import deque
from datetime import datetime

from . import config as modconfig
from . import cue as modcue
from .fuentes import FuenteFFmpeg, FuenteMemoria
from .idioma import N_, tr
from .motor import Voz
from .planificador import (AIRE, ERROR, FIN, PLAN, PREP, PROG, TOL_FALTA, AnclaAudio,
                           AnclaBloque, AnclaCruce, Cancion, Pase, Planificador, Tramo,
                           hora_en_punto)
from .registro import Registro

PRINCIPALES = ("cancion", "senal", "evento", "cuna", "relleno", "jingle_publi")


class Emisor:
    AVANCE = 2.0              # s de antelacion con que un cruce se entrega al motor
    MARGEN_ANCLA = 1.5        # s que se suman al fundido previo para entregar un ancla
    PREPARAR = 25.0           # s de antelacion con que se arranca un decodificador
    MIRAR = 10.0              # cada cuantos s se mira si han cambiado las carpetas y las listas

    def __init__(self, cfg, bib, rot, motor, ffmpeg: str, soxr: bool = False,
                 registro=None, cues=None, titulo=None):
        self.cfg = cfg.copia()
        self.bib = bib
        self.rot = rot
        self.motor = motor
        self.ffmpeg = ffmpeg
        self.soxr = soxr
        self.registro = registro or Registro("")
        self.cues = cues
        self.titulo = titulo
        self.plan = Planificador(self.cfg, self)
        self.reabrir = None               # lo pone el nucleo: reabre la tarjeta si se cae

        self.emitiendo = False
        self.planes = []                  # la hora en curso y, cerca del final, la siguiente
        self.previa = []                  # parado: la pauta que saldria si se emitiera ya
        self._t_previa = 0.0
        self.ib = 0                       # bloque en curso de planes[0]
        self.items = {}                   # id de voz -> Item
        self.sonando = []                 # musica en el motor que un ancla tendra que callar
        self.cont_j = 0                   # cambios de cancion desde el ultimo jingle
        self.ultimo_jingle = ""           # para no dar el mismo dos veces seguidas
        self.actual = None
        self.jingle_actual = None
        self.sonadas = deque(maxlen=600)  # ultimas canciones al aire, para no repetir
        self.historial = deque(maxlen=400)
        self.avisos = deque(maxlen=40)
        self.vetadas = {}                 # ruta -> hasta cuando no se cuenta con ella
        self.buzon = queue.Queue()
        self._hilo = None
        self._salir = False
        self._saltos = motor.saltos
        self._t_rehacer = 0.0
        self._t_guardar = 0.0
        self._t_foto = 0.0
        self._t_reabrir = 0.0
        self._t_mirar = 0.0
        self._cambios = bib.cambios       # hasta donde se han tenido en cuenta los cambios de la biblioteca
        self._foto ={"emitiendo": False, "pauta": [], "avisos": []}
        for st in rot.e.values():         # lo que sono antes de cerrar tambien cuenta
            if isinstance(st, dict):
                self.sonadas.extend(st.get("rec", [])[-60:])

    # ============================================================ surtidor

    def cola(self, origen: str, orden: str = "aleatorio", dur_min: float = 0.0,
             dur_max: float = 0.0) -> list:
        """Pistas ya analizadas de un origen, en el orden de su rotacion."""
        if not origen:
            return []
        rutas = self.bib.listar(origen)
        if not rutas:
            return []
        en_cola = self.rot.cola(origen, orden, rutas, artista=self._artista,
                                separar=self.cfg.mezcla.separar_artista)
        ahora = time.monotonic()
        res = []
        pedidas = 0
        for r in en_cola[:400]:
            p = self.bib.pista(r, urgente=pedidas < 12)
            if p is None:
                pedidas += 1
                if orden == "secuencial":
                    break                                 # sin saltarse el orden
                continue
            if p.error or p.largo <= 0.2 or self.vetadas.get(r, 0.0) > ahora:
                continue
            if dur_min and p.largo < dur_min:
                continue
            if dur_max and p.largo > dur_max:
                continue
            res.append(p)
            if len(res) >= 140:
                break
        return res

    def vuelta(self, origen: str, orden: str) -> list:
        return self.rot.vuelta(origen, orden) if origen else []

    def pista(self, ruta: str):
        return self.bib.pista(ruta, urgente=True)

    def pendiente(self, origen: str) -> bool:
        return self.bib.pendiente(origen)

    def _artista(self, ruta: str) -> str:
        p = self.bib.conocida(ruta)
        return p.artista.lower() if p is not None else ""

    # ============================================================ interfaz (cualquier hilo)

    def iniciar(self) -> None:
        self.buzon.put(("iniciar",))

    def detener(self) -> None:
        self.buzon.put(("detener",))

    def saltar(self) -> None:
        self.buzon.put(("saltar",))

    def replanificar(self) -> None:
        self.buzon.put(("replanificar",))

    def aplicar_config(self, cfg) -> None:
        self.buzon.put(("config", cfg.copia()))

    def instantanea(self) -> dict:
        return self._foto

    def arrancar_hilo(self) -> None:
        if self._hilo is None:
            self._salir = False
            self._hilo = threading.Thread(target=self._bucle, daemon=True, name="emisor")
            self._hilo.start()

    def parar_hilo(self) -> None:
        self._salir = True
        h, self._hilo = self._hilo, None
        if h is not None:
            h.join(timeout=2.0)

    def _bucle(self) -> None:
        while not self._salir:
            try:
                self.paso()
            except Exception:
                self._aviso(tr("Error interno: ") + traceback.format_exc(limit=3).strip().splitlines()[-1])
                traceback.print_exc()
                time.sleep(0.2)
            time.sleep(0.03)

    # ============================================================ el paso

    def paso(self) -> None:
        self._ordenes()
        self._eventos()
        ahora = time.monotonic()
        if ahora - self._t_mirar > self.MIRAR:
            self._t_mirar = ahora
            self._mirar_biblioteca()
        if self.emitiendo:
            self._vigilar()
            self._asegurar_planes()
            self._programar()
            self._preparar()
        elif ahora - self._t_previa > 4.0:
            self._t_previa = ahora
            self._vista_previa()
        if ahora - self._t_foto > 0.2:
            self._t_foto = ahora
            self._foto = self._fotografiar()
        if ahora - self._t_guardar > 20.0:
            self._t_guardar = ahora
            self.rot.guardar()

    def _aviso(self, texto: str) -> None:
        if self.avisos and self.avisos[-1][1] == texto:
            return
        self.avisos.append((time.time(), texto))

    def _ordenes(self) -> None:
        while True:
            try:
                o = self.buzon.get_nowait()
            except queue.Empty:
                return
            if o[0] == "iniciar":
                self._iniciar()
            elif o[0] == "detener":
                self._detener()
            elif o[0] == "saltar":
                self._saltar()
            elif o[0] == "replanificar":
                if self.emitiendo:
                    self._replanificar()
            elif o[0] == "config":
                self.cfg = o[1]
                self.plan.cfg = self.cfg
                if self.cues is not None:
                    self.cues.configurar(self.cfg.cue)
                if self.titulo is not None:
                    self.titulo.configurar(self.cfg.metadatos)
                if self.emitiendo:
                    self._replanificar()
                self._t_previa = 0.0

    def _mirar_biblioteca(self) -> None:
        """
        Las carpetas y las listas pueden cambiar con el programa en marcha. Se
        pide a la biblioteca que las vuelva a mirar (lo hace como mucho una vez
        por minuto) y, si han entrado o salido audios, se vuelve a elegir lo
        que queda de pauta: lo nuevo entra en su rotacion y lo que ya no esta
        sale de ella sin llegar a fallar en antena.
        """
        for o in modconfig.origenes(self.cfg):
            self.bib.listar(o)
        cambios = self.bib.cambios
        if cambios == self._cambios:
            return
        if self.emitiendo and self.planes:
            if self._al_caer():
                return                                    # con un cambio de audio encima, no: despues
            self._replantear()
        self._cambios = cambios

    def _al_caer(self) -> bool:
        """Si lo siguiente de la pauta entra ya: cambiarlo ahora por otro no le daria tiempo a decodificarse."""
        ahora = self.motor.ahora()
        for _, t in self._proximos():
            return t - ahora < self.PREPARAR + 5.0
        return False

    def _vista_previa(self) -> None:
        """
        Parado: la rotacion de lo que queda de hora, como si se empezara a
        emitir ahora mismo. Se rehace cada pocos segundos (el reloj corre y la
        biblioteca puede estar aun analizandose); como elegir no tiene azar,
        la lista no baila: solo se va acortando por el final.
        """
        ahora = time.time()
        pase = Pase(self.sonadas, self.cont_j, self.ultimo_jingle)
        planes = [self.plan.planificar_hora(hora_en_punto(ahora), desde=ahora + 0.25, pase=pase)]
        if ahora >= planes[0].h1 - 300.0:
            planes.append(self.plan.planificar_hora(planes[0].h1, pase=pase))
        self.previa = planes

    def _iniciar(self) -> None:
        if self.emitiendo:
            return
        self.emitiendo = True
        self.previa = []
        self.planes = []
        self.ib = 0
        self.cont_j = 0
        self.actual = None
        self.jingle_actual = None
        self._saltos = self.motor.saltos
        self._cambios = self.bib.cambios                  # la pauta se hace ahora, con lo que hay
        self.registro.escribir(self.motor.ahora(), "sistema", N_("Comienza la emisión"))

    def _detener(self) -> None:
        if not self.emitiendo:
            return
        self.emitiendo = False
        fs = self.motor.fs
        self.motor.orden("vaciar", self.motor.m, int(0.4 * fs))
        for plan in self.planes:
            self._soltar_plan(plan)
        self.planes = []
        self.ib = 0
        self.sonando = []
        self.actual = None
        self.jingle_actual = None
        self.rot.guardar()
        self.registro.escribir(self.motor.ahora(), "sistema", N_("Emisión detenida"))

    # ============================================================ planes

    def _bloque(self):
        """El bloque de la pauta en el que esta el cursor (None si aun no hay mas plan)."""
        while self.planes:
            p = self.planes[0]
            if self.ib < len(p.bloques):
                return p.bloques[self.ib]
            if len(self.planes) < 2:
                return None
            self.planes.pop(0)                            # cambio de hora
            self.ib = 0
        return None

    def _siguiente_bloque(self):
        if not self.planes:
            return None
        p = self.planes[0]
        if self.ib + 1 < len(p.bloques):
            return p.bloques[self.ib + 1]
        if len(self.planes) > 1 and self.planes[1].bloques:
            return self.planes[1].bloques[0]
        return None

    def _asegurar_planes(self) -> None:
        ahora = self.motor.ahora()
        if not self.planes:
            self.planes = [self.plan.planificar_hora(hora_en_punto(ahora), desde=ahora + 0.25,
                                                     llenar=False)]
            self.ib = 0
            self._replantear()
            self._avisos_plan(self.planes[0])
        if len(self.planes) < 2 and ahora >= self.planes[-1].h1 - 300.0:
            self._planificar_siguiente()
        if ahora - self._t_rehacer > 3.0 and any(p.incompleto for p in self.planes):
            # algo estaba sin analizar cuando se planifico: se vuelve a intentar
            self._t_rehacer = ahora
            if self.planes[0].incompleto:
                self._replanificar()
            elif len(self.planes) > 1:
                self._planificar_siguiente()

    def _planificar_siguiente(self) -> None:
        actual = self.planes[0]
        for viejo in self.planes[1:]:
            self._soltar_plan(viejo)
        nuevo = self.plan.planificar_hora(actual.h1, pase=self._pase_anclas([actual]), llenar=False)
        self.planes[1:] = [nuevo]
        # el ultimo tramo de esta hora acaba donde empieza la siguiente
        if actual.bloques and nuevo.bloques and isinstance(actual.bloques[-1], Tramo):
            ult, primero = actual.bloques[-1], nuevo.bloques[0]
            tipo = "cruce" if isinstance(primero, AnclaCruce) else "fundido"
            if abs(ult.fin - primero.t) > 1e-3 or ult.fin_tipo != tipo:
                ult.fin, ult.fin_tipo = primero.t, tipo
                self._replantear()
                self._avisos_plan(nuevo)
                return
        self._replantear(solo_siguiente=True)
        self._avisos_plan(nuevo)

    def _avisos_plan(self, plan) -> None:
        for a in plan.avisos:
            self._aviso(a)

    @staticmethod
    def _pase_anclas(planes, estados=(PLAN, PREP, PROG)) -> Pase:
        """
        Pase para planificar las anclas de una hora. La musica de `planes` que
        aun no ha sonado sigue en su cola: sin contarla, el relleno de un
        bloque nuevo repetiria el de otro que todavia esta por salir. Con los
        jingles pasa lo mismo.
        """
        pase = Pase()
        for plan in planes:
            for b in plan.bloques:
                for it in (b.canciones if isinstance(b, Tramo) else b.piezas):
                    if it.tipo in ("cancion", "relleno") and it.estado in estados:
                        pase.planeadas.append(it.pista.ruta)
                    elif it.tipo in ("jingle", "jingle_publi") and it.estado in estados:
                        pase.ocupados.append(it.pista.ruta)
                    j = getattr(it, "jingle", None)       # el del cruce de salida de una cancion
                    if j is not None and j.estado in estados:
                        pase.ocupados.append(j.pista.ruta)
        return pase

    def _poner_hora(self, b: Tramo) -> None:
        """Pasa a hora de reloj el punto de partida de un tramo, que se lleva en frames."""
        if b.ic > 0:
            cab = b.canciones[b.ic - 1]
            cab.t_ini = self.motor.wall_de(cab.f_ini)
        elif b.f_base is not None:
            b.ini = self.motor.wall_de(b.f_base)
        elif b.inmediato:
            b.ini = self.motor.ahora() + 0.3

    def _replantear(self, solo_siguiente: bool = False) -> None:
        """
        Vuelve a elegir canciones para todo lo que aun no se ha entregado al
        motor, de aqui en adelante y en orden, para que nada se repita.
        """
        pase = Pase(self.sonadas, self.cont_j, self.ultimo_jingle)
        # lo que ya ha sonado esta descontado de su rotacion; lo que esta en la pauta sin
        # haber salido, no: se apunta aqui para que no se vuelva a elegir
        for plan in self.planes:
            for b in plan.bloques:
                if not isinstance(b, Tramo):
                    for it in b.piezas:
                        if it.estado not in (PLAN, PREP, PROG):
                            continue
                        if it.tipo in ("jingle", "jingle_publi"):
                            pase.ocupados.append(it.pista.ruta)
                        elif it.tipo == "relleno":
                            pase.planeadas.append(it.pista.ruta)  # por si sale de la carpeta de las canciones
        for ip, plan in enumerate(self.planes):
            for b in plan.bloques[(self.ib if ip == 0 else 0):]:
                if not isinstance(b, Tramo):
                    continue
                for c in b.canciones[:max(0, b.ic - 1)]:
                    if c.jingle is not None and c.jingle.estado == PROG:
                        # el del cruce recien entregado al motor, que aun no ha empezado a sonar
                        pase.ocupados.append(c.jingle.pista.ruta)
                        pase.ultimo_jingle = c.jingle.pista.ruta
                if solo_siguiente and ip == 0:            # esta hora se queda como esta
                    for c in b.canciones:
                        pase.vistos.append(c.pista.ruta)
                        if c.estado in (PLAN, PREP, PROG):
                            pase.planeadas.append(c.pista.ruta)
                    for c in b.canciones[max(0, b.ic - 1):-1]:    # los cruces que le quedan
                        if c.jingle is not None:
                            pase.ocupados.append(c.jingle.pista.ruta)
                            pase.cont_j, pase.ultimo_jingle = 0, c.jingle.pista.ruta
                        else:
                            pase.cont_j += 1
                    continue
                for c in b.canciones[:b.ic]:
                    pase.vistos.append(c.pista.ruta)
                    if c.estado in (PLAN, PREP, PROG):
                        pase.planeadas.append(c.pista.ruta)
                self._poner_hora(b)
                self.plan.elegir(b, pase)
                self._ajustar(b, rellenar=False)
                b.reintento = self.motor.ahora()

    def _ajustar(self, b: Tramo, rellenar: bool = True) -> None:
        """El reajuste: reparte lo que sobra entre las canciones que quedan del tramo."""
        self._poner_hora(b)
        tope = None
        if b.ic > 0:
            cab = b.canciones[b.ic - 1]
            tope = max(0.0, cab.t_ini + cab.avance - (self.motor.ahora() + 0.3))
        self.plan.ajustar(b, tope)
        while self.plan.sobra_ultima(b):
            self.plan.ajustar(b, tope)
        self.plan.horario(b)
        if rellenar and b.desajuste < -TOL_FALTA:
            ahora = self.motor.ahora()
            if ahora - b.reintento > 2.0:                 # falta musica: a por mas
                b.reintento = ahora
                self._replantear()

    def _soltar_item(self, it) -> None:
        if it is not None and it.fuente is not None and it.estado in (PLAN, PREP):
            it.fuente.cerrar()
            it.fuente = None
            it.estado = PLAN

    def _soltar_plan(self, plan) -> None:
        """Cierra los decodificadores de lo que estaba preparado y ya no va a sonar."""
        for b in plan.bloques:
            if isinstance(b, Tramo):
                for c in b.canciones:
                    self._soltar_item(c)
                    self._soltar_item(c.jingle)
            else:
                for it in b.piezas:
                    self._soltar_item(it)

    def _soltar_resto(self, b: Tramo) -> None:
        """Llega el ancla: lo que quedara sin entregar de este tramo ya no entra."""
        for c in b.canciones[b.ic:]:
            self._soltar_item(c)
            self._soltar_item(c.jingle)
        del b.canciones[b.ic:]
        if b.ic > 0:
            cab = b.canciones[b.ic - 1]
            self._soltar_item(cab.jingle)
            cab.jingle = None
            cab.extra = 0.0

    def _replanificar(self) -> None:
        """
        Rehace la pauta desde ahora (ha cambiado la configuracion, o el reloj
        ha dado un salto). Lo que ya esta en el motor sigue su curso.
        """
        b = self._bloque()
        cab = None
        base = None
        if isinstance(b, Tramo):
            if b.ic > 0:
                cab = b.canciones[b.ic - 1]
            elif b.f_base is not None:
                base = b.f_base                           # hay un ancla sonando: se respeta
        desde = self.motor.ahora() + 0.25
        if base is not None:
            desde = max(desde, self.motor.wall_de(base))
        pase = self._pase_anclas(self.planes, (PROG,))    # de lo viejo solo sonara lo que ya esta en el motor
        for plan in self.planes:
            self._soltar_plan(plan)
        plan = self.plan.planificar_hora(hora_en_punto(desde), desde=desde, pase=pase, llenar=False)
        if plan.bloques and isinstance(plan.bloques[0], Tramo):
            t = plan.bloques[0]
            if cab is not None:
                t.canciones = [cab]
                t.ic = 1
                t.f_base = cab.f_ini
                t.inmediato = False
            elif base is not None:
                t.f_base = base
                t.inmediato = False
        self.planes = [plan]
        self.ib = 0
        self._replantear()
        self._avisos_plan(plan)

    # ============================================================ entrega al motor

    def _ganancia(self, it) -> float:
        mz = self.cfg.mezcla
        db = it.pista.ganancia_db(mz.objetivo_lufs) if mz.normalizar else 0.0
        if it.tipo in ("cancion", "relleno"):
            db += mz.gan_canciones
        elif it.tipo in ("jingle", "jingle_publi"):
            db += mz.gan_jingles
        elif it.tipo == "cuna":
            db += mz.gan_cunas
        else:
            db += mz.gan_senales
        return 10.0 ** (db / 20.0)

    def _preparar_item(self, it) -> None:
        if it.fuente is not None:
            return
        p = it.pista
        it.fuente = FuenteFFmpeg(self.ffmpeg, p.ruta, p.cue_in, p.cue_out, self.motor.fs, self.soxr)
        it.fuente.preparar()
        if it.estado == PLAN:
            it.estado = PREP

    def _lanzar(self, it, frame: int, musica: bool = False) -> None:
        self._preparar_item(it)
        fs = self.motor.fs
        v = Voz(it.fuente, frame, self._ganancia(it))
        it.voz = v
        it.f_ini = frame
        it.t_ini = self.motor.wall_de(frame)
        it.estado = PROG
        self.items[v.id] = it
        self.motor.orden("voz", v)
        if it.suena is not None:                          # pieza que se corta: fundido al final
            n = max(1, int(round(it.fundido * fs)))
            self.motor.orden("fundir", v.id, frame + int(round(it.suena * fs)) - n, n, 1.5)
        if musica:
            self.sonando.append(it)

    def _fundido_salida(self, c, f_out: int) -> None:
        """Funde la cancion que sale a partir de su punto de cruce."""
        if c.voz is None or getattr(c, "saliendo", False):
            return
        mz = self.cfg.mezcla
        fs = self.motor.fs
        p = c.pista
        queda = p.largo - (f_out - c.f_ini) / float(fs)   # audio que le queda al llegar al cruce
        if queda <= 0.02:
            return
        cola = max(0.0, p.largo - self.plan.avance(p)) if c.tipo == "cancion" else queda
        if queda <= cola + 0.05:
            dur, exp = queda, 1.0                         # final natural: solo se le acompana
        else:
            dur, exp = min(queda, max(mz.crossfade, cola)), 2.0
        c.saliendo = True
        self.motor.orden("fundir", c.voz.id, f_out, int(dur * fs), exp)

    def _callar(self, frame: int) -> None:
        """Antes de un ancla: lo que suene baja y llega a silencio justo en `frame`."""
        fs = self.motor.fs
        fundido = max(0.05, self.cfg.senales.fundido)
        for it in self.sonando:
            if it.voz is None:
                continue
            fin_nat = it.f_ini + int(round(it.pista.largo * fs))
            if fin_nat <= frame:
                continue                                  # acaba sola antes
            corte = (fin_nat - frame) / float(fs)         # lo que se le quita
            dur = min(fundido, max(0.03, 4.0 * corte))    # si es una pizca, el fundido tambien
            n = int(dur * fs)
            self.motor.orden("fundir", it.voz.id, frame - n, n, 1.6)
            it.saliendo = True
            if isinstance(it, Cancion) and corte > 0.3:
                it.nota = tr("cortada %.1f s antes") % corte

    def _av_ancla(self, b: Tramo) -> int:
        fs = self.motor.fs
        if b.fin_tipo == "fundido":
            return int((max(0.0, self.cfg.senales.fundido) + self.MARGEN_ANCLA) * fs)
        return int(self.AVANCE * fs)

    def _base_siguiente(self, frame: int) -> None:
        """La musica vuelve en `frame`: se le dice al tramo que viene."""
        sig = self._siguiente_bloque()
        if isinstance(sig, Tramo):
            sig.f_base = frame
            sig.ini = self.motor.wall_de(frame)
            sig.inmediato = False

    def _programar(self) -> None:
        for _ in range(200):
            b = self._bloque()
            if b is None:
                return
            if isinstance(b, Tramo):
                sigue = self._programar_tramo(b)
            elif isinstance(b, AnclaCruce):
                sigue = self._programar_cruce(b)
            elif isinstance(b, AnclaBloque):
                sigue = self._programar_bloque(b)
            else:
                sigue = self._programar_audio(b)
            if not sigue:
                return

    def _programar_tramo(self, b: Tramo) -> bool:
        motor = self.motor
        fs = motor.fs
        m = motor.m
        av = int(self.AVANCE * fs)
        if motor.frame_de(b.fin) - m <= self._av_ancla(b):
            self._soltar_resto(b)                         # llega el ancla: ella calla lo que suene
            self.ib += 1
            return True

        if b.ic == 0:                                     # --- la primera del tramo
            if not b.canciones:
                ahora = motor.ahora()
                if ahora - b.reintento > 1.0:
                    b.reintento = ahora
                    self._replantear()
                    if not b.canciones and b.fin - ahora > TOL_FALTA:
                        fr = b.franja
                        if self.bib.pendiente(fr.canciones) or self.bib.pendientes():
                            self._aviso(tr("Analizando la biblioteca: la música empezará enseguida"))
                        else:
                            self._aviso(tr("No hay canciones que emitir en «%s»: revisa su carpeta o lista")
                                        % modconfig.nombre_franja(fr.nombre))
                if not b.canciones:
                    return False
            c = b.canciones[0]
            self._preparar_item(c)
            if c.fuente.error:
                self._fuente_rota(c)
                return True
            de_golpe = b.f_base is None and b.inmediato
            if b.f_base is not None:
                frame = b.f_base
            elif b.inmediato:
                if not c.fuente.lista() and not motor.simulado:
                    return False                          # aun no hay audio decodificado
                frame = m + int(0.2 * fs)
            else:
                frame = motor.frame_de(b.ini)
            if frame - m > av:
                return False
            frame = max(frame, m + 64)
            self._lanzar(c, frame, musica=True)
            b.f_base = frame
            b.ic = 1
            if de_golpe:
                self._replantear()                        # ahora que se sabe cuando ha empezado de verdad
            else:
                self._ajustar(b)
            return True

        cab = b.canciones[b.ic - 1]
        self._ajustar(b)
        if b.ic >= len(b.canciones):
            return False                                  # es la ultima: se espera al ancla
        f_out = cab.f_ini + int(round((cab.avance - cab.recorte) * fs))
        if f_out - m > av:
            return False
        sig = b.canciones[b.ic]
        self._preparar_item(sig)
        if sig.fuente.error:
            self._fuente_rota(sig)
            return True
        self._transicion(b, cab, sig, max(f_out, m + 64))
        b.ic += 1
        self._ajustar(b)
        return True

    def _transicion(self, b: Tramo, cab: Cancion, sig: Cancion, f_out: int) -> None:
        """El cruce: sale `cab`, entra `sig`, y encima el jingle si lo hay."""
        mz = self.cfg.mezcla
        fs = self.motor.fs
        if cab.salto:
            cab.saliendo = True                           # ya la fundio el salto
        else:
            self._fundido_salida(cab, f_out)
        j = cab.jingle
        if j is not None:
            self._preparar_item(j)
            if j.fuente.error:
                self._aviso(tr("No se puede reproducir el jingle %s") % j.pista.nombre())
                self.vetadas[j.pista.ruta] = time.monotonic() + 600.0
                j = None
        f_sig = f_out
        if j is not None:
            self._lanzar(j, f_out, musica=True)
            f_sig = f_out + int(round(cab.extra * fs))
            self.cont_j = 0
        else:
            self.cont_j += 1
        self._lanzar(sig, f_sig, musica=True)
        if j is not None and b.franja.jingles_modo != "entre" and mz.atenuacion_jingle > 0.05:
            # la cancion entra por debajo del jingle y sube cuando este acaba
            f_fin = f_out + int(round(j.pista.largo * fs))
            rampa = int(0.7 * fs)
            if f_fin - f_sig > rampa:
                nivel = 10.0 ** (-mz.atenuacion_jingle / 20.0)
                self.motor.orden("duck", sig.voz.id, f_sig, f_sig + 1, f_fin - rampa, f_fin, nivel)

    def _programar_cruce(self, a: AnclaCruce) -> bool:
        """Hora en punto sin senal: la que suena cruza con la primera de la hora nueva."""
        motor = self.motor
        frame = motor.frame_de(a.t)
        if frame - motor.m > int(self.AVANCE * motor.fs):
            return False
        frame = max(frame, motor.m + 64)
        for it in self.sonando:
            if isinstance(it, Cancion):
                self._fundido_salida(it, frame)
        self._base_siguiente(frame)
        self.ib += 1
        return True

    def _programar_audio(self, a: AnclaAudio) -> bool:
        """Senal horaria o evento: la musica calla y el audio arranca en su frame exacto."""
        motor = self.motor
        fs = motor.fs
        frame = motor.frame_de(a.t)
        antes = int((max(0.0, self.cfg.senales.fundido) + self.MARGEN_ANCLA) * fs)
        if frame - motor.m > antes:
            return False
        tarde = (motor.m - frame) / float(fs)
        frame = max(frame, motor.m + 64)
        self._callar(frame)
        if tarde > (0.3 if a.clase == "senal" else 30.0):
            # una senal horaria fuera de hora es peor que ninguna (pasa si se
            # empieza a emitir justo cuando ya tenia que estar sonando)
            self._aviso(tr("%s omitida: llegaba %.1f s tarde") % (a.nombre or tr("Señal"), tarde))
            for it in a.piezas:
                self._soltar_item(it)
            self._base_siguiente(frame)
            self.ib += 1
            return True
        for it in a.piezas:
            self._lanzar(it, frame + int(round(it.desfase * fs)))
        self._base_siguiente(frame + int(round(a.dur * fs)))
        self.ib += 1
        return True

    def _programar_bloque(self, a: AnclaBloque) -> bool:
        """Bloque de publicidad / desconexion entero: silencios, jingle, contenido y CUE."""
        motor = self.motor
        fs = motor.fs
        frame = motor.frame_de(a.t)                       # aqui empieza el silencio previo
        antes = int((max(0.0, self.cfg.senales.fundido) + self.MARGEN_ANCLA) * fs)
        if frame - motor.m > antes:
            return False
        frame = max(frame, motor.m + 64)
        a.t = motor.wall_de(frame)
        self._callar(frame)
        for it in a.piezas:
            self._preparar_item(it)
            if it.fuente.error:
                self._aviso(tr("No se puede reproducir %s") % it.pista.nombre())
                it.estado = ERROR
                continue
            self._lanzar(it, frame + int(round(it.desfase * fs)))
        self._base_siguiente(frame + int(round(a.dur * fs)))
        self.historial.append(a)
        if a.cfg.cue and self.cfg.cue.activo:
            self._cues(a, frame)
        self.ib += 1
        return True

    def _cues(self, a: AnclaBloque, frame: int) -> None:
        motor = self.motor
        fs = motor.fs
        adelanto = self.cfg.cue.adelanto_ms / 1000.0
        f1 = frame + int(round(a.o_cue1 * fs))
        f2 = frame + int(round(a.o_cue2 * fs))
        t1, t2 = motor.wall_de(f1), motor.wall_de(f2)
        comun = dict(emisora=self.cfg.emisora, bloque=a.nombre, duracion=float(t2 - t1),
                     contenido=float(a.n), silencio=float(a.cfg.silencio_despues))
        d1 = modcue.variables(modconfig.CUE_BREAK, t1, **comun)
        d2 = modcue.variables(modconfig.CUE_ENDBREAK, t2, **comun)
        if self.cues is not None:
            self.cues.programar(t1 - adelanto, "inicio", d1)
            self.cues.programar(t2 - adelanto, "retorno", d2)
        for d in self.cfg.cue.destinos:                   # los DTMF van dentro del audio
            if d.activo and d.tipo == "dtmf":
                for f, plantilla, datos in ((f1, d.inicio, d1), (f2, d.retorno, d2)):
                    tonos = modcue.tonos_dtmf(modcue.componer(plantilla, datos), fs)
                    if len(tonos):
                        self.motor.orden("voz", Voz(FuenteMemoria(tonos),
                                                    f - int(round(adelanto * fs))))

    # ============================================================ lo que va pasando

    def _eventos(self) -> None:
        ev = self.motor.eventos
        while True:
            try:
                tipo, vid, f = ev.popleft()
            except IndexError:
                return
            it = self.items.get(vid)
            if it is None:
                continue
            if tipo == "inicio":
                if abs(f - it.f_ini) > 480:               # arranco tarde: su cadena se mueve con ella
                    it.f_ini = f
                it.t_ini = self.motor.wall_de(f)
                it.estado = AIRE
                self._al_aire(it)
            else:
                del self.items[vid]
                self._terminado(it, f)

    def _al_aire(self, it) -> None:
        p = it.pista
        if it.origen:
            self.rot.consumir(it.origen, it.orden, p.ruta)
        if it.tipo in ("cancion", "relleno"):             # el relleno puede salir de la carpeta de las canciones
            self.sonadas.append(p.ruta)
        self.historial.append(it)
        if it.tipo in PRINCIPALES:
            self.actual = it
        else:
            self.jingle_actual = it
            self.ultimo_jingle = p.ruta
        self.registro.escribir(it.t_ini, it.tipo, p.titulo or p.nombre(), p.artista,
                               it.dur, it.nota, p.ruta)
        if self.titulo is not None:
            self.titulo.anunciar(it.tipo, p.titulo or p.nombre(), p.artista, self.cfg.emisora)

    def _terminado(self, it, f: int) -> None:
        nunca = it.estado != AIRE
        it.estado = ERROR if nunca else FIN
        if it.fuente is not None:
            it.fuente.cerrar()
        if it in self.sonando:
            self.sonando.remove(it)
        if it is self.jingle_actual:
            self.jingle_actual = None
        if nunca and self.emitiendo:
            self._aviso(tr("No se ha podido reproducir %s") % it.pista.nombre())
            self.vetadas[it.pista.ruta] = time.monotonic() + 600.0
        b = self._bloque() if self.emitiendo else None
        if isinstance(b, Tramo) and b.ic > 0 and b.canciones[b.ic - 1] is it:
            fs = self.motor.fs
            previsto = it.f_ini + int(round((it.avance - it.recorte) * fs))
            if previsto - f > fs:
                # se ha acabado antes de lo que decia su analisis (fichero cambiado
                # o danado): la siguiente entra ya
                sonado = max(0.05, (f - it.f_ini) / float(fs))
                it.avance = it.lleno = sonado
                it.recorte = 0.0
                self._replantear()

    def _fuente_rota(self, it) -> None:
        """Un audio de la pauta que no se deja decodificar: fuera, y a elegir otro."""
        self._aviso(tr("No se puede reproducir %s") % it.pista.nombre())
        self.vetadas[it.pista.ruta] = time.monotonic() + 600.0
        self._soltar_item(it)
        it.estado = ERROR
        for plan in self.planes:
            for b in plan.bloques:
                if isinstance(b, Tramo):
                    if it in b.canciones[b.ic:]:
                        b.canciones.remove(it)
                    for c in b.canciones:
                        if c.jingle is it:
                            c.jingle = None
                            c.extra = 0.0
        self._replantear()

    def _saltar(self) -> None:
        """Salto manual: la cancion que suena se funde ya y entra la siguiente."""
        b = self._bloque()
        if not self.emitiendo or not isinstance(b, Tramo) or b.ic == 0:
            return
        cab = b.canciones[b.ic - 1]
        if cab.estado != AIRE or cab.salto:
            return
        fs = self.motor.fs
        frame = self.motor.m + int(0.3 * fs)
        sonado = (frame - cab.f_ini) / float(fs)
        if cab.avance - cab.recorte - sonado < self.AVANCE + 0.5:
            return                                        # ya estaba saliendo
        self._soltar_item(cab.jingle)
        cab.jingle = None
        cab.extra = 0.0
        cab.avance = cab.lleno = max(0.05, sonado)
        cab.recorte = 0.0
        cab.salto = True
        cab.dur = sonado
        self.motor.orden("fundir", cab.voz.id, frame,
                         int(max(0.1, self.cfg.mezcla.fundido_salto) * fs), 1.5)
        self._replantear()

    def _vigilar(self) -> None:
        motor = self.motor
        if motor.simulado:
            return
        if motor.saltos != self._saltos:                  # el reloj ha dado un brinco
            self._saltos = motor.saltos
            self._aviso(tr("El reloj ha dado un salto: se rehace la pauta"))
            self._replanificar()
        if motor.abierta() and not motor.viva():
            ahora = time.monotonic()
            if ahora - self._t_reabrir > 6.0 and self.reabrir is not None:
                self._t_reabrir = ahora
                self._aviso(tr("La salida de audio no responde: se intenta reabrir"))
                try:
                    self.reabrir()
                except Exception as e:
                    self._aviso(tr("No se pudo reabrir la salida: %s") % e)

    # ============================================================ preparar

    def _proximos(self):
        """Los audios que vienen, en orden, con su hora prevista."""
        for ip, plan in enumerate(self.planes):
            for b in plan.bloques[(self.ib if ip == 0 else 0):]:
                if isinstance(b, Tramo):
                    if b.ic > 0:
                        cab = b.canciones[b.ic - 1]
                        if cab.jingle is not None:
                            yield cab.jingle, cab.t_ini + cab.dur
                    for c in b.canciones[b.ic:]:
                        yield c, c.t_ini
                        if c.jingle is not None:
                            yield c.jingle, c.t_ini + c.dur
                else:
                    for it in b.piezas:
                        yield it, b.t + it.desfase

    def _preparar(self) -> None:
        """Arranca con tiempo los decodificadores de lo que esta al caer."""
        ahora = self.motor.ahora()
        n = 0
        for it, t in self._proximos():
            if t - ahora > self.PREPARAR and n >= 3:
                break
            n += 1
            if it.estado == PLAN and it.fuente is None:
                self._preparar_item(it)
            elif (it.estado == PREP and it.fuente is not None and it.fuente.error
                  and it.tipo in ("cancion", "jingle")):
                self._fuente_rota(it)
                return
            if n >= 14:
                break

    # ============================================================ foto para la interfaz

    @staticmethod
    def _fila(it) -> dict:
        p = it.pista
        nota = it.nota
        if isinstance(it, Cancion):
            if it.salto:
                nota = tr("saltada")
            elif not nota and it.recorte > 0.25:
                nota = (tr("se cortará %.1f s antes") if it.ultima else tr("cruce adelantado %.1f s")) % it.recorte
            if it.jingle is not None:
                nota = (nota + " · " if nota else "") + tr("jingle encima del cruce")
        return {"t": it.t_ini, "tipo": it.tipo, "titulo": p.titulo or p.nombre(),
                "artista": p.artista, "dur": it.dur, "estado": it.estado, "nota": nota}

    @staticmethod
    def _filas_bloque(a: AnclaBloque, ahora: float) -> list:
        """Lo que no es audio de un bloque: silencios y CUE."""
        def fila(desfase, tipo, titulo, dur=0.0):
            t = a.t + desfase
            estado = FIN if t + dur <= ahora else (AIRE if t <= ahora else PLAN)
            return {"t": t, "tipo": tipo, "titulo": titulo, "artista": "", "dur": dur,
                    "estado": estado, "nota": a.nombre}
        filas = []
        if a.o_jingle > 0.01:
            filas.append(fila(0.0, "silencio", tr("Silencio"), a.o_jingle))
        if a.cfg.cue:
            filas.append(fila(a.o_cue1, "cue", tr("CUE de desconexión")))
            filas.append(fila(a.o_cue2, "cue", tr("CUE de reconexión")))
        if a.o_salida - a.o_fin > 0.01:
            filas.append(fila(a.o_fin, "silencio", tr("Silencio"), a.o_salida - a.o_fin))
        return filas

    def _fotografiar(self) -> dict:
        motor = self.motor
        ahora = motor.ahora() if self.emitiendo else time.time()
        foto = {"emitiendo": self.emitiendo, "ahora": ahora, "pauta": [], "actual": None,
                "jingle": None, "ancla": None, "franja": "", "h0": hora_en_punto(ahora),
                "avisos": [{"t": t, "texto": x} for t, x in self.avisos],
                "analizando": self.bib.pendientes(), "secos": motor.secos,
                "cortes": motor.cortes,
                "cues": list(self.cues.enviados)[-6:] if self.cues is not None else []}
        planes = self.planes if self.emitiendo else self.previa
        ib = self.ib if self.emitiendo else 0
        h0 = planes[0].h0 if planes else foto["h0"]
        foto["h0"] = h0
        foto["h1"] = h0 + 3600.0
        foto["franja"] = modconfig.nombre_franja(planes[0].franja.nombre) if planes else ""
        filas = []
        if self.emitiendo:
            for x in self.historial:
                if isinstance(x, AnclaBloque):
                    if x.t + x.dur >= h0 - 1.0:
                        filas += self._filas_bloque(x, ahora)
                elif x.t_ini >= h0 - 30.0 and x.tipo != "jingle":
                    filas.append(self._fila(x))
        ancla = None
        for ip, plan in enumerate(planes):
            for b in plan.bloques[(ib if ip == 0 else 0):]:
                if isinstance(b, Tramo):
                    for c in b.canciones:
                        if c.estado in (PLAN, PREP, PROG):
                            filas.append(self._fila(c))
                    continue
                if ancla is None and not isinstance(b, AnclaCruce):
                    ancla = {"t": b.t, "clase": b.clase, "nombre": getattr(b, "nombre", "")}
                if isinstance(b, AnclaBloque):
                    filas += self._filas_bloque(b, ahora)
                for it in b.piezas:
                    if it.estado in (PLAN, PREP, PROG):
                        f = self._fila(it)
                        f["t"] = b.t + it.desfase
                        filas.append(f)
        filas.sort(key=lambda f: f["t"])
        foto["pauta"] = filas
        foto["ancla"] = ancla
        if not self.emitiendo:
            return foto
        if self.actual is not None:
            a = self._fila(self.actual)
            a["sonando"] = self.actual.estado == AIRE
            foto["actual"] = a
        if self.jingle_actual is not None and self.jingle_actual.estado == AIRE:
            foto["jingle"] = self._fila(self.jingle_actual)
        return foto
