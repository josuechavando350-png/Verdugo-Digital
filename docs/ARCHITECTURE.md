# Arquitectura inicial

`CLI / cliente MCP → Engine → validación y políticas → plan → aprobación cuando corresponde → adaptador → API autorizada → resultado → estado y eventos`

El motor es el punto único de ejecución. El catálogo de 100 proyectos tiene IDs estables y dominios comerciales. Las bibliotecas, servicios, CLIs y herramientas de CI no se tratan como aplicaciones idénticas: cada una necesitará un adaptador apropiado. En esta entrega hay 18 adaptadores HTTP, no 100 procesos en ejecución.

## Contrato de una acción

Objeto con exactamente `service`, `operation`, `params`, `key`. No admite sobrescribir tenant, origen, cabeceras, rol ni shell. Una clave tiene hasta 100 caracteres alfanuméricos, guion o guion bajo. Su fingerprint incluye contexto del tenant, solicitud normalizada y vínculo a credencial/versionado.

`plan` persiste la descripción pero no hace red. `execute` es falso por defecto. Las lecturas necesitan configuración explícita; las escrituras remotas necesitan un plan aprobado, de un solo uso y con expiración. `approve-batch` aprueba un conjunto exacto de planes en una transacción local. Los planes dinámicos que dependen de resultados previos solo se pueden aprobar después de conocer esos valores.

## Conexión entre sistemas

Los workflows declaran pasos, `depends_on` y referencias `{"$ref":"step.field"}`. El motor ordena el DAG, rechaza ciclos, resuelve datos y ejecuta cada paso con clave derivada de workflow/paso. Al reanudar utiliza resultados persistidos. Se validan adapters y puertas de configuración antes del primer paso; además se preparan todas las acciones con parámetros estáticos antes de ejecutar. Valores dependientes se validan cuando existen.

Las recetas transforman una persona canónica (`first_name`, `last_name`, `email`) en los formatos específicos de Twenty y Chatwoot. Otros adaptadores exponen lecturas limitadas; las respuestas siguen en formato del proveedor, no se presume normalización semántica total. Algunas rutas solo implementan la primera página: nunca se presentan como una extracción completa.

## Estado, evidencia e idempotencia

SQLite contiene planes, ejecuciones, eventos y registros comerciales. Todas las consultas llevan tenant. Los estados son `planned`, `awaiting_approval`, `running`, `succeeded`, `failed`, `uncertain`; un workflow puede quedar `paused`. Una reclamación de ejecución se hace bajo `BEGIN IMMEDIATE` para evitar envíos simultáneos con la misma clave. Los efectos locales y su cierre se confirman juntos.

No hay transacción distribuida entre proveedores. Una caída después de un POST puede dejar un resultado desconocido. Se detiene, no se duplica el POST. No existe todavía una consola de conciliación de estados inciertos. Los eventos son persistentes pero no inmutables contra el administrador del host.

## Frontera de confianza

Esta versión es para un operador/host confiable. Los roles son permisos del proceso, no identidad autenticada remotamente. Quien controla los archivos, el código o SQLite puede modificarlos. Para producción multiempresa se requiere identidad/SSO, autorizaciones independientes, secretos separados, backups probados, cifrado de almacenamiento, retención y pruebas de carga. El aislamiento lógico probado no certifica aislamiento hostil entre clientes del mismo host.

El transporte fija la IP resuelta para cada conexión y conserva la verificación TLS del hostname. Bloquea destinos no públicos por defecto, metadatos link-local, redirecciones y proxies de entorno. Red privada HTTPS requiere opt-in del administrador; HTTP se limita a loopback explícito para pruebas. Hay timeout de socket de 10 segundos y tamaño máximo de respuesta de 1 MiB, no un SLA de latencia extremo a extremo. No ejecutar shell desde datos de proveedores.

Credenciales solo desde variables `VERDUGO_*`, nunca desde parámetros del asistente. Los resultados se redactan por claves sensibles y coincidencias de secretos conocidos. Esto no elimina toda PII ni sustituye una política de privacidad. La base almacena datos comerciales; está fuera de Git y debe protegerse a nivel de host.

## Economía

Se almacenan importes enteros y se filtra por moneda. `real` significa datos declarados para operación real, no prueba bancaria. `reconciled_receipts_minor` y `commercial_success_probability` permanecen nulos mientras no exista conciliación/modelo validado. Costos fijos, impuestos, devoluciones, atribución e incrementalidad todavía no se calculan.

## Extensión v0.2

`bridge → workflow → Engine` reutiliza exactamente las aprobaciones y ejecuciones de CLI/MCP. `identities` tiene unicidad por tenant/servicio/ámbito/ID remoto y por ejecución fuente. Solo se acepta una fuente exitosa, del tenant correcto, con servicio/acción de creación correctos, email coherente con el contacto y contrato de respuesta explícito. El ámbito combina origen y workspace/cuenta; no se asume que dos IDs iguales de diferentes instancias son la misma persona.

`workflow_manifests` fija el hash de la definición al planificar. Antes del primer efecto se comprueban credenciales y destinos también de los pasos con valores dependientes. Los valores dinámicos aún requieren validación cuando se resuelven; no hay transacción distribuida.

`doctor` solo prepara o ejecuta acciones GET de SPECS, sin seguir URLs de paginación devueltas por proveedores y sin transformar datos externos en instrucciones. Su resumen excluye el cuerpo de las respuestas; los resultados permanecen en el almacenamiento local sujeto a la política de privacidad del host. Los errores y estados inciertos no se reintentan automáticamente.
