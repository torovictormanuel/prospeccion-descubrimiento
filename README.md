# Prospección por descubrimiento — estudios contables

Sistema para **entender los problemas de los estudios contables antes de
venderles nada**. Contacta leads de forma amable, les pide un form de 4
minutos y, si quieren, agenda una charla de 20-30 minutos con diagnóstico
gratis. Todo lo que responden queda en una planilla para buscar patrones.

```
LinkedIn (semi-automático) ──► Form (Vercel → embudo unificado) ──► Cal.com / WhatsApp (agente Lía)
        ▲                               │                              │
        └──── n8n: investiga, redacta, sincroniza y te avisa ◄─────────┘
                                │
                     Google Sheet: Pipeline · Hallazgos · Respuestas form
```

## En producción

| Qué | Dónde |
|---|---|
| Form | https://descubrimiento.vercel.app |
| Agenda (Cal.com, 30 min) | https://cal.com/victor-toro-sa1hch/descubrimiento — event type ID `7696927` |
| Base de datos | Embudo unificado de la web: Supabase `victortoro-web` (São Paulo), tablas `prospectos` e `interacciones`, con canal de llegada. El form guarda a través de `https://victortoro-web.vercel.app/api/descubrimiento` |
| Planilla | Google Sheet *Pipeline_Ventas* (`1PuwDTHeZ7BntraREG7Hb5QAeK7ZB_c9w3PnjwZAJ2qA`), la llena el workflow 05 |
| Deploy | Vercel `prospeccion-descubrimiento-form`, raíz `form/`, se publica solo con cada push a `main` |

## Estructura

| Carpeta | Qué es |
|---|---|
| [`form/`](form/) | Form de descubrimiento: HTML/JS sin frameworks + función `/api/respuesta` en Vercel |
| [`supabase/`](supabase/) | Tabla original de respuestas, **ya no se usa** (el proyecto quedó pausado). El esquema vigente está en el repo `victortoro-web`, `backend/` |
| [`agente-whatsapp/`](agente-whatsapp/) | Agente Lía (FastAPI + Claude): conversa, registra hallazgos y agenda en Cal.com |
| [`n8n/`](n8n/) | 7 workflows para importar + tests de su lógica |
| [`scripts/`](scripts/) | Generadores de los workflows y de la planilla |
| [`docs/`](docs/) | Investigación del rubro, diseño del form e instalación |

## Empezar

1. Leé [la investigación](docs/investigacion-flujo-estudio-contable.md) y
   [el diseño del form](docs/diseno-form.md).
2. Seguí [la guía de instalación](docs/instalacion.md).

## Probar en local

```bash
cd form && npm test && npm run dev
```

Abrí `http://localhost:3000/?c=Ab12Cd34`. Sin `EMBUDO_URL` y `EMBUDO_SECRET`, las respuestas se
guardan en `respuestas-dev.jsonl`, que git ignora.

## Modificar

- **Preguntas:** editá `form/public/preguntas.js` (y subí `VERSION`). Después
  corré `python scripts/build_n8n.py` para que el workflow 05 tome las
  etiquetas nuevas.
- **Planilla:** `python scripts/build_pipeline.py "<carpeta con los CSV>"`
  la regenera desde cero. **Pisa la planilla existente**: no la corras si ya
  cargaste datos.

## Datos personales

Los CSV de leads, la planilla y las respuestas **no van al repo** (están en
`.gitignore`). Antes de subirlo a GitHub, revisá que no haya secretos ni datos
de leads en el historial.
