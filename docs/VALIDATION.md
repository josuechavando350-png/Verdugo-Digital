# Evidencia de Verdugo Digital v0.3.0

Fecha: 2026-11-11. Runtime local: Python 3.13.5.

`python -m unittest discover -s tests -v`: **166 pruebas aprobadas, cero fallos**: 110 existentes y 56 nuevas. Se ejecutan también compilación, demo sintética y controles de inventario. GitHub Actions se consulta por commit: su resultado no se deduce de las pruebas locales.

Inventario: 100 proyectos; 18 adaptadores HTTP / 20 acciones externas acotadas; 6 acciones del núcleo; 12 herramientas MCP; 82 proyectos sin adaptador; **0 proveedores validados en vivo**.

Cobertura nueva: autenticación de cuerpo/tenant/fuente/fecha, firmas inválidas, JSON duplicado, límites, campos prohibidos, deduplicación concurrente, atomicidad inbox/cola/auditoría, rotación de secreto, cupos, reinicio, dos workers disputando un trabajo, lease vencido y confirmación antigua, espera/reintentos limitados, bloqueo por aprobación y cambio de ruta, separación de empresas, confidencialidad de metadatos y roles.

Se comprueba recuperación tras una creación completada antes de confirmar el trabajo sin duplicar POST; una escritura interrumpida permanece `running` y no se reenvía. Una atestación humana sintética de `uncertain` permite reanudar el puente sin reenviar la primera creación. El código no verifica en vivo esa evidencia. Se prueba que una actualización fallida revierte también el registro de conciliación.

Prueba HTTP completa: petición firmada a receptor loopback → cola persistente → aprobación → worker → dos rutas HTTP sintéticas → dos identidades. La repetición del evento no reenvía creaciones. Otro caso usa CLI como proceso real, y MCP marca bloqueos como incompletos. Se crea una base con el esquema previo v0.2 y se verifica la adición de tablas conservando registros/aprobaciones.

Límites: no es auditoría exhaustiva, prueba de carga, revisión jurídica, instalación de 100 proyectos, validación de firmas nativas de proveedores, despliegue ni evidencia de ingresos. HTTP local no apto para exposición pública. No hay IAM real, supervisor 24/7, sincronización bidireccional o recuperación automática de acciones `running`.
