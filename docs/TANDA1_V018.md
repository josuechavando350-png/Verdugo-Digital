# Tanda 1, continuación v0.18 — dos contratos acotados

Base exacta: `da34f47b6bc6116e553f08801e281f1e695dcc8c` del PR #16.
Se mantiene el plan de Claude, el motor compartido y la política sin proveedores
pagados ni excepciones de licencia. No se modifica `main` ni se aprovisiona hosting.

## Operaciones

| Servicio | Operación | Ruta fija | Autenticación | Resultado retenido |
|---|---|---|---|---|
| Uptime Kuma | `monitors.summary` | GET `/api/monitors` | Clave API Bearer nativa; revisión explícita de acceso | Monitores en respuesta, habilitados y pausados |
| Gotenberg | `health.summary` | GET `/health` | Proxy autenticador Bearer revisado; la ruta original es pública | Estado reportado y número de comprobaciones |

**Alcance deliberadamente limitado.** Un monitor habilitado puede vigilar un sitio
caído: `active` no prueba disponibilidad. Un `/health` positivo de Gotenberg no
prueba generación de PDFs, almacenamiento, entrega ni resultados comerciales.
No se ejecutan conversiones, se suben documentos o se crean/pausan monitores.

## Contratos consultados, no supuestos

Los SHA originales coinciden con `sources/parts` y se conservan con los blobs
inspeccionados en `sources/contracts-v018.json`.

- Uptime Kuma, `4f6661cfa83a06be0353d5536ef3d9ee0064f534`:
  `server/routers/api-router.js` declara `/api/monitors`, la envoltura
  `{ok:true,monitors:[...]}` y los campos; `server/auth.ts` exige clave API y
  la opción `apiEnabled`, sin reutilizar cookies para esta ruta. El API figura
  como **Alpha**, condicionado a habilitar «API and MCP».
- Gotenberg, `4d577e1467aaffa080b1e89d64ecb86c2fba4e98`:
  `pkg/modules/api/api.go` monta `/health` **sin** `securityMiddleware`.
  `go.mod` fija `github.com/alexliesenfeld/health v0.8.1`; su documentación
  muestra `{status,details:{nombre:{status,timestamp,error?}}}` y HTTP 503
  cuando falla la salud. La respuesta privada completa no se conserva.

Se corrige con esta evidencia la nota anterior del plan que afirmaba que Uptime
Kuma solo tenía `/metrics`. No se extiende esta conclusión a versiones distintas.
No se acepta una clave legacy de métricas como equivalente a la clave API nativa.

## Configuración del operador

`verdugo init` deja ambas entradas con `enabled=false`, `license_reviewed=false`
y `version=null`. La versión exacta desplegada, origen HTTPS, permisos mínimos y
el secreto mediante `token_env=VERDUGO_*` deben revisarse antes de activarlas.
La licencia permitida por política sigue sin equivaler a revisión jurídica.

Para Uptime Kuma: `auth_mode="native_api_key_bearer"` y
`api_access_reviewed=true` tras comprobar la API Alpha habilitada y una clave
válida. Para Gotenberg: `auth_mode="reviewed_proxy_bearer"` y
`proxy_auth_reviewed=true` tras comprobar un proxy que rechace acceso sin token.
El código no instala ese proxy ni demuestra su existencia por aceptar la marca.

No guardar claves en Git, URL, argumentos del comando o solicitudes de usuario.
Las marcas de revisión deben ser booleanos exactos, no `1` ni la cadena `"true"`.

## Una entrada y un único estado

`examples/readiness-v018.json` usa el mismo `workflow` por CLI y MCP:

```sh
python -m verdugo --config privado.local.json workflow @examples/readiness-v018.json
# Solo después de revisar y configurar el entorno autorizado:
python -m verdugo --config privado.local.json workflow @examples/readiness-v018.json --execute
```

El primer comando solo planifica. Los dos servicios usan el tenant del Engine;
ningún parámetro puede elegir tenant, URL, método, consulta, filtro, límite o token.
Las credenciales, políticas de autenticación, versión e implementación quedan
ligadas al fingerprint. Repetir el identificador de un flujo exitoso reutiliza su
resultado, no hace un sondeo nuevo. Para una lectura nueva se necesita un ID nuevo.

Una sola respuesta, máximo 1 MiB. Uptime admite hasta 1.000 monitores únicos;
Gotenberg hasta 32 comprobaciones. Exceder el límite produce fallo, no truncado ni
exportación completa ficticia. Se rechazan redirecciones y códigos distintos de
200; un 503 de Gotenberg permanece fallo. No se guardan nombres, URLs, IPs, tags,
identificadores, timestamps, cuerpos de errores ni credenciales del proveedor.

## Verificación y qué falta

Las **26 pruebas nuevas** usan contratos sintéticos y sockets HTTP locales:
rutas/cabeceras, autenticación, límites, esquemas, ausencia de datos privados,
CLI/MCP, persistencia, reanudación y aislamiento entre empresas. No ejecutan
Uptime Kuma ni Gotenberg originales; por ello `live_verified=false` y
`production_certified=false` permanecen sin cambios.

```sh
python -m unittest discover -s tests -p 'test_readiness_reads_v018.py' -v
python -m unittest discover -s tests -v
python -m verdugo --state :memory: status
python -m verdugo connections
```

Nuevo recuento derivado del código: 65 adaptadores HTTP / 69 acciones; 19 recetas
locales; 84 proyectos con operación implementada incluyendo 19 HTTP excluidos.
Bajo política: **65 conectados, 179 pendientes, 56 piezas, 22 excluidos**.
No es un porcentaje de despliegue, ni 65 servidores ejecutándose. La primera
tanda conserva 44 pendientes; todavía requiere más implementación y pruebas.

Los workflows ordinarios deben aprobar en el commit publicado: verificación
Python, simulación Termux, auditoría de conexiones SQLite, bibliotecas originales
y servicios originales que el repositorio ya verifica. Esas últimas pruebas no
certifican automáticamente estos dos conectores nuevos. No se solicitan fusiones
hasta ver los resultados; cualquier resultado pendiente se informa como pendiente.
