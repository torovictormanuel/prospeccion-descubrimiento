# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit

"""
Servidor principal del agente de WhatsApp (descubrimiento de problemas).
Funciona con cualquier proveedor (Meta, Twilio) gracias a la capa de providers.

Además del webhook expone GET /api/eventos, que n8n consulta cada pocos
minutos para pasar al Google Sheet lo que pasó en las conversaciones
(nuevos contactos, hallazgos, llamadas agendadas, bajas).
"""

import os
import re
import hmac
import time
import logging
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import (
    inicializar_db,
    guardar_mensaje,
    obtener_historial,
    mensaje_ya_procesado,
    marcar_mensaje_procesado,
    crear_prospecto_si_no_existe,
    registrar_evento,
    listar_eventos,
)
from agent.providers import obtener_proveedor

load_dotenv()

# Configuración de logging según entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

# Proveedor de WhatsApp (se configura en .env con WHATSAPP_PROVIDER)
proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))
SYNC_API_KEY = os.getenv("SYNC_API_KEY", "")

# El link wa.me trae un texto precargado que vincula el chat con su fila del Pipeline:
#   desde LinkedIn: "Hola Victor, vengo de LinkedIn (ref 12)"   → ref = "12" (columna ID)
#   desde el form:  "... completé el formulario (código Ab12Cd34)" → ref = "Ab12Cd34" (columna Código)
REF_RE = re.compile(r"\bref\.?\s*#?\s*(\d{1,6})\b|\bc[oó]digo\s*:?\s*([A-Za-z0-9]{6,12})\b", re.IGNORECASE)
MAX_LARGO_MENSAJE = 2000  # evita que un mensaje gigante dispare el consumo de tokens

# Rate limit en memoria (un solo proceso alcanza para esta escala).
# Por teléfono: frena a alguien que manda 50 mensajes seguidos y quema tokens.
# Por IP en /api/eventos: frena fuerza bruta sobre la API key.
LIMITES = {"telefono": (15, 600), "api": (30, 60)}  # (máx. pedidos, ventana en segundos)
_hits: dict[str, deque] = defaultdict(deque)


def excede_limite(tipo: str, clave: str) -> bool:
    maximo, ventana = LIMITES[tipo]
    ahora = time.monotonic()
    cola = _hits[f"{tipo}:{clave}"]
    while cola and ahora - cola[0] > ventana:
        cola.popleft()
    if len(cola) >= maximo:
        return True
    cola.append(ahora)
    return False


def enmascarar(telefono: str) -> str:
    """Los logs no guardan el número completo (dato personal)."""
    return f"***{telefono[-4:]}" if telefono else "?"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    if not SYNC_API_KEY:
        logger.warning("SYNC_API_KEY vacío — /api/eventos queda deshabilitado")
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="AgentKit — WhatsApp AI Agent (Descubrimiento)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if ENVIRONMENT == "production" else "/docs",
    redoc_url=None,
)


@app.middleware("http")
async def headers_seguridad(request: Request, call_next):
    """API sin interfaz web: se bloquea que cualquier navegador la embeba o interprete."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/")
async def health_check():
    """Endpoint de salud para monitoreo."""
    return {"status": "ok", "service": "agentkit"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook (requerido por Meta Cloud API, no-op para otros)."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """
    Recibe mensajes de WhatsApp via el proveedor configurado.
    Procesa el mensaje, genera respuesta con Claude y la envía de vuelta.
    """
    try:
        # Verificar que el POST realmente venga del proveedor (firma HMAC).
        # Sin esto, cualquiera que descubra la URL podría hacer que el
        # agente gaste tokens de Claude respondiendo mensajes falsos.
        if not await proveedor.validar_autenticidad(request):
            logger.warning("Webhook rechazado: firma inválida o ausente")
            raise HTTPException(status_code=403, detail="Firma inválida")

        # Parsear webhook — el proveedor normaliza el formato
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            # Ignorar mensajes propios o vacíos
            if msg.es_propio or not msg.texto:
                continue

            # Idempotencia: Meta y Twilio pueden reintentar la entrega del
            # mismo webhook (timeouts, reintentos automáticos). Sin este
            # chequeo, el mismo mensaje se procesaría y respondería 2+ veces.
            if await mensaje_ya_procesado(msg.mensaje_id):
                logger.info(f"Mensaje {msg.mensaje_id} ya procesado — se ignora reintento")
                continue
            await marcar_mensaje_procesado(msg.mensaje_id)

            if excede_limite("telefono", msg.telefono):
                logger.warning(f"Rate limit: {enmascarar(msg.telefono)} superó el máximo de mensajes")
                continue

            texto = msg.texto[:MAX_LARGO_MENSAJE]
            # El contenido solo se loguea en desarrollo: en producción es dato personal
            logger.debug(f"Mensaje de {msg.telefono}: {texto}")
            logger.info(f"Mensaje recibido de {enmascarar(msg.telefono)}")

            # Primer mensaje: crear el prospecto y vincularlo con su fila del Pipeline
            match = REF_RE.search(texto)
            ref = (match.group(1) or match.group(2)) if match else None
            if await crear_prospecto_si_no_existe(msg.telefono, ref):
                await registrar_evento(msg.telefono, "primer_contacto", {"texto": texto[:300]})

            # Obtener historial ANTES de guardar el mensaje actual
            # (brain.py agrega el mensaje actual, evitando duplicados)
            historial = await obtener_historial(msg.telefono)

            # Generar respuesta con Claude
            respuesta = await generar_respuesta(texto, historial, msg.telefono)

            # Guardar mensaje del usuario Y respuesta del agente en memoria
            await guardar_mensaje(msg.telefono, "user", texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            # Enviar respuesta por WhatsApp via el proveedor
            await proveedor.enviar_mensaje(msg.telefono, respuesta)

            logger.debug(f"Respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        # No se devuelve el detalle del error: puede filtrar información interna
        raise HTTPException(status_code=500, detail="Error interno")


@app.get("/api/eventos")
async def api_eventos(request: Request, desde_id: int = 0, x_api_key: str = Header(default="")):
    """
    Bitácora para n8n. Requiere el header X-API-Key = SYNC_API_KEY.
    n8n guarda el último id recibido y pide solo lo nuevo (?desde_id=N).
    """
    if excede_limite("api", request.client.host if request.client else "?"):
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes")
    if not SYNC_API_KEY or not hmac.compare_digest(x_api_key, SYNC_API_KEY):
        raise HTTPException(status_code=401, detail="No autorizado")
    eventos = await listar_eventos(max(0, desde_id))
    return {"eventos": eventos, "ultimo_id": eventos[-1]["id"] if eventos else desde_id}
