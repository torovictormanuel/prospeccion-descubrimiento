"""
Genera los workflows de n8n del sistema de prospección por descubrimiento.

Uso (desde la raíz del repo):  python scripts/build_n8n.py
Las etiquetas de las preguntas del form se leen de form/public/preguntas.js.
"""
import json, subprocess, sys, uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "n8n"
OUT.mkdir(parents=True, exist_ok=True)
FORM = json.loads(subprocess.run(["node", str(RAIZ / "scripts" / "preguntas_json.mjs")],
                                 capture_output=True, text=True, check=True, encoding="utf-8").stdout)

TZ_JS = "const TZ = 'America/Argentina/Buenos_Aires';\n"
FECHAS_JS = r"""
// Las fechas de la planilla pueden venir como 28/10/2026, 2026-10-28 o número de serie
const parseFecha = v => {
  if (v === undefined || v === null || v === '') return null;
  const s = String(v).trim();
  let m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return DateTime.fromObject({ year: +m[3], month: +m[2], day: +m[1] }, { zone: TZ });
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return DateTime.fromObject({ year: +m[1], month: +m[2], day: +m[3] }, { zone: TZ });
  if (/^\d+(\.\d+)?$/.test(s)) return DateTime.fromObject({ year: 1899, month: 12, day: 30 }, { zone: TZ }).plus({ days: Math.floor(+s) });
  return null;
};
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
// '3. Conversación' → 3. '10. Nutrir' cuenta como 0 para poder reactivar el lead.
const numEtapa = e => { const n = parseInt(String(e || '0'), 10) || 0; return n === 10 ? 0 : n; };
"""


class WF:
    def __init__(self, name):
        self.name, self.nodes, self.conn, self.x = name, [], {}, 0

    def node(self, name, type_, version, params, pos=None, **extra):
        if pos is None:
            self.x += 240
            pos = [self.x, 300]
        n = {"parameters": params, "id": str(uuid.uuid4()), "name": name, "type": type_,
             "typeVersion": version, "position": pos}
        n.update(extra)
        self.nodes.append(n)
        return name

    def link(self, a, b, out=0, inp=0):
        outs = self.conn.setdefault(a, {}).setdefault("main", [])
        while len(outs) <= out:
            outs.append([])
        outs[out].append({"node": b, "type": "main", "index": inp})

    def chain(self, *names):
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def save(self, filename, nota):
        self.nodes.append({"parameters": {"content": nota, "height": 420, "width": 520},
                           "id": str(uuid.uuid4()), "name": "Nota", "type": "n8n-nodes-base.stickyNote",
                           "typeVersion": 1, "position": [0, -220]})
        wf = {"name": self.name, "nodes": self.nodes, "connections": self.conn, "active": False,
              "settings": {"executionOrder": "v1", "timezone": "America/Argentina/Buenos_Aires"},
              "pinData": {}, "meta": {"templateCredsSetupCompleted": False}}
        (OUT / filename).write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")


# ── helpers de nodos ─────────────────────────────────────────
def config(wf, campos, pos=None):
    asg = []
    for k, v in campos.items():
        asg.append({"id": str(uuid.uuid4()), "name": k, "value": v,
                    "type": "number" if isinstance(v, (int, float)) else "string"})
    return wf.node("Config", "n8n-nodes-base.set", 3.4,
                   {"mode": "manual", "assignments": {"assignments": asg}, "options": {}}, pos)


def sheet_ref(hoja):
    return ({"__rl": True, "value": "={{ $('Config').first().json.sheetId }}", "mode": "id"},
            {"__rl": True, "value": hoja, "mode": "name"})


def leer(wf, name, hoja="Pipeline", pos=None):
    doc, sh = sheet_ref(hoja)
    return wf.node(name, "n8n-nodes-base.googleSheets", 4.5,
                   {"operation": "read", "documentId": doc, "sheetName": sh, "options": {}}, pos,
                   executeOnce=True, alwaysOutputData=True)


def actualizar(wf, name, pos=None):
    doc, sh = sheet_ref("Pipeline")
    return wf.node(name, "n8n-nodes-base.googleSheets", 4.5,
                   {"operation": "update", "documentId": doc, "sheetName": sh,
                    "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": ["ID"], "schema": []},
                    "options": {"cellFormat": "USER_ENTERED"}}, pos)


def agregar(wf, name, hoja, pos=None):
    doc, sh = sheet_ref(hoja)
    return wf.node(name, "n8n-nodes-base.googleSheets", 4.5,
                   {"operation": "append", "documentId": doc, "sheetName": sh,
                    "columns": {"mappingMode": "autoMapInputData", "value": {}, "schema": []},
                    "options": {"cellFormat": "USER_ENTERED"}}, pos)


def code(wf, name, js, pos=None, por_item=False):
    p = {"jsCode": js}
    if por_item:
        p["mode"] = "runOnceForEachItem"
    return wf.node(name, "n8n-nodes-base.code", 2, p, pos)


def mail(wf, name, pos=None):
    return wf.node(name, "n8n-nodes-base.gmail", 2.1,
                   {"sendTo": "={{ $('Config').first().json.miEmail }}", "subject": "={{ $json.asunto }}",
                    "emailType": "html", "message": "={{ $json.html }}", "options": {"appendAttribution": False}}, pos)


def schedule(wf, name, rule, pos=None):
    return wf.node(name, "n8n-nodes-base.scheduleTrigger", 1.2, {"rule": {"interval": [rule]}}, pos)


# ════════════════════════════════════════════════════════════
# 01 — Agente investigador + cola diaria de LinkedIn
# ════════════════════════════════════════════════════════════
w = WF("01 Investigador + cola diaria LinkedIn")
t = schedule(w, "Lunes a viernes 8:30", {"field": "cronExpression", "expression": "30 8 * * 1-5"})
c = config(w, {
    "sheetId": "PEGAR_ID_DEL_GOOGLE_SHEET",
    "miEmail": "TU_EMAIL@gmail.com",
    "waNumero": "549XXXXXXXXXX",
    "calLink": "https://cal.com/victor-toro-sa1hch/descubrimiento",
    "formUrl": "https://TU-FORM.vercel.app",
    "geminiModelo": "gemini-2.5-flash",
    "leadsPorDia": 12,
    "tokenAcciones": "PEGAR_TOKEN_LARGO_ALEATORIO",
    "n8nUrl": "http://localhost:5678",
})
l1 = leer(w, "Leer pipeline")

ELEGIR = TZ_JS + r"""
// Elige los leads a investigar hoy: Activos, sin mensajes todavía y con perfil personal de LinkedIn.
const cfg = $('Config').first().json;
const peso = { Alta: 0, Media: 1 };  // Baja queda afuera a propósito
const filas = $input.all().map(i => i.json).filter(f => f.ID !== undefined && f.ID !== '');
const elegidos = filas.filter(f =>
  String(f['Secuencia'] || '').trim() === 'Activa' &&
  String(f['No contactar'] || '').toUpperCase() !== 'SI' &&
  ['1. Prospecto', '2. Contactado'].includes(f['Etapa']) &&
  Number(f['Paso LinkedIn'] || 0) === 0 &&
  !String(f['Mensaje 1'] || '').trim() &&
  /linkedin\.com\/in\//i.test(String(f['LinkedIn / Web'] || '')) &&
  f['Prioridad'] in peso
).sort((a, b) => peso[a['Prioridad']] - peso[b['Prioridad']] || Number(a.ID) - Number(b.ID))
 .slice(0, Number(cfg.leadsPorDia) || 12);

// Sin leads nuevos igual hay que pasar por el loop para que salga el mail con los seguimientos
if (!elegidos.length) return [{ json: { vacio: true } }];
return elegidos.map(f => {
  const esEstudio = String(f['Segmento']).startsWith('Estudio');
  const rubro = esEstudio ? 'estudio contable' : 'vendedor/tienda de Mercado Libre';
  const prompt = `Sos un investigador de prospectos B2B en Argentina. Buscá en Google información PÚBLICA y verificable sobre este ${rubro}:
- Empresa: ${f['Empresa']}
- Ubicación: ${f['Ubicación'] || 'Argentina'}
- Persona: ${f['Contacto'] || '(sin nombre)'} — ${f['Cargo'] || ''}
No inventes datos. No uses información privada de LinkedIn.

Contexto: Victor Toro es analista de datos y está ESTUDIANDO cómo mejorar los procesos internos de ${esEstudio ? 'los estudios contables de 10 a 50 personas' : 'los vendedores de Mercado Libre'} (qué tareas se repiten, dónde se va el tiempo). NO vende nada: quiere entender el problema antes de proponer soluciones. Para no quitarle tiempo, le pide completar un form de 4 minutos; a cambio ofrece el informe con los resultados de todos y un diagnóstico para su estudio.

Devolvé SOLO un objeto JSON, sin texto extra, con estas claves:
"dato": una frase con un dato real y específico de la empresa (servicios, especialidad, tipo de clientes, antigüedad, novedad). Si no encontrás nada verificable, "".
"fuente": URL de donde sacaste el dato, o "".
"conexion": nota de solicitud de conexión de LinkedIn, máximo 250 caracteres, sin pitch, que mencione el dato si existe.
"mensaje1": mensaje tras aceptar, máximo 700 caracteres, muy amable. Se presenta como Victor, explica que está estudiando cómo mejorar los procesos internos de los estudios, aclara que no vende nada, pide que complete el form de 4 minutos y ofrece a cambio el informe con los resultados de todos y un diagnóstico para su estudio. Incluí LITERALMENTE el marcador {LINK_FORM} (el form) y, como alternativa si prefiere charlar directo, {LINK_AGENDA}.
"mensaje2": seguimiento de máximo 300 caracteres: recordá el form con {LINK_FORM} y, si no tiene ni 4 minutos, hacé UNA sola pregunta que pueda contestar ahí: cuál es la tarea que más tiempo le saca al equipo cada mes.
"cierre": cierre amable de máximo 250 caracteres, sin insistir, ofreciendo el informe cuando esté listo.
Español rioplatense, con "vos", tono cercano y profesional. Tuteá usando su nombre de pila si lo tenés.`;
  return { json: {
    ID: f.ID, empresa: f['Empresa'], contacto: f['Contacto'] || '', esEstudio,
    geminiBody: { contents: [{ role: 'user', parts: [{ text: prompt }] }], tools: [{ google_search: {} }],
                  generationConfig: { temperature: 0.5 } },
  } };
});
"""
e1 = code(w, "Elegir leads del día", ELEGIR)
loop = w.node("Uno por uno", "n8n-nodes-base.splitInBatches", 3, {"options": {}})
es_lead = w.node("¿Hay lead?", "n8n-nodes-base.if", 2.2, {
    "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                   "conditions": [{"id": str(uuid.uuid4()), "leftValue": "={{ $json.vacio }}", "rightValue": "",
                                   "operator": {"type": "boolean", "operation": "notTrue", "singleValue": True}}],
                   "combinator": "and"}, "options": {}}, [w.x + 240, 160])
w.x += 240
gem = w.node("Gemini investiga", "n8n-nodes-base.httpRequest", 4.2, {
    "method": "POST",
    "url": "=https://generativelanguage.googleapis.com/v1beta/models/{{ $('Config').first().json.geminiModelo }}:generateContent",
    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
    "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.geminiBody) }}",
    "options": {"timeout": 90000},
}, [w.x + 240, 160], onError="continueRegularOutput")

ARMAR = TZ_JS + r"""
// Convierte la respuesta de Gemini en los textos finales, con los links reales.
// Si Gemini falló o devolvió algo raro, se usan plantillas por defecto.
const cfg = $('Config').first().json;
const lead = $('Uno por uno').item.json;
const id = String(lead.ID);
const hoy = $now.setZone(TZ).toFormat('yyyy-MM-dd');
const waLink = `https://wa.me/${cfg.waNumero}?text=${encodeURIComponent(`Hola Victor, vengo de LinkedIn (ref ${id})`)}`;
const agendaLink = `${cfg.calLink}?metadata[ref]=${id}&notes=${encodeURIComponent('ref ' + id)}`;
// Código aleatorio para el link del form: identifica al lead sin exponer su ID ni datos personales
const ABC = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
const codigo = Array.from({ length: 8 }, () => ABC[Math.floor(Math.random() * ABC.length)]).join('');
const formLink = `${String(cfg.formUrl).replace(/\/$/, '')}/?c=${codigo}&f=linkedin`;

let r = {};
try {
  const texto = ($json.candidates?.[0]?.content?.parts || []).map(p => p.text || '').join('');
  r = JSON.parse(texto.slice(texto.indexOf('{'), texto.lastIndexOf('}') + 1));
} catch (e) { r = {}; }

const nombre = String(lead.contacto || '').split(' ')[0];
const hola = nombre ? `Hola ${nombre}` : 'Hola';
const rubro = lead.esEstudio ? 'los estudios contables de 10 a 50 personas' : 'los vendedores de Mercado Libre';
const def = {
  conexion: `${hola}, estoy estudiando cómo mejorar los procesos internos de ${rubro} en Argentina y me gustaría sumarte a mi red.`,
  mensaje1: `${hola}, ¡gracias por conectar! Soy Victor Toro, analista de datos. Estoy estudiando cómo mejorar los procesos internos de ${rubro}: qué tareas se repiten todos los meses y dónde se va el tiempo del equipo. No vendo nada: quiero entender bien el problema antes de proponer soluciones.\n\nPara no quitarte tiempo armé un form de 4 minutos: {LINK_FORM}\n\nA cambio te mando el informe con los resultados de todos los estudios y, si querés, un diagnóstico con ideas para el tuyo. Si preferís charlarlo directo, 20 min: {LINK_AGENDA}`,
  mensaje2: `${hola}, ¿pudiste ver el form? ({LINK_FORM}) Si no tenés ni 4 minutos, me sirve igual que me contestes solo esto: ¿cuál es la tarea que más tiempo le saca a tu equipo cada mes?`,
  cierre: `${hola}, no te escribo más sobre esto. Si en algún momento querés contarme cómo trabajan o recibir el informe cuando esté listo, respondeme por acá. ¡Gracias!`,
};
const reemplazar = s => String(s).split('{LINK_FORM}').join(formLink).split('{LINK_AGENDA}').join(agendaLink).split('{LINK_WHATSAPP}').join(waLink);
const txt = k => reemplazar(String(r[k] || '').trim() || def[k]);
let m1 = txt('mensaje1');
if (!m1.includes(formLink)) m1 = reemplazar(def.mensaje1);  // el link del form es obligatorio

return { json: {
  'ID': lead.ID,
  'Dato investigado': r.dato ? `${r.dato}${r.fuente ? ' (' + r.fuente + ')' : ''}` : ($json.error ? 'Gemini no respondió: revisar a mano' : ''),
  'Mensaje conexión': txt('conexion').slice(0, 295),
  'Mensaje 1': m1,
  'Mensaje 2': txt('mensaje2'),
  'Mensaje cierre': txt('cierre'),
  'Link WhatsApp': waLink,
  'Link agenda': agendaLink,
  'Código': codigo,
  'Link form': formLink,
  'Próxima acción': 'Enviar solicitud de conexión en LinkedIn',
  'Fecha próx. acción': hoy,
} };
"""
arm = code(w, "Armar mensajes", ARMAR, [w.x + 480, 160], por_item=True)
gua = actualizar(w, "Guardar mensajes", [w.x + 720, 160])
pau = w.node("Pausa (límite Gemini gratis)", "n8n-nodes-base.wait", 1.1, {"amount": 5, "unit": "seconds"},
             [w.x + 960, 160], webhookId=str(uuid.uuid4()))
l2 = leer(w, "Leer pipeline actualizado", pos=[w.x + 240, 440])

COLA = TZ_JS + FECHAS_JS + r"""
// Arma el mail con las tareas de LinkedIn de hoy. Cada tarea trae el mensaje listo
// y botones que actualizan la planilla (workflow 04).
const cfg = $('Config').first().json;
const hoy = $now.setZone(TZ).startOf('day');
const filas = $input.all().map(i => i.json).filter(f => f.ID !== undefined && f.ID !== '');
const vence = f => { const d = parseFecha(f['Fecha próx. acción']); return !d || d <= hoy; };
const url = (f, accion, paso = '') =>
  `${cfg.n8nUrl}/webhook/pipeline-accion?id=${encodeURIComponent(f.ID)}&accion=${accion}&paso=${paso}&t=${encodeURIComponent(cfg.tokenAcciones)}`;
const btn = (href, texto, color) =>
  `<a href="${href}" style="display:inline-block;margin:4px 6px 0 0;padding:6px 12px;border-radius:6px;background:${color};color:#fff;text-decoration:none;font-size:13px">${texto}</a>`;

const PASOS = {
  0: { col: 'Mensaje conexión', titulo: '1 · Enviá la solicitud de conexión', sig: 1 },
  1: { col: 'Mensaje 1', titulo: '2 · Si aceptó, mandá el Mensaje 1', sig: 2 },
  2: { col: 'Mensaje 2', titulo: '3 · Seguimiento con una sola pregunta', sig: 3 },
  3: { col: 'Mensaje cierre', titulo: '4 · Mensaje de cierre', sig: 4 },
};
const activos = filas.filter(f =>
  String(f['Secuencia'] || '') === 'Activa' && String(f['No contactar'] || '').toUpperCase() !== 'SI' &&
  ['1. Prospecto', '2. Contactado'].includes(f['Etapa']) && String(f['Mensaje 1'] || '').trim());

let html = `<div style="font-family:Arial,sans-serif;max-width:680px">`;
let total = 0;
for (const [paso, p] of Object.entries(PASOS)) {
  const lista = activos.filter(f => Number(f['Paso LinkedIn'] || 0) === Number(paso) && vence(f));
  if (!lista.length) continue;
  total += lista.length;
  html += `<h3 style="margin:24px 0 8px">${p.titulo} (${lista.length})</h3>`;
  for (const f of lista) {
    html += `<div style="border:1px solid #ddd;border-radius:8px;padding:12px;margin-bottom:10px">
      <b>${esc(f['Empresa'])}</b> — ${esc(f['Contacto'])} <span style="color:#666">${esc(f['Cargo'])}</span><br>
      <a href="${esc(f['LinkedIn / Web'])}">Abrir perfil de LinkedIn</a>
      ${f['Dato investigado'] ? `<div style="color:#555;font-size:12px;margin-top:4px">🔎 ${esc(f['Dato investigado'])}</div>` : ''}
      <div style="background:#f6f8fa;border-radius:6px;padding:10px;margin-top:8px;font-size:14px">${esc(f[p.col])}</div>
      ${btn(url(f, 'enviado', p.sig), '✅ Enviado', '#2e7d32')}
      ${Number(paso) === 1 ? btn(url(f, 'esperar'), '⏳ Todavía no aceptó', '#757575') : ''}
      ${Number(paso) > 0 ? btn(url(f, 'respondio'), '💬 Respondió', '#1565c0') : ''}
      ${btn(url(f, 'descartar'), '✖ Descartar', '#c62828')}
    </div>`;
  }
}

// Leads que necesitan que respondas vos (escalados por el agente o que contestaron en LinkedIn)
const tuyos = filas.filter(f => /^Responder/i.test(String(f['Próxima acción'] || '')) && vence(f) && !String(f['Etapa']).startsWith('9.'));
if (tuyos.length) {
  html += `<h3 style="margin:24px 0 8px">💬 Te toca responder (${tuyos.length})</h3><ul>`;
  for (const f of tuyos) html += `<li><b>${esc(f['Empresa'])}</b> — ${esc(f['Próxima acción'])}${f['WhatsApp'] ? ` · <a href="https://wa.me/${String(f['WhatsApp']).replace(/\D/g, '')}">WhatsApp</a>` : ''}</li>`;
  html += `</ul>`;
}

// Leads Activos sin perfil personal: hay que buscar al decisor a mano
const sinPerfil = filas.filter(f => String(f['Secuencia']) === 'Activa' && ['Alta', 'Media'].includes(f['Prioridad']) &&
  String(f['Etapa']) === '1. Prospecto' && !/linkedin\.com\/in\//i.test(String(f['LinkedIn / Web'] || ''))).slice(0, 5);
if (sinPerfil.length) {
  html += `<h3 style="margin:24px 0 8px">🔍 Buscá al socio o dueño (5 de ${filas.filter(f => String(f['Secuencia']) === 'Activa' && !/linkedin\.com\/in\//i.test(String(f['LinkedIn / Web'] || ''))).length})</h3>
    <p style="font-size:13px;color:#555">Pegá su perfil en la columna "LinkedIn / Web" y su nombre en "Contacto". Mañana el investigador le arma los mensajes.</p><ul>`;
  for (const f of sinPerfil) html += `<li>${esc(f['Empresa'])} — ${esc(f['Ubicación'])}${f['LinkedIn / Web'] ? ` · <a href="${esc(f['LinkedIn / Web'])}">página actual</a>` : ''}</li>`;
  html += `</ul>`;
}
html += `<p style="color:#888;font-size:12px;margin-top:24px">Los botones funcionan en la PC donde corre n8n. Si cerraste n8n, actualizá la planilla a mano.</p></div>`;

if (!total && !tuyos.length && !sinPerfil.length) return [];
return [{ json: { asunto: `Prospección de hoy: ${total} mensajes de LinkedIn${tuyos.length ? ` + ${tuyos.length} para responder` : ''}`, html } }];
"""
cola = code(w, "Armar cola del día", COLA, [w.x + 480, 440])
env = mail(w, "Mandar cola por mail", [w.x + 720, 440])

w.chain(t, c, l1, e1, loop)
w.link(loop, l2, out=0)       # salida "done": terminó de investigar
w.link(loop, es_lead, out=1)  # salida "loop": un lead por vez
w.link(es_lead, gem, out=0)
w.link(es_lead, loop, out=1)  # ítem vacío: vuelve directo al loop
w.chain(gem, arm, gua, pau)
w.link(pau, loop)
w.chain(l2, cola, env)
w.save("01_investigador_cola_linkedin.json",
       "## 01 · Agente investigador + cola diaria\n"
       "1. Completá el nodo **Config** (ID del Sheet, tu email, número de WhatsApp del agente, link de Cal.com, token).\n"
       "2. Credenciales: Google Sheets OAuth2, Gmail OAuth2 y una **Header Auth** para Gemini con nombre `x-goog-api-key` y tu API key de Google AI Studio (gratis).\n"
       "3. Si Gemini da error 404 o 429, cambiá `geminiModelo` por el modelo gratis vigente en ai.google.dev.\n"
       "4. Activá el workflow. Corre de lunes a viernes a las 8:30.")

# ════════════════════════════════════════════════════════════
# 02 — Sync del agente de WhatsApp → Sheet + avisos
# ════════════════════════════════════════════════════════════
w = WF("02 Sync agente WhatsApp")
t = schedule(w, "Cada 15 minutos", {"field": "minutes", "minutesInterval": 15})
c = config(w, {"sheetId": "PEGAR_ID_DEL_GOOGLE_SHEET", "miEmail": "TU_EMAIL@gmail.com",
               "agenteUrl": "https://TU-URL-DEL-AGENTE"})
cur = code(w, "Cursor", r"""
// Último evento ya procesado. Se guarda en los datos estáticos del workflow
// (solo persisten en ejecuciones automáticas, no al probar con 'Execute').
const s = $getWorkflowStaticData('global');
return [{ json: { desde_id: s.ultimoId || 0 } }];
""")
tr = w.node("Traer eventos", "n8n-nodes-base.httpRequest", 4.2, {
    "url": "={{ $('Config').first().json.agenteUrl }}/api/eventos",
    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
    "sendQuery": True, "queryParameters": {"parameters": [{"name": "desde_id", "value": "={{ $json.desde_id }}"}]},
    "options": {"timeout": 30000},
})
ifn = w.node("¿Hay eventos?", "n8n-nodes-base.if", 2.2, {
    "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                   "conditions": [{"id": str(uuid.uuid4()), "leftValue": "={{ $json.eventos.length }}", "rightValue": 0,
                                   "operator": {"type": "number", "operation": "gt"}}],
                   "combinator": "and"}, "options": {}})
lp = leer(w, "Leer pipeline")
PROC = TZ_JS + FECHAS_JS + r"""
// Traduce los eventos del agente a cambios en la planilla, filas de Hallazgos y avisos.
const resp = $('Traer eventos').first().json;
const eventos = resp.eventos || [];
const filas = $('Leer pipeline').all().map(i => i.json).filter(f => f.ID !== undefined && f.ID !== '');
const porId = Object.fromEntries(filas.map(f => [String(f.ID), f]));
const porCodigo = Object.fromEntries(filas.filter(f => f['Código']).map(f => [String(f['Código']), f]));
const hoy = $now.setZone(TZ).toFormat('yyyy-MM-dd');
const updates = {}, hallazgos = [], avisos = [];

for (const e of eventos) {
  const d = e.detalle || {};
  // ref = ID numérico (link de LinkedIn) o Código (link del form)
  const fila = e.ref ? (porId[String(e.ref)] || porCodigo[String(e.ref)]) : null;
  const cuando = DateTime.fromISO(e.creado_en).setZone(TZ);
  const quien = fila ? `${fila['Empresa']} (${fila['Contacto'] || e.nombre || 'sin nombre'})`
                     : `${e.nombre || 'Alguien'}${e.empresa ? ' de ' + e.empresa : ''} — +${e.telefono} (sin ref)`;
  const wa = `<a href="https://wa.me/${e.telefono}">abrir chat</a>`;

  if (e.tipo === 'hallazgo') hallazgos.push({
    'Fecha': cuando.toFormat('yyyy-MM-dd'), 'ID': fila ? fila.ID : '', 'Empresa': fila ? fila['Empresa'] : (e.empresa || ''),
    'Contacto': fila ? fila['Contacto'] : (e.nombre || ''), 'Tema': d.tema || '', 'Descripción': d.descripcion || '',
    'Frecuencia': d.frecuencia || '', 'Impacto': d.impacto || '', 'Herramienta actual': d.herramienta_actual || '',
    'Cita textual': d.cita_textual || '', 'Fuente': 'WhatsApp' });

  if (!fila) {
    if (['primer_contacto', 'agendado', 'escalar'].includes(e.tipo)) avisos.push(`<b>${e.tipo}</b>: ${esc(quien)} · ${wa}`);
    continue;
  }
  const u = updates[fila.ID] ??= { 'ID': fila.ID };
  const etapa = () => u['Etapa'] || fila['Etapa'];
  const subir = nueva => {
    if (/^(8|9)\./.test(String(etapa()))) return;
    if (numEtapa(nueva) > numEtapa(etapa())) u['Etapa'] = nueva;
  };

  switch (e.tipo) {
    case 'primer_contacto':
      subir('3. Conversación');
      Object.assign(u, { 'Canal': 'WhatsApp', 'WhatsApp': '+' + e.telefono, 'Secuencia': 'Pausada',
        'Último contacto': cuando.toFormat('yyyy-MM-dd'), 'Próxima acción': 'Conversando con Lía por WhatsApp',
        'Toques': Number(fila['Toques'] || 0) + 1 });
      avisos.push(`📲 <b>${esc(quien)}</b> escribió por WhatsApp · ${wa}`);
      break;
    case 'datos':
      if (d.nombre && !fila['Contacto']) u['Contacto'] = d.nombre;
      if (d.email && !fila['Email']) u['Email'] = d.email;
      break;
    case 'hallazgo': {
      const base = u['Dolor detectado'] ?? fila['Dolor detectado'] ?? '';
      u['Dolor detectado'] = ((base ? base + ' | ' : '') + `${d.tema}: ${d.descripcion}`).slice(0, 1500);
      break;
    }
    case 'agendado': {
      const ini = DateTime.fromISO(d.inicio).setZone(TZ);
      subir('4. Reunión agendada');
      Object.assign(u, { 'Fecha próx. acción': ini.toFormat('yyyy-MM-dd'),
        'Próxima acción': `Llamada de descubrimiento ${ini.toFormat('dd/MM HH:mm')}` });
      avisos.push(`📅 <b>${esc(quien)}</b> agendó la llamada para el <b>${ini.toFormat('dd/MM HH:mm')}</b><br>
        <span style="color:#555">Lo que ya contó: ${esc(u['Dolor detectado'] ?? fila['Dolor detectado'] ?? '—')}</span>`);
      break;
    }
    case 'no_contactar':
      Object.assign(u, { 'Etapa': '9. Perdido', 'No contactar': 'SI', 'Secuencia': 'Terminada', 'Próxima acción': '' });
      avisos.push(`🚫 ${esc(quien)} pidió no ser contactado (${esc(d.motivo)})`);
      break;
    case 'escalar':
      Object.assign(u, { 'Próxima acción': `Responder por WhatsApp: ${d.motivo}`, 'Fecha próx. acción': hoy });
      avisos.push(`⚠️ <b>${esc(quien)}</b> necesita que le respondas vos: ${esc(d.motivo)} · ${wa}`);
      break;
  }
}

// Se avanza el cursor acá: si una escritura posterior falla, ese lote no se reintenta
// (queda en el agente y en el mail de aviso, se puede cargar a mano).
$getWorkflowStaticData('global').ultimoId = resp.ultimo_id;
return [{ json: { updates: Object.values(updates), hallazgos, avisos } }];
"""
pr = code(w, "Procesar eventos", PROC)
x0 = w.x
s1 = code(w, "Filas a actualizar", "return $json.updates.map(u => ({ json: u }));", [x0 + 240, 140])
a1 = actualizar(w, "Actualizar pipeline", [x0 + 480, 140])
s2 = code(w, "Hallazgos a cargar", "return $json.hallazgos.map(h => ({ json: h }));", [x0 + 240, 300])
a2 = agregar(w, "Cargar hallazgos", "Hallazgos", [x0 + 480, 300])
s3 = code(w, "Armar aviso", r"""
const avisos = $json.avisos;
if (!avisos.length) return [];
const html = `<div style="font-family:Arial,sans-serif;max-width:680px"><ul>${avisos.map(a => `<li style="margin-bottom:10px">${a}</li>`).join('')}</ul></div>`;
return [{ json: { asunto: `Pipeline: ${avisos.length} novedad${avisos.length > 1 ? 'es' : ''} del agente de WhatsApp`, html } }];
""", [x0 + 240, 460])
m3 = mail(w, "Avisarme", [x0 + 480, 460])
w.chain(t, c, cur, tr, ifn)
w.link(ifn, lp, out=0)
w.chain(lp, pr)
for a, b in ((s1, a1), (s2, a2), (s3, m3)):
    w.link(pr, a)
    w.link(a, b)
w.save("02_sync_agente_whatsapp.json",
       "## 02 · Sync del agente de WhatsApp\n"
       "1. **Config**: ID del Sheet, tu email y la URL pública del agente (sin barra final).\n"
       "2. Credencial **Header Auth** en *Traer eventos*: nombre `X-API-Key`, valor = `SYNC_API_KEY` del .env del agente.\n"
       "3. Activá el workflow: el cursor de eventos solo se guarda en ejecuciones automáticas.")

# ════════════════════════════════════════════════════════════
# 03 — Sync de reservas de Cal.com → Sheet + avisos
# ════════════════════════════════════════════════════════════
w = WF("03 Sync reservas Cal.com")
t = schedule(w, "Cada 30 minutos", {"field": "minutes", "minutesInterval": 30})
c = config(w, {"sheetId": "PEGAR_ID_DEL_GOOGLE_SHEET", "miEmail": "TU_EMAIL@gmail.com"})
tr = w.node("Traer reservas", "n8n-nodes-base.httpRequest", 4.2, {
    "url": "https://api.cal.com/v2/bookings",
    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
    "sendQuery": True, "queryParameters": {"parameters": [{"name": "status", "value": "upcoming"}, {"name": "take", "value": "100"}]},
    "sendHeaders": True, "headerParameters": {"parameters": [{"name": "cal-api-version", "value": "2026-02-25"}]},
    "options": {"timeout": 30000},
})
lp = leer(w, "Leer pipeline")
RES = TZ_JS + FECHAS_JS + r"""
// Vincula cada reserva nueva de Cal.com con su fila: primero por la ref del link,
// después por el email del invitado.
const s = $getWorkflowStaticData('global');
s.uids = s.uids || [];
const reservas = $('Traer reservas').first().json.data || [];
const filas = $('Leer pipeline').all().map(i => i.json).filter(f => f.ID !== undefined && f.ID !== '');
const porId = Object.fromEntries(filas.map(f => [String(f.ID), f]));
const porCodigo = Object.fromEntries(filas.filter(f => f['Código']).map(f => [String(f['Código']), f]));
const porEmail = Object.fromEntries(filas.filter(f => f['Email']).map(f => [String(f['Email']).toLowerCase(), f]));
const updates = [], avisos = [];

for (const b of reservas) {
  if (String(b.status || '').toLowerCase() !== 'accepted' || s.uids.includes(b.uid)) continue;
  s.uids.push(b.uid);
  let ref = b.metadata?.ref;
  if (!ref) { const m = JSON.stringify(b).match(/ref\s*#?\s*(\d{1,6})/i); if (m) ref = m[1]; }
  const codigo = b.metadata?.codigo;  // reserva hecha desde la pantalla final del form
  const inv = (b.attendees || [])[0] || {};
  const fila = (ref && porId[String(ref)]) || (codigo && porCodigo[String(codigo)]) ||
               (inv.email && porEmail[String(inv.email).toLowerCase()]) || null;
  const ini = DateTime.fromISO(b.start).setZone(TZ);
  const viaAgente = !!b.metadata?.telefono;  // el workflow 02 ya avisó estas

  if (fila) {
    const u = { 'ID': fila.ID, 'Fecha próx. acción': ini.toFormat('yyyy-MM-dd'),
      'Próxima acción': `Llamada de descubrimiento ${ini.toFormat('dd/MM HH:mm')}`, 'Secuencia': 'Pausada' };
    if (!/^(8|9)\./.test(String(fila['Etapa'])) && numEtapa(fila['Etapa']) < 4) u['Etapa'] = '4. Reunión agendada';
    if (!fila['Email'] && inv.email) u['Email'] = inv.email;
    updates.push(u);
  }
  if (!viaAgente) avisos.push(`📅 <b>${esc(fila ? fila['Empresa'] : inv.name || 'Alguien')}</b>${fila ? ` (${esc(fila['Contacto'])})` : ' — no la encontré en la planilla'}
    reservó para el <b>${ini.toFormat('dd/MM HH:mm')}</b> · ${esc(inv.email)}
    ${fila ? `<br><span style="color:#555">Dolor detectado: ${esc(fila['Dolor detectado'] || '—')} · <a href="${esc(fila['LinkedIn / Web'])}">perfil</a></span>` : ''}`);
}
s.uids = s.uids.slice(-500);
return [{ json: { updates, avisos } }];
"""
pr = code(w, "Procesar reservas", RES)
x0 = w.x
s1 = code(w, "Filas a actualizar", "return $json.updates.map(u => ({ json: u }));", [x0 + 240, 200])
a1 = actualizar(w, "Actualizar pipeline", [x0 + 480, 200])
s3 = code(w, "Armar aviso", r"""
const avisos = $json.avisos;
if (!avisos.length) return [];
const html = `<div style="font-family:Arial,sans-serif;max-width:680px"><ul>${avisos.map(a => `<li style="margin-bottom:10px">${a}</li>`).join('')}</ul><p>Guion de la llamada: hoja "Guion llamada" de la planilla.</p></div>`;
return [{ json: { asunto: `Nueva llamada de descubrimiento agendada (${avisos.length})`, html } }];
""", [x0 + 240, 400])
m3 = mail(w, "Avisarme", [x0 + 480, 400])
w.chain(t, c, tr, lp, pr)
for a, b in ((s1, a1), (s3, m3)):
    w.link(pr, a)
    w.link(a, b)
w.save("03_sync_reservas_calcom.json",
       "## 03 · Sync de reservas de Cal.com\n"
       "1. **Config**: ID del Sheet y tu email.\n"
       "2. Credencial **Header Auth** en *Traer reservas*: nombre `Authorization`, valor `Bearer cal_live_...` (Cal.com → Settings → Developer → API Keys).\n"
       "3. Funciona aunque n8n corra local: consulta Cal.com, no necesita webhook público.")

# ════════════════════════════════════════════════════════════
# 04 — Botones del mail diario → actualizan la planilla
# ════════════════════════════════════════════════════════════
w = WF("04 Botones del mail diario")
t = w.node("Botón del mail", "n8n-nodes-base.webhook", 2,
           {"httpMethod": "GET", "path": "pipeline-accion", "responseMode": "responseNode", "options": {}},
           webhookId=str(uuid.uuid4()))
c = config(w, {"sheetId": "PEGAR_ID_DEL_GOOGLE_SHEET", "tokenAcciones": "PEGAR_TOKEN_LARGO_ALEATORIO"})
lp = leer(w, "Leer pipeline")
ACC = TZ_JS + r"""
// Aplica el botón que tocaste en el mail. El token evita que otro sitio dispare acciones.
const cfg = $('Config').first().json;
const q = $('Botón del mail').first().json.query || {};
if (!cfg.tokenAcciones || cfg.tokenAcciones.startsWith('PEGAR') || q.t !== cfg.tokenAcciones) throw new Error('Token inválido');
const fila = $input.all().map(i => i.json).find(f => String(f.ID) === String(q.id));
if (!fila) throw new Error(`No encontré el lead ${q.id}`);
const hoy = $now.setZone(TZ);
const fmt = d => d.toFormat('yyyy-MM-dd');
const u = { 'ID': fila.ID };

switch (q.accion) {
  case 'enviado': {
    const paso = Number(q.paso);
    if (![1, 2, 3, 4].includes(paso)) throw new Error('Paso inválido');
    if (Number(fila['Paso LinkedIn'] || 0) >= paso) break;  // doble clic: no se cuenta dos veces
    const dias = { 1: 3, 2: 4, 3: 6, 4: 7 }[paso];
    const prox = { 1: 'Ver si aceptó y mandar Mensaje 1', 2: 'Mandar Mensaje 2 si no respondió',
                   3: 'Mandar mensaje de cierre', 4: 'Sin respuesta: pasar a Nutrir o Perdido' }[paso];
    Object.assign(u, { 'Paso LinkedIn': paso, 'Toques': Number(fila['Toques'] || 0) + 1, 'Canal': 'LinkedIn',
      'Etapa': fila['Etapa'] === '1. Prospecto' ? '2. Contactado' : fila['Etapa'],
      'Último contacto': fmt(hoy), 'Fecha próx. acción': fmt(hoy.plus({ days: dias })), 'Próxima acción': prox });
    if (paso === 4) u['Secuencia'] = 'Terminada';
    break;
  }
  case 'esperar':
    Object.assign(u, { 'Fecha próx. acción': fmt(hoy.plus({ days: 3 })), 'Próxima acción': 'Ver si aceptó la solicitud' });
    break;
  case 'respondio':
    Object.assign(u, { 'Etapa': '3. Conversación', 'Secuencia': 'Pausada', 'Último contacto': fmt(hoy),
      'Próxima acción': 'Responder en LinkedIn y pasarle el link de WhatsApp o de agenda', 'Fecha próx. acción': fmt(hoy) });
    break;
  case 'descartar':
    Object.assign(u, { 'Etapa': '9. Perdido', 'Secuencia': 'Terminada', 'Próxima acción': '', 'Fecha próx. acción': '' });
    break;
  default:
    throw new Error('Acción inválida');
}
return [{ json: u }];
"""
ac = code(w, "Aplicar acción", ACC)
up = actualizar(w, "Actualizar pipeline")
rs = w.node("Responder", "n8n-nodes-base.respondToWebhook", 1.1, {
    "respondWith": "text",
    "responseBody": "=<html><body style=\"font-family:Arial;padding:40px\"><h2>✅ Listo</h2>"
                    "<p>Actualicé el lead {{ $('Botón del mail').first().json.query.id }} "
                    "({{ $('Botón del mail').first().json.query.accion }}). Podés cerrar esta pestaña.</p></body></html>",
    "options": {"responseHeaders": {"entries": [{"name": "Content-Type", "value": "text/html; charset=utf-8"}]}},
})
w.chain(t, c, lp, ac, up, rs)
w.save("04_botones_mail_diario.json",
       "## 04 · Botones del mail diario\n"
       "1. **Config**: el mismo ID del Sheet y el **mismo token** que en el workflow 01.\n"
       "2. Activá el workflow. Los botones del mail llaman a http://localhost:5678/webhook/pipeline-accion, "
       "así que funcionan en la PC donde corre n8n.")

# ════════════════════════════════════════════════════════════
# 05 — Respuestas del form (Supabase) → Pipeline, Hallazgos, Respuestas form
# ════════════════════════════════════════════════════════════
w = WF("05 Sync respuestas del form")
t = schedule(w, "Cada 15 minutos", {"field": "minutes", "minutesInterval": 15})
c = config(w, {"sheetId": "PEGAR_ID_DEL_GOOGLE_SHEET", "miEmail": "TU_EMAIL@gmail.com"})
cur = code(w, "Cursor", r"""
// Última respuesta ya procesada (solo persiste en ejecuciones automáticas).
return [{ json: { desde_id: $getWorkflowStaticData('global').ultimoId || 0 } }];
""")
sb = w.node("Traer respuestas", "n8n-nodes-base.supabase", 1, {
    "operation": "getAll", "tableId": "respuestas_descubrimiento", "returnAll": True,
    "filterType": "string", "filterString": "=id=gt.{{ $json.desde_id }}",
})
lp = leer(w, "Leer pipeline")
FORM_JS = "const PREG = " + json.dumps(FORM["preguntas"], ensure_ascii=False) + ";\n"
RESP = TZ_JS + FECHAS_JS + FORM_JS + r"""
// Cada respuesta del form actualiza su lead (por código del link o por email),
// crea filas en Hallazgos y una fila completa en "Respuestas form" para analizar patrones.
const respuestas = $('Traer respuestas').all().map(i => i.json).filter(r => r.id).sort((a, b) => a.id - b.id);
const filas = $('Leer pipeline').all().map(i => i.json).filter(f => f.ID !== undefined && f.ID !== '');
const porCodigo = Object.fromEntries(filas.filter(f => f['Código']).map(f => [String(f['Código']), f]));
const porEmail = Object.fromEntries(filas.filter(f => f['Email']).map(f => [String(f['Email']).toLowerCase(), f]));
let maxId = Math.max(0, ...filas.map(f => Number(f.ID) || 0));
const etiqueta = (p, v) => Array.isArray(v) ? v.map(x => p.opciones[x] || x).join(', ') : (p.opciones[v] ?? (v === true ? 'Sí' : v ?? ''));
const pregunta = Object.fromEntries(PREG.map(p => [p.id, p]));
// WhatsApp argentino sin código de país (10 dígitos) → formato internacional para wa.me
const normalizarWa = n => { const d = String(n || '').replace(/\D/g, ''); if (!d) return ''; return '+' + (d.length === 10 ? '549' + d : d); };

const updates = [], nuevos = [], hallazgos = [], crudas = [], avisos = [];
for (const r of respuestas) {
  const a = r.respuestas || {};
  const cuando = DateTime.fromISO(r.created_at).setZone(TZ);
  const fecha = cuando.toFormat('yyyy-MM-dd');
  let fila = (r.codigo && porCodigo[r.codigo]) || porEmail[String(r.email || '').toLowerCase()] || null;
  const wa = normalizarWa(r.whatsapp);
  const interes = r.interes_charla;
  const seguimiento = {
    agendar: { etapa: '3. Conversación', prox: 'Esperando que reserve en Cal.com (si en 2 días no reservó, escribirle)', dias: 2 },
    contactar: { etapa: '3. Conversación', prox: `Responder: coordinar charla por ${({ whatsapp: 'WhatsApp', mail: 'mail', llamada: 'llamada' })[a.canal] || 'mail'}`, dias: 0 },
    ahora_no: { etapa: '10. Nutrir', prox: 'Mandarle el informe y recontactar', dias: 60 },
  }[interes] || { etapa: '3. Conversación', prox: 'Revisar respuesta del form', dias: 0 };
  const dolor = `Form: ${a.tarea_eliminar || ''}`.slice(0, 600);

  if (fila) {
    const u = { 'ID': fila.ID, 'Secuencia': 'Pausada', 'Canal': 'Form', 'Último contacto': fecha,
      'Próxima acción': seguimiento.prox, 'Fecha próx. acción': cuando.plus({ days: seguimiento.dias }).toFormat('yyyy-MM-dd'),
      'Dolor detectado': ((fila['Dolor detectado'] ? fila['Dolor detectado'] + ' | ' : '') + dolor).slice(0, 1500) };
    const actual = String(fila['Etapa'] || '');
    if (!/^(8|9)\./.test(actual) && (seguimiento.etapa.startsWith('10.') ? numEtapa(actual) < 3 : numEtapa(seguimiento.etapa) > numEtapa(actual))) u['Etapa'] = seguimiento.etapa;
    if (!fila['Email']) u['Email'] = r.email;
    if (!fila['WhatsApp'] && wa) u['WhatsApp'] = wa;
    if (!fila['Contacto']) u['Contacto'] = r.nombre;
    if (!fila['Cargo']) u['Cargo'] = r.rol;
    updates.push(u);
  } else {
    // Llegó alguien que no estaba en la lista (le reenviaron el link): se agrega como lead nuevo
    maxId += 1;
    fila = { 'ID': maxId, 'Empresa': r.estudio, 'Contacto': r.nombre };
    nuevos.push({ 'ID': maxId, 'Segmento': 'Estudio contable', 'Prioridad': 'Alta', 'Empresa': r.estudio, 'Contacto': r.nombre,
      'Cargo': r.rol, 'Ubicación': a.localidad || '', 'Email': r.email, 'WhatsApp': wa, 'Etapa': seguimiento.etapa,
      'Canal': 'Form', 'Toques': 0, 'Último contacto': fecha, 'Próxima acción': seguimiento.prox,
      'Fecha próx. acción': cuando.plus({ days: seguimiento.dias }).toFormat('yyyy-MM-dd'), 'Dolor detectado': dolor,
      'Secuencia': 'Pausada', 'Paso LinkedIn': 0, 'Código': r.codigo || '', 'Notas': 'Llegó por el form (referido)' });
  }

  for (const t of a.tareas_tiempo || []) hallazgos.push({ 'Fecha': fecha, 'ID': fila.ID, 'Empresa': r.estudio, 'Contacto': r.nombre,
    'Tema': pregunta.tareas_tiempo.opciones[t] || t, 'Descripción': 'Marcada en el form como una de las 3 tareas que más tiempo llevan',
    'Frecuencia': '', 'Impacto': etiqueta(pregunta.horas_repetitivas, a.horas_repetitivas) + ' h/semana en tareas repetitivas',
    'Herramienta actual': etiqueta(pregunta.control_tareas, a.control_tareas), 'Cita textual': '', 'Fuente': 'Form' });
  hallazgos.push({ 'Fecha': fecha, 'ID': fila.ID, 'Empresa': r.estudio, 'Contacto': r.nombre, 'Tema': 'Tarea que eliminaría',
    'Descripción': a.tarea_eliminar || '', 'Frecuencia': '', 'Impacto': '', 'Herramienta actual': '',
    'Cita textual': a.ultima_vez || '', 'Fuente': 'Form' });

  const cruda = { 'Fecha': fecha, 'ID': fila.ID, 'Código': r.codigo || '', 'Versión': r.version, 'Segundos': r.segundos,
    'Estudio': r.estudio, 'Nombre': r.nombre, 'Rol': r.rol, 'Email': r.email, 'WhatsApp': wa };
  for (const p of PREG) if (!['nombre', 'rol', 'estudio', 'email', 'whatsapp', 'consentimiento'].includes(p.id)) cruda[p.id] = etiqueta(p, a[p.id]);
  crudas.push(cruda);

  const textoInteres = { agendar: '📅 quiere agendar ya', contactar: '💬 quiere que lo contactes', ahora_no: 'ahora no' }[interes] || interes;
  avisos.push(`<b>${esc(r.nombre)}</b> (${esc(r.rol)}, ${esc(r.estudio)}) completó el form — <b>${textoInteres}</b><br>
    <span style="color:#555">Tareas: ${esc(etiqueta(pregunta.tareas_tiempo, a.tareas_tiempo))}<br>
    “${esc(a.tarea_eliminar)}”</span>
    ${wa ? `<br><a href="https://wa.me/${wa.replace('+', '')}">WhatsApp</a> · ` : '<br>'}<a href="mailto:${esc(r.email)}">${esc(r.email)}</a>
    ${fila && !nuevos.find(n => n.ID === fila.ID) ? '' : ' · <i>lead nuevo (no estaba en la lista)</i>'}`);
}
if (respuestas.length) $getWorkflowStaticData('global').ultimoId = respuestas[respuestas.length - 1].id;
return [{ json: { updates, nuevos, hallazgos, crudas, avisos } }];
"""
pr = code(w, "Procesar respuestas", RESP)
x0 = w.x
ramas = [
    (code(w, "Filas a actualizar", "return $json.updates.map(u => ({ json: u }));", [x0 + 240, 60]), actualizar(w, "Actualizar pipeline", [x0 + 480, 60])),
    (code(w, "Leads nuevos", "return $json.nuevos.map(u => ({ json: u }));", [x0 + 240, 220]), agregar(w, "Agregar al pipeline", "Pipeline", [x0 + 480, 220])),
    (code(w, "Hallazgos a cargar", "return $json.hallazgos.map(h => ({ json: h }));", [x0 + 240, 380]), agregar(w, "Cargar hallazgos", "Hallazgos", [x0 + 480, 380])),
    (code(w, "Respuestas completas", "return $json.crudas.map(r => ({ json: r }));", [x0 + 240, 540]), agregar(w, "Cargar respuestas", "Respuestas form", [x0 + 480, 540])),
    (code(w, "Armar aviso", r"""
const avisos = $json.avisos;
if (!avisos.length) return [];
const html = `<div style="font-family:Arial,sans-serif;max-width:680px"><h3>Nuevas respuestas del form</h3><ul>${avisos.map(a => `<li style="margin-bottom:14px">${a}</li>`).join('')}</ul></div>`;
return [{ json: { asunto: `Form: ${avisos.length} respuesta${avisos.length > 1 ? 's' : ''} nueva${avisos.length > 1 ? 's' : ''}`, html } }];
""", [x0 + 240, 700]), mail(w, "Avisarme", [x0 + 480, 700])),
]
w.chain(t, c, cur, sb, lp, pr)
for a, b in ramas:
    w.link(pr, a)
    w.link(a, b)
w.save("05_sync_respuestas_form.json",
       "## 05 · Respuestas del form → planilla\n"
       "1. **Config**: ID del Sheet y tu email.\n"
       "2. Credencial **Supabase API** en *Traer respuestas*: Host = URL del proyecto, Service Role Secret = la service role key (queda cifrada en n8n).\n"
       "3. La planilla necesita la hoja **Respuestas form** (ya viene en Pipeline_Ventas.xlsx).\n"
       "4. Activá el workflow: el cursor solo se guarda en ejecuciones automáticas.")

print("OK:", sorted(p.name for p in OUT.glob("*.json")))
