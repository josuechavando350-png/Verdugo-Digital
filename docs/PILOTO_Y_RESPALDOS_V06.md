# Verdugo Digital v0.6 — puerta de aceptación y respaldo local

**Objetivo:** pasar del contrato programado a una comprobación reproducible contra una instalación *autorizada*. No declarar que 100 proyectos están instalados ni que un GET 200 confirma una integración comercial.

## Inventario en esta versión

- 100 proyectos del catálogo; 22 adaptadores HTTP con 26 operaciones delimitadas; 78 proyectos sin adaptador.
- Una nueva herramienta MCP (`verdugo_pilot`) da 18 en total. **Ninguna herramienta MCP hace backups, acepta licencias, aprueba escrituras o instala servicios**.
- Seis servicios soportados por la puerta de comprobación de solo lectura: Twenty, Chatwoot, Listmonk, Umami, Mautic y Formbricks. El resto de los 22 sigue disponible a través de `doctor` y sus contratos actuales; no están certificados.
- Se añade copia SQLite consistente y verificación de integridad local. **No cifrada; sin restauración automática**.
- Ningún servidor, proveedor, credencial ni campaña se desplegó por esta actualización.

## Comprobación de contrato: `pilot`

1. Elegir instancias de prueba autorizadas (primero Twenty/Chatwoot). Verificar licencia, edición, versión exacta, cuenta, endpoint y scopes de solo lectura.
2. Configurar servicios en `verdugo.local.json` (fuera de Git): `enabled: true`, `license_reviewed: true`, versión concreta, URL HTTPS, referencia `token_env` que empiece por `VERDUGO_`. Guardar el token en el entorno del proceso, nunca en JSON ni repositorio.
3. Añadir a cada servicio un objeto `acceptance` con `reviewed: true`, `environment: "sandbox"`, `collection_path` (ruta exacta validada contra la edición desplegada), `collection_type` (`array` u `object`) y `contract_ref` a la especificación que el operador revisó. Los placeholders de `examples/` están deshabilitados y **no son esquemas certificados**.
4. Revisar primero la planificación sin llamadas externas:

```bash
python -m verdugo --config verdugo.local.json pilot @examples/pilot-request.json
```

5. Si todas las precondiciones se cumplen, realizar las lecturas:

```bash
python -m verdugo --config verdugo.local.json pilot @examples/pilot-request.json --execute
```

La operación valida *todos* los destinos/credenciales/contratos antes de realizar la primera lectura, y ejecuta **un GET con respuesta acotada por cada servicio**. No sigue enlaces ni instrucciones del proveedor. La salida solo contiene cantidad observada, estado, instante y SHA-256 del resultado. Puede registrar material sensible en el SQLite protegido; no se deben exportar bases de datos al repositorio.

Cada `probe_id` identifica una ejecución y su configuración exacta. Repetirlo reutiliza resultados ya guardados, no vuelve a consultar. Usar otro ID para una comprobación fresca. Cambiar configuración bajo el mismo ID falla. Una forma incorrecta da `schema_mismatch`, no un falso cero.

**Semántica:** `schema_observed` indica que la respuesta del endpoint autorizado coincide con una forma revisada. `production_certified: false` y `live_verified: 0` siguen siendo explícitos. La configuración `fixture` sirve solo para pruebas sintéticas y no se admite `production` en esta puerta. Una respuesta válida no comprueba la integridad del servicio, consentimientos, cuentas de otros tenants, costos ni capacidad de entregar ventas.

## Backups y continuidad

Para no perder oportunidades registradas, se agregó una copia consistente usando la API `sqlite3.Connection.backup`. Con la aplicación ya configurada y un directorio dedicado **privado (0700)**:

```bash
mkdir -m 700 -p ./respaldos.local
python -m verdugo --state .state/verdugo.sqlite3 backup-local --to ./respaldos.local/pre-cambio.sqlite3
python -m verdugo verify-backup --file ./respaldos.local/pre-cambio.sqlite3
```

La verificación comprueba estructura de la base, `integrity_check`, foreign keys y hash SHA-256. Una copia crea un archivo nuevo modo `0600`; rechaza enlaces, directorios compartidos y sobrescrituras. No se exportan registros por la salida CLI; **la copia sí contiene datos personales y claves del motor (no credenciales externas si se respetó la configuración)**.

**No está cifrada.** No subir copias a GitHub, no enviarlas por correo ni a nubes sin cifrado externo con gestión de claves. La verificación de integridad no prueba que la restauración funcione. Para restaurar hay que detener procesos, aislar el entorno, validar esquema e integridad y reconciliar operaciones `running`/`uncertain` sin reenviar POST. La protección `run_guards` tiene ámbito de archivo/inodo y las restauraciones a otro archivo *no* se desbloquean automáticamente. No se entregó operación de restauración online.

## Criterios para activar el primer piloto real

- Instancia autorizada, versión fija, licencia revisada y cuenta técnica con mínimos permisos.
- Comprobar el formato de respuestas en la instalación concreta con el pilot de solo lectura.
- Crear un registro de contacto sintético en sandbox mediante el flujo existente y aprobación separada, no con datos de terceros.
- Probar la consulta de identificación, un fallo con resultado incierto y conciliación humana sin duplicación.
- Verificar respaldo **cifrado para almacenamiento externo** y restauración aislada, controles IAM, privacidad y registro de errores antes de producción.
- Comprobar cobros y facturación con fuentes externas independientes antes de presentar métricas como ingresos reconciliados.

## Evidencia de ingeniería

- Las pruebas locales y la CI ejercitan fixtures y servidores HTTP en loopback; no existen credenciales reales ni pruebas de proveedores externos.
- Las pruebas verifican fail-closed por contrato/permiso, formas de respuesta incorrectas, eventos adversarios, duplicados/replays, ausencia de exposición de PII en informes, snapshots consistentes y rechazo de copias inseguras.
- No hay servidor HTTP de producción, daemon 24/7, sincronización bidireccional, IAM empresarial, conectores de pago en vivo ni probabilidad demostrada de 90% de éxito.

**La meta de los siguientes cambios es completar el primer piloto de un proveedor real, no aumentar números de adaptadores desconectados.**
