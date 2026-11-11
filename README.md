# Verdugo Digital

Núcleo de control comercial para NexusBotStudio y empresas cliente. Una entrada CLI/MCP para planes, flujos, eventos y evidencia. **v0.6.0 de ingeniería; no son 100 servicios desplegados.**

## Estado verificable

| Componente | Estado |
|---|---|
| Selección original | 100 proyectos registrados |
| Adaptadores HTTP | 22 implementados / 26 acciones delimitadas |
| Núcleo comercial | 6 acciones existentes más registro local de hitos y seguimiento a 30 días; pagos declarados, no verificación bancaria |
| Herramientas MCP | 18, por stdio; sin autoaprobación de efectos externos |
| Eventos entrantes | Sobre canónico HMAC-SHA256, 2 rutas permitidas |
| Cola | SQLite persistente, deduplicación, leases, intentos limitados y bloqueo |
| Recuperación | Guardia local v0.4.1 + lectura de contacto + revisión humana separada |
| Pruebas locales v0.6 | **296 aprobadas**, fixtures y HTTP loopback; CI se valida por commit |
| Proveedores externos validados en vivo | **0** |
| Proyectos sin adaptador | **78** |
| Probabilidad comercial del 90% | No demostrada por este código |

Registrar, implementar, configurar, desplegar y validar son etapas distintas. El grafo de 100 proyectos representa rutas lógicas, no conectividad real. No descarga ni ejecuta los repositorios externos. No hay hosting, campañas ni operación permanente activados por este código.

## Inicio local

Python 3.11 o superior, sin dependencias de terceros para el núcleo:

```bash
python -m unittest discover -s tests -v
python -m verdugo demo
python -m verdugo --state :memory: status
python -m verdugo init --out verdugo.local.json
```

La demo utiliza una base temporal y datos ficticios: cero llamadas externas e ingresos reales. La configuración generada mantiene los 100 proyectos deshabilitados, sin fuentes entrantes activas y sin secretos. Nunca publicar estado, perfiles ni credenciales.

## Una orden, varios sistemas

```bash
python -m verdugo --config verdugo.local.json bridge @examples/canonical-contact.json > contact-plan.local.json
python -m verdugo --config verdugo.local.json --role approver --actor local-human approve-batch @contact-plan.local.json
python -m verdugo --config verdugo.local.json bridge @examples/canonical-contact.json --execute
python -m verdugo --config verdugo.local.json doctor
```

El puente sigue: captura local → creación en Twenty → vínculo del ID → creación en Chatwoot → vínculo del ID → resumen. La aprobación por lote cubre las dos escrituras exactas. El flujo conserva resultados al reanudarse; no envía mensajes ni inicia campañas.

Una integración exige habilitación, revisión de licencia/uso, versión desplegada explícita, origen HTTPS y secreto `VERDUGO_*` fuera de Git. Las versiones, ediciones, esquemas, cuentas y permisos todavía requieren validación en instancias autorizadas. El contenido externo se trata como datos, no como instrucciones.

## Nuevo v0.6: puerta de aceptación y respaldo coherente

- `pilot`: una sola orden para preparar o consultar seis conectores prioritarios con **lecturas acotadas y contratos revisados**. Cada proveedor debe habilitarse explícitamente en configuración local; no hay credenciales ni servidores incluidos. Los resultados de sandbox y los fixtures **nunca cuentan como integración productiva certificada**.
- `backup-local` y `verify-backup`: copia SQLite consistente y verificación de integridad, con permisos privados y sin reemplazar datos existentes. Los respaldos **no están cifrados** y no se publican en GitHub. No permiten restaurar operaciones de escritura dudosas automáticamente.

```bash
python -m verdugo --config verdugo.local.json pilot @examples/pilot-request.json
# Una vez validada licencia, edición, API, token y esquema en un sandbox autorizado:
python -m verdugo --config verdugo.local.json pilot @examples/pilot-request.json --execute
mkdir -m 700 -p ./respaldos.local
python -m verdugo backup-local --to ./respaldos.local/pre-cambio.sqlite3
python -m verdugo verify-backup --file ./respaldos.local/pre-cambio.sqlite3
```

Procedimiento y restricciones: [puerta de aceptación y copias](docs/PILOTO_Y_RESPALDOS_V06.md).

## Nuevo v0.5: tablero comercial de 30 días

Verdugo añade un **registro local e inmutable de hitos comerciales** por prospecto (contacto, reunión, propuesta, seguimiento, cierre) usando la identidad compartida de los leads y pagos del núcleo. Desde CLI o MCP puede devolver el avance respecto de 6 clientes mínimos y 10 como objetivo operativo; no infiere un 90% de probabilidad ni verifica depósitos bancarios.

```bash
python -m verdugo --state :memory: commercial-report
python -m verdugo --state :memory: commercial-next
# Registros del operador con evidencia privada; primero planificar:
python -m verdugo --config verdugo.local.json commercial-record @evento.local.json
python -m verdugo --config verdugo.local.json commercial-record @evento.local.json --execute
```

Sin prospectos capturados, el informe muestra 0; ningún dato ficticio se contará como ingreso real. Los hitos no envían mensajes, crean anuncios ni cobran. `commercial-next` destaca prospectos sin seguimiento y tareas vencidas, sin revelar nombres ni correos en la respuesta. La vinculación a `core.payment.record` es una comprobación local de datos declarados, **no conciliación bancaria**. [Guía y límites del control comercial](docs/COMERCIAL_30_DIAS.md).

## Consulta conjunta de superficies comerciales

Mautic, Easy!Appointments, Formbricks y Dub se suman al mismo motor, diagnóstico, workflows y controles. No son instalaciones de los productos ni conectores de todas sus funciones.

```bash
python -m verdugo --config verdugo.local.json surface @examples/commercial-surfaces.json
python -m verdugo --config verdugo.local.json surface @examples/commercial-surfaces.json --execute
```

La salida presenta cuántos objetos llegaron en cada respuesta, su procedencia y fecha. No suma entidades diferentes ni convierte contactos, servicios, encuestas o enlaces en clientes pagados. No es exportación completa, atribución ni sincronización bidireccional. Repetir el ID reutiliza lecturas guardadas; usar un ID nuevo para una observación fresca.

## Nuevo: lectura de comprobación y recuperación

Una creación incierta no se reenvía. El operador puede proponer un ID remoto y leerlo con la misma cuenta, versión, credencial y política de red del plan original. El contrato de respuesta debe revisarse y habilitarse mediante `readback_reviewed` y `readback_record_path` en la configuración local.

```bash
python -m verdugo --config verdugo.local.json reconciliation-list
python -m verdugo --config verdugo.local.json readback @examples/contact-readback.json
python -m verdugo --config verdugo.local.json readback @examples/contact-readback.json --execute
# Revisar la evidencia antes de preparar el archivo local de confirmación:
python -m verdugo --config verdugo.local.json --role approver --actor local-human reconcile-readback @readback-review.local.json --execute
```

Comprobar un ID, correo, nombre y ámbito no demuestra que el POST original creara ese contacto. La lectura solo produce evidencia; no aprueba, no resuelve automáticamente y no garantiza ausencia de duplicados. La revisión separada exige una observación coincidente de hasta cinco minutos y conserva trazabilidad. Acciones `running` permanecen bloqueadas. Procedimiento, límites y fuentes: [v0.4](docs/V04.md).

## Eventos, cola y asistentes

Los eventos canónicos firmados se almacenan atómicamente junto con trabajos. Aceptar no significa procesar. `worker --execute` entrega como máximo uno; `queue`, `job-plan`, `job-resume` y `reconciliation-list` comparten el mismo estado. El receptor `ingress-local` está restringido a loopback y **no debe exponerse en Internet**. El contrato no verifica firmas nativas de proveedores. [Procedimiento v0.3](docs/EVENTS.md).

```bash
python -m verdugo --config verdugo.local.json --tenant nexus --actor assistant mcp
```

MCP stdio con revisiones legacy `2025-11-25` y `2025-06-18`. Sus 18 herramientas incluyen `verdugo_contact_readback` y `verdugo_surface_overview`. No hay herramientas para aprobar, firmar eventos o confirmar conciliaciones. **Publicar en GitHub no conecta este chat al MCP ni mantiene un asistente 24/7.**

## Límites y actualización

Respaldar SQLite antes de actualizar. v0.4 añade `contact_readbacks`, v0.4.1 añade guardias de ejecución local y v0.5 añade `commercial_events` y v0.6 añade `pilot_manifests` y `pilot_observations`; no borra ni cambia planes, aprobaciones, ejecuciones o identidades. Una prueba de compatibilidad conserva los fingerprints de creación v0.3. Cambiar secretos, versiones o destinos invalida la comprobación: no borrar estado ni cambiar claves para forzar un POST.

SQLite y roles locales no constituyen IAM, aislamiento hostil entre empresas ni alta disponibilidad. Faltan ingreso productivo, supervisor, retención, firmas nativas, sincronización bidireccional e identidad IAM. La recuperación local de `running` es cooperativa y limitada a un solo host, no recuperación distribuida. Los resultados almacenados pueden contener datos personales y exigen protección del host y copias probadas.

Los pagos son declaraciones por moneda/dataset, no conciliación bancaria ni utilidad neta. Ninguna prueba sintética demuestra rentabilidad o éxito comercial. Las licencias externas siguen separadas; no se redistribuye aquí su código. El código original todavía no tiene licencia de redistribución elegida.

Documentación: [operación v0.6](docs/PILOTO_Y_RESPALDOS_V06.md), [control comercial v0.5](docs/COMERCIAL_30_DIAS.md), [recuperación v0.4.1](docs/V041.md), [entrega y pendientes v0.4](docs/V04.md), [fuentes nuevas](docs/API_SOURCES_V04.md), [arquitectura previa](docs/ARCHITECTURE.md), [validación histórica v0.3](docs/VALIDATION.md).
