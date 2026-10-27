import { test } from "node:test";
import assert from "node:assert/strict";
import { validarRespuesta } from "../lib/validar.js";

const valida = () => ({
  segundos: 120,
  codigo: "Ab12Cd34",
  fuente: "linkedin",
  sitio_web: "",
  respuestas: {
    tamano: "11-25", clientes: "150-300", tipo_clientes: ["monotributo", "empleadores"],
    tareas_tiempo: ["pedir_documentacion", "sueldos"], doc_canales: ["whatsapp", "mail"],
    doc_tarde: "25-50", horas_repetitivas: "15-30",
    control_tareas: "excel", dependencia: "mucho", vencimiento_pasado: "trimestre",
    honorarios_tarde: "<25", uso_ia: "no_se_como",
    tarea_eliminar: "Perseguir a los clientes para que manden las facturas.",
    nombre: "Ana Pérez", rol: "Socia", estudio: "Estudio Pérez", email: "Ana@Estudio.com.ar",
    whatsapp: "+54 9 11 2345-6789", interes_charla: "agendar", canal: "whatsapp",
    quiere_informe: true, consentimiento: true,
  },
});

test("acepta una respuesta completa y normaliza email y teléfono", () => {
  const r = validarRespuesta(valida());
  assert.equal(r.ok, true);
  assert.equal(r.datos.respuestas.email, "ana@estudio.com.ar");
  assert.equal(r.datos.respuestas.whatsapp, "5491123456789");
  assert.equal(r.datos.codigo, "Ab12Cd34");
});

test("rechaza opciones que no existen", () => {
  const b = valida(); b.respuestas.tamano = "1000";
  assert.equal(validarRespuesta(b).errores.tamano, "Opción inválida");
});

test("respeta el máximo de opciones en preguntas múltiples", () => {
  const b = valida(); b.respuestas.tareas_tiempo = ["sueldos", "arca", "consultas", "honorarios"];
  assert.equal(validarRespuesta(b).errores.tareas_tiempo, "Máximo 3");
});

test("exige consentimiento y las obligatorias", () => {
  const b = valida(); delete b.respuestas.consentimiento; delete b.respuestas.tarea_eliminar;
  const r = validarRespuesta(b);
  assert.equal(r.ok, false);
  assert.ok(r.errores.consentimiento && r.errores.tarea_eliminar);
});

test("detecta bots por el campo trampa y por velocidad", () => {
  assert.equal(validarRespuesta({ ...valida(), sitio_web: "spam.com" }).bot, true);
  assert.equal(validarRespuesta({ ...valida(), segundos: 3 }).bot, true);
});

test("descarta código y fuente con formato raro sin fallar", () => {
  const r = validarRespuesta({ ...valida(), codigo: "<script>", fuente: "../../x" });
  assert.equal(r.ok, true);
  assert.equal(r.datos.codigo, null);
  assert.equal(r.datos.fuente, null);
});

test("recorta textos largos y quita caracteres de control", () => {
  const b = valida(); b.respuestas.tarea_eliminar = "a\u0000b".padEnd(5000, "x");
  const r = validarRespuesta(b);
  assert.equal(r.datos.respuestas.tarea_eliminar.length, 600);
  assert.ok(!r.datos.respuestas.tarea_eliminar.includes("\u0000"));
});

test("rechaza tipos inesperados (arrays u objetos donde va texto)", () => {
  const b = valida(); b.respuestas.tamano = ["11-25"]; b.respuestas.consentimiento = "true";
  const r = validarRespuesta(b);
  assert.equal(r.errores.tamano, "Opción inválida");
  assert.ok(r.errores.consentimiento);
  assert.equal(validarRespuesta([]).ok, false);
});
