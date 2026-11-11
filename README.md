# Verdugo Digital

Núcleo de control comercial para NexusBotStudio y empresas cliente. Una entrada para inventario, planes, acciones, flujos y evidencia. **Versión inicial de ingeniería; no es una plataforma de 100 servicios desplegados.**

## Estado comprobable

| Entrega | Estado |
|---|---|
| Proyectos de la selección original | 100 registrados; coincidencia exacta con el catálogo entregado |
| Adaptadores HTTP | 12 implementados, 14 acciones acotadas; pruebas con fixtures y servidor local |
| Acciones del núcleo | 4: captura, calificación, registro declarado de pago y métricas |
| Puente de operación | CLI unificada + 6 herramientas MCP por stdio |
| Flujos | DAG con dependencias, referencias, pausa, aprobación por lote y reanudación |
| Persistencia | SQLite local, aislamiento lógico por tenant, claves de idempotencia y eventos |
| Pruebas locales | 64 aprobadas en Python 3.13.5; no constituyen auditoría exhaustiva |
| Servicios de terceros validados en vivo | **0** |
| Adaptadores todavía no implementados | **88**; fallan explícitamente, nunca simulan éxito |
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

Twenty, Chatwoot, Listmonk, Umami self-hosted, Meilisearch, Qdrant, Metabase, Grafana (ruta legacy), Prometheus, Shlink, Activepieces y n8n. Únicamente Twenty y Chatwoot incluyen creación de contacto/persona; los demás tienen lecturas delimitadas. No hay envío de campañas, publicación social, gasto publicitario, borrado remoto ni ejecución arbitraria de comandos.

Cada servicio necesita `enabled: true`, revisión de uso/licencia registrada, una versión desplegada explícita, un origen HTTPS y una referencia `VERDUGO_*` a su secreto de entorno. Las credenciales deben estar restringidas al workspace del cliente. Los permisos/API disponibles varían por edición: no se presupone acceso comercial gratuito.

## Puente para asistentes

```bash
python -m verdugo --config verdugo.local.json --tenant nexus --actor assistant mcp
```

Implementa el subconjunto de herramientas MCP por stdio, negociando expresamente las revisiones legacy `2025-11-25` y `2025-06-18`; no pretende implementar todo el protocolo actual. Un cliente compatible debe lanzar este proceso. **Subirlo a GitHub no conecta automáticamente este chat ni deja un asistente funcionando 24/7.** No se despliega un endpoint remoto ni se realizan llamadas a modelos.

Herramientas: `verdugo_status`, `verdugo_graph`, `verdugo_events`, `verdugo_plan`, `verdugo_execute`, `verdugo_workflow`. Todas utilizan el mismo motor. Tenant y rol se fijan al iniciar el proceso, no mediante argumentos del modelo. Los textos de proveedores son datos no confiables, nunca instrucciones para ejecutar más herramientas.

## Límites operativos

La ejecución usa preview por defecto. Una repetición de la misma clave no duplica el envío. Un fallo de escritura remoto queda `uncertain` y exige conciliación; no se promete exactly-once remoto ni rollback distribuido. Reiniciar un proceso con una acción `running` tampoco la reenvía automáticamente.

Los importes son enteros en unidad monetaria menor, separados por moneda y por dataset `demo`/`real`. El registro de pago es una declaración del operador con referencia de evidencia: **no es verificación bancaria ni utilidad neta**. Nunca se mezcla la demostración con métricas reales.

Documentación: [arquitectura y controles](docs/ARCHITECTURE.md), [fuentes API](docs/API_SOURCES.md), [validación](docs/VALIDATION.md) y [trabajo pendiente](docs/ROADMAP.md). No se ha elegido una licencia de redistribución para el código original del proyecto. Los 100 repositorios externos conservan sus propias licencias; aquí no se redistribuye su código.
