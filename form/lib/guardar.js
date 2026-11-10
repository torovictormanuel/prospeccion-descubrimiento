// Guarda una respuesta validada en el embudo unificado de prospectos (Supabase victortoro-web),
// el mismo donde entran los leads de la web, con su canal de llegada.
// El form no tiene la clave de esa base: le pasa la respuesta al servidor de la web
// (/api/descubrimiento) con un secreto compartido que solo existe en los dos servidores.
// Sin el embudo configurado y fuera de producción, escribe en un archivo local para poder probar.
import { appendFile } from "node:fs/promises";
import { createHash } from "node:crypto";

export function embudoConfigurado() {
  return Boolean(process.env.EMBUDO_URL && process.env.EMBUDO_SECRET);
}

export function hashIp(ip) {
  // Sin sal, un hash de IPv4 se revierte probando las 4 mil millones de IPs.
  // Si no se define IP_HASH_SALT se usa el secreto del embudo: ya vive solo en el servidor.
  const sal = process.env.IP_HASH_SALT || process.env.EMBUDO_SECRET || "";
  return createHash("sha256").update(`${sal}:${ip}`).digest("hex").slice(0, 32);
}

// Devuelve "ok" o "limite"; lanza un error si no se pudo guardar.
export async function guardarRespuesta(datos, ipHash) {
  if (embudoConfigurado()) {
    const res = await fetch(`${process.env.EMBUDO_URL.replace(/\/$/, "")}/api/descubrimiento`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-embudo-secret": process.env.EMBUDO_SECRET },
      body: JSON.stringify({ datos, ip_hash: ipHash }),
      signal: AbortSignal.timeout(9000),
    });
    if (res.status === 429) return "limite";
    if (!res.ok) throw new Error(`El embudo respondió ${res.status}`);
    return "ok";
  }
  if (process.env.NODE_ENV === "production" || process.env.VERCEL_ENV === "production") {
    throw new Error("Embudo no configurado");
  }
  await appendFile(process.env.ARCHIVO_DEV || "respuestas-dev.jsonl", JSON.stringify({ ...datos, ip_hash: ipHash, created_at: new Date().toISOString() }) + "\n");
  return "ok";
}
