# Evidencia local de esta entrega

Fecha: 2026-11-11. Runtime observado: Python 3.13.5. Comando: `python -m unittest discover -s tests -v`.

**64 pruebas aprobadas; cero fallos.** También se ejecutaron compilación, demo completa y comparación exacta de los 100 repositorios contra `Nexus_100_repos_evidencias.json` del paquete original.

Cobertura funcional probada: inventario/estado veraz, 12 recetas API y 14 acciones, preview sin red, límites de parámetros, versiones/configuración/licencias, secretos ausentes, aprobación exacta y por lote, expiración, cambio de credencial, incertidumbre después de escritura, repetición tras reinicio, reclamación concurrente única, separación entre tenants/datasets/monedas, pagos duplicados, evidencia requerida, DAG/ciclos/referencias, pausa y reanudación, negociación MCP/stdio real, destinos prohibidos y una llamada HTTP local real con rechazo de redirecciones.

Los tests de proveedores usan fixtures; el servidor HTTP es local y ficticio. **Ninguno de los 12 servicios se validó en vivo, y no se ejecutaron los otros 88 proyectos.** Una prueba local del transporte no es una integración end-to-end contra el producto real.

Esta evidencia no es una auditoría exhaustiva de seguridad, cobertura formal, prueba de carga, revisión jurídica ni certificación de producción. La configuración de CI se incluye separadamente; su ejecución debe comprobarse en GitHub, no deducirse de este documento.
