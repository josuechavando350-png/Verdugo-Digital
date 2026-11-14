# Verdugo Digital v0.15 — 13 conectores nuevos de solo lectura (solo servicios gratuitos)

Cada ruta, encabezado de autenticación y forma de respuesta se tomó del **código fuente o
archivo OpenAPI en el commit fijado** de `sources/parts`, no de memoria. Todos son `GET`, con
parámetros fijos en código, una sola página y una proyección que guarda solo recuentos.
Ninguno envía mensajes, cobra, crea sandboxes, ejecuta prompts ni escribe nada.

Las pruebas usan respuestas sintéticas y un servidor HTTP local (loopback). **Ningún proveedor
real fue probado**: antes de usar uno, corre `pilot` con un sandbox autorizado.

| Pieza | Acción | Llamada | Autenticación | Evidencia (commit fijado) | Qué se guarda | Costo / condición |
|---|---|---|---|---|---|---|
| `vllm` | `models.list` | `GET /v1/models` | Authorization: Bearer (--api-key) | [vllm-project/vllm@37ea94f715](https://github.com/vllm-project/vllm/tree/37ea94f715acc34f84bc3728ec3e365e40eb53ac): vllm/entrypoints/openai/models/api_router.py; vllm/entrypoints/serve/middleware/authenticate.py | Recuento de modelos servidos. | Software libre; el costo es el servidor con GPU. |
| `ollama` | `models.list` | `GET /api/tags` | Authorization: Bearer | [ollama/ollama@a5864fcb33](https://github.com/ollama/ollama/tree/a5864fcb33969705de3c0ebfedf4b2a16c970bcc): server/routes.go; api/types.go (ListResponse.models) | Recuento de modelos locales. | Ollama local no tiene autenticación propia: ponlo detrás de un proxy (p. ej. Caddy) que exija el token, o usa la API de ollama.com. |
| `label-studio` | `projects.list` | `GET /api/projects/?page=1&page_size=30` | Authorization: Token (token heredado) | [HumanSignal/label-studio@8831d8b9eb](https://github.com/HumanSignal/label-studio/tree/8831d8b9eb507ebb3ce29ab0021e494bc1893a16): label_studio/projects/urls.py; label_studio/projects/api.py; label_studio/jwt_auth/auth.py | Recuento de proyectos de etiquetado (primera página). | La organización debe tener habilitado el token heredado. |
| `grist` | `orgs.list` | `GET /api/orgs` | Authorization: Bearer | [gristlabs/grist-core@a3c557ac1b](https://github.com/gristlabs/grist-core/tree/a3c557ac1bc4bd55b9b9d4333842bec255586ff4): app/gen-server/ApiServer.ts; app/server/lib/Authorizer.ts | Recuento de organizaciones visibles. | Grist autoalojado o en la nube. |
| `datasette` | `databases.list` | `GET /-/databases.json` | Authorization: Bearer (token de API) | [simonw/datasette@32590d8f32](https://github.com/simonw/datasette/tree/32590d8f32244d922ee1f444e432fb48b11ce05b): datasette/app.py; datasette/default_permissions/tokens.py | Recuento de bases conectadas. | Commit fijado en la rama principal (serie 1.0). |
| `svix` | `applications.list` | `GET /api/v1/app?limit=50` | Authorization: Bearer | [svix/svix-webhooks@bb44d9a55f](https://github.com/svix/svix-webhooks/tree/bb44d9a55f2bd409cb502d8bdab6b2e28710846c): server/openapi.json (ListResponse_ApplicationOut_) | Recuento de aplicaciones de webhooks y si hay más páginas. | Servidor Svix autoalojado o nube. |
| `cube` | `cubes.list` | `GET /cubejs-api/v1/meta` | Authorization: Bearer <JWT> | [cube-js/cube@e19cbba0fc](https://github.com/cube-js/cube/tree/e19cbba0fcc1441c20eeef484408f340550c0225): packages/cubejs-api-gateway/src/gateway.ts | Recuento de cubos de la capa semántica. | Ruta base por defecto /cubejs-api. |
| `langflow` | `flows.list` | `GET /api/v1/flows/?get_all=false&header_flows=true&remove_example_flows=true&page=1&size=50` | x-api-key | [langflow-ai/langflow@260cbf347c](https://github.com/langflow-ai/langflow/tree/260cbf347cc5563cc48c79094c175ca31532ea2b): src/backend/base/langflow/api/v1/flows.py; services/auth/utils.py | Recuento de flujos (sin ejemplos). |  |
| `crowdsec` | `decisions.summary` | `GET /v1/decisions` | X-Api-Key (clave de bouncer) | [crowdsecurity/crowdsec@e20782bb3c](https://github.com/crowdsecurity/crowdsec/tree/e20782bb3c532f0b9b9a469c0bdaa003588ec8e5): pkg/apiserver/controllers/controller.go; controllers/v1/decisions.go; middlewares/v1/api_key.go | Recuento de decisiones por tipo (ban/captcha/throttle). No guarda IPs. | Ojo: CrowdSec actualiza la hora de última consulta del bouncer. |
| `clickhouse` | `databases.count` | `GET /?query=SELECT count() AS databases FROM system.databases FORMAT JSON` | X-ClickHouse-User + X-ClickHouse-Key | [ClickHouse/ClickHouse@e847346055](https://github.com/ClickHouse/ClickHouse/tree/e8473460558a9f85074a90e89519a7fddb6bcacf): src/Server/HTTP/authenticateUserByHTTP.cpp; src/Server/HTTPHandler.cpp (GET de solo lectura) | Número de bases de datos. La consulta es fija en el código. | Usar un usuario de solo lectura. |
| `dittofeed` | `segments.list` | `GET /api/admin/segments?workspaceId=<uuid>` | Authorization: Bearer (clave admin) | [dittofeed/dittofeed@91277939a9](https://github.com/dittofeed/dittofeed/tree/91277939a9afcee797ab2562025f6b02d823b00c): packages/api/src/buildApp/router.ts; adminAuth.ts; controllers/segmentsController.ts | Recuento de segmentos del workspace. | Requiere workspace_id revisado. |
| `android-sms-gateway` | `devices.list` | `GET /devices` | Basic (usuario y contraseña del servidor local) | [capcom6/android-sms-gateway@e2c6bb56a4](https://github.com/capcom6/android-sms-gateway/tree/e2c6bb56a4d60bd39195e9415589a3ec14bd00a7): app/src/main/java/me/capcom/smsgateway/modules/localserver/WebService.kt; routes/DeviceRoutes.kt | Número de dispositivos y de SIMs. Sin números de teléfono. | Gratis: el teléfono Android es la pasarela y usa tu plan de mensajes. Requiere HTTPS (p. ej. detrás de Caddy) porque el motor no manda credenciales por HTTP en red local. |
| `sendportal` | `campaigns.summary` | `GET /api/v1/campaigns` | Authorization: Bearer (token de API del workspace) | [mettle/sendportal-core](https://github.com/mettle/sendportal-core) (MIT): src/Routes/ApiRoutes.php; Controllers/Api/CampaignsController.php; Models/CampaignStatus.php; app [mettle/sendportal@f759dc848e](https://github.com/mettle/sendportal/tree/f759dc848ec986d82f294082ff14009e8c4e90a6): routes/api.php, AppServiceProvider (bearerToken) | Campañas por estado (draft/queued/sending/sent/cancelled). Sin contenido ni destinatarios. | Gratis y autoalojado; el envío de correo usa tu propio servidor (p. ej. Postal). |

## Configuración privada mínima

Cada conector arranca apagado en `verdugo init`. Para activarlo: `enabled`, `license_reviewed`,
`version` exacta, `base_url` y `token_env` con el secreto en una variable de entorno `VERDUGO_*`.
Campos extra: Android SMS Gateway `username`, ClickHouse `username` (de solo lectura) y
Dittofeed `workspace_id`.

## Servicios de pago retirados

Por decisión de Josue (13-nov-2026) no queda nada de pago: Stripe, Twilio, Mercado Pago, E2B y
Composio salieron del catálogo y sus conectores se borraron. En su lugar entraron piezas gratuitas y
autoalojadas: Android SMS Gateway, Krayin CRM, SendPortal, microsandbox y Huginn. Krayin, microsandbox
y Huginn quedan **pendientes**: el paquete REST de Krayin no tiene licencia, microsandbox solo expone
llamadas POST y Huginn no tiene API JSON de lectura.

## Mapa de conexión

`python -m verdugo connections` muestra, para las 322 piezas, su tipo (servicio, biblioteca,
componente, cli, mcp, protocolo, datos o excluido) y su estado calculado desde el código:
**conectado** solo si existe un adaptador implementado y la licencia lo permite. Los componentes
(Next.js, Tailwind, shadcn…) se conectan al construir la plataforma, no a través del motor.

