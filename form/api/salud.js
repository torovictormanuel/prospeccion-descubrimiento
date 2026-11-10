// GET /api/salud — para un monitor de uptime gratis (UptimeRobot, Better Stack).
// Solo dice si la función está viva y configurada; no expone ningún valor.
import { embudoConfigurado } from "../lib/guardar.js";

export default function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  const configurado = embudoConfigurado();
  res.status(configurado ? 200 : 503).json({ ok: configurado });
}
