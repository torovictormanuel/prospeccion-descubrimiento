# Cómo trabaja un estudio contable en Argentina (y dónde le duele)

Investigación previa al diseño del form de descubrimiento. Fuentes al final.
Fecha: octubre 2026.

> Ojo con las fuentes: varias son de proveedores de software (Thomson Reuters,
> Xubio, Nubox), que tienen interés en mostrar el problema. Se usan para
> formular **hipótesis**; el form sirve para confirmarlas o descartarlas con
> estudios reales.

## 1. El flujo de trabajo, de punta a punta

Un estudio de 10 a 50 personas repite el mismo ciclo **todos los meses** para
cada cliente, más picos estacionales.

| # | Etapa | Qué pasa | Herramientas típicas |
|---|---|---|---|
| 1 | **Alta del cliente** | Relevamiento, clave fiscal delegada en ARCA, alta de impuestos, honorarios pactados | Mail, papel, Excel |
| 2 | **Pedido de documentación** | Facturas de compra y venta, extractos bancarios, novedades de sueldos (altas, bajas, horas extra, licencias) | WhatsApp, mail, papel, Drive |
| 3 | **Carga y procesamiento** | Registro de comprobantes, conciliación bancaria, imputaciones | Holistor, Tango, Xubio, Onvio, Excel |
| 4 | **Liquidaciones** | IVA, Ingresos Brutos, retenciones y percepciones, monotributo, sueldos (F.931 y Libro de Sueldos Digital) | Sistema contable, aplicativos de ARCA |
| 5 | **Presentación y pago** | DDJJ en ARCA, VEPs, planes de pago, embargos | Web de ARCA (con caídas en días pico) |
| 6 | **Comunicación con el cliente** | Avisar qué pagar y cuándo, responder consultas y explicar cambios normativos | WhatsApp, mail, teléfono |
| 7 | **Cobro de honorarios** | Abono mensual y trabajos extra; seguimiento de los que pagan tarde | Excel, transferencia, recordatorios a mano |
| 8 | **Gestión interna** | Asignar tareas, controlar vencimientos por cliente, revisar el trabajo del equipo, capacitar | Excel, agenda, software de vencimientos (Aconpy, Onvio) |

**Calendario que tensiona todo:**
- **Mensual:** los vencimientos de ARCA se escalonan por terminación de CUIT.
  Durante el mes vencen autónomos, empleadores, monotributo (día 20), IVA y
  anticipos de Ganancias y Bienes Personales.
- **Semestral:** la recategorización del monotributo (enero y julio) multiplica
  el trabajo en estudios con muchos monotributistas.
- **Temporada alta (mayo a julio):** Ganancias y Bienes Personales anuales y
  regímenes de información, todo escalonado por CUIT, más los cambios
  normativos permanentes.

## 2. Problemas recurrentes (hipótesis a validar)

| # | Problema | Evidencia encontrada | Etapa |
|---|---|---|---|
| H1 | **Clientes que mandan la documentación tarde o incompleta**, por canales dispersos | El 90 % de los contadores encuestados dice que la impuntualidad de los clientes complica su trabajo (Nubox, 2019). El CPCE de la Provincia de Buenos Aires (RePro) la nombra entre las urgencias que se repiten. | 2 |
| H2 | **Carga manual de comprobantes** | Es lo más buscado para automatizar: 30 % de quienes todavía no usan IA quieren usarla para eso (Thomson Reuters + CPCECABA, 561 contadores). | 3 |
| H3 | **Urgencia permanente y vencimientos encima** | "La urgencia se vuelve rutina" (RePro). Mayo a julio concentra presentaciones (Blog del Contador, en iProfesional). | 4-5 |
| H4 | **La web de ARCA se cae en días pico** | Equipos que se conectan después de medianoche para categorizar (Estudio Piacentini, en iProfesional). VEPs y planes que no se pudieron cargar. | 5 |
| H5 | **Consultas de clientes por WhatsApp a toda hora** | Canales desordenados (RePro). Clientes que preguntan por normas que todavía no están reglamentadas (iProfesional). | 6 |
| H6 | **Honorarios que se cobran tarde o que quedaron desactualizados** | "No fuimos preparados para cobrar" (Contadores en Red). Clientes que consumen más horas que las pactadas (RePro). | 7 |
| H7 | **Todo depende del socio o titular** | Cuello de botella, cuesta delegar ("nadie lo hace igual") y el conocimiento está en las personas, no en procedimientos (RePro). | 8 |
| H8 | **Control de tareas y vencimientos en Excel o "de memoria"** | El 42 % elegiría un gerenciador de tareas contables como la herramienta con IA más útil (Thomson Reuters). | 8 |
| H9 | **Burnout y trabajo fuera de horario** | El 34 % adoptaría IA para tener equilibrio entre trabajo y vida personal, la primera motivación, por encima de ganar más (6 %) (Thomson Reuters). Hay casos públicos de abandono de la profesión (iProfesional). | todas |
| H10 | **Interés en la IA, pero sin saber cómo implementarla** | Solo el 36 % la usa; entre los que no, 39 % no sabe cómo implementarla y 31 % no sabe cómo hacerlo. En estudios de más de 10 empleados la usa el 54 % (Thomson Reuters). | — |

**Conclusión para el negocio:** el dolor más mencionado no es técnico-contable.
Es **operativo y de coordinación**: conseguir la información del cliente,
ordenar canales, controlar tareas y vencimientos, y no depender de una sola
persona. Justo ahí la automatización (WhatsApp, recordatorios, tableros,
carga asistida con IA) tiene más impacto y menos riesgo profesional.

### Hipótesis sumadas en la v2 (sesión "Sistema complementario contable")

El proyecto **no busca reemplazar el sistema contable** del contador, sino
complementarlo donde se queda corto.

| # | Hipótesis | Por qué importa | Pregunta |
|---|---|---|---|
| H11 | Lo que más cuesta es lo que **no está en ARCA**: novedades de sueldos, extractos, retenciones de bancos, tickets, compras del exterior y plataformas | Los sistemas en la nube (SOS Contador, Xubio) ya importan lo que está en ARCA | `fuera_arca` |
| H12 | Los sistemas de escritorio (Holistor, Bejerman, Tango, Catedral) **no tienen portal para el cliente** | Define el segmento: escritorio → capa intermedia completa; nube → solo lo que no está en ARCA | `sistema` |
| H13 | Hay huecos concretos del sistema que se repiten: recibir la documentación, saber qué falta, carga manual, sueldos, bancos, avisos y tablero | Es exactamente lo que se puede sumar sin competir con el sistema | `falla_sistema` |

El form también se abrió a **contadores en general** (independientes, socios,
empleados de estudios y contadores de empresa), con la pregunta `modalidad`
para segmentar.

## 3. Cómo se traduce en preguntas

Reglas (método *The Mom Test* aplicado a un form):
- Preguntar por **el último mes**, no por "en general", ni por "¿usarías…?".
- Usar casi siempre opciones cerradas, para poder **contar patrones** entre
  estudios, y dejar **una sola abierta** para la historia concreta.
- Que se pueda responder en **4 minutos** desde el celular.
- Cada pregunta valida una hipótesis (columna "Valida" en
  [diseno-form.md](diseno-form.md)).

## Fuentes

- Thomson Reuters + CPCECABA — [Informe IA en estudios contables en Argentina 2025](https://www.thomsonreuters.com.ar/content/dam/ewp-m/documents/argentina/es/pdf/white-papers/informe-inteligencia-artificial-en-la-contabilidad-en-argentina-2025.pdf) (561 profesionales)
- RePro (CPCE Provincia de Buenos Aires) — [Cómo saber si el estudio contable creció más rápido que su organización](https://reprodigital.com.ar/nota/1175)
- iProfesional — [El desafío de ser contador en Argentina](https://www.iprofesional.com/impuestos/461079-el-desafio-de-ser-contador-en-argentina-de-luchar-con-arca-a-los-cambios-normativos)
- Nubox — [Impuntualidad de los clientes: el dolor de los contadores](https://blog.nubox.com/contadores/relacion-cliente-contador)
- Contadores en Red — [Falta recurrente de pago de honorarios](https://contadoresenred.com/como-pararnos-ante-la-falta-recurrente-de-pago-de-honorarios-por-gabriel-nicosia/) · [Ley 27.799 y los estudios](https://contadoresenred.com/impacto-de-la-ley-27-799-en-los-estudios-contables/amp/)
- Thomson Reuters — [Burnout contable](https://www.thomsonreuters.com.ar/es/soluciones-fiscales-contables-gestion/blog-contadores/burnout-contable.html)
- Calendario ARCA — [Econoblog, vencimientos octubre 2026](https://www.econoblog.com.ar/159543/arca-establecio-los-vencimientos-de-octubre-de-2026/) · [BBVA, calendario fiscal 2026](https://www.bbva.com/es/ar/empresas/calendario-fiscal-arca-2026-en-argentina-monotributo-iva-ganancias-y-aportes/)
- ARCA — [Libro de Sueldos Digital](https://www.afip.gob.ar/LibrodeSueldosDigital/novedades-beneficios/definicion.asp)
- Recategorización del monotributo — [Todo Jujuy, julio 2026](https://www.todojujuy.com/pais/a-no-dormirse-este-viernes-vence-la-recategorizacion-monotributo-n229960)
- Herramientas de vencimientos — [Onvio, grilla de vencimientos](https://www.thomsonreuters.com/es-ar/help/onvio/due-dates/grilla-vencimientos) · [Blog del Contador, sistemas de planificación](https://blogdelcontador.com.ar/que-es-un-sistema-de-planificacion-para-estudios-contables-y-por-que-es-clave-hoy-en-dia)
- Gestorías — [Clientes que no mandan las facturas a tiempo](https://copilotgestoria.com/blog/clientes-no-envian-facturas-a-tiempo-protocolo-gestoria-2026)
