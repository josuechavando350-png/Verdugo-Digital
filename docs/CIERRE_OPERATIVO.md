# Revisión operativa de Verdugo Digital

Base: `edbe8b94e85073dbea687868a293447385f15272`, después de integrar los lotes A y B.
La suite inicial pasó sus 763 pruebas antes de modificar código.

## Motor

- El interruptor ahora se comprueba también al registrar prospectos, registrar
  etapas comerciales, consultar el embudo y recuperar seguimientos por CLI/MCP.
  Se vuelve a comprobar dentro de la transacción, incluso al repetir un registro.
  Antes estas entradas directas podían evitar el control de Engine.preflight.
- El alta de un tenant exige operador, conserva la configuración existente y
  serializa las altas con un bloqueo local y sustitución atómica. Rechaza enlaces
  simbólicos. Los nuevos tenants exigen registro y periodo pagado antes de operar;
  la cuenta propia y las configuraciones antiguas conservan su compatibilidad.
- La importación desde bytes y desde archivo usa el mismo parser y la misma tabla.
  La vista previa devuelve agregados y una huella ligada a bytes, tenant, plataforma,
  moneda y conjunto real/demo. Cambiar el archivo o su destino invalida la confirmación.
  El CSV, la ruta y los nombres de campaña no se conservan.
- Los diagnósticos administrativos siguen disponibles para un cliente apagado;
  su informe comercial se presenta como bloqueado, sin sustituir datos por ceros.
- Se corrigió el formato de fechas de pago y el resumen del activador: una ruta
  implementada no se anuncia como instalada.

Validación local: 772 pruebas del núcleo. Las nueve nuevas comprueban el bloqueo
real por CLI/MCP, replay, alta concurrente, roles, enlaces, estado inicial, huella
de importación y privacidad. CI debe comprobar los tres workflows del commit final.

## Qué significa terminar

El catálogo sigue en 300 libres: 244 con operaciones de motor, 13 componentes con
uso y prueba en el panel, 43 piezas de construcción sin uso justificado. No se
añaden importaciones decorativas ni se elimina el denominador para declarar 100%.
La tabla de las 43 decisiones está en [LOTE_B_300.md](LOTE_B_300.md).

Las pruebas usan datos sintéticos. Cuentas reales, permisos, versiones de las
instancias y resultados comerciales requieren comprobación en el entorno del
operador. `live_verified` sigue en 0; un CSV real tampoco certifica un proveedor.
No hay captación autónoma, promesa de clientes, comunicaciones, anuncios pagados
ni despliegue público como consecuencia de esta revisión.
