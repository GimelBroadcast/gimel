# -*- coding: utf-8 -*-
"""
Planificador: la pauta de una hora, cuadrada al segundo.

Una hora se compone de ANCLAS y TRAMOS:

    ancla   algo que ocurre a una hora de reloj exacta: la senal horaria, un
            bloque de publicidad / desconexion, un evento a minuto fijo
    tramo   la musica que hay entre dos anclas

Cada tramo tiene que durar exactamente lo que hay entre sus dos anclas, y se
cuadra en dos pasos:

 1. ELEGIR. Las canciones salen de la rotacion en su orden, salvo las dos o
    tres ultimas del tramo: esas se escogen, de entre las proximas de la cola,
    buscando la combinacion cuya suma mas se acerca por arriba al hueco que
    queda. Con una biblioteca normal el sobrante baja de un segundo.

 2. RECORTAR. Lo que sobre se reparte a partes iguales entre las canciones del
    tramo adelantando su cruce con la siguiente (con un tope por cancion). Si
    aun asi sobra, lo paga la ultima: la corta el fundido previo al ancla.

Todo aqui va en segundos y horas de reloj; el emisor lo pasa a frames. No hay
nada aleatorio: con la misma rotacion y las mismas horas sale el mismo plan,
asi que replanificar no baraja lo que ya se habia anunciado.
"""

import itertools
import math
from collections import deque
from datetime import datetime

import numpy as np

from .idioma import tr

PLAN, PREP, PROG, AIRE, FIN, ERROR = "plan", "prep", "prog", "aire", "fin", "error"

TOL_FALTA = 3.0               # hueco al final de un tramo que no merece otra cancion
MIN_BLOQUE = 5.0              # un bloque al que le quedan menos segundos que esto no sale
MIN_TROZO = 8.0               # una cuna cortada que fuera a sonar menos que esto no entra
FUNDIDO_CUNA = 1.0            # fundido de una cuna cortada


def hora_en_punto(t: float) -> float:
    """Comienzo (epoch) de la hora local en la que cae t."""
    d = datetime.fromtimestamp(t)
    return float(round(t - (d.minute * 60 + d.second + d.microsecond / 1e6)))


class Item:
    """Un audio de la pauta y lo que el emisor va sabiendo de el."""

    def __init__(self, tipo: str, pista, origen: str = "", orden: str = ""):
        self.tipo = tipo              # cancion | jingle | senal | evento | cuna | relleno | jingle_publi
        self.pista = pista
        self.origen = origen          # de que carpeta sale, para apuntarlo en su rotacion
        self.orden = orden
        self.t_ini = 0.0              # hora prevista de arranque
        self.dur = 0.0                # lo que suena hasta que entra lo siguiente
        self.f_ini = None             # frame de mezcla, cuando ya esta entregado al motor
        self.estado = PLAN
        self.fuente = None
        self.voz = None
        self.nota = ""
        self.desfase = 0.0            # piezas de un ancla: segundos desde su comienzo
        self.suena = None             # si se corta: cuanto suena (None = entera)
        self.fundido = 0.0            # fundido final cuando se corta


class Cancion(Item):
    def __init__(self, pista, avance: float, origen: str = "", orden: str = ""):
        super().__init__("cancion", pista, origen, orden)
        self.avance = avance          # de su arranque a su punto de mezcla natural
        self.lleno = pista.largo      # entera, hasta que deja de sonar
        self.recorte = 0.0            # segundos que se adelanta su salida
        self.jingle = None            # Item del jingle de su cruce de salida
        self.extra = 0.0              # tiempo que ese jingle mete antes de la siguiente
        self.ultima = False
        self.salto = False            # la han saltado a mano


class Tramo:
    """Musica entre dos anclas."""

    def __init__(self, ini: float, fin: float, fin_tipo: str, franja):
        self.ini = ini
        self.fin = fin
        self.fin_tipo = fin_tipo      # fundido (la corta el ancla) | cruce (enlaza con la hora siguiente)
        self.franja = franja
        self.canciones = []
        self.ic = 0                   # cuantas estan ya entregadas al motor
        self.f_base = None            # frame en que arranca la primera
        self.inmediato = False        # arrancar ya (al empezar a emitir)
        self.desajuste = 0.0          # >0 sobra (se recorta), <0 falta (silencio al final)
        self.reintento = 0.0


class AnclaAudio:
    """Senal horaria o evento: a la hora t suena esto, con la musica ya bajada."""

    def __init__(self, clase: str, t: float):
        self.clase = clase            # senal | evento
        self.t = t
        self.piezas = []
        self.dur = 0.0                # hasta que vuelve la musica
        self.nombre = ""

    def mover(self, dt: float) -> None:
        self.t += dt


class AnclaCruce:
    """Hora en punto sin senal: la ultima cancion de una hora cruza con la primera de la otra."""

    clase = "cruce"
    dur = 0.0
    piezas = ()

    def __init__(self, t: float):
        self.t = t

    def mover(self, dt: float) -> None:
        self.t += dt


class AnclaBloque:
    """
    Bloque de publicidad / desconexion. Todo son segundos desde t (cuando
    empieza el silencio previo y la musica ya tiene que haber callado):

        t ........ silencio previo ...... o_jingle ... o_contenido ......
        ...... contenido (n segundos EXACTOS) ...... o_fin ... negro ...
        ... o_salida (jingle de vuelta) ... dur (vuelve la musica)

    El CUE de desconexion sale en o_cue1 y el de reconexion en o_cue2.
    """

    clase = "bloque"

    def __init__(self, cfg_bloque, t: float, jingle, jingle_salida, dur_salida: float):
        b = cfg_bloque
        self.cfg = b
        self.nombre = b.nombre
        self.t = t
        self.jingle = jingle                  # Item o None
        self.jingle_salida = jingle_salida
        self.dur_salida = dur_salida
        self.piezas = []
        self.contenido = []
        self.n = float(b.duracion)
        self.cortado = False
        self._offsets()

    def _offsets(self) -> None:
        b = self.cfg
        j = self.jingle.pista.largo if self.jingle else 0.0
        self.o_jingle = max(0.0, b.silencio_antes)
        self.o_contenido = self.o_jingle + j
        self.o_fin = self.o_contenido + self.n
        self.o_salida = self.o_fin + max(0.0, b.silencio_despues)
        self.dur = self.o_salida + (self.dur_salida if self.jingle_salida else 0.0)
        self.o_cue1 = max(0.0, b.cue_tras)
        self.o_cue2 = self.o_fin + max(0.0, b.cue_retorno_tras)

    def fijo(self) -> float:
        """Lo que ocupa el bloque sin contar el contenido."""
        return self.dur - self.n

    def acortar(self, n: float) -> None:
        self.n = n
        self.cortado = True
        self._offsets()

    def mover(self, dt: float) -> None:
        self.t += dt

    def montar(self, contenido: list) -> None:
        """Coloca todas las piezas con su desfase respecto a t."""
        self.contenido = contenido
        self.piezas = []
        if self.jingle:
            self.jingle.desfase = self.o_jingle
            self.piezas.append(self.jingle)
        for it in contenido:
            it.desfase += self.o_contenido
            self.piezas.append(it)
        if self.jingle_salida:
            self.jingle_salida.desfase = self.o_salida
            self.piezas.append(self.jingle_salida)


class PlanHora:
    def __init__(self, h0: float, franja):
        self.h0 = h0
        self.h1 = h0 + 3600.0
        self.franja = franja
        self.bloques = []
        self.incompleto = False       # faltaba algo por analizar: conviene rehacerlo
        self.avisos = []

    def tramos(self):
        return [b for b in self.bloques if isinstance(b, Tramo)]


_COMB = {}


def _combinaciones(w: int, k: int) -> np.ndarray:
    c = _COMB.get((w, k))
    if c is None:
        c = np.array(list(itertools.combinations(range(w), k)), dtype=np.int16)
        _COMB[(w, k)] = c
    return c


def repartir(exceso: float, topes: list):
    """
    Reparte 'exceso' segundos a partes iguales sin pasar del tope de nadie.
    Devuelve (lo que le toca a cada uno, lo que no ha cabido).
    """
    n = len(topes)
    rec = [0.0] * n
    libres = [i for i in range(n) if topes[i] > 1e-6]
    resto = max(0.0, exceso)
    while resto > 1e-9 and libres:
        parte = resto / len(libres)
        llenas = [i for i in libres if topes[i] - rec[i] <= parte]
        if not llenas:
            for i in libres:
                rec[i] += parte
            return rec, 0.0
        for i in llenas:
            resto -= topes[i] - rec[i]
            rec[i] = topes[i]
        libres = [i for i in libres if i not in llenas]
    return rec, max(0.0, resto)


class Pase:
    """
    Lo que se va comprometiendo a lo largo de una pasada de planificacion, que
    puede abarcar varios tramos y dos horas. Hace falta porque la rotacion solo
    descuenta un audio cuando SUENA: lo que esta en la pauta sin haber salido
    sigue en la cola, y sin esta cuenta se volveria a elegir.
    """

    def __init__(self, vistos=(), cont_j: int = 0, ultimo_jingle: str = ""):
        self.vistos = list(vistos)        # lo sonado y lo ya planificado, en orden
        self.planeadas = []               # canciones y relleno en la pauta que aun no han sonado
        self.ocupados = set()             # jingles y piezas ya apalabrados
        self.cont_j = cont_j              # cruces desde el ultimo jingle
        self.ultimo_jingle = ultimo_jingle


class Planificador:
    MARGEN = 0.4             # sobrante que se busca: vale mas recortar medio segundo que quedarse corto
    VENTANA = 48              # canciones de la cola entre las que se escoge el final de un tramo
    LAMBDA = 0.02             # lo que "cuesta", en segundos, sacar una cancion de un puesto mas atras
    PENA_VUELTA = 45.0        # y lo que cuesta repetir una antes de que hayan sonado todas

    def __init__(self, cfg, surtidor):
        self.cfg = cfg
        self.sur = surtidor

    # ------------------------------------------------------------ piezas

    def avance(self, p) -> float:
        mz = self.cfg.mezcla
        return max(0.1, p.mezcla(mz.umbral, mz.solape_max) - p.cue_in)

    def nueva_cancion(self, p, franja) -> Cancion:
        return Cancion(p, self.avance(p), franja.canciones, franja.orden)

    @staticmethod
    def avance_corto(p, umbral: float = -24.0, solape: float = 1.5) -> float:
        """Un jingle o una senal: lo siguiente entra casi al final."""
        return max(0.05, p.mezcla(umbral, solape) - p.cue_in)

    def extra_jingle(self, franja, pj) -> float:
        """Tiempo que pasa entre que sale una cancion y entra la siguiente por culpa del jingle."""
        if pj is None:
            return 0.0
        if franja.jingles_modo == "entre":
            return self.avance_corto(pj)
        return max(0.0, pj.largo - self.cfg.mezcla.solape_jingle)

    def _primero(self, origen: str, orden: str, ocupados):
        """El siguiente audio de una rotacion que no este ya comprometido en el plan."""
        cola = self.sur.cola(origen, orden) if origen else []
        for p in cola:
            if p.ruta not in ocupados:
                return p
        return cola[0] if cola else None

    @staticmethod
    def _sin_planear(cola: list, planeadas: list) -> list:
        """La cola sin lo ya apalabrado: cada audio planeado se lleva su proximo pase."""
        if not planeadas:
            return list(cola)
        quitar = {}
        for r in planeadas:
            quitar[r] = quitar.get(r, 0) + 1
        libres = []
        for p in cola:
            if quitar.get(p.ruta, 0) > 0:
                quitar[p.ruta] -= 1
            else:
                libres.append(p)
        return libres

    # ------------------------------------------------------------ anclas

    def senal_de(self, h: float):
        """(hora a la que arranca el audio, Pista o None, falta analizarla) de la senal de la hora h."""
        cfg = self.cfg
        momento = datetime.fromtimestamp(h + 1)
        franja = cfg.franja_de(momento)
        if not (cfg.senales.activas and franja.senal):
            return h, None, False
        ruta = cfg.senales.archivo_de(momento.hour)
        if not ruta:
            return h, None, False
        p = self.sur.pista(ruta)
        if p is None:
            return h, None, True
        if p.error or p.largo <= 0.05:
            return h, None, False
        s = cfg.senales
        if s.sincronia == "final":
            adelanto = p.largo
        elif s.sincronia == "segundo":
            adelanto = min(max(0.0, s.segundo - p.cue_in), p.largo)
        else:
            adelanto = 0.0
        return h - adelanto, p, False

    def _ancla_senal(self, t: float, p, franja, ocupados) -> AnclaAudio:
        a = AnclaAudio("senal", t)
        a.nombre = tr("Señal horaria")
        it = Item("senal", p)
        a.piezas.append(it)
        a.dur = self.avance_corto(p)
        if franja.jingle_tras_senal and franja.jingles_origen:
            pj = self._primero(franja.jingles_origen, "aleatorio", ocupados)
            if pj is not None:
                j = Item("jingle", pj, franja.jingles_origen, "aleatorio")
                j.desfase = a.dur
                a.piezas.append(j)
                a.dur += self.avance_corto(pj)
                ocupados.add(pj.ruta)
        return a

    def _ancla_evento(self, h0: float, ev, ocupados, plan):
        p = self._primero(ev.origen, ev.orden, ocupados)
        if p is None:
            plan.incompleto |= self.sur.pendiente(ev.origen)
            return None
        ocupados.add(p.ruta)
        a = AnclaAudio("evento", h0 + ev.desfase())
        a.nombre = ev.nombre
        a.piezas.append(Item("evento", p, ev.origen, ev.orden))
        a.dur = self.avance_corto(p)
        return a

    def _ancla_bloque(self, h0: float, b, franja, ocupados, plan):
        jingle = salida = None
        dur_salida = 0.0
        if b.jingle:
            origen = b.jingle_origen or franja.jingles_origen
            pj = self._primero(origen, "aleatorio", ocupados)
            if pj is not None:
                jingle = Item("jingle_publi", pj, origen, "aleatorio")
                ocupados.add(pj.ruta)
            elif origen:
                plan.incompleto |= self.sur.pendiente(origen)
        if b.jingle_salida:
            origen = b.jingle_salida_origen or franja.jingles_origen
            pj = self._primero(origen, "aleatorio", ocupados)
            if pj is not None:
                salida = Item("jingle_publi", pj, origen, "aleatorio")
                dur_salida = self.avance_corto(pj)
                ocupados.add(pj.ruta)
        a = AnclaBloque(b, 0.0, jingle, salida, dur_salida)
        programada = h0 + b.desfase()
        if b.referencia == "silencio":
            a.t = programada
        elif b.referencia == "contenido":
            a.t = programada - a.o_contenido
        else:
            a.t = programada - a.o_jingle
        return a

    def _contenido(self, b, n: float, plan, pase: "Pase") -> list:
        """Las piezas del contenido de un bloque, con su desfase desde que empieza el contenido."""
        if b.contenido == "relleno":
            piezas = self._relleno(b.relleno_origen, 0.0, n, pase)
            if not piezas and b.relleno_origen:
                plan.incompleto |= self.sur.pendiente(b.relleno_origen)
            return piezas
        cola = self.sur.cola(b.origen, b.orden) if b.origen else []
        if not cola and b.origen:
            plan.incompleto |= self.sur.pendiente(b.origen)
        elegidas = self._elegir_cunas(cola, n, b.orden)
        suma = sum(p.largo for p in elegidas)
        hueco = n - suma
        piezas = []
        pausa = 0.0
        if 0.05 < hueco < 3.0 and elegidas:               # se reparte en respiros entre cunas
            pausa = hueco / len(elegidas)
            hueco = 0.0
        t = 0.0
        for p in elegidas:
            it = Item("cuna", p, b.origen, b.orden)
            it.desfase = t
            it.dur = p.largo
            piezas.append(it)
            t += p.largo + pausa
        if hueco > 0.05:
            t = suma
            if b.sobrante == "cortar" and cola and hueco >= MIN_TROZO:
                # mas cunas, repitiendo si hace falta; la ultima se corta al llegar
                usadas = {p.ruta for p in elegidas}
                resto = [p for p in cola if p.ruta not in usadas] or list(cola)
                i = 0
                while n - t > 0.05 and i < 200:
                    p = resto[i % len(resto)]
                    i += 1
                    it = Item("cuna", p, b.origen, b.orden)
                    it.desfase = t
                    if p.largo <= n - t + 0.05:
                        it.dur = p.largo
                        t += p.largo
                    else:
                        it.suena = n - t
                        it.dur = it.suena
                        it.fundido = min(FUNDIDO_CUNA, it.suena)
                        it.nota = tr("cortada")
                        t = n
                    piezas.append(it)
            elif b.sobrante == "relleno" and b.relleno_origen:
                piezas += self._relleno(b.relleno_origen, t, n - t, pase)
            # si no, lo que falta hasta la duracion exacta se queda en silencio
        return piezas

    @staticmethod
    def _elegir_cunas(cola: list, n: float, orden: str) -> list:
        """Las cunas que mejor llenan n segundos sin pasarse."""
        if not cola:
            return []
        if orden == "secuencial":
            res, t = [], 0.0
            for p in cola:
                if t + p.largo > n + 0.05:
                    break
                res.append(p)
                t += p.largo
            return res
        vistas, cands = set(), []
        for p in cola:
            if p.ruta not in vistas:
                vistas.add(p.ruta)
                cands.append(p)
            if len(cands) >= 16:
                break
        # todas las sumas posibles (2^16 como mucho): la mayor que no se pasa, y a
        # igualdad la que tira de las primeras de la cola
        sumas = np.zeros(1)
        puestos = np.zeros(1)
        for i, p in enumerate(cands):
            sumas = np.concatenate([sumas, sumas + p.largo])
            puestos = np.concatenate([puestos, puestos + i + 1])
        validas = sumas <= n + 0.05
        mejor = sumas[validas].max()
        empate = validas & (sumas >= mejor - 0.05)
        j = int(np.flatnonzero(empate)[np.argmin(puestos[empate])])
        return [p for i, p in enumerate(cands) if j >> i & 1]

    def _relleno(self, origen: str, desde: float, n: float, pase: "Pase") -> list:
        """
        Musica de relleno que cubre n segundos y acaba fundiendose. Sale de su
        baraja a partir de donde lo dejo el bloque anterior: lo que ya lleva
        otro bloque de la pauta no se vuelve a coger, aunque aun no haya sonado.
        """
        cola = self.sur.cola(origen, "aleatorio") if origen else []
        piezas = []
        if not cola or n <= 0.05:
            return piezas
        cola = self._sin_planear(cola, pase.planeadas) or cola
        t = 0.0
        for i in range(40):
            p = cola[i % len(cola)]
            pase.planeadas.append(p.ruta)
            it = Item("relleno", p, origen, "aleatorio")
            it.desfase = desde + t
            if t + p.largo >= n:
                it.suena = n - t
                it.dur = it.suena
                it.fundido = min(max(0.05, self.cfg.senales.fundido), it.suena)
                piezas.append(it)
                break
            it.dur = self.avance(p)
            piezas.append(it)
            t += it.dur
        return piezas

    # ------------------------------------------------------------ la hora

    def planificar_hora(self, h0: float, desde=None, pase=None, llenar: bool = True) -> PlanHora:
        """
        La pauta de la hora que empieza en h0. Con `desde` se planifica solo lo
        que queda a partir de esa hora de reloj (al empezar a emitir o al
        replanificar): lo anterior no existe y la musica arranca ya.
        """
        cfg = self.cfg
        momento = datetime.fromtimestamp(h0 + 1)
        franja = cfg.franja_de(momento)
        dia, hora = momento.weekday(), momento.hour
        plan = PlanHora(h0, franja)
        pase = Pase() if pase is None else pase
        ocupados = pase.ocupados

        t_fin, p_fin, falta = self.senal_de(plan.h1)
        plan.incompleto |= falta
        fin_tipo = "fundido" if p_fin is not None else "cruce"

        anclas = []
        if desde is None:
            t_s, p_s, falta = self.senal_de(h0)
            plan.incompleto |= falta
            if p_s is not None:
                anclas.append(self._ancla_senal(t_s, p_s, franja, ocupados))
            else:
                anclas.append(AnclaCruce(h0))
        if franja.eventos:
            for ev in cfg.eventos:
                if ev.origen and ev.cubre(dia, hora):
                    a = self._ancla_evento(h0, ev, ocupados, plan)
                    if a is not None:
                        anclas.append(a)
        if franja.publicidad:
            for b in cfg.publicidad:
                if b.cubre(dia, hora):
                    anclas.append(self._ancla_bloque(h0, b, franja, ocupados, plan))
        primera = anclas[0] if desde is None else None
        anclas.sort(key=lambda a: (a is not primera, a.t))

        cursor = desde
        for a in anclas:
            if a is primera:
                plan.bloques.append(a)
                cursor = a.t + a.dur
                continue
            if a.t < cursor - 1e-6:
                if desde is not None and a.t < desde:
                    continue                              # ya ha pasado o esta a medias
                a.mover(cursor - a.t)                     # se pisa con lo anterior: va detras
            if isinstance(a, AnclaBloque):
                cabe = t_fin - a.t - a.fijo()
                if cabe < min(MIN_BLOQUE, a.n):
                    plan.avisos.append(tr("«%s» no cabe antes de la hora siguiente") % a.nombre)
                    continue
                if cabe < a.n - 1e-6:
                    a.acortar(cabe)
                    plan.avisos.append(tr("«%s» recortado a %.0f s: no cabe entero") % (a.nombre, cabe))
                a.montar(self._contenido(a.cfg, a.n, plan, pase))
            elif a.t + a.dur > t_fin + 1e-6:
                plan.avisos.append(tr("«%s» no cabe antes de la hora siguiente") % a.nombre)
                continue
            if a.t - cursor >= 1.0:
                plan.bloques.append(Tramo(cursor, a.t, "fundido", franja))
            plan.bloques.append(a)
            cursor = a.t + a.dur
        if t_fin - cursor >= 1.0:
            plan.bloques.append(Tramo(cursor, t_fin, fin_tipo, franja))
        if desde is not None and plan.bloques and isinstance(plan.bloques[0], Tramo):
            plan.bloques[0].inmediato = True

        self.horario_anclas(plan)
        if llenar:
            self.llenar_plan(plan, pase)
        return plan

    @staticmethod
    def horario_anclas(plan: PlanHora) -> None:
        """Pone hora prevista a las piezas de las anclas."""
        for a in plan.bloques:
            if isinstance(a, Tramo):
                continue
            for it in a.piezas:
                it.t_ini = a.t + it.desfase
                if not it.dur:
                    it.dur = it.suena if it.suena is not None else it.pista.largo

    def llenar_plan(self, plan: PlanHora, pase: "Pase") -> None:
        """Elige canciones para todos los tramos de un plan que aun no ha empezado."""
        for b in plan.bloques:
            if isinstance(b, Tramo):
                self.elegir(b, pase)
                self.ajustar(b)
                while self.sobra_ultima(b):
                    self.ajustar(b)
                self.horario(b)

    # ------------------------------------------------------------ elegir

    def elegir(self, tramo: Tramo, pase: "Pase") -> None:
        """
        Canciones para lo que queda del tramo. Lo ya entregado al motor (las
        tramo.ic primeras) no se toca; lo demas se sustituye. En `pase` va lo
        comprometido hasta aqui (ver Pase) y se le anade lo que se elija.
        """
        vistos, planeadas, ocupados = pase.vistos, pase.planeadas, pase.ocupados
        fr = tramo.franja
        fundido = tramo.fin_tipo == "fundido"
        fijas = tramo.canciones[:tramo.ic]
        viejas = {c.pista.ruta: c for c in tramo.canciones[tramo.ic:]}
        cab = fijas[-1] if fijas else None
        t0 = cab.t_ini if cab is not None else tramo.ini
        disponible = tramo.fin - t0

        fr_c = fr                                         # de que franja salen las canciones
        cands = self.sur.cola(fr.canciones, fr.orden, fr.dur_min, fr.dur_max) if fr.canciones else []
        general = self.cfg.general
        if not cands and fr is not general and general.canciones:
            # la carpeta de la franja esta vacia o no esta: antes que callar, la general
            fr_c = general
            cands = self.sur.cola(general.canciones, general.orden, general.dur_min, general.dur_max)
        jq = []
        if fr.jingles and fr.jingles_origen:
            todos = self.sur.cola(fr.jingles_origen, "aleatorio")
            jq = [p for p in todos if p.ruta not in ocupados] or todos
        cada = max(1, int(fr.jingles_cada))

        def toca(est):
            """Si al siguiente cruce le toca jingle. est = (cruces desde el ultimo, puntero, ultimo jingle)."""
            cont, ptr, previo = est
            if not jq:
                return None, est
            cont += 1
            if cont < cada:
                return None, (cont, ptr, previo)
            pj = jq[ptr % len(jq)]
            if pj.ruta == previo and len(jq) > 1:         # el mismo dos veces seguidas, no
                ptr += 1
                pj = jq[ptr % len(jq)]
            return pj, (0, ptr + 1, pj.ruta)

        def poner_jingle(c, pj):
            if pj is None:
                c.jingle = None
                c.extra = 0.0
                return
            if c.jingle is None or c.jingle.pista.ruta != pj.ruta or c.jingle.estado not in (PLAN, PREP):
                c.jingle = Item("jingle", pj, fr.jingles_origen, "aleatorio")
            c.extra = self.extra_jingle(fr, pj)

        def cancion(p):
            c = viejas.pop(p.ruta, None)                  # si ya estaba preparada, se aprovecha
            if c is None:
                c = self.nueva_cancion(p, fr_c)
            c.recorte = 0.0
            return c

        # una cancion no vuelve hasta que hayan pasado `sep` distintas: media
        # carpeta (con una sola, sep = 0 y se repite sin mas)
        propias = {p.ruta for p in cands}
        distintas = len(propias)
        sep = 0 if distintas <= 1 else min(distintas - 1, max(1, distintas // 2))
        recientes = deque([r for r in vistos if r in propias][-sep:], maxlen=sep) if sep else ()
        secuencial = fr_c.orden == "secuencial"
        pend = self._sin_planear(cands, planeadas)        # lo ya apalabrado no esta disponible
        # las que aun no han salido en esta vuelta de la rotacion: tienen preferencia
        en_vuelta = set() if secuencial else set(self.sur.vuelta(fr_c.canciones, fr_c.orden))
        en_vuelta.difference_update(planeadas)
        nuevas = []
        est = (pase.cont_j, 0, pase.ultimo_jingle)
        acc = 0.0                                         # de t0 al arranque de la proxima cancion
        previa = cab

        if cab is not None:
            ult = cab.lleno if fundido else cab.avance
            if ult + TOL_FALTA > disponible or not pend:
                poner_jingle(cab, None)                   # la cabeza llena el tramo: es la ultima
                tramo.canciones = fijas
                self._soltar(viejas)
                return
            pj, est = toca(est)
            poner_jingle(cab, pj)
            acc = cab.avance + cab.extra
        elif disponible < TOL_FALTA:
            tramo.canciones = fijas
            self._soltar(viejas)
            return

        for _ in range(400):
            resto = disponible - acc
            if resto < TOL_FALTA:
                break
            if secuencial:
                if not pend:
                    break
                c = cancion(pend.pop(0))
                nuevas.append(c)
                ult = c.lleno if fundido else c.avance
                if acc + ult >= disponible + self.MARGEN:
                    break                                 # con esta se cierra el tramo
                pj, est = toca(est)
                poner_jingle(c, pj)
                acc += c.avance + c.extra
                previa = c
                continue

            ventana, ya = [], set()
            for i, p in enumerate(pend):
                if p.ruta in ya or p.ruta in recientes:
                    continue
                ya.add(p.ruta)
                ventana.append((i, p))
                if len(ventana) >= self.VENTANA:
                    break
            if not ventana:
                break
            media = sum(self.avance(p) for _, p in ventana[:12]) / min(12, len(ventana))
            if resto > 3.3 * media and len(ventana) > 4:
                i, p = ventana[0]                         # cuerpo del tramo: la que toca
                pend.pop(i)
                en_vuelta.discard(p.ruta)
                if sep:
                    recientes.append(p.ruta)
                c = cancion(p)
                pj, est = toca(est)
                poner_jingle(c, pj)
                acc += c.avance + c.extra
                nuevas.append(c)
                previa = c
                continue

            def extras_de(k, e=est):                      # jingles de los k-1 cruces del final
                total = 0.0
                for _ in range(k - 1):
                    pj, e = toca(e)
                    total += self.extra_jingle(fr, pj)
                return total

            fuera = [p.ruta not in en_vuelta for _, p in ventana]
            idx, sobra = self._mejor_final(resto, [p for _, p in ventana], fundido, extras_de,
                                           previa.pista.artista.lower() if previa else "",
                                           None if all(fuera) else fuera)
            elegidas = [ventana[j] for j in idx]
            for n_, (i, p) in enumerate(elegidas):
                c = cancion(p)
                en_vuelta.discard(p.ruta)
                if sep:
                    recientes.append(p.ruta)
                nuevas.append(c)
                if n_ < len(elegidas) - 1 or sobra < -TOL_FALTA:
                    pj, est = toca(est)
                    poner_jingle(c, pj)
                    acc += c.avance + c.extra
                previa = c
            for i in sorted((i for i, _ in elegidas), reverse=True):
                pend.pop(i)
            if sobra >= -TOL_FALTA:
                break                                     # tramo cubierto

        if nuevas:
            poner_jingle(nuevas[-1], None)
        elif cab is not None:
            poner_jingle(cab, None)
        tramo.canciones = fijas + nuevas
        self._soltar(viejas)
        for c in nuevas:
            vistos.append(c.pista.ruta)
            planeadas.append(c.pista.ruta)
        # el contador de jingles queda como lo dejen los cruces que de verdad existen
        # (todas menos la ultima tienen uno)
        cont, ultimo = pase.cont_j, pase.ultimo_jingle
        for c in (([cab] if cab is not None else []) + nuevas)[:-1]:
            if c.jingle is not None:
                ocupados.add(c.jingle.pista.ruta)
                cont, ultimo = 0, c.jingle.pista.ruta
            else:
                cont += 1
        pase.cont_j, pase.ultimo_jingle = cont, ultimo

    @staticmethod
    def _soltar(viejas: dict) -> None:
        """Cierra los decodificadores de las canciones que ya no entran en el plan."""
        for c in viejas.values():
            for it in (c, c.jingle):
                if it is not None and it.fuente is not None and it.estado in (PLAN, PREP):
                    it.fuente.cerrar()
                    it.fuente = None
                    it.estado = PLAN

    def _mejor_final(self, resto: float, pistas: list, fundido: bool, extras_de,
                     art_previo: str, fuera=None):
        """
        La combinacion de 1 a 4 canciones (en el orden de la cola) que mejor
        llena `resto` segundos. Devuelve (indices en `pistas`, sobrante).

        `fuera` marca las que ya sonaron en esta vuelta de la rotacion: usarlas
        es repetir antes de que hayan salido todas, y solo compensa si la
        alternativa es destrozar una cancion (PENA_VUELTA segundos de sobrante).
        """
        W = len(pistas)
        A = np.array([self.avance(p) for p in pistas])
        U = np.array([p.largo for p in pistas]) if fundido else A
        artes = [p.artista.lower() for p in pistas]
        pena = np.array(fuera, dtype=np.float64) * self.PENA_VUELTA if fuera is not None else None
        m = self.MARGEN
        mejor = (math.inf, [0], 0.0)
        for k in range(1, 5):
            if k > W:
                break
            idx = _combinaciones(min(W, 48 if k <= 3 else 30), k)
            T = U[idx[:, -1]] + extras_de(k)
            if k > 1:
                T = T + A[idx[:, :-1]].sum(axis=1)
            E = T - resto
            coste = np.where(E >= m, E - m, np.where(E >= 0.0, 3.0 * (m - E), 1000.0 - E))
            coste = coste + self.LAMBDA * idx.sum(axis=1)
            if pena is not None:
                coste = coste + pena[idx].sum(axis=1)
            n = min(12, len(coste))
            cerca = np.argpartition(coste, n - 1)[:n]
            cerca = cerca[np.argsort(coste[cerca])]
            elegido = None
            for j in cerca:
                comb = idx[j]
                previo = art_previo
                choca = False
                for i in comb:
                    if artes[i] and artes[i] == previo:
                        choca = True
                        break
                    previo = artes[i]
                if not choca:
                    elegido = j
                    break
            if elegido is None:
                elegido = cerca[0]
            if coste[elegido] < mejor[0]:
                mejor = (float(coste[elegido]), [int(i) for i in idx[elegido]], float(E[elegido]))
        return mejor[1], mejor[2]

    # ------------------------------------------------------------ recortar

    def ajustar(self, tramo: Tramo, tope_cabeza=None) -> float:
        """
        Reparte lo que sobra entre las canciones que aun pueden recortarse (de
        la ultima entregada al motor en adelante). Devuelve el desajuste: >0
        sobraba (ya repartido), <0 falta (quedara silencio al final).
        """
        mz = self.cfg.mezcla
        k = max(0, tramo.ic - 1)
        cs = tramo.canciones[k:]
        for c in tramo.canciones:
            c.ultima = False
        if not cs:
            tramo.desajuste = -(tramo.fin - tramo.ini)
            return tramo.desajuste
        cs[-1].ultima = True
        t0 = cs[0].t_ini if tramo.ic > 0 else tramo.ini
        disponible = tramo.fin - t0
        nats = [c.avance for c in cs]
        if tramo.fin_tipo == "fundido":
            nats[-1] = cs[-1].lleno
        exceso = sum(nats) + sum(c.extra for c in cs[:-1]) - disponible
        for c in cs:
            c.recorte = 0.0
        tramo.desajuste = exceso
        if exceso <= 0:
            return exceso
        topes = [min(mz.recorte_max, max(0.0, c.avance - mz.min_suena)) for c in cs[:-1]]
        if topes and tope_cabeza is not None:
            topes[0] = max(0.0, min(topes[0], tope_cabeza))
        rec, resto = repartir(exceso, topes)
        for c, r in zip(cs[:-1], rec):
            c.recorte = r
        cs[-1].recorte = resto
        return exceso

    def sobra_ultima(self, tramo: Tramo) -> bool:
        """
        Si la ultima cancion del tramo iba a sonar tan poco que es mejor no
        ponerla: se quita (siempre que quitandola no quede un hueco).
        """
        mz = self.cfg.mezcla
        k = max(0, tramo.ic - 1)
        cs = tramo.canciones[k:]
        if len(cs) < 2 or len(tramo.canciones) - 1 < tramo.ic:
            return False
        ult = cs[-1]
        nat = ult.lleno if tramo.fin_tipo == "fundido" else ult.avance
        if nat - ult.recorte >= mz.min_suena:
            return False
        ant = cs[-2]
        t0 = cs[0].t_ini if tramo.ic > 0 else tramo.ini
        sin = (sum(c.avance for c in cs[:-2]) + sum(c.extra for c in cs[:-2])
               + (ant.lleno if tramo.fin_tipo == "fundido" else ant.avance))
        if sin - (tramo.fin - t0) < -0.5:
            return False                                  # quitarla dejaria silencio
        tramo.canciones.pop()
        self._soltar({ult.pista.ruta: ult})
        j = ant.jingle                                    # el cruce que ya no va a existir
        if j is not None and j.fuente is not None and j.estado in (PLAN, PREP):
            j.fuente.cerrar()
        ant.jingle = None
        ant.extra = 0.0
        return True

    def horario(self, tramo: Tramo) -> None:
        """Hora prevista de arranque y duracion de cada cancion que aun no ha empezado."""
        k = max(0, tramo.ic - 1)
        cs = tramo.canciones[k:]
        if not cs:
            return
        t = cs[0].t_ini if tramo.ic > 0 else tramo.ini
        for c in cs:
            c.t_ini = t
            if c.ultima:
                nat = c.lleno if tramo.fin_tipo == "fundido" else c.avance
                c.dur = max(0.0, min(nat - c.recorte, tramo.fin - t))
            else:
                c.dur = c.avance - c.recorte
                if c.jingle is not None:
                    c.jingle.t_ini = t + c.dur
                    c.jingle.dur = c.jingle.pista.largo
                t += c.dur + c.extra
