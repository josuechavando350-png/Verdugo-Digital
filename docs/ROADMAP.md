# Continuación verificable

## Entregado hasta v0.3.0

100 IDs registrados, 18 adaptadores HTTP / 20 acciones delimitadas, 6 acciones comerciales del núcleo y 12 herramientas MCP. Flujos por CLI/MCP, aprobación de escrituras por lote, identidades canónicas, diagnóstico central y persistencia local.

La v0.3 añade recepción HMAC de eventos canónicos, inbox/cola atómicos, deduplicación, cupos por fuente, leases con rechazo de confirmaciones antiguas, reintentos acotados y bloqueo ante incertidumbre. Añade conciliación humana de `uncertain` para creaciones Twenty/Chatwoot, sin reenvío. 166 pruebas locales. No se instalaron productos externos ni se validaron en vivo.

## Siguiente prioridad técnica

1. Recuperación verificable de procesos muertos y acciones `running`, sin asumir ausencia de efectos; verificación de evidencia directamente contra APIs autorizadas. No resetear intentos ni claves para aparentar recuperación.
2. Ingreso productivo con firmas nativas por proveedor, TLS, IAM, cuotas de solicitudes/disco, retención, paginación completa y observabilidad. El receptor HTTP actual es exclusivamente local de aceptación.
3. Suscripciones y sincronización bidireccional con versiones de registros, prevención de bucles y resolución de conflictos. Un sobre canónico no es un adaptador de webhook nativo.
4. Worker supervisado, heartbeat, pruebas de carga/fallos prolongados, respaldo/restauración y evaluación de un backend multiworker productivo. SQLite compartido en un host no acredita escalabilidad horizontal.

## Primera validación externa

Se necesita un host autorizado, versiones/ediciones verificadas, cuentas de prueba, secretos fuera de Git y presupuesto definido. No se ha contratado infraestructura. Verificar esquema y permisos de Twenty/Chatwoot; ejecutar lectura, creación y recuperación en sandbox. Guardar evidencia privada e IDs, sin publicar contactos ni credenciales. Las pruebas locales no sustituyen esta puerta.

## Los otros 82 proyectos

Cada proyecto requiere su integración apropiada: API, biblioteca, proceso, pipeline o control de infraestructura. No inventar una API uniforme para bibliotecas que no la tienen. Declarar acciones, costos, permisos, licencia/edición, versiones, contratos, pruebas y evidencia real. Los sustitutos se eligen por contexto; no deben ser fuentes de verdad simultáneas para el mismo dato sin resolver conflictos.

## Puertas comerciales

Definir éxito, conseguir clientes pagados, conciliar cobros/costos, comprobar capacidad de entrega y retención. Ni el catálogo, ni las pruebas, ni pagos declarados demuestran rentabilidad o probabilidad del 90%. No habilitar servicios solo para aumentar un contador.
