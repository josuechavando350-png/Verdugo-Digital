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

## Revisar, respaldar y recuperar

En **Producto → Estado de tu instalación** revisa configuración privada, integridad
de la base, panel compilado, trabajos por conciliar y respaldo reciente. Un resultado
correcto cubre esta instalación; las cuentas reales y las ventas se verifican aparte.

El operador puede marcar la confirmación y pulsar **Crear respaldo local**. Incluye
configuración y datos de todos los clientes, sin cifrar. El resultado indica dónde
se guardó. No lo subas a Git. Conserva aparte las claves de variables de entorno y
los perfiles; la copia no los incluye. Para protección ante pérdida del equipo,
conserva también una copia cifrada fuera de él.

La recuperación se hace fuera del panel. Detén panel, ingress y workers, verifica
la copia y usa un destino nuevo dentro de una carpeta privada:

```sh
python3 -m verdugo verify-product-backup --directory ~/.verdugo/respaldos.local/ID
python3 -m verdugo restore-product --from ~/.verdugo/respaldos.local/ID --to ~/.verdugo/recuperado
python3 -m verdugo restore-product --from ~/.verdugo/respaldos.local/ID --to ~/.verdugo/recuperado --execute
VERDUGO_HOME="$HOME/.verdugo/recuperado" bash scripts/activar.sh --panel --instalar
```

Sustituye `ID` por la carpeta indicada al guardar. La vista previa no cambia nada.
La recuperación conserva pagos y ventas, apaga servicios y exige revisar trabajos
inciertos. No sobrescribe la base original ni reanuda actividad externa. Comprueba
los datos antes de encender servicios. No operes dos copias a la vez.

Para actualizar, conserva el paquete anterior y un respaldo antes de detener la
operación. Extrae la versión nueva en otra carpeta, instálala y revisa los datos.
Si falla, recupera la copia en un directorio nuevo para usar la versión anterior;
contrasta los cambios posteriores al respaldo antes de continuar. Las instrucciones
completas están en `docs/ENTREGA_LOCAL.md` dentro del paquete.
