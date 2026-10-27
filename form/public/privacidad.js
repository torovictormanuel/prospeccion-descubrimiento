import { CONFIG } from "./config.js";

document.querySelectorAll("[data-contacto]").forEach(n => { n.textContent = CONFIG.contactoPrivacidad; });
