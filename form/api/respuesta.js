// POST /api/respuesta — recibe el form, lo valida y lo guarda.
import { validarRespuesta } from "../lib/validar.js";
import { guardarRespuesta, hashIp } from "../lib/guardar.js";

const MAX_BYTES = 20_000;
// Rate limit en memoria por instancia: frena ráfagas de un mismo origen.
// Para tráfico real conviene sumar una regla de rate limit en el firewall de Vercel.
const VENTANA_MS = 60 * 60 * 1000;
const MAX_POR_IP = 10; // varias personas de un mismo estudio pueden compartir la IP de la oficina
const hits = new Map();

function excedeLimite(clave) {
  const ahora = Date.now();
  const lista = (hits.get(clave) || []).filter(t => ahora - t < VENTANA_MS);
  if (lista.length >= MAX_POR_IP) { hits.set(clave, lista); return true; }
  lista.push(ahora);
  hits.set(clave, lista);
  if (hits.size > 5000) hits.clear(); // evita crecer sin límite
  return false;
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "Método no permitido" });
  }
  if (!String(req.headers["content-type"] || "").includes("application/json")) {
    return res.status(415).json({ ok: false, error: "Se espera JSON" });
  }
  if (Number(req.headers["content-length"] || 0) > MAX_BYTES) {
    return res.status(413).json({ ok: false, error: "Demasiado grande" });
  }

  const ip = String(req.headers["x-forwarded-for"] || req.socket?.remoteAddress || "?").split(",")[0].trim();
  const ipHash = hashIp(ip);
  if (excedeLimite(ipHash)) {
    return res.status(429).json({ ok: false, error: "Demasiados envíos. Probá más tarde." });
  }

  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { return res.status(400).json({ ok: false, error: "JSON inválido" }); }
  }

  const v = validarRespuesta(body);
  if (v.bot) return res.status(200).json({ ok: true }); // al bot no se le dice que fue detectado
  if (!v.ok) return res.status(422).json({ ok: false, errores: v.errores });

  try {
    await guardarRespuesta(v.datos, ipHash);
  } catch (e) {
    console.error("Error guardando respuesta:", e.message);
    return res.status(503).json({ ok: false, error: "No pudimos guardar tu respuesta. Probá de nuevo en un minuto." });
  }
  return res.status(200).json({ ok: true });
}
