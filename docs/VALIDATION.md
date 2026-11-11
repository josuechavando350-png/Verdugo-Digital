# Evidencia de Verdugo Digital v0.2.0

Fecha: 2026-11-11. Runtime local: Python 3.13.5.

`python -m unittest discover -s tests -v`: **110 pruebas aprobadas, cero fallos**. Incluye las 64 anteriores y 46 nuevas. Se ejecutaron también `python -m compileall -q verdugo`, la demo comercial sintética y los controles de catálogo.

Inventario comprobado: 100 proyectos, 18 adaptadores HTTP, 20 acciones externas acotadas, 6 acciones del núcleo, 8 herramientas MCP, 82 proyectos sin adaptador y **0 servicios externos validados en vivo**.

Nuevas pruebas: contratos de las seis recetas, autenticación Frappe/Langfuse/Chatwoot, paginación, rechazo de recheck y selectores de cuenta inyectados, cambio de autenticación/red/contrato invalidando planes, extracción de ID sin evaluación de expresiones, respuestas sin ID o HTTP 202 inciertas, definición inmutable del flujo, preflight de credenciales dependientes, identidad/tenant/dataset/origen y conflictos, pausa/aprobación/reinicio y diagnóstico central con resultados honestos.

Se ejecutó el puente de contactos sobre un servidor HTTP sintético local: creó un registro ficticio en cada ruta, guardó dos alias y la repetición no reenvió las escrituras. También se simuló un fallo del segundo proveedor y se comprobó que no duplicaba el primero ni reintentaba el resultado incierto. Esto prueba el código y el transporte bajo fixtures, no Twenty o Chatwoot reales.

CLI/MCP identifican bloqueos como ejecución no completada. Se probó que una migración aditiva conserva registros y ejecuciones, aunque la compatibilidad de planes externos de v0.1 no está garantizada por los nuevos fingerprints.

No es auditoría exhaustiva de seguridad, revisión jurídica, prueba de carga, despliegue ni evidencia de ingresos. GitHub Actions debe consultarse por separado para el commit publicado; no se infiere su resultado a partir de las pruebas locales.
