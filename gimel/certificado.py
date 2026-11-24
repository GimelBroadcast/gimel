# -*- coding: utf-8 -*-
"""
Certificado de emision: las cunas que han salido al aire entre dos fechas,
con su hora real, sacadas del registro (datos/registro/AAAA-MM-DD.csv). Sale
como una pagina HTML lista para imprimir o guardar en PDF desde el navegador.

Se puede filtrar por un texto (el anunciante, la campana): vale cualquier
trozo del titulo, del artista o del nombre del fichero.
"""

import html
import os
from datetime import date, datetime, timedelta

from .idioma import tr
from .registro import NOMBRES


def filas(registro, desde: date, hasta: date, filtro: str = "", tipos=("cuna",)) -> list:
    """Las lineas del registro de esos tipos entre las dos fechas (incluidas)."""
    nombres = {NOMBRES[t] for t in tipos}
    filtro = filtro.strip().lower()
    res = []
    dia = desde
    while dia <= hasta and len(res) < 100000:
        for f in registro.leer(dia.isoformat(), limite=100000):
            if f.get("tipo") not in nombres:
                continue
            texto = " ".join((f.get("titulo", ""), f.get("artista", ""), f.get("fichero", ""))).lower()
            if filtro and filtro not in texto:
                continue
            res.append(f)
        dia += timedelta(days=1)
    return res


def html_certificado(registro, desde: date, hasta: date, filtro: str = "", emisora: str = "") -> str:
    lineas = filas(registro, desde, hasta, filtro)
    totales = {}
    for f in lineas:
        clave = f.get("titulo") or os.path.basename(f.get("fichero", ""))
        n, s = totales.get(clave, (0, 0.0))
        try:
            seg = float(f.get("segundos") or 0)
        except ValueError:
            seg = 0.0
        totales[clave] = (n + 1, s + seg)
    e = html.escape
    periodo = desde.strftime("%d/%m/%Y") + (" – " + hasta.strftime("%d/%m/%Y") if hasta != desde else "")
    cab = "".join("<th>%s</th>" % e(tr(x)) for x in ("Fecha", "Hora", "Cuña", "Segundos"))
    cuerpo = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td class='n'>%s</td></tr>" % (
            e(datetime.strptime(f["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y")), e(f.get("hora", "")[:8]),
            e(f.get("titulo") or os.path.basename(f.get("fichero", ""))), e(f.get("segundos", "")))
        for f in lineas)
    resumen = "".join("<tr><td>%s</td><td class='n'>%d</td><td class='n'>%.0f</td></tr>" % (e(k), n, s)
                      for k, (n, s) in sorted(totales.items()))
    return """<!doctype html>
<html><head><meta charset="utf-8"><title>%(titulo)s</title>
<style>
body { font: 13px/1.45 "Segoe UI", Arial, sans-serif; color: #111; background: #fff; margin: 32px; }
h1 { font-size: 20px; margin: 0 0 4px; } h2 { font-size: 14px; margin: 26px 0 8px; }
.dato { color: #444; margin: 2px 0; }
table { border-collapse: collapse; width: 100%%; margin-top: 6px; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid #ddd; }
th { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #555; border-bottom: 2px solid #999; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.firma { margin-top: 48px; color: #444; }
@media print { body { margin: 12mm; } }
</style></head><body>
<h1>%(titulo)s</h1>
<p class="dato">%(emisora)s</p>
<p class="dato">%(l_periodo)s: %(periodo)s%(filtro)s</p>
<p class="dato">%(l_total)s: %(total)d</p>
<h2>%(l_resumen)s</h2>
<table><tr><th>%(l_cuna)s</th><th class="n">%(l_pases)s</th><th class="n">%(l_seg)s</th></tr>%(resumen)s</table>
<h2>%(l_detalle)s</h2>
<table><tr>%(cab)s</tr>%(cuerpo)s</table>
<p class="firma">%(l_generado)s %(ahora)s · GIMEL</p>
</body></html>""" % {
        "titulo": e(tr("Certificado de emisión")), "emisora": e(emisora),
        "l_periodo": e(tr("Periodo")), "periodo": e(periodo),
        "filtro": (" · " + e(tr("Filtro")) + ": «" + e(filtro) + "»") if filtro.strip() else "",
        "l_total": e(tr("Pases emitidos")), "total": len(lineas),
        "l_resumen": e(tr("Resumen por cuña")), "l_cuna": e(tr("Cuña")), "l_pases": e(tr("Pases")),
        "l_seg": e(tr("Segundos")), "resumen": resumen or "<tr><td colspan='3'>%s</td></tr>" % e(tr("Ninguna")),
        "l_detalle": e(tr("Detalle de pases")), "cab": cab, "cuerpo": cuerpo,
        "l_generado": e(tr("Generado el")), "ahora": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
