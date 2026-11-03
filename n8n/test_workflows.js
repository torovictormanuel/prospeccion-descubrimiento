// Ejecuta los nodos Code de los workflows con datos reales y respuestas simuladas.
// Uso: node n8n/test_workflows.js <carpeta n8n> <filas.json exportadas de la hoja Pipeline>
// Necesita luxon (viene con n8n): LUXON=<ruta a node_modules/luxon> si no está en la ruta por defecto.
const fs = require('fs');
const { DateTime } = require(process.env.LUXON || 'C:/Users/victo/AppData/Roaming/npm/node_modules/n8n/node_modules/luxon');
const wfDir = process.argv[2];
const rows = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const getCode = (file, node) => JSON.parse(fs.readFileSync(`${wfDir}/${file}`, 'utf8')).nodes.find(n => n.name === node).parameters.jsCode;
const statics = {};
async function run(file, node, ctx) {
  const items = (ctx.input || []).map(j => ({ json: j }));
  const $ = name => ({ first: () => ({ json: ctx.nodes[name][0] }), all: () => ctx.nodes[name].map(j => ({ json: j })), item: { json: ctx.nodes[name][0] } });
  const fn = new Function('$', '$input', '$json', '$now', 'DateTime', '$getWorkflowStaticData', `return (async()=>{${getCode(file, node)}})()`);
  return fn($, { all: () => items, first: () => items[0] }, ctx.json || (items[0] || {}).json, DateTime.now(), DateTime, () => (statics[file] ??= {}));
}
const ok = (c, m) => { console.log((c ? 'OK   ' : 'FAIL ') + m); if (!c) process.exitCode = 1; };

(async () => {
  const cfg = { sheetId: 'x', miEmail: 'yo@x.com', waNumero: '5491100000000', calLink: 'https://cal.com/v/d', formUrl: 'https://form.test/', leadsPorDia: 12, tokenAcciones: 'tok123', n8nUrl: 'http://localhost:5678' };
  const F1 = '01_investigador_cola_linkedin.json';

  // 1) Elegir leads
  const el = await run(F1, 'Elegir leads del día', { input: rows, nodes: { Config: [cfg] } });
  ok(el.length > 0 && el.length <= 12 && el.every(i => i.json.geminiBody), `elige ${el.length} leads con prompt`);
  ok(el.every(i => rows.find(r => r.ID === i.json.ID)['LinkedIn / Web'].includes('/in/')), 'solo leads con perfil personal');
  const vac = await run(F1, 'Elegir leads del día', { input: rows.map(r => ({ ...r, Secuencia: 'Pausada' })), nodes: { Config: [cfg] } });
  ok(vac.length === 1 && vac[0].json.vacio, 'sin leads → ítem vacío para que igual salga el mail');

  // 2) Armar mensajes con respuesta de Gemini buena y con error
  const lead = el[0].json;
  const gemOk = { candidates: [{ content: { parts: [{ text: '```json\n{"dato":"Atiende pymes agro","fuente":"https://x.com","conexion":"Hola Jorge, vi que atienden pymes agro.","mensaje1":"Hola Jorge... completá {LINK_FORM} o charlemos {LINK_AGENDA}","mensaje2":"¿Viste el form? {LINK_FORM}","cierre":"Gracias"}\n```' }] } }] };
  let a = await run(F1, 'Armar mensajes', { json: gemOk, nodes: { Config: [cfg], 'Uno por uno': [lead] } });
  ok(/^[A-Za-z0-9]{8}$/.test(a.json['Código']), `código del lead: ${a.json['Código']}`);
  ok(a.json['Link form'] === `https://form.test/?c=${a.json['Código']}&f=linkedin`, 'link del form con código y sin doble barra');
  ok(a.json['Mensaje 1'].includes(a.json['Link form']) && a.json['Mensaje 1'].includes('metadata[ref]=' + lead.ID), 'Mensaje 1 con link al form y a la agenda');
  ok(a.json['Mensaje 2'].includes(a.json['Link form']), 'Mensaje 2 recuerda el form');
  ok(a.json['Dato investigado'].startsWith('Atiende pymes agro'), 'dato investigado guardado');
  const sinForm = { candidates: [{ content: { parts: [{ text: '{"mensaje1":"Hola, charlemos: {LINK_AGENDA}"}' }] } }] };
  a = await run(F1, 'Armar mensajes', { json: sinForm, nodes: { Config: [cfg], 'Uno por uno': [lead] } });
  ok(a.json['Mensaje 1'].includes(a.json['Link form']), 'si Gemini omite el form, se usa la plantilla con el form');
  a = await run(F1, 'Armar mensajes', { json: { error: { message: '429' } }, nodes: { Config: [cfg], 'Uno por uno': [lead] } });
  ok(a.json['Mensaje 1'].includes('No vendo nada') && a.json['Mensaje 1'].includes('form de 4 minutos'), 'Gemini caído → plantilla por defecto con el form');
  ok(a.json['Mensaje conexión'].length <= 295, 'nota de conexión ≤ 295 caracteres');

  // 3) Cola del día
  const conMsgs = rows.map(r => r.ID === lead.ID ? { ...r, ...a.json } : r);
  const cola = await run(F1, 'Armar cola del día', { input: conMsgs, nodes: { Config: [cfg] } });
  ok(cola.length === 1 && cola[0].json.html.includes('accion=enviado&paso=1') && cola[0].json.html.includes('t=tok123'), `mail diario: "${cola[0].json.asunto}"`);
  ok(cola[0].json.html.includes('Buscá al socio'), 'incluye tarea de buscar decisores sin perfil');

  // 4) Botones del mail
  const F4 = '04_botones_mail_diario.json';
  const q = (accion, paso = '') => ({ query: { id: String(lead.ID), accion, paso, t: 'tok123' } });
  let b = await run(F4, 'Aplicar acción', { input: conMsgs, nodes: { Config: [{ tokenAcciones: 'tok123' }], 'Botón del mail': [q('enviado', '1')] } });
  ok(b[0].json['Paso LinkedIn'] === 1 && b[0].json['Etapa'] === '2. Contactado' && b[0].json['Toques'] === 1, 'botón Enviado paso 1 → Contactado, 1 toque');
  const tras = conMsgs.map(r => r.ID === lead.ID ? { ...r, ...b[0].json } : r);
  b = await run(F4, 'Aplicar acción', { input: tras, nodes: { Config: [{ tokenAcciones: 'tok123' }], 'Botón del mail': [q('enviado', '1')] } });
  ok(Object.keys(b[0].json).length === 1, 'doble clic no suma otro toque');
  let err = null;
  try { await run(F4, 'Aplicar acción', { input: tras, nodes: { Config: [{ tokenAcciones: 'tok123' }], 'Botón del mail': [{ query: { id: '1', accion: 'descartar', t: 'malo' } }] } }); } catch (e) { err = e.message; }
  ok(err === 'Token inválido', 'token incorrecto se rechaza');
  const cola2 = await run(F1, 'Armar cola del día', { input: tras, nodes: { Config: [cfg] } });
  ok(!cola2.length || !cola2[0].json.html.includes(`id=${lead.ID}&accion=enviado&paso=1`), 'tras enviar, el lead no reaparece hoy');

  // 5) Sync del agente de WhatsApp
  const F2 = '02_sync_agente_whatsapp.json';
  const ref = String(lead.ID);
  const evs = { eventos: [
    { id: 1, tipo: 'primer_contacto', telefono: '5491122223333', ref, creado_en: '2026-10-27T13:00:00Z', detalle: {} },
    { id: 2, tipo: 'datos', telefono: '5491122223333', ref, creado_en: '2026-10-27T13:01:00Z', detalle: { email: 'j@e.com' } },
    { id: 3, tipo: 'hallazgo', telefono: '5491122223333', ref, creado_en: '2026-10-27T13:02:00Z', detalle: { tema: 'documentación', descripcion: 'piden papeles a mano', cita_textual: 'un caos' } },
    { id: 4, tipo: 'agendado', telefono: '5491122223333', ref, creado_en: '2026-10-27T13:03:00Z', detalle: { inicio: '2026-10-29T13:00:00+00:00' } },
    { id: 5, tipo: 'primer_contacto', telefono: '5491199999999', ref: null, nombre: 'Ana', creado_en: '2026-10-27T13:04:00Z', detalle: {} },
  ], ultimo_id: 5 };
  const p = await run(F2, 'Procesar eventos', { nodes: { 'Traer eventos': [evs], 'Leer pipeline': tras } });
  const u = p[0].json.updates[0];
  ok(u.Etapa === '4. Reunión agendada' && u.Email === 'j@e.com' && u.WhatsApp === '+5491122223333' && u.Secuencia === 'Pausada', 'eventos → etapa 4, email, whatsapp, secuencia pausada');
  ok(u['Próxima acción'] === 'Llamada de descubrimiento 29/10 10:00', `hora local correcta: ${u['Próxima acción']}`);
  ok(p[0].json.hallazgos.length === 1 && p[0].json.hallazgos[0].Fuente === 'WhatsApp', 'hallazgo para hoja Hallazgos');
  ok(p[0].json.avisos.length === 3 && p[0].json.avisos.some(x => x.includes('sin ref')), '3 avisos (incluido contacto sin ref)');
  ok(statics[F2].ultimoId === 5, 'cursor guardado');

  // 6) Sync de Cal.com
  const F3 = '03_sync_reservas_calcom.json';
  const resv = { data: [
    { uid: 'u1', status: 'accepted', start: '2026-10-30T15:00:00Z', attendees: [{ name: 'X', email: 'x@y.com' }], metadata: { ref } },
    { uid: 'u2', status: 'accepted', start: '2026-10-30T16:00:00Z', attendees: [{ name: 'Z', email: 'z@y.com' }], metadata: {}, bookingFieldsResponses: { notes: 'ref 99999' } },
    { uid: 'u3', status: 'cancelled', start: '2026-10-30T17:00:00Z', attendees: [], metadata: {} } ] };
  let r3 = await run(F3, 'Procesar reservas', { nodes: { 'Traer reservas': [resv], 'Leer pipeline': tras } });
  ok(r3[0].json.updates.length === 1 && r3[0].json.updates[0].Etapa === '4. Reunión agendada', 'reserva por link vinculada por ref');
  ok(r3[0].json.avisos.length === 2, 'avisa la reserva vinculada y la que no encontró');
  r3 = await run(F3, 'Procesar reservas', { nodes: { 'Traer reservas': [resv], 'Leer pipeline': tras } });
  ok(r3[0].json.updates.length === 0 && r3[0].json.avisos.length === 0, 'no repite reservas ya procesadas');

  // 7) Reserva hecha desde la pantalla final del form (metadata.codigo)
  const conCodigo = tras.map(r => r.ID === lead.ID ? { ...r, 'Código': 'Ab12Cd34' } : r);
  r3 = await run(F3, 'Procesar reservas', { nodes: { 'Traer reservas': [{ data: [
    { uid: 'u9', status: 'accepted', start: '2026-11-02T14:00:00Z', attendees: [{ name: 'Ana', email: 'nueva@y.com' }], metadata: { codigo: 'Ab12Cd34' } }] }], 'Leer pipeline': conCodigo } });
  ok(r3[0].json.updates[0]?.ID === lead.ID, 'reserva desde el form vinculada por código');

  // 8) Respuestas del form (workflow 05)
  const F5 = '05_sync_respuestas_form.json';
  const base = { version: '2026-10-v1', fuente: 'linkedin', segundos: 140, rol: 'Socia', created_at: '2026-10-27T15:00:00Z', ip_hash: 'x' };
  const respAll = [
    { ...base, id: 7, codigo: 'Ab12Cd34', nombre: 'Ana Pérez', email: 'ana@e.com', whatsapp: '1123456789', estudio: 'Estudio X', interes_charla: 'contactar',
      respuestas: { tamano: '11-25', tipo_clientes: ['monotributo'], tareas_tiempo: ['pedir_documentacion', 'sueldos'], horas_repetitivas: '15-30', control_tareas: 'excel',
        tarea_eliminar: 'Perseguir facturas', ultima_vez: 'El mes pasado…', canal: 'whatsapp', interes_charla: 'contactar', quiere_informe: true, consentimiento: true } },
    { ...base, id: 8, codigo: null, nombre: 'Beto Ruiz', email: 'beto@nuevo.com', whatsapp: null, estudio: 'Estudio Referido', interes_charla: 'ahora_no',
      respuestas: { tamano: '6-10', tareas_tiempo: ['arca'], tarea_eliminar: 'ARCA', interes_charla: 'ahora_no', consentimiento: true, localidad: 'Rosario' } },
  ];
  const p5 = await run(F5, 'Procesar respuestas', { nodes: { 'Traer respuestas': respAll, 'Leer pipeline': conCodigo } });
  const o = p5[0].json;
  const u5 = o.updates[0];
  ok(u5.ID === lead.ID && u5.Secuencia === 'Pausada' && u5.Etapa === '3. Conversación', 'form vincula por código, pausa la secuencia y sube a Conversación');
  ok(u5['Próxima acción'] === 'Responder: coordinar charla por WhatsApp', 'pidió contacto → aparece como "Responder" en el mail diario');
  ok(u5.WhatsApp === '+5491123456789', `WhatsApp normalizado: ${u5.WhatsApp}`);
  ok(o.nuevos.length === 1 && o.nuevos[0].ID === Math.max(...rows.map(r => r.ID)) + 1 && o.nuevos[0].Etapa === '10. Nutrir', 'respuesta sin lead → lead nuevo con ID siguiente, en Nutrir');
  ok(o.hallazgos.length === 5 && o.hallazgos.some(h => h.Tema === 'Pedir y perseguir documentación a clientes'), 'hallazgos con etiquetas legibles (3 tareas + 2 abiertas)');
  ok(o.crudas[0].tareas_tiempo === 'Pedir y perseguir documentación a clientes, Liquidación de sueldos y novedades' && !('consentimiento' in o.crudas[0]), 'fila de Respuestas form con etiquetas');
  ok(o.avisos.length === 2 && o.avisos[1].includes('lead nuevo'), 'avisa ambas respuestas y marca el referido');
  ok(statics[F5].ultimoId === 8, 'cursor del form guardado');

  // 06) Buscador: valida, no duplica y no escribe si la búsqueda falló
  const F6 = '06_buscador_leads.json';
  const cfg6 = { leadsBuscar: 10 };
  const bus = (await run(F6, 'Armar búsqueda', { nodes: { Config: [cfg6] } }))[0].json;
  ok(bus.geminiBody.tools[0].google_search && bus.ciudad && bus.perfil, 'buscador arma la búsqueda con Google');
  const previa = [{ ID: 7, Contacto: 'Ana Pérez', Empresa: 'Estudio Pérez', 'LinkedIn / Web': 'https://www.linkedin.com/in/ana-perez/' }];
  const respuesta = l => ({ candidates: [{ content: { parts: [{ text: JSON.stringify({ leads: l }) }] }, groundingMetadata: { webSearchQueries: ['q'] } }] });
  const nodos6 = { Config: [cfg6], 'Armar búsqueda': [bus], 'Leer pipeline': previa };
  const v = (await run(F6, 'Validar leads', { json: respuesta([
    { nombre: 'Luis Gómez', cargo: 'Socio', empresa: 'Estudio Contable Gómez', linkedin: 'https://ar.linkedin.com/in/luis-gomez?trk=x' },
    { nombre: 'Ana Pérez', cargo: 'Socia', empresa: 'Estudio Pérez', linkedin: 'https://www.linkedin.com/in/ANA-PEREZ/' },
    { nombre: 'Marta Díaz', cargo: 'Contadora', empresa: 'Estudio Díaz', linkedin: 'https://www.linkedin.com/company/estudio-diaz/' },
    { nombre: 'Juan Ruiz', cargo: 'Vendedor', empresa: 'Zapatería Ruiz', linkedin: 'https://www.linkedin.com/in/juan-ruiz/' },
  ]), nodes: nodos6 }))[0].json;
  ok(v.nuevos.length === 1 && v.nuevos[0].ID === 8 && v.nuevos[0]['LinkedIn / Web'] === 'https://www.linkedin.com/in/luis-gomez/', 'buscador deja solo el lead nuevo y válido');
  ok(v.nuevos[0].Prioridad === 'Alta' && v.nuevos[0].Secuencia === 'Activa' && v.nuevos[0].Etapa === '1. Prospecto', 'lead nuevo queda listo para el 01');
  const caido = (await run(F6, 'Validar leads', { json: { error: { message: '402 sin créditos' } }, nodes: nodos6 }))[0].json;
  ok(caido.nuevos.length === 0 && caido.asunto.includes('falló'), 'si Gemini falla no agrega leads y avisa');
  const sinBuscar = (await run(F6, 'Validar leads', { json: { candidates: [{ content: { parts: [{ text: '{"leads":[{"nombre":"X Y","cargo":"Socio","empresa":"Estudio","linkedin":"https://linkedin.com/in/x-y"}]}' }] } }] }, nodes: nodos6 }))[0].json;
  ok(sinBuscar.nuevos.length === 0, 'descarta respuestas de Gemini que no buscaron en Google');

  // 07) Recordatorios: una vez por reserva, solo del evento correcto y con el teléfono del form
  const F7 = '07_recordatorio_charla.json';
  const cfg7 = { eventTypeId: 7696927 };
  const reserva = (uid, h, extra = {}) => ({ uid, status: 'accepted', eventTypeId: 7696927, start: DateTime.now().plus({ hours: h }).toISO(), attendees: [{ name: 'Luis Gómez', email: 'luis@x.com' }], ...extra });
  const nodos7 = rs => ({ Config: [cfg7], 'Traer reservas': [{ data: rs }], 'Leer pipeline': [{ ID: 8, Email: 'luis@x.com', WhatsApp: '+5491123456789' }] });
  const rec1 = await run(F7, 'Elegir recordatorios', { nodes: nodos7([reserva('a', 20), reserva('b', 1), reserva('c', 72), reserva('d', 20, { eventTypeId: 999 }), reserva('e', 20, { status: 'cancelled' })]) });
  ok(rec1.length === 2 && rec1[0].json.tipo === '24h' && rec1[1].json.tipo === '2h', 'recordatorios: solo reservas aceptadas del evento, a 24 h y 2 h');
  ok(rec1[0].json.telefono === '5491123456789' && rec1[0].json.nombre === 'Luis', 'recordatorio toma el WhatsApp del form');
  const rec2 = await run(F7, 'Elegir recordatorios', { nodes: nodos7([reserva('a', 19.5), reserva('b', 0.5)]) });
  ok(rec2.length === 0, 'no repite un recordatorio ya enviado');
  const rec3 = await run(F7, 'Elegir recordatorios', { nodes: nodos7([reserva('a', 1.5)]) });
  ok(rec3.length === 1 && rec3[0].json.tipo === '2h', 'la misma reserva recibe después el de 2 h');
  const rec4 = await run(F7, 'Elegir recordatorios', { nodes: { Config: [cfg7], 'Traer reservas': [{ data: [reserva('f', 20, { attendees: [{ name: 'Sin Tel', email: 'otra@x.com' }] })] }], 'Leer pipeline': [] } });
  ok(rec4.length === 1 && rec4[0].json.tieneTelefono === false, 'sin teléfono sale solo el mail');

  // Una operación que n8n no conoce no da error: la condición queda siempre en falso.
  const VALIDAS = { boolean: ['exists', 'notExists', 'empty', 'notEmpty', 'true', 'false', 'equals', 'notEquals'],
    number: ['exists', 'notExists', 'empty', 'notEmpty', 'equals', 'notEquals', 'gt', 'lt', 'gte', 'lte'] };
  const ifs = fs.readdirSync(wfDir).filter(f => f.endsWith('.json')).flatMap(f => JSON.parse(fs.readFileSync(`${wfDir}/${f}`, 'utf8')).nodes.filter(n => n.type.endsWith('.if')));
  ok(ifs.length > 0 && ifs.every(n => n.parameters.conditions.conditions.every(c => (VALIDAS[c.operator.type] || []).includes(c.operator.operation))), 'nodos IF con operaciones válidas de n8n');
})().catch(e => { console.log('EXCEPCIÓN', e); process.exitCode = 1; });
