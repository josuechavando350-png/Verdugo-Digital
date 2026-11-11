# Eventos y recuperación — v0.3

## Fronteras de confianza

Este receptor acepta un contrato canónico propio, no webhooks nativos. Un emisor o traductor autorizado debe verificar primero la firma y la legitimidad del proveedor original. No reenviar payloads externos sin comprobarlos. El secreto permite insertar contactos en la ruta configurada; mantenerlo fuera del navegador, Git y prompts del modelo.

La ruta y el dataset los fija el operador por tenant y fuente. El mensaje no puede especificar tenant, rol, workflow, destino, aprobación ni pago. Solo existe `contact.submitted`, con manejadores `lead.capture` (local) o `contact.bridge` (Twenty/Chatwoot). No se importan ni ejecutan instrucciones del mensaje.

Ejemplo de fuente: copiar la estructura de `examples/ingress-config.json` a la configuración local, sustituir el nombre del secreto y habilitarla explícitamente. `examples/incoming-contact.json` contiene datos ficticios. No usar datos de prueba en producción.

## Contrato criptográfico

POST `/v1/events/website`, `Content-Type: application/json`. Cabeceras únicas:

- `X-Verdugo-Timestamp`: segundos Unix enteros; ventana máxima de ±300 segundos.
- `X-Verdugo-Signature`: `sha256=` seguido del HMAC-SHA256 hexadecimal en minúsculas.

El material firmado es, en bytes UTF-8:

```text
verdugo/v1\n{tenant}\n{source}\n{timestamp}\n{raw_body}
```

`\n` representa un salto de línea real. No reconstruir JSON después de firmarlo. El cuerpo exacto está incluido, así como tenant, fuente y fecha. La clave viene de una variable `VERDUGO_*` con al menos 32 caracteres ASCII imprimibles, generada aleatoriamente por el operador. El código no evalúa su entropía. `verdugo.ingress.signature` documenta el contrato de referencia; no está expuesto al MCP.

Se rechazan cuerpos vacíos o mayores de 32 KiB, JSON duplicado/no válido, campos extra, esquemas incorrectos, solicitudes comprimidas y autenticación inválida. La firma usa comparación de tiempo constante de la biblioteca estándar. La aceptación protege autenticidad del emisor configurado, no demuestra consentimiento ni exactitud comercial del contenido.

## Semántica de entrega

Inbox, trabajo y evento de auditoría se escriben en la misma transacción SQLite. La respuesta HTTP 202 significa persistido, no ejecutado. Repetir `(tenant, source, event_id)` con el mismo cuerpo devuelve el mismo trabajo; cambiar el cuerpo devuelve 409. Incluso diferencias de espacios cambian el hash del cuerpo. Un reintento tardío debe firmarse con fecha actual manteniendo el mismo ID y cuerpo. No cambiar el ID para eludir un conflicto.

La identidad local deriva de tenant, fuente y external_id; un evento nuevo del mismo perfil reutiliza las claves comerciales. No hay actualización automática de perfiles, fusión por email ni reconciliación entre fuentes. Un perfil cambiado queda bloqueado para evitar sobrescribirlo silenciosamente.

Hay cupo pendiente por fuente; se cuentan también trabajos bloqueados y muertos para que un fallo sostenido no eluda el límite. Duplicados ya aceptados no consumen otro cupo. No hay todavía retención/purga, cuota total de disco, ni rate limiting de producción.

## Worker y estados

`pending → leased → succeeded | blocked | pending | dead`.

Cada worker reclama un solo trabajo mediante transacción `BEGIN IMMEDIATE`, con token de posesión y vencimiento. Solo el dueño vigente puede confirmar su resultado. Otro worker puede recuperar un lease vencido; un intento antiguo no puede sobreescribir su confirmación. Eso protege la cola, no agrega transacciones distribuidas a los proveedores.

La entrega es al menos una vez y utiliza las mismas claves de ejecución. Un fallo después del resultado comercial pero antes de confirmar el trabajo reutiliza los resultados guardados. Si el proceso muere durante una escritura, el estado `running` se bloquea al recuperar; no se repite el POST. No hay heartbeat ni supervisor permanente en esta versión.

Errores inesperados del worker reciben espera exponencial acotada e intentos limitados. Contratos, configuración, aprobaciones y escrituras inciertas se bloquean, no se reintentan ciegamente. Cada reclamación consume un intento, incluso si luego necesita aprobación. El cupo agotado queda `dead` y no existe un botón automático de reset. Inspeccionar evidencia antes de cualquier recuperación manual adicional.

```bash
python -m verdugo --config verdugo.local.json queue
python -m verdugo --config verdugo.local.json job JOB_ID
python -m verdugo --config verdugo.local.json job-plan JOB_ID > job-plan.local.json
# Para contact.bridge: revisar y aprobar antes de entregar.
python -m verdugo --config verdugo.local.json --role approver approve-batch @job-plan.local.json
python -m verdugo --config verdugo.local.json worker --execute
# Solo si quedó bloqueado y se resolvió la causa:
python -m verdugo --config verdugo.local.json job-resume JOB_ID --execute
python -m verdugo --config verdugo.local.json worker --execute
```

`job-plan` de captura local no tiene lote de escrituras externas. No necesita `approve-batch`. La CLI usa salida 1 para estados incompletos, incluidos pending/blocked/dead; no implica que el comando haya sido ignorado. No confundir reencolado con finalización.

## Conciliación de contacto incierto

El operador debe inspeccionar el proveedor original y confirmar el objeto correcto, email, cuenta/workspace y resultado. Preparar JSON privado:

```json
{
  "key": "CLAVE_EXACTA_DE_LA_ACCION",
  "fingerprint": "FINGERPRINT_EXACTO_DEL_PLAN",
  "response": {"data": {"createPerson": {"id": "ID_VERIFICADO"}}},
  "verified_email": "contacto@example.invalid",
  "evidence_ref": "REFERENCIA_PRIVADA_A_LA_VERIFICACION"
}
```

El ejemplo de respuesta corresponde al fixture Twenty; usar la forma realmente verificada que coincida con `result_id_path`. La confirmación exige rol local `approver`, acción `uncertain`, fingerprint y email coincidentes e ID válido. Conserva actor, evidencia y hashes; actualiza el resultado atómicamente. Devuelve `basis: human_attestation`, nunca verificación automática. La evidencia falsa o incorrecta no puede ser descubierta solamente por validación de esquema.

No se confirman acciones `running`, pagos ni otros servicios. No se reabre una escritura supuestamente no aplicada, ni se cambian claves. Detener/fencear de forma verificable procesos posiblemente activos e incorporar recuperación de ese estado sigue pendiente. El MCP solo lista casos; no autoriza la conciliación.

## Receptor local y producción pendiente

```bash
python -m verdugo --config verdugo.local.json ingress-local --port 8765
```

Siempre escucha en `127.0.0.1`; requiere estado persistente y rol operador. Cada petición abre y cierra su Engine. No tiene TLS público, IAM, controles perimetrales ni resistencia de producción a carga o abuso. **No exponer este servidor de aceptación en Internet ni asumir que un proxy lo certifica.** Hace falta un servicio de ingreso productivo, validación nativa por proveedor, autorización real, observabilidad, retención y pruebas de carga.

## Fuentes técnicas consultadas

- Python HMAC y `compare_digest`: https://docs.python.org/3/library/hmac.html
- Transacciones SQLite y concurrencia: https://www.sqlite.org/lang_transaction.html
- Advertencia de `http.server` para producción: https://docs.python.org/3/library/http.server.html

Revisión: 2026-11-11. Las pruebas de este repositorio ejercitan su implementación propia y no certifican los servicios externos.
