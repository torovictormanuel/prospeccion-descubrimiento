# Diseño del form de descubrimiento

**Objetivo:** encontrar los problemas operativos que más se repiten en estudios
contables de 10 a 50 personas y conseguir la charla de 20-30 minutos, **sin
vender**. Se completa en unos 4 minutos desde el celular.

Las preguntas viven en [`form/public/preguntas.js`](../form/public/preguntas.js).
Si cambiás una, cambiá también `VERSION` para poder separar las respuestas
viejas de las nuevas al analizar.

## Estructura (5 pantallas cortas)

| Pantalla | Pregunta | Tipo | Valida |
|---|---|---|---|
| 1 · Tu estudio | Personas en el estudio | una opción | segmento |
| | Clientes activos | una opción | segmento |
| | Tipo de clientes | varias | segmento |
| 2 · El último mes | Tareas que llevaron más tiempo del debido (hasta 3) | varias | H1-H8 |
| | Por dónde llega la documentación | varias | H1, H5 |
| | Parte de los clientes que mandó todo tarde o incompleto | una opción | H1 |
| | Horas por semana en tareas repetitivas | una opción | H2, H9 |
| 3 · Cómo se organizan | Con qué controlan tareas y vencimientos | una opción | H8 |
| | Qué pasa si la persona clave se va 2 semanas | una opción | H7 |
| | Última vez que se pasó un vencimiento por algo interno | una opción | H3 |
| | Parte de los clientes que paga honorarios tarde | una opción | H6 |
| | Uso de IA o automatizaciones | una opción | H10 |
| 4 · Una sola historia | La tarea que eliminarías para siempre, y por qué | abierta | todas |
| | (opcional) La última vez que salió mal | abierta | todas |
| 5 · Contacto | Nombre, rol, estudio, email, WhatsApp (opcional), localidad | datos | — |
| | ¿Charla de 20-30 min con diagnóstico gratis? | una opción | siguiente paso |
| | Canal preferido · quiere el informe · **consentimiento** | — | — |

## Por qué así

- **El último mes y la última vez:** los hechos concretos son más
  confiables que las opiniones ("en general nos cuesta…").
- **Opciones cerradas:** permiten contar. Con 15-20 respuestas ya se ve qué
  tarea aparece más y en qué tamaño de estudio.
- **Una sola abierta obligatoria:** es la que da el lenguaje real del cliente
  para tus mensajes y tu propuesta futura.
- **Datos de contacto al final:** primero se da valor; pedir datos al principio
  baja la tasa de respuesta.
- **Incentivo sin venta:** un diagnóstico con ideas concretas y el informe
  comparativo. Es reciprocidad, no un pitch.

## Qué pasa al enviar

| Respuesta a "¿charla?" | Pantalla final | Pipeline (n8n 05) |
|---|---|---|
| Sí, elijo horario | Botón a Cal.com (con nombre y email ya cargados) y botón a WhatsApp | Etapa 3 · "Esperando reserva" → al reservar, el 03 la pasa a 4 |
| Sí, escríbanme | Gracias + botón opcional a WhatsApp | Etapa 3 · "Responder: coordinar charla" (aparece en tu mail diario) |
| Ahora no | Gracias + aviso de que le llega el informe | Etapa 10 · Nutrir, recontacto en 60 días |

En todos los casos se crean filas en **Hallazgos** (una por cada tarea marcada
y una con la respuesta abierta) y una fila en **Respuestas form**, con una
columna por pregunta para analizar patrones en Sheets o Power BI.

## Cómo analizar los patrones (cuando haya 15 o más respuestas)

1. En **Respuestas form**, contá cuántas veces aparece cada tarea en
   `tareas_tiempo` (una tabla dinámica o `COUNTIF(..., "*sueldos*")`).
2. Cruzalo con `tamano` y `tipo_clientes`: ¿el dolor cambia entre estudios de
   6-10 y de 26-50 personas?
3. Cruzá `doc_tarde` con `doc_canales`: si los que reciben todo por WhatsApp
   tienen más demoras, ahí hay una solución concreta.
4. Leé todas las respuestas abiertas y agrupalas por tema (codificación
   cualitativa). El tema que más se repite **y** tiene más costo (horas,
   multas, `dependencia = mucho`) es tu primer piloto.
