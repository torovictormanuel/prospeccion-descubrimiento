import csv, sys
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule, CellIsRule
from openpyxl.utils import get_column_letter

SRC = Path(sys.argv[1])
OUT = SRC / "Pipeline_Ventas.xlsx"

def read(name):
    raw = (SRC / name).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return list(csv.DictReader(txt.splitlines(), delimiter=";"))

estudios = read("estudios_contables_10_50.csv")
personas = read("personas_estudios_contables.csv")
tiendas = read("tiendas_mercadolibre.csv")

F = "Arial"
H_FILL = PatternFill("solid", fgColor="1F3864")
H_FONT = Font(name=F, bold=True, color="FFFFFF")
IN_FILL = PatternFill("solid", fgColor="FFF2CC")
BASE = Font(name=F, size=10)
thin = Side(style="thin", color="D9D9D9")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

def header(ws, row, cols, widths=None):
    for i, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=i, value=c)
        cell.fill, cell.font = H_FILL, H_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

wb = Workbook()

# ---------------- Etapas ----------------
et = wb.active
et.title = "Etapas"
etapas = [
    ("1. Prospecto", 0.00, "Está en la lista y encaja con el cliente ideal (ICP).", "Investigaste 1 dato propio de la empresa para personalizar."),
    ("2. Contactado", 0.05, "Enviaste el primer mensaje (LinkedIn/email/WhatsApp).", "Responde. Si no, seguí la cadencia (hasta 5-6 toques)."),
    ("3. Conversación", 0.10, "Respondió y hay intercambio.", "Acepta una llamada de 20-30 min."),
    ("4. Reunión agendada", 0.20, "Llamada con fecha y hora confirmada.", "Se hace la reunión de diagnóstico."),
    ("5. Diagnóstico", 0.40, "Conocés el dolor, el costo de ese dolor, quién decide y si hay presupuesto.", "Las 4 cosas están claras y te pide propuesta."),
    ("6. Propuesta enviada", 0.60, "Propuesta con precio, alcance y plazo, presentada en llamada (no solo por mail).", "Acepta o pide ajustes."),
    ("7. Negociación", 0.80, "Ajustando precio/alcance/condiciones.", "Firma o paga el anticipo."),
    ("8. Ganado", 1.00, "Pagó / firmó.", "Onboarding + pedir referido a los 30 días."),
    ("9. Perdido", 0.00, "Dijo que no o desapareció tras toda la cadencia.", "Anotar el motivo en Notas."),
    ("10. Nutrir", 0.00, "Interés real pero no ahora.", "Recontactar en 60-90 días con algo de valor."),
]
header(et, 1, ["Etapa", "Probabilidad de cierre", "Qué significa", "Criterio para pasar a la siguiente"], [24, 14, 60, 60])
for r, e in enumerate(etapas, 2):
    for c, v in enumerate(e, 1):
        cell = et.cell(row=r, column=c, value=v)
        cell.font, cell.border = BASE, BORDER
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    et.cell(row=r, column=2).number_format = "0%"
    et.cell(row=r, column=2).font = Font(name=F, size=10, color="0000FF")
n_et = len(etapas) + 1
et.cell(row=n_et + 2, column=1, value="Las probabilidades (en azul) son supuestos iniciales: ajustalas con tus tasas reales después de 1-2 meses.").font = Font(name=F, italic=True, size=9)

# ---------------- Pipeline ----------------
pl = wb.create_sheet("Pipeline", 0)
cols = ["ID", "Segmento", "Prioridad", "Empresa", "Contacto", "Cargo", "Ubicación", "LinkedIn / Web",
        "Email", "WhatsApp", "Etapa", "Canal", "Toques", "Último contacto", "Próxima acción",
        "Fecha próx. acción", "Dolor detectado", "Valor estimado (USD)", "Probabilidad",
        "Valor ponderado (USD)", "Alerta", "Notas",
        # columnas que escriben los agentes (n8n) — W en adelante
        "Secuencia", "No contactar", "Paso LinkedIn", "Dato investigado", "Mensaje conexión",
        "Mensaje 1", "Mensaje 2", "Mensaje cierre", "Link WhatsApp", "Link agenda", "Código", "Link form"]
widths = [6, 16, 9, 34, 26, 22, 20, 40, 22, 14, 20, 12, 8, 13, 28, 13, 30, 12, 11, 13, 11, 30,
          11, 10, 9, 40, 40, 50, 40, 40, 30, 30, 11, 34]
header(pl, 1, cols, widths)
pl.row_dimensions[1].height = 32

import re
def clean_estudio(name):
    n = re.sub(r"\(.*?\)", "", name.lower())
    for w in ("estudio contable e impositivo", "estudio contable", "estudio"):
        n = n.replace(w, "")
    return n.strip(" .-")

DECISORES = ("socio", "titular", "director", "fundador", "gerente", "ceo", "partner", "dueñ")
def pick(group):
    dec = [p for p in group if any(k in p["Cargo"].lower() for k in DECISORES)]
    return (dec or group or [None])[0]

rows, usados = [], set()
# Estudios contables: 1 fila por estudio, contacto principal = socio/titular encontrado
for e in estudios:
    key = clean_estudio(e["Estudio"])
    match = [p for p in personas if key and clean_estudio(p["Estudio"]) and
             (key in clean_estudio(p["Estudio"]) or clean_estudio(p["Estudio"]) in key)]
    usados.update(id(p) for p in match)
    p = pick(match)
    rows.append(["Estudio contable", "Alta", e["Estudio"], p["Nombre"] if p else "", p["Cargo"] if p else "",
                 e["Ubicación"], (p["LinkedIn"] if p else "") or e["Link"], "", ""])
# Contactos cuyo estudio no está en la lista de estudios: se agregan como leads propios
sueltos = {}
for p in personas:
    if id(p) not in usados:
        nombre = p["Estudio"] if clean_estudio(p["Estudio"]) not in ("", "—", "propio", "contable") else f"Estudio de {p['Nombre']}"
        sueltos.setdefault(nombre, []).append(p)
for nombre, group in sueltos.items():
    p = pick(group)
    rows.append(["Estudio contable", "Alta", nombre, p["Nombre"], p["Cargo"], p["Ubicación"], p["LinkedIn"], "", ""])
for t in tiendas:
    tam = t.get("Tamaño") or t.get("TamaÃ±o") or ""
    prio = "Baja" if tam.lower().startswith("grande") else "Media"
    web = t.get("Sitio web", "")
    rows.append(["Tienda ML · " + t.get("Rubro", ""), prio, t["Empresa"], "", "", "", web,
                 t.get("Email", ""), t.get("WhatsApp", "")])

FIRST = 2
for i, r in enumerate(rows):
    row = FIRST + i
    vals = [i + 1] + r
    for c, v in enumerate(vals, 1):
        pl.cell(row=row, column=c, value=v)
    pl.cell(row=row, column=11, value="1. Prospecto")
    pl.cell(row=row, column=13, value=0)
    pl.cell(row=row, column=23, value="Pausada" if r[1] == "Baja" else "Activa")
    pl.cell(row=row, column=25, value=0)
    pl.cell(row=row, column=19, value=f'=IFERROR(INDEX(Etapas!$B$2:$B${n_et},MATCH(K{row},Etapas!$A$2:$A${n_et},0)),0)')
    pl.cell(row=row, column=20, value=f'=IF(R{row}="","",R{row}*S{row})')
    pl.cell(row=row, column=21, value=f'=IF(OR(LEFT(K{row},2)="8.",LEFT(K{row},2)="9."),"",IF(AND(P{row}<>"",P{row}<TODAY()),"VENCIDO",IF(P{row}=TODAY(),"HOY","")))')
LAST = FIRST + len(rows) - 1

for row in pl.iter_rows(min_row=FIRST, max_row=LAST):
    for cell in row:
        cell.font, cell.border = BASE, BORDER
    for c in (11, 12, 13, 14, 15, 16, 17, 18, 22, 23, 24):
        row[c - 1].fill = IN_FILL
    for c in range(26, 31):
        row[c - 1].alignment = Alignment(wrap_text=False, vertical="top")
    row[13].number_format = row[15].number_format = "dd/mm/yyyy"
    row[17].number_format = row[19].number_format = "$#,##0;($#,##0);-"
    row[18].number_format = "0%"

pl.freeze_panes = "E2"
pl.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{LAST}"

dv_et = DataValidation(type="list", formula1=f"=Etapas!$A$2:$A${n_et}", allow_blank=True)
dv_canal = DataValidation(type="list", formula1='"LinkedIn,Email,WhatsApp,Llamada,Presencial,Referido"', allow_blank=True)
dv_prio = DataValidation(type="list", formula1='"Alta,Media,Baja"', allow_blank=True)
dv_seq = DataValidation(type="list", formula1='"Activa,Pausada,Terminada"', allow_blank=True)
dv_nc = DataValidation(type="list", formula1='"SI"', allow_blank=True)
for dv, col in ((dv_et, "K"), (dv_canal, "L"), (dv_prio, "C"), (dv_seq, "W"), (dv_nc, "X")):
    pl.add_data_validation(dv)
    dv.add(f"{col}{FIRST}:{col}{LAST + 200}")

pl.conditional_formatting.add(f"U{FIRST}:U{LAST + 200}", CellIsRule(operator="equal", formula=['"VENCIDO"'], fill=PatternFill("solid", fgColor="F8CBAD"), font=Font(name=F, bold=True, color="C00000")))
pl.conditional_formatting.add(f"U{FIRST}:U{LAST + 200}", CellIsRule(operator="equal", formula=['"HOY"'], fill=PatternFill("solid", fgColor="FFE699"), font=Font(name=F, bold=True)))
pl.conditional_formatting.add(f"A{FIRST}:AH{LAST + 200}", FormulaRule(formula=[f'LEFT($K{FIRST},2)="8."'], fill=PatternFill("solid", fgColor="C6EFCE")))
pl.conditional_formatting.add(f"A{FIRST}:AH{LAST + 200}", FormulaRule(formula=[f'OR(LEFT($K{FIRST},2)="9.",$X{FIRST}="SI")'], font=Font(color="A6A6A6")))
for c in range(23, 35):
    pl.cell(row=1, column=c).fill = PatternFill("solid", fgColor="375623")

# ---------------- Tablero ----------------
db = wb.create_sheet("Tablero", 1)
db["A1"] = "Tablero del pipeline"
db["A1"].font = Font(name=F, bold=True, size=14)
db["A2"] = "Todo se calcula solo desde la hoja Pipeline. No edites esta hoja."
db["A2"].font = Font(name=F, italic=True, size=9)
header(db, 4, ["Etapa", "Cantidad", "% del total", "Valor (USD)", "Valor ponderado (USD)"], [24, 11, 11, 14, 20])
rng = lambda c: f"Pipeline!${c}${FIRST}:${c}${LAST + 200}"
for i in range(len(etapas)):
    r = 5 + i
    db.cell(row=r, column=1, value=f"=Etapas!A{2 + i}")
    db.cell(row=r, column=2, value=f"=COUNTIF({rng('K')},A{r})")
    db.cell(row=r, column=3, value=f"=IF($B${5 + len(etapas)}=0,0,B{r}/$B${5 + len(etapas)})").number_format = "0%"
    db.cell(row=r, column=4, value=f"=SUMIF({rng('K')},A{r},{rng('R')})").number_format = "$#,##0;($#,##0);-"
    db.cell(row=r, column=5, value=f"=SUMIF({rng('K')},A{r},{rng('T')})").number_format = "$#,##0;($#,##0);-"
tot = 5 + len(etapas)
db.cell(row=tot, column=1, value="Total")
db.cell(row=tot, column=2, value=f"=SUM(B5:B{tot - 1})")
db.cell(row=tot, column=4, value=f"=SUM(D5:D{tot - 1})").number_format = "$#,##0;($#,##0);-"
db.cell(row=tot, column=5, value=f"=SUM(E5:E{tot - 1})").number_format = "$#,##0;($#,##0);-"
for c in range(1, 6):
    db.cell(row=tot, column=c).font = Font(name=F, bold=True)

k = tot + 2
db.cell(row=k, column=1, value="Indicadores clave").font = Font(name=F, bold=True, size=12)
# contactados = etapa >= 2 (excluye prospecto); el resto según orden de etapas
kpis = [
    ("Seguimientos VENCIDOS", f'=COUNTIF({rng("U")},"VENCIDO")', "0"),
    ("Seguimientos para HOY", f'=COUNTIF({rng("U")},"HOY")', "0"),
    ("Contactados (todo menos Prospecto)", f"=B{tot}-B5", "0"),
    ("Tasa de respuesta (Conversación+ / Contactados)", f"=IF(B{k + 3}=0,0,(SUM(B7:B12))/B{k + 3})", "0%"),
    ("Tasa de reunión (Reunión+ / Contactados)", f"=IF(B{k + 3}=0,0,(SUM(B8:B12))/B{k + 3})", "0%"),
    ("Tasa de cierre (Ganados / Propuesta+Negociación+Ganados)", f"=IF(SUM(B10:B12)=0,0,B12/SUM(B10:B12))", "0%"),
    ("Pipeline abierto ponderado (USD)", f"=SUM(E6:E11)", "$#,##0;($#,##0);-"),
]
for j, (lbl, f, fmt) in enumerate(kpis, 1):
    db.cell(row=k + j, column=1, value=lbl).font = BASE
    c = db.cell(row=k + j, column=2, value=f)
    c.number_format, c.font = fmt, Font(name=F, bold=True)
db.column_dimensions["A"].width = 58
db.cell(row=k + len(kpis) + 2, column=1, value="Metas sugeridas para arrancar: respuesta ≥ 10%, reunión ≥ 5% de contactados, cierre ≥ 20% de propuestas.").font = Font(name=F, italic=True, size=9)


def tabla(ws, filas, cols, widths):
    header(ws, 1, cols, widths)
    for r, v in enumerate(filas, 2):
        for c, x in enumerate(v, 1):
            cell = ws.cell(row=r, column=c, value=x)
            cell.font, cell.border = BASE, BORDER
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    return len(filas) + 1

def nota(ws, row, txt):
    ws.cell(row=row, column=1, value=txt).font = Font(name=F, italic=True, size=9)

# ---------------- Cadencia (LinkedIn semi-automático, modo descubrimiento) ----------------
cd = wb.create_sheet("Cadencia")
cad = [
    (1, "Día 0", "Solicitud de conexión", "Vos (clic en el mail del día)", "Nota corta, sin pitch. El agente investigador la redacta con un dato real del estudio. LinkedIn gratis limita las notas por mes: si no te quedan, mandá la solicitud sin nota."),
    (2, "Al aceptar (o día 3)", "Mensaje 1: link al form", "Vos", "Explicás que estás estudiando cómo mejorar los procesos internos de los estudios, que no vendés nada, y pedís completar el form de 4 minutos (link con su código). A cambio: el informe con los resultados de todos y un diagnóstico. Alternativa: link de agenda."),
    (3, "Día +4", "Mensaje 2: recordatorio + una pregunta", "Vos", "Recordás el form y, si no tiene ni 4 minutos, una pregunta que pueda contestar ahí: '¿cuál es la tarea que más tiempo le saca al equipo cada mes?'."),
    (4, "Día +10", "Mensaje de cierre", "Vos", "Dejás de escribir, con la puerta abierta para recibir el informe. Después la Secuencia pasa a Terminada."),
    ("—", "Cuando completa el form", "Respuestas form", "Automático", "n8n (workflow 05) carga sus respuestas, pausa la secuencia y crea Hallazgos. Si eligió agendar, la pantalla final le muestra Cal.com y WhatsApp. Si pidió que lo contacten, aparece en tu mail diario."),
    ("—", "Cuando escribe por WhatsApp", "Agente Lía", "Automático", "Si viene del form, no repite preguntas: agenda directo. Si viene de LinkedIn, hace 3 preguntas (de a una), registra los hallazgos y agenda la llamada en Cal.com."),
    ("—", "Cuando reserva", "Llamada agendada", "Automático", "La etapa pasa a '4. Reunión agendada' y te llega un mail con lo que ya contó para preparar la llamada."),
]
fin = tabla(cd, cad, ["Paso", "Cuándo", "Qué", "Quién", "Detalle"], [6, 22, 28, 26, 110])
nota(cd, fin + 2, "Regla de oro: es una investigación. Nada de precios, demos ni 'tengo una solución'. Si alguien pide precio, el agente te deriva.")
nota(cd, fin + 3, "Si no respondió nada después del paso 4 → '10. Nutrir' (volver en 60-90 días con el informe) o '9. Perdido'.")

# ---------------- Hallazgos (lo escribe n8n desde el agente de WhatsApp) ----------------
hz = wb.create_sheet("Hallazgos")
header(hz, 1, ["Fecha", "ID", "Empresa", "Contacto", "Tema", "Descripción", "Frecuencia", "Impacto",
               "Herramienta actual", "Cita textual", "Fuente"],
       [12, 6, 30, 22, 24, 50, 18, 24, 24, 45, 12])
hz.freeze_panes = "A2"
nota(hz, 3, "Esta hoja la completa n8n con cada problema que la gente cuenta en el form o por WhatsApp. Las llamadas cargalas a mano con Fuente = 'Llamada'.")
nota(hz, 4, "Cuando tengas 10-15 filas: ordená por Tema y contá cuántas veces se repite cada uno. El problema que más se repite y más cuesta es el que conviene resolver primero.")

# ---------------- Respuestas form (una fila por respuesta, una columna por pregunta) ----------------
# Los encabezados salen de form/public/preguntas.js para que coincidan con lo que escribe el workflow 05.
import json, subprocess
_form = json.loads(subprocess.run(["node", str(Path(__file__).resolve().parent / "preguntas_json.mjs")],
                                  capture_output=True, text=True, check=True, encoding="utf-8").stdout)
_excluir = {"nombre", "rol", "estudio", "email", "whatsapp", "consentimiento"}
rf = wb.create_sheet("Respuestas form")
cols_rf = ["Fecha", "ID", "Código", "Versión", "Segundos", "Estudio", "Nombre", "Rol", "Email", "WhatsApp"] + \
          [p["id"] for p in _form["preguntas"] if p["id"] not in _excluir]
header(rf, 1, cols_rf, [12, 6, 11, 11, 9, 28, 22, 18, 26, 16] + [22] * (len(cols_rf) - 10))
rf.freeze_panes = "B2"
nota(rf, 3, "La completa n8n (workflow 05). Ideal para tablas dinámicas o para conectar a Power BI y buscar patrones por tamaño de estudio y tipo de cliente.")

# ---------------- Guion de la llamada (20 min, The Mom Test) ----------------
gl = wb.create_sheet("Guion llamada")
guion = [
    ("0-2 min", "Encuadre", "Gracias por el tiempo. Te cuento: estoy investigando cómo trabajan los estudios de su tamaño antes de construir nada. No te voy a vender nada. ¿Te molesta si tomo notas?"),
    ("2-5 min", "Contexto", "¿Cómo está armado el estudio? ¿Cuántas personas, qué tipo de clientes, qué haces vos en el día a día?"),
    ("5-12 min", "La última vez", "¿Cuál fue la última tarea que les llevó mucho más tiempo del que debería? Contame qué pasó, paso a paso. ¿Quién la hizo? ¿Con qué herramientas?"),
    ("12-15 min", "Costo", "¿Cada cuánto pasa? ¿Cuántas horas o personas se van ahí? ¿Qué pasa cuando sale mal (multas, reclamos, horas extra)?"),
    ("15-18 min", "Lo que ya probaron", "¿Intentaron resolverlo? ¿Qué usaron, cuánto pagaron, por qué lo dejaron? (Si nunca buscaron solución, quizás no duele tanto.)"),
    ("18-20 min", "Cierre", "¿Hay alguien más del rubro con quien debería hablar? ¿Te puedo escribir cuando tenga el informe o algo para mostrarte?"),
    ("Evitar", "Errores típicos", "Preguntar '¿usarías…?' o '¿pagarías…?' · contar tu idea · aceptar elogios como validación · hablar más que el otro. Buscá hechos, números y compromisos (una presentación, una prueba, un referido)."),
    ("Después", "Registrar", "Cargá cada problema en Hallazgos (Fuente = Llamada) y actualizá Etapa, Dolor detectado y Próxima acción en Pipeline."),
]
tabla(gl, guion, ["Tiempo", "Bloque", "Qué preguntar / decir"], [11, 20, 120])

# ---------------- Guía ----------------
g = wb.create_sheet("Guía")
g.column_dimensions["A"].width = 120
lines = [
    ("Cómo funciona el sistema", True),
    ("1. Agente investigador (n8n, 8:30 de lunes a viernes): toma 12 leads Activos, busca datos públicos de cada estudio con Gemini y escribe los mensajes personalizados en las columnas verdes.", False),
    ("2. Te llega un mail con la cola del día: perfil de LinkedIn + mensaje listo para copiar + botón 'Enviado'. Vos mandás en LinkedIn (unos 10 minutos por día) y tocás el botón.", False),
    ("3. El botón actualiza la planilla sola: Paso LinkedIn, Toques, Último contacto y la fecha del próximo paso.", False),
    ("4. El Mensaje 1 lleva el link al form de 4 minutos (con un código que identifica al lead). Al terminar, si quiere la charla, elige horario en Cal.com o escribe por WhatsApp al agente Lía.", False),
    ("5. Cada 15 minutos n8n trae lo nuevo del form, del agente y de Cal.com: cambia la Etapa, carga Hallazgos y Respuestas form, y te avisa por mail.", False),
    ("", False),
    ("Qué completás vos", True),
    ("Celdas amarillas: Etapa (si cambia por fuera de los agentes), Notas, Valor estimado (recién después del diagnóstico). Columna No contactar = SI frena todo para ese lead.", False),
    ("Columnas verdes (W a AH): las escriben los agentes. Podés editar los mensajes antes de mandarlos, pero no cambies el Código: es lo que vincula la respuesta del form con el lead.", False),
    ("", False),
    ("Metodología", True),
    ("• Fase actual: descubrimiento. El objetivo es entender el problema, no vender. Meta: 15 llamadas o conversaciones con hallazgos.", False),
    ("• Captar: LinkedIn semi-automático (los agentes preparan, vos enviás) + WhatsApp solo si la persona escribe primero (consentimiento).", False),
    ("• Entrevistar: The Mom Test (ver hoja Guion llamada). Hechos pasados, no opiniones sobre ideas.", False),
    ("• Después: con los problemas que más se repiten armás la oferta (piloto chico) y recién ahí usás Diagnóstico → Propuesta → Negociación.", False),
    ("", False),
    ("Prioridad inicial", True),
    ("Alta = estudios contables 11-50 · Media = tiendas ML medianas · Baja = grandes retailers (Secuencia Pausada: retomalos cuando tengas casos de éxito).", False),
]
for r, (txt, bold) in enumerate(lines, 1):
    c = g.cell(row=r, column=1, value=txt)
    c.font = Font(name=F, bold=bold, size=12 if bold else 10)
    c.alignment = Alignment(wrap_text=True)

wb.save(OUT)
print(OUT, len(rows), "leads")
