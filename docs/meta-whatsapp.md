# Cómo obtener las credenciales de Meta (WhatsApp Cloud API) para el agente Lía

El agente necesita 4 valores en `agente-whatsapp/.env`:

| Variable | Qué es |
|---|---|
| `META_ACCESS_TOKEN` | Token para enviar mensajes. Usá uno **permanente** (paso 5), no el temporal de 24 h |
| `META_PHONE_NUMBER_ID` | ID del número de WhatsApp del agente (no es el número en sí) |
| `META_APP_SECRET` | Secreto de la app, para validar que los webhooks vienen de Meta |
| `META_VERIFY_TOKEN` | Una palabra secreta que inventás vos, para verificar el webhook |

> Ya tenés una app de Meta (la de la demo inmobiliaria, ver nota "Meta - WhatsApp"
> en Obsidian). Lo más rápido es **reutilizar esa app** y sumarle un número nuevo.

## 0. Antes de empezar: el número

- El número del agente **no puede estar usándose en la app de WhatsApp** (ni
  normal ni Business). Tu 1153371839 es tu WhatsApp personal: si lo registrás
  en la Cloud API, deja de funcionar en tu celular.
- Recomendado: una línea nueva solo para el agente (chip prepago o eSIM).
  Tiene que poder recibir SMS o una llamada para verificarse.
- Mientras tanto, el form manda a la gente a tu número personal y respondés
  vos. Cuando tengas el número del agente, cambiás `waNumero` en
  `form/public/config.js` y en el nodo Config del workflow 01.

## 1. App de Meta

1. Entrá a https://developers.facebook.com/apps con tu cuenta.
2. Abrí la app existente, o creá una nueva: *Create App* → caso de uso
   **"Connect with customers through WhatsApp"** (o tipo *Business*) →
   asociala a tu portfolio de negocio (Business Manager).
3. Si es nueva, en el panel agregá el producto **WhatsApp**.

## 2. Probar con el número de prueba (opcional pero recomendado)

1. WhatsApp → **API Setup**. Meta te da un número de prueba gratis.
2. En "To", agregá tu número personal como destinatario de prueba (hasta 5).
3. Copiá el **Phone number ID** del número de prueba y el **token temporal**.
4. Con eso ya podés probar el agente en local (ver paso 6) antes de tener la
   línea nueva.

## 3. Agregar el número real del agente

1. WhatsApp → **API Setup** → *Add phone number*.
2. Completá el perfil: nombre visible (por ejemplo "Victor Toro · Investigación
   contable"), categoría *Servicios profesionales*, descripción corta.
   Meta revisa el nombre visible: usá uno real y coherente con tu negocio.
3. Verificá el número por SMS o llamada.
4. Copiá su **Phone number ID** → `META_PHONE_NUMBER_ID`.

## 4. App secret

App → *App settings* → **Basic** → *App secret* → *Show* → `META_APP_SECRET`.

## 5. Token permanente (System User)

El token de *API Setup* vence a las 24 h. Para producción:

1. https://business.facebook.com → **Configuración del negocio** →
   *Usuarios* → **Usuarios del sistema** → *Agregar* → rol **Administrador**.
2. *Asignar activos*: la **app** (control total) y la **cuenta de WhatsApp
   Business** (control total).
3. *Generar token* → elegí la app → caducidad **Nunca** → permisos
   `whatsapp_business_messaging` y `whatsapp_business_management`.
4. Copialo una sola vez a `META_ACCESS_TOKEN` (y a tu nota de Obsidian). No
   lo pegues en chats.

## 6. Webhook (para que el agente reciba mensajes)

1. Levantá el agente y exponelo con HTTPS:
   ```bash
   cd agente-whatsapp
   uvicorn agent.main:app --port 8000
   ```
   En otra terminal:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
2. Inventá un `META_VERIFY_TOKEN` (cualquier palabra larga) y ponelo en `.env`.
3. WhatsApp → **Configuration** → *Webhook* → *Edit*:
   - Callback URL: `https://TU-URL-DE-CLOUDFLARED/webhook`
   - Verify token: el mismo `META_VERIFY_TOKEN`
4. En *Webhook fields*, suscribite a **messages**.
5. Mandá "Hola" al número del agente desde tu celular: tiene que contestar Lía.

## 7. Pasar la app a modo Live

App → arriba, cambiá de *Development* a **Live**. Meta pide:
- **URL de política de privacidad:** usá la del form,
  `https://prospeccion-descubrimiento-form.vercel.app/privacidad`.
- Ícono y categoría de la app.

En modo *Development* solo le contesta a los números de prueba.

## Costos y límites

- Las conversaciones que **inicia la persona** (desde el form o el link
  `wa.me`) y las respuestas dentro de las 24 h siguientes **no se cobran**.
  Así funciona este sistema.
- Escribirle primero a alguien requiere una plantilla aprobada y sí tiene
  costo. Este sistema no lo hace.
- Sin verificar el negocio en Meta hay límites de volumen, pero alcanzan de
  sobra para la etapa de descubrimiento.

## Seguridad

- Las claves van **solo** en `agente-whatsapp/.env` (git lo ignora) y en tu
  nota privada de Obsidian.
- Si un token se filtra: Business Manager → Usuarios del sistema → revocar y
  generar otro.
