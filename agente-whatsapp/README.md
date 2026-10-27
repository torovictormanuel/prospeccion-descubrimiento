# Agente Lía — WhatsApp para estudios contables (descubrimiento)

Copia de [whatsapp-agentkit](https://github.com/torovictormanuel/Agent-IA---whatsApp-)
especializada en una sola cosa: **conversar con contadores para entender los
problemas de su estudio y agendar una charla con Victor**. No vende.

El kit original sigue intacto en su propio repo. Esta copia diverge a
propósito: el código del agente está en la raíz (no en `examples/`) y se
versiona junto al contexto del rubro. La documentación del kit base está en
[KIT_README.md](KIT_README.md) y la guía para generar agentes con Claude Code
en [CLAUDE.md](CLAUDE.md).

## Qué sabe del rubro

Todo lo que está en `knowledge/*.md` se agrega al system prompt
(`agent/brain.py`):

| Archivo | Contenido |
|---|---|
| [01_como_funciona_un_estudio_contable.md](knowledge/01_como_funciona_un_estudio_contable.md) | Estructura del estudio, tipos de clientes, circuito mensual, calendario (vencimientos por CUIT, recategorización, temporada alta), herramientas y términos (ARCA, VEP, F.931, SIFERE…) |
| [02_dolores_y_como_hablan.md](knowledge/02_dolores_y_como_hablan.md) | Las 10 hipótesis de dolor, cómo las dicen los contadores, repreguntas, datos de encuestas y señales de dolor real |
| [03_como_conversar_con_un_contador.md](knowledge/03_como_conversar_con_un_contador.md) | Tono, lo que nunca hay que hacer (pedir datos de clientes, asesorar, vender), momento del año y ejemplos |

Para sumar conocimiento, agregá otro `.md` numerado. Lo privado (notas de
clientes) va en `knowledge/privado/`, que no se sube a git ni entra al prompt.

El prompt largo se marca para *prompt caching*: después del primer mensaje
se cobra mucho menos por repetirlo.

## Cómo llega la gente

| Desde | Texto precargado del link `wa.me` | Vincula con |
|---|---|---|
| LinkedIn | `Hola Victor, vengo de LinkedIn (ref 12)` | columna **ID** del Pipeline |
| Form | `Hola Victor, completé el formulario (código Ab12Cd34)…` | columna **Código** del Pipeline |

La persona inicia la conversación: hay consentimiento y no hace falta
plantilla aprobada de Meta. Si viene del form, Lía no repite preguntas y
pasa directo a agendar.

## Herramientas (`agent/tools.py`)

`guardar_datos_contacto` · `registrar_hallazgo` · `ver_horarios_disponibles`
· `agendar_llamada` (Cal.com API v2) · `marcar_no_contactar` ·
`escalar_a_victor`. Todo queda en una bitácora que n8n lee con
`GET /api/eventos?desde_id=N` (header `X-API-Key`) para actualizar la planilla.

## Probar sin WhatsApp

```bash
cd agente-whatsapp
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env                              # y completá ANTHROPIC_API_KEY
python tests/test_local.py
```

Probá con `Hola Victor, vengo de LinkedIn (ref 12)` o con
`Hola Victor, completé el formulario (código Ab12Cd34)`, y escribí `eventos`
para ver lo que leería n8n.

## Conectar a WhatsApp real

1. Completá `.env`: credenciales de Meta (incluido `META_APP_SECRET`),
   `CAL_*` y `SYNC_API_KEY`.
2. `uvicorn agent.main:app --port 8000`
3. Exponé el puerto con HTTPS. Para el piloto alcanza con
   `cloudflared tunnel --url http://localhost:8000` (la URL cambia en cada
   reinicio).
4. En Meta → WhatsApp → Configuración, poné `https://TU-URL/webhook` y el
   `META_VERIFY_TOKEN`, y suscribite al campo `messages`.
5. En n8n, el workflow *02 Sync agente WhatsApp* apunta a `https://TU-URL/api/eventos`.

## Seguridad

Firma HMAC del webhook, idempotencia de reintentos, rate limit por teléfono
y por IP, logs sin números completos ni contenido de mensajes en producción,
y headers de seguridad.

## Costos

Meta: gratis en conversaciones que inicia el cliente. Claude Haiku: centavos
por conversación (menos con el cache). Cal.com: plan gratis.
