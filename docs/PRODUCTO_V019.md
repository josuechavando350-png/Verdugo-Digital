# Verdugo Digital v0.19 — operación conjunta

Continúa el PR #17 desde `088c759033fd52e2ece9f6cb0d23590bd378a160`.
No se reemplazan Engine, transporte, roles, catálogo ni SQLite. No hay segundo
orquestador, servidor público o base de datos externa.

## Entrada del producto

`product-status` / `verdugo_product_status` muestran las 322 entradas con su estado
calculado, operaciones locales/HTTP, configuración habilitada y registro comercial
del tenant. Son lecturas locales; no prueban credenciales, instalaciones ni salud.

`product-run` / `verdugo_product_run` reciben `id`, `services`, `dataset` y `currency`.
El selector admite las 33 consultas implementadas que proyectan datos a recuentos
o estados, son permitidas por política y no dependen del contrato Airbyte Cloud.
Las operaciones con otros contratos siguen disponibles en `workflow`; este
informe no las ejecuta automáticamente ni crea excepciones de licencia.

1. Valida todos los contratos seleccionados sin llamar a ningún proveedor.
2. Si falta configuración, devuelve `blocked` con los servicios afectados, sin
   omitirlos silenciosamente. `doctor` proporciona diagnóstico local adicional.
3. Genera un único workflow `product-<id>`, determinista aunque cambie el orden
   de la selección. La definición queda vinculada a servicios, dataset y moneda.
4. Ejecuta cada consulta mediante `Engine.execute`; sus proyecciones se guardan
   en `runs` con el mismo control de idempotencia, permisos y auditoría.
5. Solo cuando terminan todas obtiene `core.metrics.summary` del mismo tenant.
6. Devuelve por servicio estado, resultado seguro, hora original, clave,
   fingerprint y digest. El resultado comercial tiene evidencia propia.

No suma monitores, servidores, repositorios y contactos como si fueran una
misma entidad. Las cifras comerciales proceden de registros locales del operador,
no de inferencias sobre recuentos remotos; demo y real permanecen separados.
No hay conciliación bancaria, certificación productiva ni sincronización bidireccional.

## Reinicio, errores y concurrencia

El mismo ID recupera resultados guardados, con `reused_observations` y la hora
original. Un ID nuevo solicita lecturas nuevas. Un fallo devuelve `paused`, el
paso afectado, los resultados previos y los pasos `not_started`; no se produce
una instantánea comercial aparentemente completa. El fallo guardado no se
reintenta automáticamente con el mismo ID. Tras revisar el fallo de lectura se
puede iniciar una nueva observación con otro ID.

Un segundo proceso no duplica una consulta en curso: recibe `running` para ese
paso y el producto queda pausado. Puede reabrirse cuando termine el primer proceso.
Las revisiones revocadas bloquean incluso un resultado guardado. Cambiar versión,
destino o credenciales invalida el plan vinculado y exige otro ID.

Las escrituras inciertas de otros workflows mantienen sus reglas anteriores de
conciliación. Esta entrada solo consulta; no desbloquea, aprueba ni reintenta
esas escrituras. SQLite y roles de proceso siguen sin ser IAM para empresas hostiles.

## Cuatro contratos de la primera tanda

Rutas, autenticación y formas de respuesta se comprobaron en código upstream
fijado. Los archivos y sus SHA de blob están en
[`sources/contracts-v019.json`](../sources/contracts-v019.json).

| Servicio | Operación y ruta fija | Autenticación | Proyección |
|---|---|---|---|
| Apache Answer | `notifications.summary`, GET `/answer/api/v1/notification/status` | Bearer de usuario activo, `auth_mode=native_user_bearer` | Recuentos de notificaciones y revisiones; permiso de revisión |
| Caddy | `http_servers.summary`, GET `/config/apps/http/servers` | Proxy Bearer revisado | Servidores HTTP configurados, listeners y rutas |
| SeaweedFS | `topology.summary`, GET `/dir/status` | Proxy Bearer revisado; esta ruta usa lista de IPs, no verificación JWT | Slots de volumen Max/Free, centros de datos y layouts |
| Dagster OSS | `repositories.summary`, POST `/graphql` | Proxy Bearer revisado | Número de nodos `Repository` de una consulta fija |

Answer valida `code=200`, enteros y booleanos; descarta nombres, mensajes y
badges. Se consulta el usuario de la credencial, no todos los miembros de la comunidad.

Caddy consulta solo el subárbol HTTP, descarta direcciones y cuerpos de rutas,
y limita servidores, listeners y rutas a 1000 cada uno. Configuración existente
no demuestra tráfico servido. No cambia ni expone la API administrativa.

SeaweedFS devuelve slots de volumen, **no bytes ni almacenamiento útil**. `Free`
puede ser negativo; no se convierte en cero ni se presenta como capacidad verificada.
Las slices Go nulas se admiten como vacías solo con sus claves presentes.
No se leen archivos, IPs, nombres de colecciones o documentos en el resultado.

Dagster acepta únicamente `VerdugoRepositories`, definida en código, solicitando
`__typename` y nodos sin nombres. Rechaza errores GraphQL, datos parciales,
uniones de error y más de 1000 nodos. No hay ejecuciones de jobs ni GraphQL de params.

Todos requieren HTTP 200 síncrono, máximo 1 MiB, sin redirecciones y una respuesta
acotada; no hay paginación automática. No se aceptan URLs, filtros, credenciales,
tenant, consultas ni métodos desde parámetros. Las tres configuraciones de proxy
exigen `auth_mode=reviewed_proxy_bearer` y `proxy_auth_reviewed=true`. Esa bandera
no crea ni acredita un proxy: fuera del fixture debe revisarse la infraestructura real.

## Uso

```sh
python -m verdugo init --out verdugo.local.json
python -m verdugo --state :memory: product-status
# Configurar/revisar solo las instancias necesarias y sus variables VERDUGO_*.
python -m verdugo --config verdugo.local.json product-run @examples/product-observe.json
python -m verdugo --config verdugo.local.json product-run @examples/product-observe.json --execute
```

El ejemplo combina Answer, Caddy, SeaweedFS, Dagster, Uptime Kuma y Gotenberg,
más la instantánea local. No requiere que el usuario gestione seis motores.
Sí requiere instancias, credenciales y revisiones reales para los seis servicios.
Todas las plantillas siguen deshabilitadas y sin aprobación de licencia.
No se ha ejecutado en el teléfono del usuario ni se ha instalado un servicio 24/7.

## Evidencia de aceptación

- Base local: 482 pruebas. Revisión: 518 pruebas, con 36 nuevas (16 de contratos
  y 20 de producto). Los resultados de CI deben observarse por commit.
- Una prueba reúne **33 respuestas sintéticas inyectadas**, 34 pasos incluyendo
  métricas locales, en una sola base y verifica la reapertura sin repetir llamadas.
- Otra recorre **seis servicios con sockets HTTP de loopback**, CLI/MCP y reinicio.
  Las respuestas de proveedor siguen siendo sintéticas.
- Se verifican fallos parciales, política, parámetros prohibidos, redirecciones,
  respuestas excesivas, privacidad, rotación, aislamiento de tenant y concurrencia.
- `real-services.yml / original-caddy` compila Caddy original en el commit
  `7591cff1fb03202ce022982af020197f3f387220` con Go 1.26.0 y `go.sum` upstream.
  Verifica su procedencia VCS y arranca el binario en un namespace sin salida de red.
  Un proxy efímero de prueba solo permite el GET fijo y comprueba ausencia de token,
  token incorrecto y rutas no permitidas. Engine obtiene la configuración real y
  su reapertura no repite la llamada. El artefacto incluye hash del binario,
  procedencia, proyección y resultado del replay. La compilación sí descarga
  dependencias públicas de Go; no se instalan permanentemente.
- Un éxito de ese trabajo acredita exclusivamente ese ensayo de Caddy y ese proxy
  de pruebas. **No acredita Apache Answer, SeaweedFS, Dagster, Kuma ni Gotenberg**.
  Tampoco certifica un proxy o despliegue productivo del operador.
- Las aceptaciones existentes de bibliotecas originales, Qdrant y Meilisearch
  se conservan y deben continuar aprobando.

Los artefactos `verdugo-v019-*` y `verdugo-caddy-v019-*` separan evidencia sintética
y servidor original. `live_verified` permanece 0 porque no hay servicio productivo certificado.

## Estado restante

322 entradas: **69 conectadas por operación permitida, 175 pendientes, 56 piezas
de construcción, 22 excluidas**. El código contiene 69 adaptadores HTTP (73
operaciones) y 19 locales; 19 HTTP históricos están bloqueados por política.
La tanda 1 mantiene 40 pendientes; las siguientes, 50, 50 y 35.
El panel, la app, instalaciones, credenciales y aceptación de los demás proveedores
siguen pendientes. Esta revisión une la operación disponible, no declara terminado
el producto completo ni incorpora los 175 conectores que faltan.
