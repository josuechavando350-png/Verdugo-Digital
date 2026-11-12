# Verdugo Digital v0.12 — Metadatos de siete proveedores

Esta versión implementa consultas GET con destino y esquema delimitados para siete
proyectos adicionales, reutilizando Engine, tenant, configuración local, historial SQLite,
idempotencia y MCP. Los endpoints son versiones concretas de API: no sustituyen la
instalación ni la certificación productiva de los proyectos.

| Proyecto | Operación | Método / ruta fija | Autorización | Respuesta |
| --- | --- | --- | --- | --- |
| Airbyte Cloud | workspaces.list | GET /v1/workspaces?limit=20&offset=N | Bearer | data[] |
| Infisical | projects.list | GET /api/v1/projects | Bearer | projects[] |
| GrowthBook | settings.read | GET /api/v1/settings | Bearer | settings{} |
| OpenMeter OSS v1 | meters.list | GET /api/v1/meters | Bearer | [] |
| Nango | connections.list | GET /connections | Bearer | connections[] |
| Trigger.dev | runs.list | GET /api/v1/runs?limit=20 | Bearer | data[] |
| Documenso v2 | envelopes.list | GET /api/v2/envelope?page=N&perPage=20 | Token literal api_* | data[] |

## Fuentes

- Airbyte Cloud: https://reference.airbyte.com/reference/listworkspaces
- Infisical: https://infisical.com/docs/api-reference/endpoints/projects/list-projects
- GrowthBook 5.2: https://www.growthbook.io/product-updates/expanded-rest-api
- OpenMeter OSS v1: https://github.com/openmeterio/openmeter/blob/main/api/spec/packages/legacy/src/meters.tsp
- Nango: https://github.com/NangoHQ/nango/blob/main/docs/reference/backend/http-api/connections/list.mdx
- Trigger.dev: https://github.com/triggerdotdev/trigger.dev/blob/main/docs/management/runs/list.mdx
- Documenso: https://docs.documenso.com/docs/developers/api/documents
- Documenso auth: https://docs.documenso.com/docs/developers/api

## Privacidad y significado

La capa read_contracts valida cada forma de respuesta y **descarta el
contenido original** antes de guardarlo en Engine. Conserva solo el número
de registros observados, estados de ejecución/documento permitidos y la
indicación de que la lectura no equivale a una exportación completa. No conserva
etiquetas de usuarios Nango, payloads de Trigger, detalles de organizaciones,
datos de firmantes de Documenso, secretos de Infisical ni configuraciones
completas de GrowthBook. Ante un esquema incompatible, falla cerrado.

- Un resultado succeeded significa únicamente que el servidor respondió con
  el esquema esperado. No acredita permisos completos, salud funcional global,
  rentabilidad, causalidad ni aislamiento multiempresa.
- Airbyte está restringido a Cloud v1 (api_surface=cloud_v1). Las instalaciones
  self-managed tienen otra ruta base y no se sustituyen en silencio.
- OpenMeter está restringido al OSS legacy v1 (api_surface=oss_v1). La API v3
  de Kong Konnect no está implementada.
- Nango requiere permiso de listado; nunca se solicita leer credenciales.
- Trigger.dev no dispara ni cancela ejecuciones.
- Documenso usa la API v2 de envelopes con Authorization: api_* sin Bearer,
  sin descargar contratos ni enviar firmas.
- Airbyte y Documenso usan páginas limitadas; las otras fuentes solo consultan
  la primera respuesta. No se siguen enlaces ni cursores externos.
- Todo está deshabilitado por defecto y exige licencia revisada, versión,
  token privado y origen autorizado. No se publican credenciales.

## Evidencia y límites

Las pruebas ejecutan HTTP local sintético, incluyen datos sensibles ficticios
y comprueban que estos no persisten en Engine. CI cubre el motor existente y
la nueva frontera de privacidad. Ningún proveedor real se conecta aquí.

**Tras pruebas aprobadas:** 100 fuentes fijadas, 37 adaptadores HTTP,
19 recetas locales, 56 proyectos con alguna operación y 44 sin adaptador.
**Producción certificada: cero.** Faltan licencias, implantación autorizada,
permisos y aceptación real por proveedor.
