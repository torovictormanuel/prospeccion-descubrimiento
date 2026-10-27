# agent/tools.py — Herramientas del agente (rubro: descubrimiento de problemas)
# Generado por AgentKit

"""
Herramientas expuestas al modelo como tools de la API de Claude.
El objetivo del agente NO es vender: es entender cómo trabaja el
prospecto, registrar sus problemas reales (hallazgos) y agendar una
llamada de descubrimiento de 20 minutos con Victor en Cal.com.

Contrato con brain.py:
  - TOOLS: lista de schemas JSON que se le pasan al modelo.
  - EJECUTAR_TOOL: dict {nombre: función} para despachar la llamada real.
  - Cada función recibe `telefono` inyectado por brain.py (el modelo
    nunca lo maneja) + los parámetros que decida el modelo.
  - Cada función retorna un dict serializable a JSON.
"""

import os
import re
import logging
from datetime import datetime, date, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from agent.memory import (
    registrar_evento,
    actualizar_prospecto,
    obtener_prospecto,
    guardar_hallazgo,
)

logger = logging.getLogger("agentkit")

CAL_API = "https://api.cal.com/v2"
CAL_API_KEY = os.getenv("CAL_API_KEY", "")
CAL_EVENT_TYPE_ID = os.getenv("CAL_EVENT_TYPE_ID", "")
CAL_LINK = os.getenv("CAL_LINK", "")
TIMEZONE = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _cal_configurado() -> bool:
    return bool(CAL_API_KEY and CAL_EVENT_TYPE_ID)


async def _link_agenda(telefono: str) -> str:
    """Link de Cal.com con la ref del prospecto, para que n8n pueda vincular la reserva a su fila."""
    if not CAL_LINK:
        return ""
    p = await obtener_prospecto(telefono)
    if p and p.ref:
        return f"{CAL_LINK}?metadata[ref]={quote(p.ref)}&notes={quote('ref ' + p.ref)}"
    return CAL_LINK


async def guardar_datos_contacto(
    telefono: str,
    nombre: str | None = None,
    empresa: str | None = None,
    rol: str | None = None,
    email: str | None = None,
) -> dict:
    """Guarda nombre, empresa, rol o email del prospecto a medida que los cuenta."""
    if email and not EMAIL_RE.match(email):
        return {"error": "El email no parece válido, pedile que lo confirme"}
    await actualizar_prospecto(telefono, nombre=nombre, empresa=empresa, rol=rol, email=email)
    await registrar_evento(telefono, "datos", {"nombre": nombre, "empresa": empresa, "rol": rol, "email": email})
    return {"guardado": True}


async def registrar_hallazgo(
    telefono: str,
    tema: str,
    descripcion: str,
    frecuencia: str | None = None,
    impacto: str | None = None,
    herramienta_actual: str | None = None,
    cita_textual: str | None = None,
) -> dict:
    """Registra un problema concreto que contó el prospecto."""
    hallazgo_id = await guardar_hallazgo(
        telefono,
        tema=tema[:100],
        descripcion=descripcion,
        frecuencia=frecuencia,
        impacto=impacto,
        herramienta_actual=herramienta_actual,
        cita_textual=cita_textual,
    )
    await registrar_evento(telefono, "hallazgo", {
        "tema": tema, "descripcion": descripcion, "frecuencia": frecuencia,
        "impacto": impacto, "herramienta_actual": herramienta_actual, "cita_textual": cita_textual,
    })
    return {"registrado": True, "hallazgo_id": hallazgo_id}


async def ver_horarios_disponibles(telefono: str, dias: int = 7) -> dict:
    """
    Consulta Cal.com y devuelve hasta 6 horarios libres en los próximos `dias`.
    Si Cal.com no está configurado o falla, devuelve el link de agenda para
    que la persona elija sola.
    """
    link = await _link_agenda(telefono)
    if not _cal_configurado():
        return {"horarios": [], "link_agenda": link}

    tz = ZoneInfo(TIMEZONE)
    desde = date.today() + timedelta(days=1)
    hasta = desde + timedelta(days=max(1, min(dias, 14)))
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{CAL_API}/slots",
                params={
                    "eventTypeId": CAL_EVENT_TYPE_ID,
                    "start": desde.isoformat(),
                    "end": hasta.isoformat(),
                    "timeZone": TIMEZONE,
                },
                headers={"Authorization": f"Bearer {CAL_API_KEY}", "cal-api-version": "2024-09-04"},
            )
        r.raise_for_status()
        por_dia = r.json().get("data", {})
    except Exception as e:
        logger.error(f"Error consultando slots de Cal.com: {e}")
        return {"horarios": [], "link_agenda": link, "aviso": "No pude consultar la agenda, ofrecé el link"}

    # Máximo 2 horarios por día y 6 en total: en WhatsApp una lista larga no se lee
    horarios = []
    for _, slots in sorted(por_dia.items()):
        for s in slots[:2]:
            inicio = s["start"] if isinstance(s, dict) else s
            dt = datetime.fromisoformat(inicio.replace("Z", "+00:00")).astimezone(tz)
            horarios.append({
                "inicio": dt.isoformat(),
                "legible": f"{DIAS[dt.weekday()]} {dt:%d/%m} a las {dt:%H:%M}",
            })
        if len(horarios) >= 6:
            break
    return {"horarios": horarios[:6], "link_agenda": link}


async def agendar_llamada(telefono: str, inicio: str, nombre: str, email: str) -> dict:
    """Reserva la llamada en Cal.com. `inicio` es uno de los ISO devueltos por ver_horarios_disponibles."""
    if not EMAIL_RE.match(email or ""):
        return {"error": "Falta un email válido para enviarle la invitación"}
    if not _cal_configurado():
        return {"error": "Agenda automática no configurada", "link_agenda": await _link_agenda(telefono)}

    try:
        inicio_utc = datetime.fromisoformat(inicio.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return {"error": "Horario inválido, volvé a consultar ver_horarios_disponibles"}

    p = await obtener_prospecto(telefono)
    metadata = {"telefono": telefono}
    if p and p.ref:
        metadata["ref"] = p.ref

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{CAL_API}/bookings",
                json={
                    "start": inicio_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "eventTypeId": int(CAL_EVENT_TYPE_ID),
                    "attendee": {"name": nombre, "email": email, "timeZone": TIMEZONE, "language": "es"},
                    "metadata": metadata,
                },
                headers={"Authorization": f"Bearer {CAL_API_KEY}", "cal-api-version": "2026-02-25"},
            )
        if r.status_code >= 400:
            logger.error(f"Cal.com rechazó la reserva: {r.status_code} — {r.text}")
            return {"error": "Ese horario ya no está disponible, ofrecé otros", "link_agenda": await _link_agenda(telefono)}
        reserva = r.json().get("data", {})
    except Exception as e:
        logger.error(f"Error creando reserva en Cal.com: {e}")
        return {"error": "No pude reservar, ofrecé el link", "link_agenda": await _link_agenda(telefono)}

    await actualizar_prospecto(telefono, nombre=nombre, email=email, estado="agendado")
    await registrar_evento(telefono, "agendado", {"inicio": inicio_utc.isoformat(), "uid": reserva.get("uid"), "email": email})
    local = inicio_utc.astimezone(ZoneInfo(TIMEZONE))
    return {"confirmado": True, "cuando": f"{DIAS[local.weekday()]} {local:%d/%m} a las {local:%H:%M}", "email": email}


async def marcar_no_contactar(telefono: str, motivo: str) -> dict:
    """La persona no quiere participar: se marca para no volver a contactarla."""
    await actualizar_prospecto(telefono, estado="no_contactar")
    await registrar_evento(telefono, "no_contactar", {"motivo": motivo})
    return {"marcado": True}


async def escalar_a_victor(telefono: str, motivo: str) -> dict:
    """Avisa a Victor para que siga la conversación en persona."""
    logger.warning(f"ESCALAR A VICTOR — telefono={telefono} motivo={motivo}")
    await actualizar_prospecto(telefono, estado="escalado")
    await registrar_evento(telefono, "escalar", {"motivo": motivo})
    return {"escalado": True}


# ════════════════════════════════════════════════════════════
# Contrato con brain.py — schemas + dispatcher
# ════════════════════════════════════════════════════════════

TOOLS = [
    {
        "name": "guardar_datos_contacto",
        "description": "Guarda nombre, empresa, rol o email del prospecto cuando los menciona. Llamala apenas tengas alguno de esos datos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string"},
                "empresa": {"type": "string", "description": "Nombre del estudio contable"},
                "rol": {"type": "string", "description": "Cargo: socio, titular, responsable de impuestos, dueño, etc."},
                "email": {"type": "string"},
            },
        },
    },
    {
        "name": "registrar_hallazgo",
        "description": "Registra UN problema concreto que contó el prospecto. Llamala después de cada respuesta que describa una tarea que les cuesta, se repite o les genera errores. Un hallazgo por problema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tema": {"type": "string", "description": "Categoría corta, ej: 'pedido de documentación', 'carga de comprobantes', 'vencimientos', 'ARCA', 'consultas de clientes', 'sueldos', 'honorarios', 'dependencia del socio'"},
                "descripcion": {"type": "string", "description": "Qué pasa, en palabras simples"},
                "frecuencia": {"type": "string", "description": "Cada cuánto pasa (si lo dijo)"},
                "impacto": {"type": "string", "description": "Horas, personas, errores o plata que cuesta (si lo dijo)"},
                "herramienta_actual": {"type": "string", "description": "Cómo lo resuelven hoy: Excel, a mano, sistema X, WhatsApp..."},
                "cita_textual": {"type": "string", "description": "La frase literal más reveladora del prospecto"},
            },
            "required": ["tema", "descripcion"],
        },
    },
    {
        "name": "ver_horarios_disponibles",
        "description": "Consulta la agenda de Victor y devuelve horarios libres para la llamada de 20 minutos, más un link de agenda como alternativa.",
        "input_schema": {
            "type": "object",
            "properties": {"dias": {"type": "integer", "description": "Cuántos días hacia adelante buscar (default 7, máx 14)"}},
        },
    },
    {
        "name": "agendar_llamada",
        "description": "Reserva la llamada en el horario que eligió la persona. Requiere su nombre y email (ahí le llega la invitación). Usá EXACTAMENTE el valor 'inicio' que devolvió ver_horarios_disponibles.",
        "input_schema": {
            "type": "object",
            "properties": {
                "inicio": {"type": "string", "description": "Fecha-hora ISO tal cual vino en ver_horarios_disponibles"},
                "nombre": {"type": "string"},
                "email": {"type": "string"},
            },
            "required": ["inicio", "nombre", "email"],
        },
    },
    {
        "name": "marcar_no_contactar",
        "description": "Usala si la persona dice que no le interesa, que no la contacten más, o se molesta por el contacto.",
        "input_schema": {
            "type": "object",
            "properties": {"motivo": {"type": "string"}},
            "required": ["motivo"],
        },
    },
    {
        "name": "escalar_a_victor",
        "description": "Avisa a Victor para que siga él la conversación: pide hablar con una persona, pregunta por precios/servicios concretos, propone un horario que no está en la agenda, o algo que no sabés responder.",
        "input_schema": {
            "type": "object",
            "properties": {"motivo": {"type": "string"}},
            "required": ["motivo"],
        },
    },
]

EJECUTAR_TOOL = {
    "guardar_datos_contacto": guardar_datos_contacto,
    "registrar_hallazgo": registrar_hallazgo,
    "ver_horarios_disponibles": ver_horarios_disponibles,
    "agendar_llamada": agendar_llamada,
    "marcar_no_contactar": marcar_no_contactar,
    "escalar_a_victor": escalar_a_victor,
}
