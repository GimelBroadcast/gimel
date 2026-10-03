'use strict';
/* Panel web de GIMEL. Sin librerias: un puñado de funciones y el DOM.
   Todo texto que venga de fuera (titulos de canciones, rutas) entra por
   textContent, nunca como HTML. */

// ---------------------------------------------------------------- idioma
/* Los textos estan en español y son la clave de su traduccion (gimel/idioma.py):
   T() da el del idioma del programa, F() ademas rellena los %s y %d, y N_() solo
   marca los de las constantes, que se traducen al pintarlos. En el HTML, lo que
   lleva data-t se traduce al cargar. */

let TEXTOS = {}, IDIOMA = 'es';
const T = s => TEXTOS[s] || s;
const N_ = s => s;
function F(s, ...valores) {
  let i = 0;
  return T(s).replace(/%[sdg]/g, () => valores[i++]);
}
async function cargarTextos() {
  try {
    const r = await (await fetch('/api/textos')).json();
    TEXTOS = r.textos || {};
    IDIOMA = r.idioma || 'es';
  } catch (e) { /* sin tabla, en español */ }
  document.documentElement.lang = IDIOMA;
  for (const el of document.querySelectorAll('[data-t]')) el.textContent = T(el.textContent.trim());
}

const NOMBRES = {cancion: N_('Canción'), jingle: N_('Jingle'), senal: N_('Señal'), evento: N_('Evento'),
                 cuna: N_('Cuña'), relleno: N_('Relleno'), jingle_publi: N_('Jingle'),
                 silencio: N_('Silencio'), cue: N_('CUE')};
const $ = (s, r) => (r || document).querySelector(s);
const pad = n => String(n).padStart(2, '0');

function h(tag, attrs, ...hijos) {
  const e = document.createElement(tag);
  let valor;
  for (const k in (attrs || {})) {
    const v = attrs[k];
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'value') valor = v;
    else if (k === 'checked') e.checked = true;
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const x of hijos.flat(Infinity)) {
    if (x === null || x === undefined || x === false) continue;
    e.append(x.nodeType ? x : document.createTextNode(String(x)));
  }
  if (valor !== undefined) e.value = valor;      // despues de los hijos: un <select> necesita sus <option>
  return e;
}

// ---------------------------------------------------------------- servidor

async function api(ruta, cuerpo) {
  const op = cuerpo === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-Gimel': '1'},
    body: JSON.stringify(cuerpo)};
  let r = await fetch(ruta, op);
  if (r.status === 401) {
    await pedirClave();
    r = await fetch(ruta, op);
  }
  if (!r.ok && r.status !== 400) throw new Error((await r.text()) || ('HTTP ' + r.status));
  return r.json();
}

let pidiendoClave = null;
function pedirClave() {
  if (pidiendoClave) return pidiendoClave;
  pidiendoClave = new Promise(resolver => {
    const campo = h('input', {type: 'password', placeholder: T('Contraseña')});
    const error = h('span', {class: 'resumen mal'});
    const entrar = async () => {
      const r = await fetch('/api/login', {method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-Gimel': '1'},
        body: JSON.stringify({clave: campo.value})});
      if (r.ok) { velo.remove(); pidiendoClave = null; resolver(); }
      else { error.textContent = T('Contraseña incorrecta'); campo.select(); }
    };
    campo.addEventListener('keydown', e => { if (e.key === 'Enter') entrar(); });
    const velo = h('div', {class: 'velo'}, h('div', {class: 'ventana', style: 'width:360px'},
      h('header', null, 'GIMEL'),
      h('div', {class: 'cuerpo', style: 'min-height:0;padding:16px'}, campo, error),
      h('footer', null, h('button', {class: 'boton verde', onclick: entrar}, T('Entrar')))));
    document.body.append(velo);
    campo.focus();
  });
  return pidiendoClave;
}

function avisar(texto, ms) {
  if (!texto) return;
  const a = h('div', {class: 'aviso-flotante'}, texto);
  document.body.append(a);
  setTimeout(() => a.remove(), ms || 5000);
}

// ---------------------------------------------------------------- horas

let TZ = 0;            // segundos que hay que sumar a UTC para tener la hora de la emisora
let DESFASE = 0;       // ms entre el reloj de la emisora y el de este navegador
const ahora = () => (Date.now() + DESFASE) / 1000;
const DIAS_LARGOS = [N_('domingo'), N_('lunes'), N_('martes'), N_('miércoles'), N_('jueves'), N_('viernes'),
                     N_('sábado')];
const MESES = [N_('enero'), N_('febrero'), N_('marzo'), N_('abril'), N_('mayo'), N_('junio'), N_('julio'),
               N_('agosto'), N_('septiembre'), N_('octubre'), N_('noviembre'), N_('diciembre')];

function hora(t) {
  const d = new Date((t + TZ) * 1000);
  return pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()) + ':' + pad(d.getUTCSeconds());
}
function fecha(t) {
  const d = new Date((t + TZ) * 1000);
  return T('%(dia)s %(n)d de %(mes)s').replace('%(dia)s', T(DIAS_LARGOS[d.getUTCDay()]))
    .replace('%(n)d', d.getUTCDate()).replace('%(mes)s', T(MESES[d.getUTCMonth()]));
}
function mmss(s) {
  s = Math.max(0, Math.round(s));
  const m = Math.floor(s / 60);
  return m >= 60 ? Math.floor(m / 60) + ':' + pad(m % 60) + ':' + pad(s % 60) : m + ':' + pad(s % 60);
}
function duracion(s) {
  if (!s) return '';
  return s < 10 ? s.toFixed(1).replace('.', T(',')) + ' s' : mmss(s);
}
function largo(s) {
  const horas = Math.floor(s / 3600), m = Math.round((s % 3600) / 60);
  return horas ? F('%d h %d min', horas, m) : F('%d min', m);
}

const ESTADOS_ICECAST = {emitiendo: N_('emitiendo'), conectando: N_('conectando…'), error: N_('sin conexión'),
                         parado: N_('parado')};
function textoIcecast(flujos, largoTexto) {
  return flujos.map(f => {
    let t = f.nombre + ': ' + T(ESTADOS_ICECAST[f.estado] || f.estado);
    if (f.estado === 'emitiendo') t += ' (' + mmss(f.segundos) + ')';
    else if (f.detalle) t += ' — ' + f.detalle;
    if (largoTexto) {
      t += '   ·   ' + f.destino;
      if (f.perdidos) t += '   ·   ' + F('%d bloques perdidos por atasco de red', f.perdidos);
    }
    return t;
  }).join(largoTexto ? '\n' : '   |   ');
}

// ---------------------------------------------------------------- emision

let E = null;          // ultimo estado recibido
let firmaPauta = '';

async function refrescar() {
  try {
    const e = await api('/api/estado');
    TZ = e.tz || 0;
    DESFASE = e.reloj * 1000 - Date.now();
    E = e;
    if (e.idioma && e.idioma !== IDIOMA && !sucio()) { location.reload(); return; }   // han cambiado el idioma
    pintarEstado();
  } catch (err) {
    $('#aire').textContent = T('SIN CONEXIÓN');
    $('#aire').className = 'aire';
  }
}

function pintarEstado() {
  const e = E;
  $('#emisora').textContent = e.emisora || '';
  document.title = (e.emisora || 'GIMEL') + (e.emitiendo ? ' · ' + T('en emisión') : '');
  const aire = $('#aire');
  aire.textContent = e.emitiendo ? T('EN EMISIÓN') : T('PARADO');
  aire.className = 'aire' + (e.emitiendo ? ' si' : '');
  const b = $('#b-emitir');
  b.textContent = e.emitiendo ? '■ ' + T('Detener') : '▶ ' + T('Emitir');
  b.className = 'boton ' + (e.emitiendo ? 'rojo' : 'verde');
  $('#b-saltar').disabled = !e.emitiendo;
  $('#b-rehacer').disabled = !e.emitiendo;
  const err = $('#error');
  err.hidden = !e.error;
  err.textContent = e.error || '';

  const a = e.actual;
  $('#s-tipo').textContent = a ? T(NOMBRES[a.tipo] || a.tipo) : '—';
  $('#s-tipo').className = 'chip t-' + (a ? a.tipo : 'silencio');
  $('#s-titulo').textContent = a ? a.titulo : (e.emitiendo ? '…' : T('Parado'));
  $('#s-artista').textContent = a ? (a.artista || '') : (e.emitiendo ? '' : T('La pauta de abajo es la que saldría si empezaras ahora'));
  $('#s-encima').textContent = e.jingle ? '♪ ' + T('encima: ') + e.jingle.titulo : '';

  $('#a-franja').textContent = e.franja ? T('Programación: ') + e.franja : '';
  const ice = textoIcecast(e.icecast || [], false);
  $('#salida').textContent = T('Salida: ') + (e.salida || []).filter(Boolean).map(T).join(' · ').replace('Windows ', '') +
    (ice ? '   ·   Icecast → ' + ice : '');
  const iceEstado = $('#ice-estado');
  if (iceEstado) iceEstado.textContent = textoIcecast(e.icecast || [], true) || T('Los envíos se conectan al empezar a emitir.');
  $('#analisis').textContent = e.analizando ? F('Analizando la biblioteca: quedan %d', e.analizando) : '';
  const lim = $('#lim');
  lim.textContent = e.limitando ? T('LIMITADOR ACTUANDO') : T('limitador');
  lim.className = 'lim' + (e.limitando ? ' si' : '');
  const db = v => Math.max(0, Math.min(100, (20 * Math.log10(Math.max(v, 1e-5)) + 48) / 48 * 100));
  $('#vu-l').style.width = db((e.vu || [0, 0])[0]) + '%';
  $('#vu-r').style.width = db((e.vu || [0, 0])[1]) + '%';

  const av = $('#avisos');
  av.replaceChildren(...(e.avisos || []).slice(-6).reverse().map(x => h('li', null, hora(x.t) + '  ' + x.texto)));
  if (e.aviso_salida) av.prepend(h('li', null, e.aviso_salida));

  const filas = e.pauta || [];
  const firma = JSON.stringify(filas.map(f => [Math.round(f.t), f.tipo, f.titulo, f.estado, f.nota, Math.round(f.dur)]));
  if (firma !== firmaPauta) {
    firmaPauta = firma;
    $('#pauta').replaceChildren(...filas.map(f => h('tr', {class: f.estado === 'aire' ? 'aire' : (f.estado === 'fin' ? 'fin' : '')},
      h('td', {class: 'hora mono'}, hora(f.t)),
      h('td', null, h('span', {class: 'chip t-' + f.tipo}, T(NOMBRES[f.tipo] || f.tipo))),
      h('td', null, f.titulo, f.artista ? h('span', {class: 'sub'}, '  —  ' + f.artista) : null),
      h('td', {class: 'dur mono'}, duracion(f.dur)),
      h('td', {class: 'nota'}, f.nota || ''))));
    $('#pauta-vacia').hidden = filas.length > 0;
  }
  $('#p-titulo').textContent = (e.emitiendo ? T('Pauta de la hora') : T('Rotación prevista (sin emitir)')) +
    (e.h0 ? '  ·  ' + hora(e.h0).slice(0, 5) + ' – ' + hora(e.h0 + 3600).slice(0, 5) : '');
  tic();
}

function tic() {
  const t = ahora();
  $('#reloj').textContent = hora(t);
  $('#fecha').textContent = fecha(t);
  if (!E) return;
  const a = E.actual;
  if (a && E.emitiendo && a.dur > 0) {
    const va = Math.max(0, t - a.t);
    $('#s-barra').style.width = Math.min(100, 100 * va / a.dur) + '%';
    $('#s-va').textContent = mmss(Math.min(va, a.dur));
    $('#s-resta').textContent = '-' + mmss(a.dur - va);
  } else {
    $('#s-barra').style.width = '0';
    $('#s-va').textContent = '';
    $('#s-resta').textContent = '';
  }
  const an = E.ancla;
  if (an && E.emitiendo) {
    $('#a-nombre').textContent = T('Falta para: ') + (an.clase === 'senal' ? T('la señal horaria') : (an.nombre || T('el siguiente bloque')));
    $('#a-cuenta').textContent = mmss(an.t - t);
  } else {
    $('#a-nombre').textContent = T('Falta para la hora en punto');
    $('#a-cuenta').textContent = mmss(3600 - ((t + TZ) % 3600));
  }
}

$('#b-emitir').addEventListener('click', async () => {
  const r = await api('/api/emision', {accion: E && E.emitiendo ? 'detener' : 'iniciar'});
  if (r.mensaje) avisar(r.mensaje, 8000);
  refrescar();
});
$('#b-saltar').addEventListener('click', () => api('/api/emision', {accion: 'saltar'}));
$('#b-rehacer').addEventListener('click', () => api('/api/emision', {accion: 'replanificar'}));

// ---------------------------------------------------------------- configuracion

let CFG = null, GUARDADA = '', ESQ = null, SALIDAS = [], NUEVOS = {}, PLANTILLAS = {}, DIAS = [];
const sucio = () => CFG && JSON.stringify(CFG) !== GUARDADA;

function marcar() {
  $('#guardar').classList.toggle('pendiente', sucio());
}

async function cargarConfig() {
  const r = await api('/api/config');
  CFG = r.config; ESQ = r.esquema; SALIDAS = r.salidas; NUEVOS = r.nuevos;
  PLANTILLAS = r.plantillas_cue; DIAS = r.dias;
  GUARDADA = JSON.stringify(CFG);
  marcar();
}

$('#guardar').addEventListener('click', async () => {
  if (!CFG) return;
  const r = await api('/api/config', CFG);
  if (!r.ok) { avisar(F('No se ha podido guardar: %s', r.mensaje), 8000); return; }
  await cargarConfig();
  pintarPagina();
  avisar(r.mensaje || T('Configuración guardada y aplicada.'));
});
window.addEventListener('beforeunload', e => { if (sucio()) { e.preventDefault(); e.returnValue = ''; } });

// --- un campo del esquema, enlazado a obj[c.clave]
function control(c, obj, repintar) {
  const poner = (v, repinta) => { obj[c.clave] = v; marcar(); if (repinta) repintar(); };
  const v = obj[c.clave];
  switch (c.tipo) {
    case 'bool':
      return h('input', {type: 'checkbox', class: 'interruptor', checked: !!v,
                         onchange: e => poner(e.target.checked, true)});
    case 'entero':
    case 'decimal': {
      const entero = c.tipo === 'entero';
      const inp = h('input', {type: 'number', min: c.min, max: c.max, step: entero ? 1 : (c.paso || 0.1), value: v,
        onchange: e => {
          let n = parseFloat(e.target.value);
          if (isNaN(n)) n = 0;
          if (c.min !== undefined) n = Math.max(c.min, n);
          if (c.max !== undefined) n = Math.min(c.max, n);
          if (entero) n = Math.round(n);
          e.target.value = n;
          poner(n, false);
        }});
      return [inp, c.sufijo ? h('span', {class: 'sub'}, c.sufijo) : null];
    }
    case 'opcion':
      return h('select', {value: String(v), onchange: e => {
        const o = c.opciones.find(x => String(x[0]) === e.target.value);
        poner(o ? o[0] : e.target.value, true);
      }}, c.opciones.map(o => h('option', {value: String(o[0])}, o[1])));
    case 'hora':
      return h('select', {value: String(v), onchange: e => poner(parseInt(e.target.value, 10), false)},
        Array.from({length: 24}, (_, i) => h('option', {value: String(i)}, pad(i) + ':00')));
    case 'hora_fin':
      return h('select', {value: String(v), onchange: e => poner(parseInt(e.target.value, 10), false)},
        Array.from({length: 24}, (_, i) => h('option', {value: String(i + 1)}, pad(i + 1) + ':00')));
    case 'dias':
      return h('div', {class: 'dias'}, DIAS.map((d, i) => h('button', {class: v[i] ? 'si' : '', onclick: e => {
        v[i] = !v[i]; e.target.className = v[i] ? 'si' : ''; marcar();
      }}, d)));
    case 'parrafo':
      return h('textarea', {value: v, oninput: e => poner(e.target.value, false)});
    case 'clave':
      return h('input', {type: 'password', value: v, autocomplete: 'new-password', oninput: e => poner(e.target.value, false)});
    case 'origen':
      return controlOrigen(c.modo || 'cualquiera', () => obj[c.clave], x => poner(x, false));
    case 'salida': {
      const api_ = obj.api;
      const sel = h('select', {value: v, onchange: e => poner(e.target.value, false)},
        h('option', {value: ''}, T('Predeterminada del sistema')),
        SALIDAS.filter(s => s.api === api_).map(s => h('option', {value: s.nombre}, s.nombre + (s.defecto ? '  ' + T('(predeterminada)') : ''))),
        v && !SALIDAS.some(s => s.api === api_ && s.nombre === v) ? h('option', {value: v}, v + '  ' + T('(no está)')) : null);
      return [sel, h('button', {class: 'boton pequeno', onclick: async () => {
        SALIDAS = (await api('/api/salidas?refrescar=1')).salidas; repintar();
      }}, T('Actualizar'))];
    }
    default:
      return h('input', {type: 'text', value: v, oninput: e => poner(e.target.value, false)});
  }
}

// --- campo de ruta con explorador y resumen de lo que hay dentro
function controlOrigen(modo, leer, poner) {
  const resumen = h('div', {class: 'resumen'});
  const inp = h('input', {type: 'text', value: leer(), spellcheck: 'false'});
  let espera = null;
  const mirar = async () => {
    const ruta = inp.value.trim();
    resumen.className = 'resumen';
    if (!ruta || modo === 'guardar') { resumen.textContent = ''; return; }
    try {
      const r = await api('/api/origen?ruta=' + encodeURIComponent(ruta));
      if (!r.existe) { resumen.textContent = T('No existe'); resumen.className = 'resumen mal'; }
      else if (modo === 'fichero') {     // un fichero suelto: solo se avisa si falla
        resumen.textContent = r.errores ? T('No se puede leer') : '';
        resumen.className = 'resumen mal';
      }
      else if (r.leyendo) { resumen.textContent = T('Leyendo…'); clearTimeout(espera); espera = setTimeout(mirar, 1500); }
      else {
        resumen.textContent = (r.ficheros === 1 ? F('%d audio', r.ficheros) : F('%d audios', r.ficheros)) +
          (r.analizados ? ' · ' + largo(r.segundos) : '') +
          (r.analizados < r.ficheros - r.errores ? ' · ' + F('analizando (%d de %d)', r.analizados, r.ficheros) : '') +
          (r.errores ? ' · ' + F('%d ilegibles', r.errores) : '');
        if (r.analizados < r.ficheros - r.errores) { clearTimeout(espera); espera = setTimeout(mirar, 3000); }
      }
    } catch (e) { resumen.textContent = ''; }
  };
  inp.addEventListener('change', () => { poner(inp.value.trim()); mirar(); });
  const caja = h('div', {class: 'ruta'}, inp,
    modo === 'guardar' ? null : h('button', {class: 'boton pequeno', onclick: async () => {
      const r = await explorar(modo, inp.value.trim());
      if (r !== null) { inp.value = r; poner(r); mirar(); }
    }}, T('Examinar…')),
    h('button', {class: 'boton pequeno', title: T('Quitar'), onclick: () => { inp.value = ''; poner(''); mirar(); }}, '✕'));
  mirar();
  return [caja, resumen];
}

function formulario(campos, obj, repintar, omitir) {
  const f = h('div', {class: 'form'});
  for (const c of campos) {
    if (omitir && omitir(c)) continue;
    if (c.si && !c.si[1].includes(obj[c.si[0]])) continue;
    if (c.tipo === 'titulo') { f.append(h('h3', null, c.etiqueta)); continue; }   // el esquema llega ya traducido
    f.append(h('div', {class: 'campo'},
      h('label', null, c.etiqueta),
      h('div', {class: 'valor'}, control(c, obj, repintar)),
      c.ayuda ? h('div', {class: 'ayuda'}, c.ayuda) : null));
  }
  return f;
}

// --- explorador de carpetas del equipo de la emisora
function explorar(modo, inicial) {
  return new Promise(resolver => {
    const cuerpo = h('div', {class: 'cuerpo'});
    const donde = h('span', {class: 'sub mono', style: 'margin-right:auto;font-size:12px'});
    let actual = '';
    const cerrar = v => { velo.remove(); resolver(v); };
    const ir = async ruta => {
      const r = await api('/api/explorar?ruta=' + encodeURIComponent(ruta));
      actual = r.ruta;
      donde.textContent = r.ruta || T('Este equipo');
      elegir.disabled = !r.ruta || modo === 'fichero';
      const filas = [];
      // sin emojis de color: hay motores de navegador a los que algunos les sientan mal
      if (r.padre !== null && r.padre !== undefined) filas.push(h('div', {class: 'entrada', onclick: () => ir(r.padre)}, '↑  ' + T('subir')));
      for (const c of r.carpetas) filas.push(h('div', {class: 'entrada', onclick: () => ir(c)}, '▸  ' + (r.ruta ? c.split(/[\\/]/).pop() : c)));
      for (const f of r.ficheros) {
        const lista = /\.(m3u8?|pls)$/i.test(f);
        if (modo === 'fichero' && lista) continue;
        filas.push(h('div', {class: 'entrada fichero', onclick: () => cerrar(f)}, (lista ? '≡  ' : '♪  ') + f.split(/[\\/]/).pop()));
      }
      if (r.error) filas.push(h('div', {class: 'vacio'}, r.error));
      cuerpo.replaceChildren(...filas);
    };
    const elegir = h('button', {class: 'boton verde', onclick: () => cerrar(actual)}, T('Elegir esta carpeta'));
    const velo = h('div', {class: 'velo'}, h('div', {class: 'ventana'},
      h('header', null, modo === 'fichero' ? T('Elegir un audio') : T('Elegir una carpeta, una lista o un audio')),
      cuerpo,
      h('footer', null, donde, h('button', {class: 'boton', onclick: () => cerrar(null)}, T('Cancelar')), elegir)));
    document.body.append(velo);
    const padre = inicial ? (/\.[a-z0-9]{2,4}$/i.test(inicial) ? inicial.replace(/[\\/][^\\/]*$/, '') : inicial) : '';
    ir(padre).catch(() => ir(''));
  });
}

// --- lista a la izquierda, formulario a la derecha
const seleccion = {};
function listaDetalle(sec, op) {
  const pintar = () => {
    const items = op.items();
    const fijo = op.fijo ? op.fijo() : null;
    const total = items.length + (fijo ? 1 : 0);
    let i = Math.min(seleccion[op.id] || 0, Math.max(0, total - 1));
    seleccion[op.id] = i;
    const esFijo = fijo && i === 0;
    const k = fijo ? i - 1 : i;
    const obj = esFijo ? fijo.obj : items[k];
    const entradas = [];
    if (fijo) entradas.push(h('li', {class: i === 0 ? 'sel' : '', onclick: () => { seleccion[op.id] = 0; pintar(); }}, fijo.nombre, h('span', {class: 'sub'}, T('el resto'))));
    items.forEach((it, n) => {
      const idx = fijo ? n + 1 : n;
      entradas.push(h('li', {class: (idx === i ? 'sel ' : '') + (op.activo(it) ? '' : 'apagado'),
        onclick: () => { seleccion[op.id] = idx; pintar(); }}, it.nombre || T('(sin nombre)'), h('span', {class: 'sub'}, op.sub(it))));
    });
    const mover = d => {
      const j = k + d;
      if (j < 0 || j >= items.length) return;
      [items[k], items[j]] = [items[j], items[k]];
      seleccion[op.id] = i + d; marcar(); pintar();
    };
    const izq = h('div', {class: 'tarjeta'},
      h('h2', null, T(op.titulo)),
      h('ul', {class: 'lista'}, entradas),
      h('div', {class: 'acciones'},
        h('button', {class: 'boton pequeno', onclick: () => {
          items.push(JSON.parse(JSON.stringify(op.nuevo()))); seleccion[op.id] = total; marcar(); pintar();
        }}, '+ ' + T('Añadir')),
        h('button', {class: 'boton pequeno', disabled: esFijo || !obj, onclick: () => {
          const copia = JSON.parse(JSON.stringify(obj)); copia.nombre = (copia.nombre || '') + ' ' + T('(copia)');
          items.splice(k + 1, 0, copia); seleccion[op.id] = i + 1; marcar(); pintar();
        }}, T('Duplicar')),
        h('button', {class: 'boton pequeno', disabled: esFijo || !obj, onclick: () => mover(-1)}, '▲'),
        h('button', {class: 'boton pequeno', disabled: esFijo || !obj, onclick: () => mover(1)}, '▼'),
        h('button', {class: 'boton pequeno', disabled: esFijo || !obj, onclick: () => {
          if (!confirm(F('¿Eliminar «%s»?', obj.nombre || ''))) return;
          items.splice(k, 1); marcar(); pintar();
        }}, T('Eliminar'))),
      op.nota ? h('p', {class: 'dato'}, T(op.nota)) : null);
    const der = h('div', {class: 'tarjeta'},
      obj ? [op.antes ? op.antes(obj, pintar) : null,
             formulario(op.esquema, obj, pintar, esFijo ? (c => c.solo_franja) : null),
             op.despues ? op.despues(obj, pintar) : null]
          : h('div', {class: 'vacio'}, T(op.vacio || N_('No hay nada todavía. Pulsa «Añadir».'))));
    sec.replaceChildren(h('div', {class: 'dos'}, izq, der));
  };
  pintar();
}

const horario = x => pad(x.desde) + '–' + pad(x.hasta);
const GENERAL = N_('Programación general');   // el nombre de fabrica de la programacion general
const SISTEMA = N_('Sistema');                // el tipo de las lineas del registro que no son audios

// ---------------------------------------------------------------- paginas

const PAGINAS = {
  franjas(sec) {
    listaDetalle(sec, {
      id: 'franjas', titulo: N_('Programación'), esquema: ESQ.franja,
      items: () => CFG.franjas,
      fijo: () => ({obj: CFG.general, nombre: !CFG.general.nombre || CFG.general.nombre === GENERAL ? T(GENERAL) : CFG.general.nombre}),
      activo: f => f.activa, sub: horario, nuevo: () => NUEVOS.franja,
      nota: N_('Cada hora se hace con la primera franja de la lista que la cubra; si no la cubre ninguna, con la programación general. El orden importa: usa ▲ y ▼.')});
  },
  publicidad(sec) {
    listaDetalle(sec, {
      id: 'publicidad', titulo: N_('Bloques'), esquema: ESQ.bloque,
      items: () => CFG.publicidad, activo: b => b.activo, nuevo: () => NUEVOS.bloque,
      sub: b => 'min ' + pad(b.minuto) + ' · ' + horario(b),
      antes: b => h('div', {class: 'esquema-bloque'},
        h('div', {class: 't-cancion'}, T('música'), h('small', null, F('baja %g s', CFG.senales.fundido))),
        b.silencio_antes > 0 ? h('div', {class: 't-silencio'}, F('silencio %g s', b.silencio_antes), h('small', null, b.cue ? F('CUE a los %g s', b.cue_tras) : '')) : null,
        b.jingle ? h('div', {class: 't-jingle_publi'}, T('jingle'), h('small', null, T('entrada'))) : null,
        h('div', {class: b.contenido === 'relleno' ? 't-relleno' : 't-cuna'}, b.contenido === 'relleno' ? T('relleno') : T('cuñas'), h('small', null, F('%g s exactos', b.duracion))),
        b.silencio_despues > 0 ? h('div', {class: 't-silencio'}, F('a negro %g s', b.silencio_despues), h('small', null, b.cue ? F('CUE a los %g s', b.cue_retorno_tras) : '')) : null,
        b.jingle_salida ? h('div', {class: 't-jingle_publi'}, T('jingle'), h('small', null, T('vuelta'))) : null,
        h('div', {class: 't-cancion'}, T('música'))),
      nota: N_('Un bloque se programa en todas las horas de su rango. La música de antes y de después se reajusta sola para que la hora siga cuadrando.'),
      vacio: N_('No hay bloques de publicidad ni de desconexión. Pulsa «Añadir».')});
  },
  icecast(sec) {
    listaDetalle(sec, {
      id: 'icecast', titulo: N_('Servidores Icecast'), esquema: ESQ.icecast,
      items: () => CFG.icecast, activo: x => x.activo, nuevo: () => NUEVOS.icecast,
      sub: x => x.formato + ' ' + x.bitrate + 'k',
      antes: () => h('p', {class: 'dato', id: 'ice-estado', style: 'white-space:pre-line;margin:0 0 14px'},
        textoIcecast((E && E.icecast) || [], true) || T('Los envíos se conectan al empezar a emitir.')),
      nota: N_('La emisión se manda a todos los servidores activos, además de salir por la tarjeta. Para emitir solo por Icecast, elige «Sin tarjeta» en Ajustes > Salida de audio.'),
      vacio: N_('No hay ningún servidor Icecast. Pulsa «Añadir».')});
  },
  eventos(sec) {
    listaDetalle(sec, {
      id: 'eventos', titulo: N_('Eventos a minuto fijo'), esquema: ESQ.evento,
      items: () => CFG.eventos, activo: x => x.activo, nuevo: () => NUEVOS.evento,
      sub: x => 'min ' + pad(x.minuto) + ' · ' + horario(x),
      nota: N_('Un audio que arranca en un minuto exacto de la hora: un boletín, la señal de las medias, una promo. La música calla antes, igual que con la señal horaria.'),
      vacio: N_('No hay eventos. Pulsa «Añadir».')});
  },
  senales(sec) {
    const pintar = () => {
      const s = CFG.senales;
      const filas = [];
      for (let i = 0; i < 24; i++) {
        filas.push(h('div', {class: 'mono'}, pad(i) + ':00'),
          h('div', {class: 'valor'}, controlOrigen('fichero', () => s.archivos[String(i)] || '', v => {
            if (v) s.archivos[String(i)] = v; else delete s.archivos[String(i)];
            marcar();
          })));
      }
      sec.replaceChildren(
        h('div', {class: 'tarjeta', style: 'margin-bottom:16px'}, h('h2', null, T('Señales horarias')), formulario(ESQ.senales, s, pintar)),
        h('div', {class: 'tarjeta'}, h('h2', null, T('El audio de cada hora')),
          h('div', {class: 'acciones', style: 'margin-bottom:12px'},
            h('button', {class: 'boton pequeno', onclick: async () => {
              const carpeta = await explorar('carpeta', '');
              if (!carpeta) return;
              const r = await api('/api/senales/auto', {carpeta});
              const n = Object.keys(r.archivos).length;
              if (!n) { avisar(T('En esa carpeta no hay audios con un número de hora en el nombre.')); return; }
              Object.assign(s.archivos, r.archivos); marcar(); pintar();
              avisar(F('%d horas asignadas por el número del nombre de cada fichero.', n));
            }}, T('Rellenar desde una carpeta…')),
            h('button', {class: 'boton pequeno', onclick: () => {
              if (confirm(T('¿Quitar el audio de las 24 horas?'))) { s.archivos = {}; marcar(); pintar(); }
            }}, T('Vaciar'))),
          h('div', {class: 'horas'}, filas)));
    };
    pintar();
  },
  cue(sec) {
    const arriba = h('div');
    const abajo = h('div');
    const medio = h('div', {style: 'margin:16px 0'});
    const pintarArriba = () => arriba.replaceChildren(h('div', {class: 'tarjeta'}, h('h2', null, T('CUE de desconexión y de reconexión')),
      formulario(ESQ.cue, CFG.cue, pintarArriba),
      h('p', {class: 'dato'}, T('El de desconexión sale durante el silencio previo a cada bloque y el de reconexión durante el negro final (los segundos se ponen en cada bloque). Se mandan a todos los servidores activos de abajo.'))));
    const pintarAbajo = () => abajo.replaceChildren(h('div', {class: 'tarjeta'}, h('h2', null, T('Título en emisión')),
      formulario(ESQ.metadatos, CFG.metadatos, pintarAbajo)));
    pintarArriba(); pintarAbajo();
    listaDetalle(medio, {
      id: 'destinos', titulo: N_('Servidores'), esquema: ESQ.destino_cue,
      items: () => CFG.cue.destinos, activo: d => d.activo, sub: d => d.tipo, nuevo: () => NUEVOS.destino_cue,
      antes: d => {
        // al cambiar de tipo se proponen el destino y los mensajes de ese tipo
        if (d._tipo && d._tipo !== d.tipo && PLANTILLAS[d.tipo]) {
          const v = PLANTILLAS[d._tipo], n = PLANTILLAS[d.tipo];
          if (!v || d.destino === v[0]) d.destino = n[0];
          if (!v || d.inicio === v[1]) d.inicio = n[1];
          if (!v || d.retorno === v[2]) d.retorno = n[2];
        }
        Object.defineProperty(d, '_tipo', {value: d.tipo, writable: true, enumerable: false, configurable: true});
        return null;
      },
      despues: d => {
        const res = h('span', {class: 'resumen'});
        const probar = ev => async () => {
          res.textContent = T('Enviando…');
          const r = await api('/api/cue/probar', {destino: d, evento: ev});
          res.textContent = r.resultado;
          res.className = 'resumen' + (String(r.resultado).startsWith('ERROR') ? ' mal' : '');
        };
        return h('div', {class: 'acciones', style: 'margin-top:14px'},
          h('button', {class: 'boton pequeno', onclick: probar('inicio')}, T('Probar: desconexión')),
          h('button', {class: 'boton pequeno', onclick: probar('retorno')}, T('Probar: reconexión')), res);
      },
      vacio: N_('No hay ningún servidor al que mandar los CUE. Pulsa «Añadir».')});
    sec.replaceChildren(arriba, medio, abajo);
  },
  ajustes(sec) {
    const bloque = (titulo, esquema, obj) => {
      const caja = h('div', {style: 'margin-bottom:16px'});
      const pintar = () => caja.replaceChildren(h('div', {class: 'tarjeta'}, h('h2', null, T(titulo)), formulario(esquema, obj, pintar)));
      pintar();
      return caja;
    };
    sec.replaceChildren(
      bloque(N_('Emisora'), ESQ.sistema, CFG),
      bloque(N_('Salida de audio'), ESQ.salida, CFG.salida),
      bloque(N_('Mezcla'), ESQ.mezcla, CFG.mezcla),
      bloque(N_('Panel web'), ESQ.web, CFG.web));
  },
  async registro(sec) {
    const pintar = async fechaPedida => {
      const r = await api('/api/registro' + (fechaPedida ? '?fecha=' + encodeURIComponent(fechaPedida) : ''));
      sec.replaceChildren(h('div', {class: 'tarjeta'},
        h('h2', null, T('Registro de emisión')),
        h('div', {class: 'acciones', style: 'margin-bottom:12px'},
          h('select', {value: r.fecha, onchange: e => pintar(e.target.value)}, r.dias.map(d => h('option', {value: d}, d))),
          h('button', {class: 'boton pequeno', onclick: () => pintar(r.fecha)}, T('Actualizar')),
          h('span', {class: 'sub'}, F('%d líneas', r.filas.length) + ' · ' + T('los ficheros están en datos/registro'))),
        r.filas.length ? h('table', null,
          h('thead', null, h('tr', null, [N_('Hora'), N_('Tipo'), N_('Título'), N_('Artista'), N_('Segundos'), N_('Nota')].map(x => h('th', null, T(x))))),
          h('tbody', null, r.filas.slice().reverse().map(f => h('tr', null,
            // el fichero se escribe siempre en español: el tipo y las lineas del sistema se traducen aqui
            h('td', {class: 'mono'}, f.hora), h('td', null, T(f.tipo)), h('td', null, f.tipo === SISTEMA ? T(f.titulo) : f.titulo),
            h('td', {class: 'sub'}, f.artista), h('td', {class: 'mono'}, f.segundos), h('td', {class: 'nota'}, f.nota)))))
          : h('div', {class: 'vacio'}, T('Todavía no se ha emitido nada.'))));
    };
    await pintar('');
  },
};

let pagina = 'emision';
function pintarPagina() {
  for (const b of document.querySelectorAll('#nav button[data-pagina]')) b.classList.toggle('activa', b.dataset.pagina === pagina);
  for (const s of document.querySelectorAll('.pagina')) s.classList.toggle('activa', s.id === 'p-' + pagina);
  if (PAGINAS[pagina] && CFG) PAGINAS[pagina]($('#p-' + pagina));
}
$('#nav').addEventListener('click', e => {
  const p = e.target.dataset && e.target.dataset.pagina;
  if (p) { pagina = p; pintarPagina(); }
});

(async () => {
  await cargarTextos();
  await refrescar();
  setInterval(refrescar, 500);
  setInterval(tic, 250);
  try { await cargarConfig(); pintarPagina(); } catch (e) { avisar(F('No se ha podido leer la configuración: %s', e.message), 10000); }
})();
