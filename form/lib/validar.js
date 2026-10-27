// Validación del lado del servidor. Nunca se confía en lo que valida el navegador:
// cada respuesta se compara contra las opciones permitidas de preguntas.js.
import { TODAS, VERSION } from "../public/preguntas.js";

const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]{1,100}\.[^\s@]{2,20}$/;
const CODIGO_RE = /^[A-Za-z0-9]{6,12}$/;
const FUENTE_RE = /^[a-z0-9_-]{1,30}$/;
const MIN_SEGUNDOS = 15; // nadie completa 5 pantallas en menos: si pasa, es un bot

// Saca caracteres de control y espacios de más. El HTML se escapa al mostrarlo,
// no acá: el dato se guarda tal cual lo escribió la persona.
const limpiar = (v, max) => String(v ?? "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").trim().slice(0, max);

export function validarRespuesta(body) {
  const errores = {};
  if (!body || typeof body !== "object" || Array.isArray(body)) return { ok: false, errores: { _: "Formato inválido" } };

  // Anti-bots: campo trampa invisible y tiempo mínimo de llenado
  if (body.sitio_web) return { ok: false, bot: true, errores: { _: "Rechazado" } };
  const segundos = Number(body.segundos);
  if (!Number.isFinite(segundos) || segundos < MIN_SEGUNDOS) return { ok: false, bot: true, errores: { _: "Rechazado" } };

  const r = body.respuestas;
  if (!r || typeof r !== "object" || Array.isArray(r)) return { ok: false, errores: { _: "Faltan respuestas" } };

  const limpio = {};
  for (const p of TODAS) {
    const v = r[p.id];
    const vacio = v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0) || v === false;
    if (vacio) {
      if (p.requerida) errores[p.id] = "Obligatoria";
      continue;
    }
    const permitidas = new Set((p.opciones || []).map(o => o[0]));
    switch (p.tipo) {
      case "single":
        if (typeof v !== "string" || !permitidas.has(v)) errores[p.id] = "Opción inválida";
        else limpio[p.id] = v;
        break;
      case "multi": {
        if (!Array.isArray(v) || v.some(x => typeof x !== "string" || !permitidas.has(x))) { errores[p.id] = "Opción inválida"; break; }
        const unicos = [...new Set(v)];
        if (p.max && unicos.length > p.max) errores[p.id] = `Máximo ${p.max}`;
        else limpio[p.id] = unicos;
        break;
      }
      case "check":
        if (v !== true) errores[p.id] = "Valor inválido";
        else limpio[p.id] = true;
        break;
      case "email": {
        const e = limpiar(v, p.maxLargo).toLowerCase();
        if (!EMAIL_RE.test(e)) errores[p.id] = "Email inválido";
        else limpio[p.id] = e;
        break;
      }
      case "tel": {
        const digitos = String(v).replace(/\D/g, "");
        if (digitos.length < 8 || digitos.length > 15) errores[p.id] = "Número inválido";
        else limpio[p.id] = digitos;
        break;
      }
      default: { // short / text
        const t = limpiar(v, p.maxLargo || 200);
        if (p.requerida && t.length < 2) errores[p.id] = "Muy corto";
        else if (t) limpio[p.id] = t;
      }
    }
  }
  if (limpio.consentimiento !== true) errores.consentimiento = "Necesitamos tu consentimiento";

  const codigo = typeof body.codigo === "string" && CODIGO_RE.test(body.codigo) ? body.codigo : null;
  const fuente = typeof body.fuente === "string" && FUENTE_RE.test(body.fuente) ? body.fuente : null;

  if (Object.keys(errores).length) return { ok: false, errores };
  return { ok: true, datos: { version: VERSION, codigo, fuente, segundos: Math.round(segundos), respuestas: limpio } };
}
