# Verdugo Digital

Núcleo de control comercial para NexusBotStudio y empresas cliente. Una entrada para inventario, planes, acciones, flujos y evidencia. **Versión 0.2.0 de ingeniería; no es una plataforma de 100 servicios desplegados.**

## Estado comprobable

| Entrega | Estado |
|---|---|
| Proyectos de la selección original | 100 registrados; coincidencia exacta con el catálogo entregado |
| Adaptadores HTTP | 18 implementados, 20 acciones acotadas; pruebas con fixtures y servidor local |
| Acciones del núcleo | 6: captura, calificación, pago declarado, métricas, vínculo de identidad y consulta de identidades |
| Puente de operación | CLI unificada + 8 herramientas MCP por stdio |
| Flujos | DAG con dependencias, referencias, pausa, aprobación por lote y reanudación |
| Persistencia | SQLite local, aislamiento lógico por tenant, claves de idempotencia y eventos |
| Pruebas locales | 110 aprobadas en Python 3.13.5; no constituyen auditoría exhaustiva |
| Servicios de terceros validados en vivo | **0** |
| Adaptadores todavía no implementados | **82**; fallan explícitamente, nunca simulan éxito |
| Probabilidad comercial del 90% | No demostrada ni calculada por este código |

Registrar un proyecto, construir su adaptador, configurarlo, desplegarlo y validar su resultado son etapas distintas. El grafo muestra conexiones **lógicas** al núcleo; no prueba conectividad de infraestructura.

## Ejecutar sin contratar infraestructura

Desde este repositorio, con Python 3.11 o superior:

```bash
python -m unittest discover -s tests -v
python -m verdugo demo
python -m verdugo --state :memory: status
python -m verdugo graph
python -m verdugo init --out verdugo.local.json
```

El núcleo no requiere paquetes de terceros. `demo` usa datos ficticios y una base temporal, hace cero llamadas externas y no registra ingresos reales. `init` genera la configuración de los 100 proyectos, todos desactivados. No descarga sus repositorios ni instala sus servicios.

## Una orden, varios sistemas

```bash
python -m verdugo --config verdugo.local.json workflow @examples/commercial-overview.json
python -m verdugo --config verdugo.local.json workflow @examples/commercial-overview.json --execute
```

Ese flujo consulta CRM, conversaciones, sitios y automatizaciones. Primero deben existir los servicios autorizados y sus credenciales. No hay endpoints productivos ni secretos incluidos.

Para una escritura, se prepara el plan exacto antes de ejecutarlo. Ejemplo de puente Twenty → Chatwoot, con un solo lote de aprobación:

```bash
python -m verdugo --config verdugo.local.json workflow @examples/contact-bridge.json > contact-plan.local.json
# Revisar destinos, cuerpos, versiones y alcance antes de aprobar.
python -m verdugo --config verdugo.local.json --role approver --actor local-human approve-batch @contact-plan.local.json
python -m verdugo --config verdugo.local.json workflow @examples/contact-bridge.json --execute
```

Los datos de esos ejemplos son ficticios. No ejecutarlos contra producción sin sustituirlos y revisar el plan. Una aprobación caduca y está ligada a tenant, acción, contenido, destino, versión, credencial y clave. El rol `approver` es una frontera del proceso local, **no un sistema IAM**: separar usuarios/permisos del sistema operativo antes de usarlo con terceros. El MCP no expone herramientas de aprobación.

## Adaptadores presentes

Twenty, Chatwoot, Listmonk, Umami self-hosted, Meilisearch, Qdrant, Metabase, Grafana (ruta legacy), Prometheus, Shlink, Activepieces, n8n, Frappe CRM, ERPNext, PostHog, Lago, Langfuse y changedetection.io. Únicamente Twenty y Chatwoot incluyen creación de contacto/persona; los demás tienen lecturas delimitadas. No hay envío de campañas, publicación social, gasto publicitario, borrado remoto ni ejecución arbitraria de comandos.

Cada servicio necesita `enabled: true`, revisión de uso/licencia registrada, una versión desplegada explícita, un origen HTTPS y una referencia `VERDUGO_*` a su secreto de entorno. Las credenciales deben estar restringidas al workspace del cliente. Los permisos/API disponibles varían por edición: no se presupone acceso comercial gratuito.

## Puente para asistentes

```bash
python -m verdugo --config verdugo.local.json --tenant nexus --actor assistant mcp
```

Implementa el subconjunto de herramientas MCP por stdio, negociando expresamente las revisiones legacy `2025-11-25` y `2025-06-18`; no pretende implementar todo el protocolo actual. Un cliente compatible debe lanzar este proceso. **Subirlo a GitHub no conecta automáticamente este chat ni deja un asistente funcionando 24/7.** No se despliega un endpoint remoto ni se realizan llamadas a modelos.

Herramientas: `verdugo_status`, `verdugo_graph`, `verdugo_events`, `verdugo_plan`, `verdugo_execute`, `verdugo_workflow`, `verdugo_bridge`, `verdugo_doctor`. Todas utilizan el mismo motor. Tenant y rol se fijan al iniciar el proceso, no mediante argumentos del modelo. Los textos de proveedores son datos no confiables, nunca instrucciones para ejecutar más herramientas.

## Límites operativos

La ejecución usa preview por defecto. Una repetición de la misma clave no duplica el envío. Un fallo de escritura remoto queda `uncertain` y exige conciliación; no se promete exactly-once remoto ni rollback distribuido. Reiniciar un proceso con una acción `running` tampoco la reenvía automáticamente.

Los importes son enteros en unidad monetaria menor, separados por moneda y por dataset `demo`/`real`. El registro de pago es una declaración del operador con referencia de evidencia: **no es verificación bancaria ni utilidad neta**. Nunca se mezcla la demostración con métricas reales.

Documentación: [arquitectura y controles](docs/ARCHITECTURE.md), [fuentes API](docs/API_SOURCES.md), [validación](docs/VALIDATION.md) y [trabajo pendiente](docs/ROADMAP.md). No se ha elegido una licencia de redistribución para el código original del proyecto. Los 100 repositorios externos conservan sus propias licencias; aquí no se redistribuye su código.

## Puente canónico y diagnóstico central (v0.2.0)

```bash
python -m verdugo --config verdugo.local.json bridge @examples/canonical-contact.json > contact-plan.local.json
python -m verdugo --config verdugo.local.json --role approver --actor local-human approve-batch @contact-plan.local.json
python -m verdugo --config verdugo.local.json bridge @examples/canonical-contact.json --execute
python -m verdugo --config verdugo.local.json doctor
python -m verdugo --config verdugo.local.json doctor --probe-id acceptance-001 --execute
```

El puente usa seis pasos: captura canónica, creación en Twenty, vínculo con su ID, creación en Chatwoot, vínculo con su ID y resumen. Se aprueban las dos escrituras en un lote. La clave del flujo deriva de tenant, lead_id y dataset: repetir el mismo perfil no vuelve a crear contactos. No fusiona automáticamente perfiles distintos con el mismo email. Los alias son locales; no existe sincronización bidireccional ni webhooks productivos.

Un flujo queda ligado a su definición. Cambiar pasos o perfil conservando su ID produce un error, no una continuación con instrucciones distintas. Una respuesta de creación sin un ID válido o una respuesta HTTP 202 no se presenta como escritura completada: queda incierta y requiere conciliación.

Antes del puente, el operador debe verificar `workspace_id` de Twenty y `result_id_path` de cada servicio contra su instancia. Las rutas de respuesta de la plantilla son fixtures, no certificación del esquema instalado. Chatwoot admite `auth_mode: bearer` (documentado para v4.19.0+) o `api_access_token` para la modalidad anterior, elegida explícitamente. Frappe usa una variable secreta con `api_key:api_secret`; Langfuse usa su clave pública en `username` y la secreta en `token_env`.

`doctor` revisa configuración de los 100 IDs. Con `--execute` realiza como máximo una lectura delimitada por adaptador habilitado; no envía mensajes ni crea recursos. Resume bloqueos y fallos sin ocultar los otros resultados. No certifica licencias, aislamiento ni validez comercial; `live_verified` sigue en cero. Reutilizar `probe-id` devuelve resultados guardados; una lectura nueva necesita otro ID.

CLI devuelve código 1 para ejecución pausada, aprobación pendiente o diagnóstico incompleto/sin configuración. MCP marca esos resultados `isError: true`. Esto impide interpretar un bloqueo como una operación terminada.

### Actualización desde v0.1

Conservar y respaldar SQLite antes de actualizar; se añade la tabla de identidades sin borrar registros. Los nuevos contratos incluyen autenticación completa, política de red y ruta de ID en el fingerprint: los planes externos antiguos pueden resultar incompatibles. No cambiar claves de idempotencia ni borrar estado para forzar un POST. Conciliar primero los objetos existentes; su importación y la consola de conciliación siguen pendientes.
