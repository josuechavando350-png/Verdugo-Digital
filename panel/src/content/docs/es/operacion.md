---
title: Operación local
---

[Volver al panel](/)

## Acceso

La primera vez usa `bash scripts/activar.sh --panel --instalar` (Python 3.12 y Node 24.22.1).
Después inicia `bash scripts/activar.sh --panel`. Para consulta, agrega `--viewer`.
Copia el token del archivo privado que indica la terminal. No lo pongas en la URL.
En Codespaces deja el puerto reenviado en **Private**. El proceso escucha solo en 127.0.0.1.

## Clientes

En Clientes abre «Crear cliente», escribe un identificador y confirma.
También puedes usar `tenant-add cliente-demo --execute` desde la terminal.
En Clientes, registra su interruptor: comienza apagado. Registrar pago, Pausar y Reanudar
requieren operador y una confirmación. Un pago es una declaración, no una revisión bancaria.
El rol viewer consulta; no tiene botones ni permisos para modificar clientes.

## Anuncios

Selecciona el cliente y el conjunto de datos. En Anuncios abre «Importar reporte de anuncios»,
elige Google o Meta, la moneda y un CSV de hasta 5 MiB. Revisa el periodo y los totales;
marca la confirmación y guarda. La vista previa no modifica métricas. Cambiar cliente,
datos, moneda o archivo exige una nueva vista previa. Una reimportación no duplica.
La CLI `ads-import` sigue disponible con vista previa y `--execute` para guardar.
Nunca agregues CSV reales al repositorio. El panel compara periodos, grafica métricas y
exporta el reporte. Las conversiones no son clientes: el costo por cliente usa ventas
pagadas declaradas del canal paid. Las proyecciones no garantizan ingresos.

## Prospectos, seguimientos y ventas

En Embudo, «Registrar prospecto» guarda su identificador, nombre y correo en tu
base privada. Comienza identificado: no se marca como contactado ni se envía nada.
Declara el canal y una referencia de evidencia sin URLs ni datos personales.

En «Registrar avance o venta» elige una etapa. Un seguimiento usa una fecha UTC;
la lista muestra los pendientes y vencidos. Para una venta, declara importe,
costos, moneda y referencia. El pago y la venta se guardan juntos o se revierten
juntos si algo falla. Las ventas de demostración nunca aparecen como reales.
Al cambiar cliente o conjunto de datos, se descartan los formularios sin guardar.

## Producto

Conectada significa que existe una operación, no que el proveedor esté desplegado o
verificado. Disponible significa que coinciden las versiones locales. Las piezas sin
una función apropiada en el panel permanecen sin integrar. El inventario se comprueba
con el manifiesto y sus pruebas; no se suman importaciones vacías.

## Privacidad

No se envía telemetría ni se usan CDNs. La sesión y los datos consultados están en
memoria del navegador. Al salir se vacían. El reporte exportado es privado: guárdalo
fuera de Git. No hay un MCP remoto ni hosting público.
