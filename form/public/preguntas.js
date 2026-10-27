// Fuente única de las preguntas del form de descubrimiento.
// La usa el navegador (para dibujar el form) y la API (para validar).
// Cada pregunta valida una hipótesis de docs/investigacion-flujo-estudio-contable.md.
//
// Tipos: "single" (una opción), "multi" (varias, con `max`), "text" (abierta),
// "short" (texto corto), "email", "tel", "check" (casilla).

export const VERSION = "2026-10-v1";

export const PASOS = [
  {
    id: "estudio",
    titulo: "Tu estudio",
    ayuda: "Para comparar estudios parecidos entre sí.",
    preguntas: [
      {
        id: "tamano", tipo: "single", requerida: true, valida: "segmento",
        texto: "¿Cuántas personas trabajan en el estudio, contándote?",
        opciones: [
          ["1", "Solo yo"], ["2-5", "2 a 5"], ["6-10", "6 a 10"],
          ["11-25", "11 a 25"], ["26-50", "26 a 50"], ["50+", "Más de 50"],
        ],
      },
      {
        id: "clientes", tipo: "single", requerida: true, valida: "segmento",
        texto: "¿Con cuántos clientes activos trabajan, más o menos?",
        opciones: [
          ["<50", "Menos de 50"], ["50-150", "50 a 150"], ["150-300", "150 a 300"],
          ["300-600", "300 a 600"], ["600+", "Más de 600"],
        ],
      },
      {
        id: "tipo_clientes", tipo: "multi", max: 7, requerida: true, valida: "segmento",
        texto: "¿Qué tipo de clientes tienen? Marcá todos los que correspondan.",
        opciones: [
          ["monotributo", "Monotributistas"], ["ri_pymes", "Responsables inscriptos / pymes"],
          ["empleadores", "Empresas con empleados"], ["sociedades", "Sociedades (SA, SRL, SAS)"],
          ["profesionales", "Profesionales / autónomos"], ["agro", "Agro"],
          ["ecommerce", "E-commerce / Mercado Libre"],
        ],
      },
    ],
  },
  {
    id: "mes",
    titulo: "El último mes",
    ayuda: "Pensá en lo que pasó de verdad este último mes, no en general.",
    preguntas: [
      {
        id: "tareas_tiempo", tipo: "multi", max: 3, requerida: true, valida: "H1-H8",
        texto: "En el último mes, ¿qué tareas les llevaron más tiempo del que deberían? Elegí hasta 3.",
        opciones: [
          ["pedir_documentacion", "Pedir y perseguir documentación a clientes"],
          ["carga_comprobantes", "Cargar comprobantes y facturas"],
          ["conciliaciones", "Conciliaciones bancarias"],
          ["sueldos", "Liquidación de sueldos y novedades"],
          ["vencimientos", "Controlar vencimientos de cada cliente"],
          ["arca", "Presentaciones y pagos en ARCA (caídas, VEPs)"],
          ["consultas", "Responder consultas de clientes (WhatsApp, mail)"],
          ["honorarios", "Cobrar honorarios"],
          ["reportes", "Armar reportes o informes para clientes"],
          ["equipo", "Revisar el trabajo del equipo o capacitar"],
          ["normativa", "Actualizarse con cambios normativos"],
        ],
      },
      {
        id: "doc_canales", tipo: "multi", max: 6, requerida: true, valida: "H1-H5",
        texto: "¿Por dónde les llega la documentación de los clientes?",
        opciones: [
          ["whatsapp", "WhatsApp"], ["mail", "Mail"], ["papel", "Papel / en persona"],
          ["drive", "Drive, Dropbox o carpeta compartida"], ["portal", "Portal o sistema del estudio"],
          ["arca", "La bajamos nosotros de ARCA o del banco"],
        ],
      },
      {
        id: "doc_tarde", tipo: "single", requerida: true, valida: "H1",
        texto: "El último mes, ¿qué parte de los clientes mandó la documentación tarde o incompleta?",
        opciones: [
          ["casi_nadie", "Casi nadie"], ["<25", "Menos de 1 de cada 4"],
          ["25-50", "Entre 1 de cada 4 y la mitad"], [">50", "Más de la mitad"],
        ],
      },
      {
        id: "horas_repetitivas", tipo: "single", requerida: true, valida: "H2-H9",
        texto: "Sumando a todo el equipo, ¿cuántas horas por semana se van en tareas repetitivas (cargar, pedir papeles, recordatorios)?",
        opciones: [
          ["<5", "Menos de 5"], ["5-15", "5 a 15"], ["15-30", "15 a 30"],
          ["30+", "Más de 30"], ["ns", "No sabría decir"],
        ],
      },
    ],
  },
  {
    id: "organizacion",
    titulo: "Cómo se organizan",
    ayuda: "Cinco preguntas rápidas.",
    preguntas: [
      {
        id: "control_tareas", tipo: "single", requerida: true, valida: "H8",
        texto: "¿Con qué controlan las tareas y vencimientos de cada cliente?",
        opciones: [
          ["excel", "Excel o Google Sheets"], ["software", "Software del estudio (Onvio, Aconpy, Holistor, etc.)"],
          ["agenda", "Agenda o papel"], ["memoria", "Cada uno a su manera / de memoria"],
          ["otro", "Otro"],
        ],
      },
      {
        id: "dependencia", tipo: "single", requerida: true, valida: "H7",
        texto: "Si el socio o la persona clave se toma 2 semanas, ¿qué pasa con el trabajo?",
        opciones: [
          ["sigue", "Sigue normal"], ["algo", "Se frenan algunas cosas"],
          ["mucho", "Se frena mucho"], ["no_puede", "No se puede tomar 2 semanas"],
        ],
      },
      {
        id: "vencimiento_pasado", tipo: "single", requerida: true, valida: "H3",
        texto: "¿Cuándo fue la última vez que se pasó un vencimiento o hubo un recargo por algo interno (no del cliente)?",
        opciones: [
          ["mes", "Este último mes"], ["trimestre", "En los últimos 3 meses"],
          ["anio", "En el último año"], ["nunca", "No recuerdo / nunca"],
        ],
      },
      {
        id: "honorarios_tarde", tipo: "single", requerida: true, valida: "H6",
        texto: "¿Qué parte de los clientes paga los honorarios tarde?",
        opciones: [
          ["casi_nadie", "Casi nadie"], ["<25", "Menos de 1 de cada 4"],
          ["25-50", "Entre 1 de cada 4 y la mitad"], [">50", "Más de la mitad"],
        ],
      },
      {
        id: "uso_ia", tipo: "single", requerida: true, valida: "H10",
        texto: "¿Ya usan IA o automatizaciones en el estudio?",
        opciones: [
          ["si", "Sí, en algunas tareas"], ["probamos", "Probamos y lo dejamos"],
          ["no_se_como", "No, no sabemos por dónde empezar"], ["no_interesa", "No, no nos interesa"],
        ],
      },
    ],
  },
  {
    id: "historia",
    titulo: "Una sola historia",
    ayuda: "Lo más valioso del form. Con dos líneas alcanza.",
    preguntas: [
      {
        id: "tarea_eliminar", tipo: "text", requerida: true, maxLargo: 600, valida: "abierta",
        texto: "Si mañana pudieras sacarte de encima UNA tarea del estudio para siempre, ¿cuál sería y por qué?",
        placeholder: "Ej.: perseguir a los clientes para que manden las facturas antes del 10…",
      },
      {
        id: "ultima_vez", tipo: "text", requerida: false, maxLargo: 800, valida: "abierta",
        texto: "(Opcional) Contame la última vez que esa tarea salió mal o llevó más de la cuenta.",
        placeholder: "Qué pasó, cuánto tiempo llevó, qué consecuencias tuvo…",
      },
    ],
  },
  {
    id: "contacto",
    titulo: "Seguimos en contacto",
    ayuda: "Para mandarte el diagnóstico y el informe. No compartimos tus datos.",
    preguntas: [
      { id: "nombre", tipo: "short", requerida: true, maxLargo: 100, texto: "Nombre y apellido", autocomplete: "name" },
      { id: "rol", tipo: "short", requerida: true, maxLargo: 100, texto: "Tu rol en el estudio", placeholder: "Socio/a, titular, responsable de impuestos…", autocomplete: "organization-title" },
      { id: "estudio", tipo: "short", requerida: true, maxLargo: 150, texto: "Nombre del estudio", autocomplete: "organization" },
      { id: "email", tipo: "email", requerida: true, maxLargo: 150, texto: "Email", autocomplete: "email" },
      { id: "whatsapp", tipo: "tel", requerida: false, maxLargo: 25, texto: "WhatsApp (opcional)", placeholder: "11 2345 6789", autocomplete: "tel" },
      { id: "localidad", tipo: "short", requerida: false, maxLargo: 100, texto: "Localidad y provincia (opcional)", autocomplete: "address-level2" },
      {
        id: "interes_charla", tipo: "single", requerida: true, valida: "siguiente paso",
        texto: "¿Te interesaría una charla de 20-30 minutos para profundizar? Te llevás un diagnóstico con ideas concretas para tu estudio, sin costo y sin venta.",
        opciones: [
          ["agendar", "Sí, quiero elegir un horario ahora"],
          ["contactar", "Sí, escríbanme para coordinar"],
          ["ahora_no", "Ahora no, gracias"],
        ],
      },
      {
        id: "canal", tipo: "single", requerida: false,
        texto: "¿Por dónde preferís que te contactemos?",
        opciones: [["whatsapp", "WhatsApp"], ["mail", "Mail"], ["llamada", "Llamada"]],
      },
      { id: "quiere_informe", tipo: "check", requerida: false, texto: "Quiero recibir el informe con los resultados de todos los estudios (anónimos)." },
      { id: "consentimiento", tipo: "check", requerida: true, texto: "Acepto que usen mis datos solo para esta investigación y para contactarme. Puedo pedir que los borren cuando quiera.", enlace: ["/privacidad.html", "Política de privacidad"] },
    ],
  },
];

export const TODAS = PASOS.flatMap(p => p.preguntas);
