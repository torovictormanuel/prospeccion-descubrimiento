// Exporta las preguntas del form como JSON para los generadores en Python.
import { TODAS, VERSION } from "../form/public/preguntas.js";
const preguntas = TODAS.map(p => ({ id: p.id, tipo: p.tipo, texto: p.texto, opciones: Object.fromEntries(p.opciones || []) }));
console.log(JSON.stringify({ version: VERSION, preguntas }));
