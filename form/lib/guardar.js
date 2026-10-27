// Guarda una respuesta validada. En producción va a Supabase con la service
// role key (solo existe en el servidor). Sin Supabase configurado y fuera de
// producción, escribe en un archivo local para poder probar.
import { appendFile } from "node:fs/promises";
import { createHash } from "node:crypto";

export function hashIp(ip) {
  const sal = process.env.IP_HASH_SALT || "";
  return createHash("sha256").update(`${sal}:${ip}`).digest("hex").slice(0, 32);
}

export async function guardarRespuesta(datos, ipHash) {
  const r = datos.respuestas;
  const fila = {
    version: datos.version,
    codigo: datos.codigo,
    fuente: datos.fuente,
    segundos: datos.segundos,
    nombre: r.nombre,
    email: r.email,
    whatsapp: r.whatsapp ?? null,
    estudio: r.estudio,
    rol: r.rol,
    interes_charla: r.interes_charla,
    respuestas: r,
    ip_hash: ipHash,
  };

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (url && key) {
    const res = await fetch(`${url}/rest/v1/respuestas_descubrimiento`, {
      method: "POST",
      headers: { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json", Prefer: "return=minimal" },
      body: JSON.stringify(fila),
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error(`Supabase respondió ${res.status}`);
    return;
  }
  if (process.env.NODE_ENV === "production" || process.env.VERCEL_ENV === "production") {
    throw new Error("Supabase no configurado");
  }
  await appendFile(process.env.ARCHIVO_DEV || "respuestas-dev.jsonl", JSON.stringify({ ...fila, created_at: new Date().toISOString() }) + "\n");
}
