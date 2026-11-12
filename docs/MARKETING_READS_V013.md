# Verdugo Digital v0.13 — Seis lecturas de marketing

## Alcance implementado

Las seis operaciones nuevas usan Engine, tenant, SQLite, CLI, MCP y workflows ya existentes. No se publican contenidos, compran anuncios, firman documentos ni crean usuarios. Todas empiezan deshabilitadas y necesitan una instancia autorizada, versión explícita, licencia/uso revisado y credencial de permisos mínimos.

| Proyecto | Operación | Petición delimitada | Resultado retenido |
|---|---|---|---|
| Postiz | channels.list | GET /public/v1/integrations (cloud) o /api/public/v1/integrations (self-hosted) | Cantidad de canales habilitados/deshabilitados observados |
| Payload | documents.list | GET /api/{colección fijada por operador}, limit=20, depth=0 | Cantidad, estados conocidos y existencia de próxima página |
| Ghost | posts.list | GET /ghost/api/admin/posts/, limit=20, fields=id,status | Cantidad, estados y existencia de próxima página |
| Plausible | traffic.summary | POST /api/v2/query con sitio fijado y métricas visitors/visits/pageviews | Tres métricas agregadas y fechas solicitadas |
| Matomo | visits.summary | POST /index.php, VisitsSummary.get con idSite fijado | nb_visits y nb_actions del período solicitado |
| Saleor | products.list | POST /graphql/ con query fija, first=20 y canal fijado | Cantidad de productos observados y existencia de próxima página |

Se consultan páginas o agregados delimitados. No se afirma exportación completa, ingresos, atribución causal ni salud global del proveedor. Payload y Ghost aceptan páginas 1..1000; Postiz y Saleor no siguen cursores. Los cuerpos originales, nombres, perfiles, HTML y datos de clientes no se guardan en los resultados. Los planes sí conservan su ámbito administrativo (origen, colección, canal, sitio y fechas), por lo que SQLite sigue requiriendo protección.

## Autenticación y fronteras

- Postiz: Authorization contiene el token literal. La configuración elige cloud o self_hosted; no acepta rutas aportadas por parámetros.
- Payload: Authorization usa el slug de la colección de autenticación, API-Key y token. La colección de contenido se fija en configuración y no puede ser la de autenticación ni una colección interna payload-*.
- Ghost: Admin API con JWT HS256, aud=/admin/, duración de 300 segundos, ID hexadecimal de 24 caracteres y secreto de 64. Accept-Version queda fijado por el operador. El fingerprint usa la clave fuente y la implementación, no el JWT temporal: renovar JWT no invalida una lectura ya registrada, rotar la clave sí invalida el plan. No se crean sesiones ni se solicitan correos o contraseñas.
- Plausible y Saleor: token Bearer. No se obtiene ni compra acceso. El acceso a Stats API depende de edición/plan y permisos del operador; validar antes de activar.
- Matomo: token_auth viaja únicamente en el cuerpo form-urlencoded privado. No se añade a la URL ni al plan persistido. No se envía por cabecera Authorization.
- Las tres peticiones POST son **lecturas concretas propiedad del código**, no una autorización genérica para ejecutar POST ni GraphQL arbitrario. Las escrituras previas Twenty/Chatwoot mantienen su aprobación separada.
- El transporte mantiene HTTPS, bloqueo de destinos no autorizados, máximo 1 MiB, rechazo de redirecciones y ausencia de reintentos automáticos. Estas seis lecturas exigen respuesta HTTP 200; 202/204 no significan lectura completada.
- Todas las respuestas se reducen a resultados permitidos. Un error GraphQL, cambio de esquema, número no finito, métrica ausente o discrepancia de sitio/fechas de Plausible produce fallo, no cero ficticio.

## Configuración y ejecución

La plantilla deja todos los proveedores apagados. Revisar origen y permisos antes de habilitar. Las bibliotecas locales conservan sus entornos opcionales; estas seis recetas no añaden dependencias Python.

Plausible y Matomo exigen start_date/end_date juntas en la petición, o report_start_date/report_end_date explícitas en configuración. El intervalo debe ser de hasta 93 días inclusivos. No se infiere la zona horaria del sitio ni una ventana de facturación. El sitio es parte de la configuración; un asistente no puede sustituirlo desde params.

El ejemplo `examples/marketing-reads.synthetic.json` es una definición de seis pasos, no una conexión ni datos reales. Con configuración privada revisada:

```sh
python -m verdugo --config verdugo.local.json workflow @examples/marketing-reads.synthetic.json
# Solo con instancias y credenciales autorizadas, después de revisar el plan:
python -m verdugo --config verdugo.local.json workflow @examples/marketing-reads.synthetic.json --execute
```

El mismo ID/claves reutiliza los resultados persistidos, incluso tras reiniciar Engine. Para una observación nueva se usa un ID nuevo. La ausencia de reenvío en pruebas no es una garantía distribuida de exactly-once. Los roles son locales, no IAM productivo multiempresa. La revisión de uso/licencia y costes no está realizada por marcar banderas en fixtures.

## Evidencia reproducible

Base exacta: commit `48555937b44f4da1ec1276c99446b83acf5dd4d4`, árbol `aeca7c0c8a354e1a6c11da8953e984421624f77e`. El ZIP fuente de Actions se verificó con SHA-256 `3a027797f93d8781abcd2cdc7328dfdf2b5ceb4c31f77045209a2b5faddcce61`. La base pasó sus 383 pruebas antes del cambio.

Se agregan 21 pruebas: autenticación, firma y renovación JWT, rotación de claves, formas/formularios HTTP, aislamiento por tenant, parámetros prohibidos, privacidad SQLite, errores 401/403/429/302/202/204, fechas, métricas, CLI/MCP, workflow de seis pasos y replay tras reabrir Engine. Son pruebas **de contrato con HTTP local sintético**, no acceso a instalaciones reales de los seis proveedores.

```sh
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p test_marketing_reads_v013.py -v
python -m verdugo --state :memory: status
```

Inventario: **62 proyectos con alguna operación delimitada (43 HTTP + 19 locales); 38 sin adaptador; 47 acciones HTTP.** Las 19 bibliotecas y Qdrant/Meilisearch conservan su aceptación separada en CI; no se extrapola a estos seis proveedores. Proveedores certificados en producción: **0**. Comprobar los tres workflows de Actions para el commit específico antes de fusionar.

## Fuentes oficiales revisadas

- Postiz: https://docs.postiz.com/public-api/introduction y https://docs.postiz.com/public-api/integrations/list
- Payload: https://payloadcms.com/docs/authentication/api-keys y https://payloadcms.com/docs/queries/pagination
- Ghost: https://docs.ghost.org/admin-api (autenticación, rutas, JWT, fields y paginación)
- Plausible: https://plausible.io/docs/stats-api (POST de solo lectura, esquema, métricas, fechas y autenticación)
- Matomo: https://developer.matomo.org/guides/reporting-api y https://developer.matomo.org/api-reference/api
- Saleor: https://docs.saleor.io/api-usage/authentication y https://docs.saleor.io/api-reference/products/queries/products

La documentación pública no certifica la edición, versión ni permisos de una instancia no inspeccionada. El operador debe verificar ese contrato y el coste antes de usar datos reales.
