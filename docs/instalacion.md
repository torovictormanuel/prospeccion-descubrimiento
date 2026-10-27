# Instalación

Objetivo de esta etapa: **entender el problema del rubro**, no vender.
Meta: 15-20 respuestas del form y 8-10 charlas.

## Cómo fluye

```
Google Sheet (Pipeline_Ventas)
   │
   ├─ 01 Investigador (n8n, L-V 8:30)
   │     Gemini + Google Search investiga 12 leads → redacta mensajes con el link al form (con código)
   │     → te manda el mail "Prospección de hoy"
   │
   ├─ VOS en LinkedIn (~10 min/día): copiás, pegás, enviás y tocás ✅ en el mail
   │     └─ 04 Botones → actualiza Paso, Toques y fechas
   │
   ├─ El prospecto completa el FORM (4 min)
   │     └─ 05 Sync form (cada 15 min) → Pipeline, Hallazgos, Respuestas form + aviso
   │     Al terminar, si quiere la charla:
   │       ├─ "Elegir horario" → Cal.com ──► 03 Sync Cal.com → Etapa 4 + aviso con lo que respondió
   │       └─ "Coordinar por WhatsApp" → Agente Lía (no repite preguntas, agenda)
   │             └─ 02 Sync agente → Etapa, Hallazgos, avisos
   │
   └─ Charla de 20-30 min con el guion de la hoja "Guion llamada"
```

**Por qué LinkedIn no está 100 % automatizado:** el acuerdo de usuario de
LinkedIn prohíbe los bots que mandan solicitudes o mensajes. Los agentes hacen
el trabajo pesado; vos solo hacés clic en "enviar".

**Por qué WhatsApp sí:** la persona escribe primero (desde el form o el link
`wa.me`). Hay consentimiento explícito y Meta no exige plantillas aprobadas.

## Pasos (en este orden)

### 1. Google Sheet
1. Subí `Pipeline_Ventas.xlsx` (está en tu carpeta "Potenciales clientes", no
   en el repo) a Google Drive → *Abrir con Hojas de cálculo de Google* →
   *Archivo → Guardar como Hojas de cálculo de Google*.
2. Copiá el ID de la URL: `docs.google.com/spreadsheets/d/`**`ESTE_ID`**`/edit`.
3. *Archivo → Configuración → Configuración regional: Argentina* (fechas
   dd/mm/aaaa).

### 2. Supabase (gratis)
1. Creá un proyecto (región São Paulo, la más cercana).
2. *SQL Editor* → pegá y ejecutá `supabase/migrations/001_respuestas_descubrimiento.sql`.
3. *Project Settings → API*: anotá la **URL** y la **service role key**
   (secreta: solo va en Vercel y en n8n, nunca en el código).
4. *Database → Backups*: el plan gratis hace un backup diario. Para más
   seguridad, exportá la tabla a CSV una vez por semana.

### 3. Cal.com (gratis)
1. Creá un evento "Charla de descubrimiento" de 30 min.
2. *Settings → Developer → API Keys* → creá una key.
3. Anotá el link público y el ID del evento (número en la URL al editarlo).

### 4. Form en Vercel (gratis)
1. Completá `form/public/config.js`: link de Cal.com, número de WhatsApp del
   agente y tu email de contacto para privacidad.
2. Probalo en local: `cd form && npm test && npm run dev`.
3. Desplegalo: `cd form && npx vercel` (te pide iniciar sesión la primera vez).
4. En Vercel → *Settings → Environment Variables*: `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, `IP_HASH_SALT` (ver `form/.env.example`).
   Redeploy: `npx vercel --prod`.
5. Recomendado: en Vercel → *Firewall*, agregá una regla de rate limit para
   `/api/respuesta` (por ejemplo, 20 por minuto por IP).
6. Recomendado: activá *Analytics* (Web Analytics, gratis y sin cookies) para
   ver cuánta gente abre el form y cuántos lo terminan.

### 5. Agente de WhatsApp
Seguí [`agente-whatsapp/README.md`](../agente-whatsapp/README.md). Probalo
primero en la terminal con `python tests/test_local.py`.

### 6. Gemini (gratis)
Creá una API key en https://aistudio.google.com/apikey. Si el modelo de
`Config → geminiModelo` deja de existir o pierde la búsqueda gratis,
cambialo por el que figure como gratis en https://ai.google.dev/gemini-api/docs/pricing.

### 7. n8n
1. Generá un token para los botones del mail (no lo compartas):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. En n8n: *Workflows → Import from file* → importá los 5 JSON de `n8n/`.
3. En cada workflow, abrí el nodo **Config** y completá los valores. Usá el
   **mismo token** en el 01 y el 04, y en el 01 poné la URL del form en
   `formUrl`.
4. Creá las credenciales (n8n las guarda cifradas, nunca van en el JSON):
   | Credencial | Tipo | Dónde |
   |---|---|---|
   | Google Sheets | Google Sheets OAuth2 | todos los nodos de Sheets |
   | Gmail | Gmail OAuth2 | nodos "Mandar cola" / "Avisarme" |
   | Gemini | Header Auth: `x-goog-api-key` = tu key | 01 · Gemini investiga |
   | Agente | Header Auth: `X-API-Key` = `SYNC_API_KEY` del agente | 02 · Traer eventos |
   | Cal.com | Header Auth: `Authorization` = `Bearer cal_live_…` | 03 · Traer reservas |
   | Supabase | Supabase API: host + service role key | 05 · Traer respuestas |
5. Abrí cada nodo de Google Sheets una vez para que cargue las columnas.
6. Activá los 5 workflows.

### 8. Prueba de punta a punta (antes de escribirle a nadie)
1. Poné tu propio LinkedIn en una fila de prueba con Prioridad Alta.
2. Ejecutá el 01 a mano → te tiene que llegar el mail con tu fila y el
   Mensaje 1 con el link al form.
3. Tocá ✅ Enviado → la fila pasa a "2. Contactado".
4. Abrí el link del form desde el celular, completalo y elegí "Sí, quiero
   elegir un horario".
5. En 15 minutos: la fila pasa a "3. Conversación", aparecen filas en
   Hallazgos y Respuestas form, y te llega el aviso.
6. Reservá en Cal.com desde la pantalla final → en 30 minutos la fila pasa a
   "4. Reunión agendada".
7. Probá también "Coordinar por WhatsApp" desde otro celular: Lía no tiene que
   repetirte las preguntas.
8. Borrá la fila de prueba, la respuesta en Supabase y cancelá la reserva.

## Límites y buenas prácticas

- **LinkedIn:** como máximo 15-20 solicitudes por día y 100 por semana.
- **Datos personales (Ley 25.326):** solo datos profesionales públicos para
  el primer contacto. El form pide consentimiento explícito y la política de
  privacidad explica cómo pedir el borrado. Respetá siempre "no me escribas
  más".
- **n8n local:** la PC tiene que estar prendida en los horarios de los
  workflows. Los botones del mail funcionan solo en esa PC.
- **Costos:** Vercel, Supabase, n8n, Cal.com y Gemini, gratis. Meta: gratis en
  conversaciones que inicia el cliente. Claude Haiku: centavos por
  conversación.

## Qué hacer con lo que aprendas

Ver la sección "Cómo analizar los patrones" en [diseno-form.md](diseno-form.md).
