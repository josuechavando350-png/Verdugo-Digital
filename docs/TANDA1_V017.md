# Verdugo v0.17 — continuación parcial de la primera tanda

## Punto de partida, sin sustituir el trabajo de Claude

Base: `35516f830cba1e0dbb06b91f44357128440fc832`, rama
`feat/v0.14-catalogo-300`, PR #15. Su árbol exacto es
`9533a6aeb23bad5ec6d23fced6c7c033b256a8f0`. La base pasó 432 pruebas locales.
La continuación implementa **cuatro** de las 185 entradas pendientes. No afirma
que se hayan terminado las 300 permitidas ni las 46 restantes de la tanda 1.

| Estado calculado | Base v0.16 | v0.17 |
|---|---:|---:|
| Entradas registradas | 322 | 322 |
| Permitidas por política / excluidas | 300 / 22 | 300 / 22 |
| Adaptadores HTTP / acciones HTTP | 59 / 63 | 63 / 67 |
| Recetas de bibliotecas locales | 19 | 19 |
| Conectadas bajo política (HTTP + locales permitidas) | 59 | 63 |
| Piezas de construcción | 56 | 56 |
| Pendientes de conector | 185 | 181 |
| Servicios productivos certificados | 0 | 0 |

`conectado` es la definición del mapa: existe una operación implementada y la
política la permite. **No significa instalado, configurado, ni verificado contra
el proveedor real.** Las 322 revisiones legales continúan pendientes; ninguna
excepción de licencia se introdujo en configuración operativa.

## Cuatro contratos incorporados

| Proyecto | Acción | Ruta exacta | Lo que persiste |
|---|---|---|---|
| OpenRefine | `projects.count` | `GET /command/core/get-all-project-metadata` | Recuento de proyectos; no IDs ni metadatos |
| Steel Browser | `sessions.summary` | `GET /v1/sessions` | Recuento y estados `idle`, `live`, `released`, `failed` |
| Crawl4AI | `hooks.summary` | `GET /hooks/info` | Número de acciones declarativas y máximo de hooks; `crawl_executed=false` |
| Fides | `policies.count` | `GET /api/v1/dsr/policy?page=1&size=50` | Recuento de políticas en esa página y si quedan más |

El módulo `verdugo/tanda1_reads.py` se conecta al mismo `Engine`, transporte,
proyector de respuestas, CLI, MCP, auditoría e idempotencia. Se separó del módulo
histórico `service_reads.py` para conservar intactos sus 16 contratos anteriores;
no es otro motor, daemon, CRM o listener. No se añadió ninguna dependencia Python.

### Autenticación que realmente existe en las fuentes

OpenRefine, Steel autoalojado y `/hooks/info` de Crawl4AI **no exigen autenticación
nativa**. El motor requiere `auth_mode="reviewed_proxy_bearer"` y
`proxy_auth_reviewed=true` en la configuración privada del operador. La plantilla
incluye el modo, pero deja la revisión en **false**, además de `enabled=false`.

La revisión debe confirmar que el origen apunta al proxy que rechaza token ausente
o incorrecto y que el servicio sin protección no queda expuesto por otra ruta.
Activar una bandera no instala ni verifica un proxy. Esta revisión no creó ninguno.
El token no se manda en la URL, parámetros, cuerpos ni evidencias públicas.

Fides usa **OAuth Bearer nativo**, con permiso de lectura de políticas; Verdugo no
crea clientes OAuth, no obtiene tokens, ni solicita privilegios automáticamente.
El operador aporta un token autorizado en una variable `VERDUGO_*`, versión exacta,
revisión de licencia y origen HTTPS. HTTP se admite solamente para loopback de
prueba con permiso explícito. No hay acceso a red privada sin revisión explícita.

La política de autenticación, huella de la credencial, versión, destino,
política de red y huella del módulo forman parte del plan. Revocar la revisión del
proxy bloquea incluso un resultado previamente almacenado: no reutiliza el caché
para eludir el control. La huella no cifra los datos de SQLite ni es una garantía
criptográfica sobre el software del proveedor.

### Contratos y versiones consultadas

La evidencia por archivo y SHA de blob está en
[`sources/contracts-v017.json`](../sources/contracts-v017.json). Solo se documentan
los archivos efectivamente inspeccionados, no la totalidad de los repositorios.

- OpenRefine `d97abdabd4c172ddba3581a9259307c7f2b86b44`:
  [`GetAllProjectMetadataCommand.java`](https://github.com/OpenRefine/OpenRefine/blob/d97abdabd4c172ddba3581a9259307c7f2b86b44/main/src/com/google/refine/commands/workspace/GetAllProjectMetadataCommand.java)
  devuelve el mapa `projects`; `main/webapp/modules/core/MOD-INF/controller.js`
  registra `get-all-project-metadata`.
- Steel `552550af79742a75fef24c24b1134e43e99e3d5e`:
  [`steel-browser-plugin.ts`](https://github.com/steel-dev/steel-browser/blob/552550af79742a75fef24c24b1134e43e99e3d5e/api/src/steel-browser-plugin.ts)
  fija `/v1`; `sessions.routes.ts`, `sessions.controller.ts` y `sessions.schema.ts`
  definen la colección y los estados.
- Crawl4AI `cae74b203a33994f7e13b9052c3b0d5c93daa0e6`:
  [`deploy/docker/server.py`](https://github.com/unclecode/crawl4ai/blob/cae74b203a33994f7e13b9052c3b0d5c93daa0e6/deploy/docker/server.py)
  expone `/hooks/info` sin `token_dep`; `hook_registry.py` describe un diccionario
  de acciones con `hook_point`, `description` y `params_schema`. Verdugo no ejecuta
  acciones del registro ni acepta código suministrado.
- Fides `e87f3ff835af368defc1ec42dc29ec545a288585`:
  [`policy_endpoints.py`](https://github.com/ethyca/fides/blob/e87f3ff835af368defc1ec42dc29ec545a288585/src/fides/api/v1/endpoints/policy_endpoints.py)
  exige `POLICY_READ` y devuelve `Page[PolicyResponse]`;
  [`urn_registry.py`](https://github.com/ethyca/fides/blob/e87f3ff835af368defc1ec42dc29ec545a288585/src/fides/common/urn_registry.py)
  fija `/api/v1` + `/dsr/policy`; `schemas/oauth.py` define el esquema Bearer.

## Guardas y pruebas

24 pruebas nuevas, dentro de un total de **456**, cubren contratos, privacidad,
tipos inválidos, paginación fija, parámetros prohibidos, autenticación/proxy,
isolación entre tenants, CLI, MCP, reinicio de Engine y resultados idempotentes.
El flujo de cuatro lecturas se ejecuta por sockets HTTP reales en loopback con
**respuestas simuladas de los proveedores**. Ninguna de las cuatro aplicaciones
originales se instaló o se ejecutó como parte de esas pruebas.

Los datos son sintéticos. Las respuestas de más de 1 MiB, redirecciones, acuses
202/204 y estructuras inválidas se rechazan. No hay reintentos automáticos ni
seguimiento de enlaces de paginación. Se procesan como máximo 1000 objetos (50 en
Fides); el resultado es un resumen de una respuesta, no una exportación completa.

Una consulta de metadatos no limpia datos de OpenRefine, no crea sesiones de Steel,
no rastrea sitios con Crawl4AI y no ejecuta accesos/borrados de Fides. Tampoco prueba
captación de clientes, ventas, cumplimiento legal ni infraestructura permanente.

Ejemplo de planificación — falla si la configuración no está revisada:

```sh
python -m verdugo init --out verdugo.local.json
# Revisar la configuración privada, las versiones y la autenticación fuera de Git.
python -m verdugo --config verdugo.local.json \
  workflow @examples/tanda1-readiness.json
# Solo con endpoints autorizados y revisión completa, añadir --execute.
```

`init` ahora reporta correctamente 322 entradas, en lugar del valor histórico 100.
Las mismas operaciones están disponibles por `verdugo_execute` y
`verdugo_workflow` de MCP; no se añadieron herramientas con ejecución arbitraria.

## Pendientes y exclusiones conservadas

El plan actualizado conserva orden y números originales. La tanda 1 tiene 46
pendientes; las siguientes mantienen 50, 50 y 35. Entre las fuentes inspeccionadas
sin nuevo conector: **Gotenberg** omite autenticación en `/health` aun cuando se
activa Basic para sus otras rutas, y `/version` devuelve texto. **Apache Answer**
registra `/question/page` entre rutas no autenticadas; falta escoger y validar
una superficie autenticada o un proxy revisado y completar sus pruebas. No se
contaron como conectados.

Se mantienen los bloqueos documentados por Claude: paquete REST de Krayin sin
licencia aprobada, token en URL de Webmention, ausencia del servidor fijado de
Letta, protocolo RESP de Valkey y operaciones de escritura de Postal. No se
habilitaron servicios de pago, excepciones de licencia, campañas, infraestructura
remota ni cambios en Vercel. `main` y la rama de Claude permanecen intactos.
