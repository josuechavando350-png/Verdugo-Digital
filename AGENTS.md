# Operación de Verdugo Digital

Nombre del producto: Verdugo Digital. No renombrarlo como Revenue OS.

Antes de cambiar código: ejecutar `python -m unittest discover -s tests -v`, leer README y consultar `python -m verdugo --state :memory: status`.

No confundir 100 entradas de catálogo con 100 adaptadores ejecutables. `verdugo/catalog.py` es el catálogo aprobado; `verdugo/adapters.py` es la lista real de acciones externas implementadas. Una integración no soportada debe devolver error, nunca éxito de prueba como resultado productivo.

Usar un flujo mediante CLI/MCP en lugar de operar servicios por separado. Mantener tenant fijo y credenciales por empresa. No leer secretos ajenos a la tarea ni guardarlos en Git. No exponer el proceso local como servidor público. No añadir comandos arbitrarios, navegación autónoma a destinos no autorizados ni herramientas de autoaprobación al MCP.

Para servicios nuevos: confirmar documentación oficial y versión, implementar una acción delimitada y su transformación, agregar pruebas de contrato, probar en sandbox autorizado, documentar costes/condiciones y registrar evidencia. No clonar/ejecutar cien proyectos automáticamente ni aceptar licencias comerciales en nombre del usuario.

No afirmar despliegues, CI, auditorías o resultados comerciales que no se hayan observado. No estimar 90% de éxito a partir de una demo. Los datos `demo` nunca cuentan como ingresos reales. Un estado de escritura `uncertain` o `running` exige conciliación antes de decidir cualquier reintento.

No aprovisionar hosting de pago, iniciar campañas ni enviar comunicaciones a terceros por el simple hecho de recibir autorización para programar el repositorio.
