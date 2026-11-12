# Verdugo Digital v0.11 — Contratos HTTP de solo lectura

**Alcance:** se agregaron ocho clientes HTTP limitados a una operación GET cada uno. Usan el Engine existente y sus controles por tenant, aprobación de uso/licencia, configuración de versión, credenciales fuera de Git, validación de origen HTTPS, bloqueo SSRF, idempotencia y auditoría. No hay instalación, despliegue ni ejecución de código de los proyectos externos.

| Proyecto | Acción | Ruta fija | Autenticación |
|---|---|---|---|
| Novu | `workflows.list` | `GET /v2/workflows` | `Authorization: ApiKey <secret>` |
| Superset | `dashboards.list` | `GET /api/v1/dashboard/` | JWT Bearer |
| Supabase | `projects.list` | `GET /v1/projects` | PAT con `projects:read` Bearer |
| Coolify | `servers.list` | `GET /api/v1/servers` | Bearer con privilegio mínimo |
| Keycloak | `realms.list` | `GET /admin/realms` | Bearer con permiso de lectura administrativa |
| Unleash | `projects.list` | `GET /api/admin/projects` | Valor del token directamente en `Authorization` |
| Medusa v2 | `products.list` | `GET /admin/products` | Secret API key con Basic literal; JWT Bearer opcional |
| OpenFGA | `stores.list` | `GET /stores` | Token Bearer en entornos con auth activada |

## Evidencia documental

- Novu: https://www.novu.co/changelog/workflows-and-environments-apis/ y autenticación REST `Authorization: ApiKey` descrita en https://github.com/novuhq/novu/blob/next/docs/community/self-hosting-novu/deploy-with-docker.mdx
- Superset: https://superset.apache.org/developer-docs/api/dashboards/
- Supabase: https://supabase.com/docs/reference/api/v1-list-all-projects y https://supabase.com/docs/reference/api/introduction
- Coolify: https://coolify.io/docs/api/endpoints/servers/list-servers
- Keycloak: https://www.keycloak.org/docs-api/latest/rest-api/
- Unleash: https://docs.getunleash.io/api/get-projects y https://docs.getunleash.io/api/admin-api-overview
- Medusa: https://docs.medusajs.com/resources/commerce-modules/api-key/concepts y https://docs.medusajs.com/resources/commerce-modules/product/guides/manage-with-admin-api
- OpenFGA: https://buf.build/openfga/api/file/main%3Aopenfga/v1/openfga_service.proto y https://github.com/openfga/python-sdk/blob/main/docs/OpenFgaApi.md

Estos enlaces describen rutas/contratos públicos; **no equivalen a pruebas de compatibilidad con la edición, versión o instancia del operador**. Novu REST usa `ApiKey`; no confundir con autenticación Bearer del MCP alojado por Novu. Para Medusa, Basic con token sin base64 es compatible con v2; una autenticación JWT debe elegirse explícitamente mediante `auth_mode: "jwt_bearer"`. No se obtienen JWT automáticamente.

## Condiciones de operación

- Todo proveedor está deshabilitado al crear la configuración: `enabled=false`, `license_reviewed=false`, sin token, con `base_url=https://example.invalid`. Una clave de ejemplo en test **no representa aprobación real**.
- Se rechazan URLs proporcionadas por el usuario, destinos/headers arbitrarios, otras operaciones, `page=0`, strings y paginación no implementada.
- Medusa acepta página 1..1000 (`limit=50,offset=(page-1)*50`); los demás solo la primera respuesta sin afirmar exportación total, incluso cuando el proveedor soporta cursor.
- Se validan estructuras esperadas de colecciones (no contenido semántico), con máximo 1000 objetos por respuesta y 1 MiB de JSON por transporte. Un fallo de esquema produce `failed`, jamás cero resultados falsos.
- Las pruebas CI usan servidores sintéticos en loopback y no representan acceso real a cuentas, validación de permisos, producción, SLA o resultados comerciales.
- No se envían mensajes, no se despliegan aplicaciones ni se hacen compras. Los reintentos de lectura con la misma clave devuelven el resultado persistido sin otra petición; una lectura fresca exige una clave distinta.
- Para habilitar un proveedor en un host real: instancia autorizada, licencia/uso revisado, versión exacta, token de permisos mínimos, conexión HTTPS, verificación de contrato de respuesta y observabilidad. Guardar PII y secretos fuera de Git.

## Estado del sistema

**49 proyectos con alguna operación implementada** (30 adaptadores HTTP y 19 locales); 51 sin adaptador. Los 100 SHA upstream siguen registrados. La aceptación en CI de ocho rutas GET no demuestra que existan 30 servidores desplegados ni que estén certificados en producción.
