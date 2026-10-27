// Servidor local para probar el form sin Vercel: sirve public/ con los mismos
// headers de vercel.json y enruta /api/respuesta a la función real.
// Sin SUPABASE_URL, las respuestas se guardan en respuestas-dev.jsonl.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import handler from "./api/respuesta.js";

const RAIZ = fileURLToPath(new URL("./public/", import.meta.url));
const PORT = Number(process.env.PORT || 3000);
const vercel = JSON.parse(await readFile(new URL("./vercel.json", import.meta.url), "utf8"));
const HEADERS = vercel.headers[0].headers;
const TIPOS = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml" };

createServer(async (req, res) => {
  for (const h of HEADERS) if (h.key !== "Strict-Transport-Security") res.setHeader(h.key, h.value);
  const url = new URL(req.url, `http://${req.headers.host}`);

  // El script de Vercel Analytics solo existe en el deploy
  if (url.pathname.startsWith("/_vercel/")) {
    res.setHeader("Content-Type", "text/javascript");
    return res.end("");
  }

  if (url.pathname === "/api/respuesta") {
    let raw = "";
    for await (const chunk of req) { raw += chunk; if (raw.length > 50_000) break; }
    req.body = raw;
    // Mismo contrato mínimo que el runtime de Vercel
    res.status = code => { res.statusCode = code; return res; };
    res.json = obj => { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(obj)); };
    return handler(req, res);
  }

  let ruta = url.pathname === "/" ? "/index.html" : url.pathname;
  if (!extname(ruta)) ruta += ".html"; // cleanUrls
  const archivo = normalize(join(RAIZ, ruta));
  if (!archivo.startsWith(normalize(RAIZ))) { res.statusCode = 403; return res.end(); }
  try {
    const contenido = await readFile(archivo);
    res.setHeader("Content-Type", TIPOS[extname(archivo)] || "application/octet-stream");
    res.end(contenido);
  } catch {
    res.statusCode = 404;
    res.end("No encontrado");
  }
}).listen(PORT, () => console.log(`Form en http://localhost:${PORT}`));
