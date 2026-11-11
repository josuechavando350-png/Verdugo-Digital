# Verdugo Digital

Núcleo de control comercial para NexusBotStudio y empresas cliente. Una entrada CLI/MCP para planes, flujos, eventos y evidencia. **v0.3.0 de ingeniería; no son 100 servicios desplegados.**

## Estado verificable

| Componente | Estado |
|---|---|
| Selección original | 100 proyectos registrados |
| Adaptadores HTTP | 18 implementados / 20 acciones delimitadas |
| Núcleo comercial | 6 acciones; pagos declarados, no verificación bancaria |
| Herramientas MCP | 12, por stdio; sin autoaprobación |
| Eventos entrantes | Sobre canónico HMAC-SHA256, 2 rutas permitidas |
| Cola | SQLite persistente, deduplicación, leases, reintentos limitados y bloqueo |
| Conciliación | Atestación humana de creaciones inciertas de contactos |
| Pruebas locales | 166 aprobadas; fixtures y HTTP loopback |
| Proveedores externos validados en vivo | **0** |
| Proyectos sin adaptador | **82** |
| Probabilidad comercial del 90% | No demostrada por este código |

Registrar, implementar, configurar, desplegar y validar son etapas distintas. El grafo de 100 proyectos representa rutas lógicas, no conectividad real. La v0.3 refuerza coordinación y recuperación; no añade proveedores a la v0.2.

## Inicio local

Python 3.11 o superior, sin dependencias de terceros para el núcleo:

```bash
python -m unittest discover -s tests -v
python -m verdugo demo
python -m verdugo --state :memory: status
python -m verdugo init --out verdugo.local.json
```

`demo` utiliza una base temporal y datos ficticios: cero llamadas externas e ingresos reales. `init` genera 100 entradas desactivadas y ninguna fuente de eventos habilitada. No descarga ni ejecuta los repositorios externos.

## Una orden, varios sistemas

```bash
python -m verdugo --config verdugo.local.json bridge @examples/canonical-contact.json > contact-plan.local.json
python -m verdugo --config verdugo.local.json --role approver --actor local-human approve-batch @contact-plan.local.json
python -m verdugo --config verdugo.local.json bridge @examples/canonical-contact.json --execute
python -m verdugo --config verdugo.local.json doctor
```

El puente sigue: captura local → creación en Twenty → vínculo del ID → creación en Chatwoot → vínculo del ID → resumen. Una aprobación por lote cubre las dos escrituras exactas. No envía mensajes ni inicia campañas. La ejecución se reanuda con las mismas claves y resultados; no fusiona contactos diferentes por email.

Una integración externa exige `enabled: true`, revisión de licencia/uso, versión desplegada explícita, origen HTTPS y secreto `VERDUGO_*` fuera de Git. El administrador debe verificar workspace, cuenta y `result_id_path` contra su instancia. Las rutas de ejemplo son fixtures, no certificación de esquemas o ediciones reales.

Hay lecturas delimitadas para Twenty, Chatwoot, Listmonk, Umami, Meilisearch, Qdrant, Metabase, Grafana, Prometheus, Shlink, Activepieces, n8n, Frappe CRM, ERPNext, PostHog, Lago, Langfuse y changedetection.io. Solo Twenty/Chatwoot tienen creación de contactos. No hay gasto publicitario, borrado remoto ni ejecución arbitraria.

## Eventos y cola (v0.3)

Un evento firmado y válido se almacena junto con un trabajo en una transacción. **Aceptado no significa procesado**: recibir el evento no llama proveedores ni aprueba nada.

```bash
python -m verdugo --config verdugo.local.json queue
python -m verdugo --config verdugo.local.json job-plan JOB_ID > job-plan.local.json
python -m verdugo --config verdugo.local.json --role approver approve-batch @job-plan.local.json
python -m verdugo --config verdugo.local.json worker --execute
```

Cada llamada al worker procesa como máximo un trabajo. Sin `--execute` solo inspecciona. No hay un daemon desplegado ni ejecución permanente al subir código.

Para pruebas locales existe `ingress-local`, ligado exclusivamente a `127.0.0.1`. **No exponerlo en Internet**: no es servidor de producción ni adaptador de firmas nativas de Twenty, Chatwoot u otros proveedores. El contrato, la configuración y el procedimiento completo están en [Eventos y recuperación](docs/EVENTS.md).

Un trabajo puede quedar `blocked` por falta de aprobación, credenciales, cambio de ruta o una escritura incierta. `job-resume JOB_ID --execute` solo lo vuelve a poner en cola; no concede permisos ni reinicia acciones. Los intentos se limitan; `dead` no significa que una acción remota no ocurrió.

```bash
python -m verdugo --config verdugo.local.json reconciliation-list
python -m verdugo --config verdugo.local.json --role approver --actor local-human reconcile @evidence.local.json --execute
```

La conciliación requiere verificar el objeto en el proveedor y aportar evidencia. El código valida la referencia al plan, email e ID; **no comprueba por sí mismo la verdad de esa evidencia**. Solo admite `uncertain`, no acciones `running` que podrían seguir activas. No hay reintento automático de POST inciertos ni promesa de exactly-once remoto.

## Puente para asistentes

```bash
python -m verdugo --config verdugo.local.json --tenant nexus --actor assistant mcp
```

Subconjunto MCP stdio que negocia revisiones legacy `2025-11-25` y `2025-06-18`. Un cliente compatible debe iniciar el proceso. **GitHub no conecta automáticamente este chat ni mantiene un asistente 24/7.**

Herramientas: `verdugo_status`, `verdugo_graph`, `verdugo_events`, `verdugo_plan`, `verdugo_execute`, `verdugo_workflow`, `verdugo_bridge`, `verdugo_doctor`, `verdugo_queue`, `verdugo_job_plan`, `verdugo_worker` y `verdugo_reconciliation_list`.

Tenant y rol se fijan al arrancar; el modelo no puede cambiarlos mediante argumentos. No hay herramientas MCP para aprobar, firmar eventos ni confirmar conciliaciones. El contenido externo se trata como datos, nunca como instrucciones. Una consulta de cola omite perfiles, credenciales y tokens de lease.

## Límites y actualización

Respaldar SQLite antes de actualizar. La migración v0.2 → v0.3 añade tablas sin borrar registros, aprobaciones o claves. Conserva los contratos y headers de adaptadores anteriores para no invalidar sus fingerprints solo por la actualización. Los planes v0.1 pueden ser incompatibles con contratos incorporados en v0.2: no borrar estado para forzar escrituras.

SQLite, WAL y workers son locales a un host; esto no acredita alta disponibilidad, escalabilidad horizontal ni seguridad multiempresa. Los roles son una frontera del proceso local, **no IAM**: separar identidades del sistema operativo, permisos y secretos antes de terceros. Los datos de negocio requieren almacenamiento protegido, retención y copias probadas.

Los importes se separan por moneda y dataset. Los pagos son declaraciones con referencia de evidencia, no conciliación bancaria ni utilidad neta. Una prueba sintética no demuestra ventas, causalidad o tasa de éxito.

Más información: [arquitectura](docs/ARCHITECTURE.md), [fuentes API](docs/API_SOURCES.md), [evidencia](docs/VALIDATION.md), [eventos](docs/EVENTS.md) y [pendientes](docs/ROADMAP.md). El código original todavía no tiene licencia de redistribución elegida. Los repositorios externos conservan las suyas; aquí no se redistribuye su código.
