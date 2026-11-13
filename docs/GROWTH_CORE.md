# Núcleo comercial local v0.1 — contrato y límites

## Alcance real

Una aplicación local Node.js/SQLite, no diez servidores instalados. El flujo
implementado es prospecto -> calificación -> venta declarada -> reporte local.
Los adaptadores de PostHog y RudderStack tienen pruebas de contrato contra HTTP
local sintético. No hay credenciales de producción ni evidencia de ingestión
real en esos proveedores. Las referencias Git de los diez proyectos se conservan.

## Datos y límites de acceso

Un proceso sirve un espacio (`VERDUGO_WORKSPACE`, por defecto `nexus`), ligado al
token del operador. Las solicitudes no pueden elegir otro espacio. El almacén
separa eventos, prospectos y pedidos por espacio. Esto **no es** autorización
multiusuario de un SaaS: quien controla el equipo o el archivo de base de datos
puede leerlo. No hay cifrado de base, roles, auditoría inmutable, retención/borrado,
respaldos automáticos ni recuperación de desastre certificados en esta versión.

`VERDUGO_STATE_DB` cambia la ruta de la base. Se exige directorio privado 0700 y
archivo regular 0600; no se aceptan enlaces simbólicos en la ruta final. SQLite
usa transacciones, claves foráneas, WAL y sincronización FULL. No copie solo el
archivo principal mientras esté abierto: el WAL puede contener datos recientes.

## API

Todas las rutas `/v1/*` exigen `Authorization: Bearer <token>`. Solo se aceptan
Host/origen de loopback. El servidor se niega a escuchar en interfaces públicas.
Los POST usan `Content-Type: application/json`, máximo 16 KiB. No se sirven CORS.

| Ruta | Operación |
|---|---|
| `GET /v1/capabilities` | Espacio, núcleo activo y destinos configurados; sin secretos |
| `GET /v1/leads?limit=50&offset=0` | Hasta 200 prospectos por página |
| `GET /v1/report` | Etapas, origen declarado, ventas por moneda y cola |
| `GET /v1/outbox` | Últimos 200 estados de entrega, sin cuerpos ni claves |
| `POST /v1/events` | Evento validado y transacción local |
| `POST /v1/outbox/dispatch` | Envío manual y explícito de trabajos pendientes |
| `GET /v1/catalog`, `GET /v1/systems` | Catálogo y sondas de conectividad previas |

Ejemplo sintético de `POST /v1/events`:

```json
{
  "id": "9137bb5d-f647-46ef-ae0e-825477332c82",
  "type": "lead.created",
  "lead_id": "demo-1",
  "data": {
    "name": "Persona de prueba",
    "source": "demo-local",
    "analytics": false,
    "marketing": false
  }
}
```

El ID de evento debe ser UUID. Reenviar el mismo ID y contenido devuelve 200
sin repetir efectos; reutilizarlo con contenido distinto devuelve 409. El cliente
debe conservar ese ID ante una respuesta incierta. `lead_id`, `order_id` y el
espacio aceptan 1–80 letras, dígitos, guion y guion bajo. No se fusionan personas
automáticamente por correo: la deduplicación implementada es de IDs y pedidos.

Tipos y campos permitidos en `data`:

- `lead.created`: `name`, `source`, booleanos `analytics`, `marketing`; `email`
  opcional. No se sobrescribe un prospecto existente.
- `lead.stage_changed`: `stage` = `qualified` o `lost`. Una venta ganada no se
  degrada por esta operación. Un perdido debe recalificarse antes de vender.
- `consent.updated`: booleanos `analytics`, `marketing`.
- `sale.recorded`: `order_id`, `amount_minor` entero positivo hasta 10^12,
  `currency` = MXN, USD o EUR. Cambia la etapa a `won`.

La hora registrada es la recepción local, no una fecha comercial importada.
`source` es el primer origen declarado por el operador: no atribución causal.
No hay devoluciones, impuestos, comisiones, margen, conciliación bancaria o ROAS.
No interprete la suma de ventas declaradas como dinero cobrado o rentabilidad.

## Adaptadores opcionales, no servicios desplegados

El archivo indicado por `VERDUGO_CONNECTIONS_JSON` debe ser privado (0600).
Por defecto no existe ninguna conexión y no se crea ningún envío. Ejemplo de
estructura, con dominio deliberadamente inexistente:

```json
{
  "posthog": {
    "enabled": true,
    "base_url": "https://posthog.example.invalid",
    "key_env": "VERDUGO_POSTHOG_KEY"
  }
}
```

El valor de la clave va únicamente en la variable de entorno. Nunca en una URL,
archivo versionado, solicitud de evento, respuesta de API o evidencia pública.
`rudderstack` utiliza la misma estructura con su propia clave y base. Se admite
HTTPS o HTTP de loopback; se rechazan userinfo, query, fragmentos y prefijos de
ruta. La configuración no puede alterarse desde HTTP.

Contratos implementados a partir de documentación primaria consultada:

- PostHog: `POST /i/v0/e/`, `api_key`, `event`, `uuid`, `timestamp`,
  `properties.distinct_id`. Sin creación de perfiles de persona.
  Fuente: https://posthog.com/tutorials/api-capture-events
- RudderStack: `POST /v1/track`, Basic Auth con write key como usuario y contraseña
  vacía; `userId`, `messageId`, `event`, `timestamp`, `properties`.
  Fuente: https://www.rudderstack.com/docs/api/http-api/
- SQLite integrado: https://nodejs.org/download/release/v22.16.0/docs/api/sqlite.html

Los cuerpos salientes excluyen los campos `name` y `email`; usan un identificador
seudónimo derivado del espacio y el lead. **No es anonimización garantizada**:
el origen y las propiedades permitidas también deben evitar información sensible.
Si RudderStack reenvía a PostHog, no habilite además la ruta directa sin revisar
la duplicación. Sus destinos pueden disparar automatizaciones propias: revise
esas consecuencias antes de autorizar una entrega.

## Consentimiento y entrega

La captura local no envía nada. Solo se encolan eventos nuevos si hay consentimiento
de analítica y destino habilitado. Marcar una casilla no obtiene consentimiento
ni certifica cumplimiento jurídico. Conceder permiso después no reenvía historial.
Retirarlo cancela lo pendiente, no deshace solicitudes en vuelo ni borra datos
ya enviados. La versión actual no implementa supresión en proveedores.

La cola enlaza cada trabajo con una huella de proveedor, URL y credencial. Cambiar
la configuración no redirige trabajos previos a otro proyecto: quedan pendientes
hasta revisión/restauración de la configuración original.

Para enviar se requiere `POST /v1/outbox/dispatch` con:

```json
{"confirm": true, "limit": 10}
```

Límite 1–50. `confirm` debe ser booleano. No hay trabajador recurrente ni envío
al arrancar. Un 2xx se registra como `accepted` **solo a nivel HTTP**, sin afirmar
lectura posterior o integración E2E. Los redirects no se siguen. Los errores de
red o 5xx quedan `uncertain`, sin reintento automático. Un proceso interrumpido
con trabajo `inflight` pasa a `uncertain` al detectar más de 60 segundos en un
nuevo intento de despacho. La conciliación/reintento manual seguro de trabajos
inciertos está pendiente; no edite sus estados para forzar una retransmisión.

## Aceptación pendiente

Ejecutar en Android real; completar los otros ocho adaptadores y los flujos entre
los diez; verificar APIs auténticas con entornos autorizados; revisar licencias,
privacidad, borrado, backups y operación comercial. Las pruebas de Node/Linux
no certifican ninguna de esas etapas por sí mismas.
