# Fuentes técnicas de v0.4

Consultadas el 2026-11-11. Son referencias de contratos, no evidencia de compatibilidad con una instancia desplegada ni revisión jurídica de licencias. Cada servicio permanece deshabilitado por defecto y exige versión explícita y revisión de uso.

| Integración | Contrato implementado | Fuente oficial |
|---|---|---|
| Twenty | GET `/rest/people/{remote_id}`, Bearer; esquema del workspace | https://docs.twenty.com/developers/extend/api |
| Chatwoot | GET `/api/v1/accounts/{account_id}/contacts/{id}`, contacto en `payload` | https://developers.chatwoot.com/api-reference/contacts/show-contact |
| Mautic | GET `/api/contacts`, OAuth Bearer; `limit`, `start`, orden por ID | https://devdocs.mautic.org/en/5.x/rest_api/contacts.html |
| Mautic | Prefijo `/api`; API habilitada por el administrador | https://devdocs.mautic.org/en/5.x/rest_api/getting_started.html |
| Easy!Appointments | GET `/index.php/api/v1/services`, Bearer; `page`, `length`, `fields` | https://easyappointments.org/documentation/rest-api/ |
| Formbricks | GET `/api/v1/management/surveys`, `x-api-key`; colección `data` | https://formbricks.com/docs/api-reference/management-api--survey/get-all-surveys |
| Dub | GET `/links`, Bearer, `pageSize: 50`; primera página sin seguir cursores | https://dub.co/docs/api-reference/links/list.md |

Twenty declara que su API se genera por workspace: `data.person` es una sugerencia de configuración, no un esquema universal certificado. Comprobarlo en Settings → Developers → API de la instancia y habilitar `readback_reviewed` solo después.

Chatwoot documenta Bearer desde v4.19.0. El modo legado `api_access_token` ya existente sigue disponible; seleccionar según versión y mantener la misma credencial/ámbito para la comprobación.

La documentación Mautic de contactos muestra una advertencia de actualización pendiente. El adaptador implementa solamente el contrato de listado documentado; no declara compatibilidad con todas las versiones. La aceptación real debe confirmar ruta, autenticación, paginación y forma de respuesta. No se incluye renovación automática de OAuth.

Easy!Appointments admite Bearer en su documentación actual. El adaptador usa únicamente ese modo y la ruta raíz documentada, no credenciales Basic administrativas ni prefijos arbitrarios. Formbricks no documenta parámetros de paginación en la página consultada: no se inventaron. La respuesta queda limitada en bytes por el transporte.

Dub marca `page` como obsoleto. Esta entrega solicita `pageSize` y rechaza páginas posteriores; no simula una exportación completa ni usa automáticamente URLs o cursores devueltos.

No se añadieron conectores de Novu, GrowthBook o Documenso en esta entrega: las consultas de documentación no se convirtieron en integraciones especulativas. Permanecen en el catálogo pendiente.
