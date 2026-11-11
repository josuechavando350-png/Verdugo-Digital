# Fuentes de contratos API

Consultadas el 11 de noviembre de 2026. Sirven para implementar las recetas, no para afirmar compatibilidad con una instancia que no se ha inspeccionado. Elegir versión y comprobar edición/permisos antes de activar.

| Adaptador | Fuente oficial | Alcance implementado |
|---|---|---|
| Twenty | https://github.com/twentyhq/twenty/blob/main/packages/twenty-docs/developers/extend/api.mdx | GET/POST `/rest/people`; consultar esquema específico del workspace |
| Chatwoot | https://developers.chatwoot.com/api-reference/conversations/conversations-list | GET conversaciones; token Bearer según documentación consultada |
| Chatwoot | https://developers.chatwoot.com/api-reference/contacts/create-contact | POST contacto; account e inbox de configuración |
| Listmonk | https://listmonk.app/docs/apis/lists/ y https://listmonk.app/docs/apis/apis/ | GET listas; Basic auth con usuario API y token |
| Umami | https://docs.umami.is/docs/api/authentication | GET `/api/websites` en self-hosted; no intercambiar con ruta Cloud |
| Meilisearch | https://specs.meilisearch.dev/specifications/text/0085-api-keys.html | GET `/indexes` con clave autorizada |
| Qdrant | https://api.qdrant.tech/api-reference/collections/get-collections | GET colecciones, cabecera `api-key` |
| Metabase | https://www.metabase.com/docs/latest/people-and-groups/api-keys y https://www.metabase.com/docs/latest/api-documentation | API key; validar `/api/dashboard` en `/api/docs` de la versión instalada |
| Grafana | https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/api-legacy/folder_dashboard_search/ | GET `/api/search`; ruta LEGACY, validar disponibilidad o migrar antes de producción |
| Prometheus | https://prometheus.io/docs/prometheus/latest/querying/api/ | GET consulta instantánea; expresiones preautorizadas por administrador |
| Shlink | https://shlink.io/documentation/api-docs/ y https://shlink.io/documentation/api-docs/authentication/ | GET `/rest/v3/short-urls`; comprobar contrato de versión instalada |
| Activepieces | https://www.activepieces.com/docs/endpoints/flows/list | GET flujos con projectId; API disponible según edición/permisos |
| n8n | https://docs.n8n.io/api/authentication/ y https://docs.n8n.io/api/api-reference/ | GET workflows; `X-N8N-API-KEY`; revisar licencia para modalidad de uso |
| MCP stdio | https://modelcontextprotocol.io/specification/2025-11-25/basic/transports | Subconjunto tools, negociación legacy explícita |

El resto de los IDs conserva los nombres/URLs de la selección original del usuario. No se fijaron 100 releases ni se reauditaron aquí sus licencias. No se incorporó código de esos repositorios, modelos, imágenes Docker ni dependencias en forma transitiva.
