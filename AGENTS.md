# Operación de Verdugo Digital

Nombre del producto: Verdugo Digital. No renombrarlo como Revenue OS.

Antes de cambiar código: ejecutar `python -m unittest discover -s tests -v`, leer README y consultar `python -m verdugo --state :memory: status`.

No confundir 100 entradas de catálogo con 100 adaptadores ejecutables. `verdugo/catalog.py` es el catálogo aprobado; `verdugo/adapters.py` es la lista real de acciones externas implementadas. Una integración no soportada debe devolver error, nunca éxito de prueba como resultado productivo.

Usar un flujo mediante CLI/MCP en lugar de operar servicios por separado. Mantener tenant fijo y credenciales por empresa. No leer secretos ajenos a la tarea ni guardarlos en Git. No exponer el proceso local como servidor público. No añadir comandos arbitrarios, navegación autónoma a destinos no autorizados ni herramientas de autoaprobación al MCP.

Para servicios nuevos: confirmar documentación oficial y versión, implementar una acción delimitada y su transformación, agregar pruebas de contrato, probar en sandbox autorizado, documentar costes/condiciones y registrar evidencia. No clonar/ejecutar cien proyectos automáticamente ni aceptar licencias comerciales en nombre del usuario.

No afirmar despliegues, CI, auditorías o resultados comerciales que no se hayan observado. No estimar 90% de éxito a partir de una demo. Los datos `demo` nunca cuentan como ingresos reales. Un estado de escritura `uncertain` o `running` exige conciliación antes de decidir cualquier reintento.

No aprovisionar hosting de pago, iniciar campañas ni enviar comunicaciones a terceros por el simple hecho de recibir autorización para programar el repositorio.

Antes de activar un proveedor real: ejecutar `pilot` con contrato revisado, revisión de licencia, versión y permisos mínimos. `pilot` solo observa formas de respuesta; no certifica producción. Copias SQLite con `backup-local` contienen datos personales sin cifrar y nunca se incorporan a Git. Restaurar exige revisión offline de escrituras inciertas.

La v0.7 añade operación comercial local `sales-intake` y `sales-desk`. No marcar un contacto como `contacted` al registrarlo: solo `identified`. Los datos demo no cuentan como real. Las cargas desde JSON local pueden incluir PII; no guardar esos archivos en Git ni imprimirlos en el informe.

Para la trazabilidad de GitHub (v0.8, ampliada en v0.14): sources/parts/ debe contener exactamente 33 archivos JSON, 10 fuentes por archivo salvo el último (2), alineadas a las 322 entradas de verdugo/catalog.py y con SHA verificable. El reporte source_evidence es solo lectura, no supone licencia aceptada, código vendorizado, adaptación funcional ni proveedor validado. Cualquier cambio exige pruebas de integridad y jamás ejecuta fuentes externas automáticamente.

Las recetas v0.10 están en verdugo/local_extended.py y comparten Engine, local_runtime y worker. No aprobar supuestos causales por defecto ni presentar precisión léxica como verdad semántica. dlt/MLflow usan almacenes temporales; únicamente Engine conserva el resultado. La aceptación debe ejecutar todas las bibliotecas con resultados específicos y reanudación verificada; no marcar 41 proyectos como certificados en producción.

La v0.12 incorpora siete operaciones de metadatos con proyección segura en read_contracts. Nunca almacenar cargas crudas de Nango, Trigger, Documenso, Airbyte, GrowthBook, Infisical u OpenMeter en resultados SQLite. Airbyte solo Cloud v1 y OpenMeter solo OSS v1, declarados explícitamente; validar esquema y prohibir cambios de ruta/credencial desde parámetros. Un GET exitoso no certifica a un proveedor ni una exportación completa.

La v0.13 usa marketing_reads para seis lecturas. Los POST son exclusivamente Plausible stats, Matomo VisitsSummary.get y la query estática de productos Saleor. No aceptar código GraphQL, métodos, tokens, URLs o selección de tenant desde params. Matomo token_auth se serializa en un cuerpo privado; el fingerprint Ghost vincula la clave origen, no el JWT efímero. No guardar payloads completos. Verificar fechas/sitio/métricas y preservar aprobaciones de escrituras anteriores. Ninguna prueba HTTP sintética certifica producción.

La v0.14 une el catálogo en 322 entradas: 300 con licencia libre y 22 excluidas por licencia. sources/licenses.json es la evidencia técnica de licencia por commit fijado y verdugo/license_policy.py la valida y falla cerrada. Solo MIT, Apache-2.0, BSD, ISC, CC0, Unlicense y PostgreSQL cuentan como libres; un proyecto nuevo con AGPL/GPL/LGPL, Elastic, SUL, BUSL, FSL, licencia propia o sin licencia no entra al portafolio. No agregar excepciones `license_policy_exception` en nombre del usuario ni en plantillas; solo el operador las escribe en su configuración privada. La clasificación no es revisión legal: `license_review` permanece `pending`. Registrar un proyecto no es integrarlo: los proyectos sin adaptador deben seguir devolviendo error.

La v0.15 añade sources/connections.json (tipo de conexión de las 322 piezas, validado por verdugo/connections.py) y service_reads con 15 lecturas GET. El estado `conectado` se calcula desde el código y nunca se escribe en el mapa. Para un conector nuevo: tomar ruta, autenticación y forma de respuesta del código u OpenAPI en el commit fijado, guardar solo recuentos, fijar el origen oficial en proveedores en la nube y no aceptar URL, método, consulta ni credencial desde params. La consulta de ClickHouse es fija; CrowdSec actualiza la hora de última consulta del bouncer. Ninguna prueba sintética certifica un proveedor real.
