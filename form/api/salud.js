// GET /api/salud — para un monitor de uptime gratis (UptimeRobot, Better Stack).
// Solo dice si la función está viva y configurada; no expone ningún valor.
import { claveSupabase } from "../lib/guardar.js";

export default function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  const configurado = Boolean(process.env.SUPABASE_URL && claveSupabase());
  res.status(configurado ? 200 : 503).json({ ok: configurado });
}
