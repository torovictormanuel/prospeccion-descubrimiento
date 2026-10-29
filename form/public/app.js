import { PASOS } from "./preguntas.js";
import { CONFIG } from "./config.js";

const $ = sel => document.querySelector(sel);
const params = new URLSearchParams(location.search);
// El código identifica al lead del pipeline sin poner datos personales en la URL
const codigo = /^[A-Za-z0-9]{6,12}$/.test(params.get("c") || "") ? params.get("c") : null;
const fuente = /^[a-z0-9_-]{1,30}$/.test(params.get("f") || "") ? params.get("f") : null;
const CLAVE_BORRADOR = `borrador-form-${codigo || "anon"}`;

let paso = 0;
let respuestas = {};
let inicio = null;

// Borrador local: si cierra la pestaña en el celular, no pierde lo que ya respondió
const guardarBorrador = () => { try { localStorage.setItem(CLAVE_BORRADOR, JSON.stringify({ paso, respuestas })); } catch {} };
const leerBorrador = () => { try { return JSON.parse(localStorage.getItem(CLAVE_BORRADOR) || "null"); } catch { return null; } };
const borrarBorrador = () => { try { localStorage.removeItem(CLAVE_BORRADOR); } catch {} };

function el(tag, attrs = {}, ...hijos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v === null || v === undefined) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const h of hijos.flat()) if (h) n.append(h);
  return n;
}

function renderPregunta(p) {
  const errorId = `err-${p.id}`;
  const err = el("p", { class: "error", id: errorId, hidden: true });
  const opcional = !p.requerida && !/opcional/i.test(p.texto) ? el("span", { class: "opcional", text: " (opcional)" }) : null;

  if (p.tipo === "single" || p.tipo === "multi") {
    const tipoInput = p.tipo === "single" ? "radio" : "checkbox";
    const cortas = p.opciones.every(o => o[1].length < 26);
    const grupo = el("div", { class: `opciones${cortas ? " cortas" : ""}` },
      p.opciones.map(([valor, etiqueta]) => {
        const actual = respuestas[p.id];
        const marcado = p.tipo === "single" ? actual === valor : (actual || []).includes(valor);
        return el("label", { class: "opcion" },
          el("input", { type: tipoInput, name: p.id, value: valor, checked: marcado }),
          el("span", { text: etiqueta }));
      }));
    const fs = el("fieldset", { "data-id": p.id, "aria-describedby": errorId }, el("legend", { text: p.texto }, opcional), grupo, err);
    if (p.tipo === "multi" && p.max) {
      fs.addEventListener("change", () => limitarMulti(fs, p.max));
      queueMicrotask(() => limitarMulti(fs, p.max));
    }
    return fs;
  }

  if (p.tipo === "check") {
    const input = el("input", { type: "checkbox", id: `q-${p.id}`, name: p.id, checked: respuestas[p.id] === true, "aria-describedby": errorId });
    const label = el("label", { for: `q-${p.id}` }, p.texto);
    if (p.enlace) label.append(" ", el("a", { href: p.enlace[0], target: "_blank", rel: "noopener", text: p.enlace[1] }));
    return el("div", { "data-id": p.id }, el("div", { class: "check" }, input, label), err);
  }

  const id = `q-${p.id}`;
  const comunes = { id, name: p.id, maxlength: p.maxLargo, placeholder: p.placeholder, autocomplete: p.autocomplete,
                    required: p.requerida, "aria-describedby": errorId };
  let campo;
  if (p.tipo === "text") {
    campo = el("textarea", comunes);
    campo.value = respuestas[p.id] || "";
  } else {
    const type = p.tipo === "email" ? "email" : p.tipo === "tel" ? "tel" : "text";
    campo = el("input", { ...comunes, type, inputmode: p.tipo === "tel" ? "tel" : null });
    campo.value = respuestas[p.id] || "";
  }
  const nodos = [el("label", { class: "etiqueta-campo", for: id, text: p.texto }, opcional), campo];
  if (p.tipo === "text") {
    const cont = el("p", { class: "contador", "aria-hidden": "true" });
    const actualizar = () => { cont.textContent = `${campo.value.length}/${p.maxLargo}`; };
    campo.addEventListener("input", actualizar);
    actualizar();
    nodos.push(cont);
  }
  return el("div", { class: "campo", "data-id": p.id }, nodos, err);
}

function limitarMulti(fs, max) {
  const inputs = [...fs.querySelectorAll("input")];
  const marcados = inputs.filter(i => i.checked).length;
  inputs.forEach(i => { i.disabled = !i.checked && marcados >= max; });
}

function render() {
  const p = PASOS[paso];
  $("#paso").replaceChildren(
    el("h2", { text: p.titulo }),
    el("p", { class: "ayuda", text: p.ayuda }),
    ...p.preguntas.map(renderPregunta));
  $("#paso-numero").textContent = `Paso ${paso + 1} de ${PASOS.length}`;
  $("#barra").style.width = `${((paso + 1) / PASOS.length) * 100}%`;
  document.querySelector(".progreso").setAttribute("aria-valuenow", String(paso + 1));
  $("#atras").style.visibility = paso === 0 ? "hidden" : "visible";
  $("#siguiente").textContent = paso === PASOS.length - 1 ? "Enviar" : "Siguiente";
  $("#error-general").textContent = "";
}

function leerPaso() {
  for (const p of PASOS[paso].preguntas) {
    if (p.tipo === "single") {
      const m = document.querySelector(`input[name="${p.id}"]:checked`);
      if (m) respuestas[p.id] = m.value; else delete respuestas[p.id];
    } else if (p.tipo === "multi") {
      respuestas[p.id] = [...document.querySelectorAll(`input[name="${p.id}"]:checked`)].map(i => i.value);
    } else if (p.tipo === "check") {
      respuestas[p.id] = document.querySelector(`input[name="${p.id}"]`).checked;
    } else {
      respuestas[p.id] = document.querySelector(`[name="${p.id}"]`).value.trim();
    }
  }
}

function validarPaso() {
  let primero = null;
  for (const p of PASOS[paso].preguntas) {
    const v = respuestas[p.id];
    let msg = "";
    const vacio = v === undefined || v === "" || v === false || (Array.isArray(v) && !v.length);
    if (p.requerida && vacio) msg = p.tipo === "check" ? "Necesitamos tu consentimiento para guardar las respuestas." : "Esta pregunta es obligatoria.";
    else if (!vacio && p.tipo === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) msg = "Revisá el email.";
    else if (!vacio && p.tipo === "tel" && !/^\d{8,15}$/.test(String(v).replace(/\D/g, ""))) msg = "Revisá el número (con característica).";
    mostrarError(p.id, msg);
    if (msg && !primero) primero = p.id;
  }
  if (primero) {
    const foco = document.querySelector(`[data-id="${primero}"] input, [data-id="${primero}"] textarea`);
    foco?.focus();
  }
  return !primero;
}

function mostrarError(id, msg) {
  const err = document.getElementById(`err-${id}`);
  if (!err) return;
  err.textContent = msg;
  err.hidden = !msg;
  document.querySelectorAll(`[data-id="${id}"] input, [data-id="${id}"] textarea`).forEach(i => {
    if (msg) i.setAttribute("aria-invalid", "true"); else i.removeAttribute("aria-invalid");
  });
}

async function enviar() {
  const boton = $("#siguiente");
  boton.disabled = true;
  boton.textContent = "Enviando…";
  try {
    const res = await fetch("/api/respuesta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        respuestas, codigo, fuente,
        segundos: Math.round((Date.now() - inicio) / 1000),
        sitio_web: $("#sitio_web").value,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.ok) {
      borrarBorrador();
      mostrarFinal();
      return;
    }
    if (data.errores) {
      // Volver al primer paso con error que marcó el servidor
      const idx = PASOS.findIndex(p => p.preguntas.some(q => data.errores[q.id]));
      if (idx >= 0) { paso = idx; render(); Object.entries(data.errores).forEach(([k, m]) => mostrarError(k, m)); }
    }
    $("#error-general").textContent = data.error || "Revisá los campos marcados.";
  } catch {
    $("#error-general").textContent = "No hay conexión. Tus respuestas quedan guardadas: probá de nuevo.";
  } finally {
    boton.disabled = false;
    boton.textContent = paso === PASOS.length - 1 ? "Enviar" : "Siguiente";
  }
}

function linkAgenda() {
  const u = new URL(CONFIG.calLink);
  u.searchParams.set("name", respuestas.nombre || "");
  u.searchParams.set("email", respuestas.email || "");
  if (codigo) u.searchParams.set("metadata[codigo]", codigo);
  return u.toString();
}

function linkWhatsApp() {
  const texto = `Hola Victor, completé el formulario${codigo ? ` (código ${codigo})` : ""}. Me gustaría coordinar la charla.`;
  return `https://wa.me/${CONFIG.waNumero}?text=${encodeURIComponent(texto)}`;
}

function mostrarFinal() {
  $("#form").hidden = true;
  const nombre = (respuestas.nombre || "").split(" ")[0];
  const acciones = $("#final-acciones");
  acciones.replaceChildren();
  $("#final-titulo").textContent = `¡Gracias${nombre ? ", " + nombre : ""}!`;
  const informe = respuestas.quiere_informe ? " Cuando tengamos las respuestas de todos, te mandamos el informe." : "";

  if (respuestas.interes_charla === "agendar") {
    $("#final-texto").textContent = "Elegí el horario que te quede cómodo para la charla de 20-30 minutos. No hace falta preparar nada: partimos de lo que respondiste." + informe;
    acciones.append(
      el("a", { class: "boton primario", href: linkAgenda(), target: "_blank", rel: "noopener", text: "Elegir horario" }),
      el("a", { class: "boton whatsapp", href: linkWhatsApp(), target: "_blank", rel: "noopener", text: "Prefiero coordinar por WhatsApp" }));
  } else if (respuestas.interes_charla === "contactar") {
    $("#final-texto").textContent = `Te escribimos en las próximas 48 horas${respuestas.canal ? " por " + ({ whatsapp: "WhatsApp", mail: "mail", llamada: "teléfono" })[respuestas.canal] : ""} para coordinar.` + informe;
    acciones.append(el("a", { class: "boton whatsapp", href: linkWhatsApp(), target: "_blank", rel: "noopener", text: "O escribinos ahora por WhatsApp" }));
  } else {
    $("#final-texto").textContent = "Tus respuestas ya nos ayudan muchísimo." + (informe || " Si más adelante querés profundizar, respondé el mensaje por el que te llegó este formulario.");
  }
  $("#final").hidden = false;
  $("#final").focus();
}

$("#responsable").textContent = CONFIG.responsable;

$("#empezar").addEventListener("click", () => {
  const b = leerBorrador();
  if (b && b.respuestas) { respuestas = b.respuestas; paso = Math.min(b.paso || 0, PASOS.length - 1); }
  inicio = Date.now();
  $("#intro").hidden = true;
  $("#form").hidden = false;
  render();
  $("#paso h2").setAttribute("tabindex", "-1");
  $("#paso h2").focus();
});

$("#atras").addEventListener("click", () => {
  leerPaso();
  guardarBorrador();
  if (paso > 0) { paso--; render(); window.scrollTo({ top: 0 }); }
});

$("#form").addEventListener("submit", e => {
  e.preventDefault();
  leerPaso();
  if (!validarPaso()) return;
  guardarBorrador();
  if (paso < PASOS.length - 1) {
    paso++;
    render();
    window.scrollTo({ top: 0 });
    const h = $("#paso h2");
    h.setAttribute("tabindex", "-1");
    h.focus();
  } else {
    enviar();
  }
});
