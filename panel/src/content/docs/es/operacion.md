---
title: Operación local
---

[Volver al panel](/)

## Acceso

Inicia `python -m verdugo --config ~/.verdugo/config.json --state ~/.verdugo/estado.sqlite panel`.
Copia el token del archivo privado que indica la terminal. No lo pongas en la URL.
En Codespaces deja el puerto reenviado en **Private**. El proceso escucha solo en 127.0.0.1.

## Clientes

Crea el tenant con `tenant-add cliente-demo --execute` desde la terminal.
En Clientes, registra su interruptor: comienza apagado. Registrar pago, Pausar y Reanudar
requieren operador y una confirmación. Un pago es una declaración, no una revisión bancaria.
El rol viewer consulta; no tiene botones ni permisos para modificar clientes.

## Anuncios

Usa `ads-import @reporte.csv --platform google` o `--platform meta` para revisar el archivo.
Agrega `--execute` para guardarlo y `--dataset demo` si los datos son sintéticos.
Nunca agregues CSV reales al repositorio. El panel compara periodos, grafica métricas y
exporta el reporte. Las conversiones no son clientes: el costo por cliente usa ventas
pagadas declaradas del canal paid. Las proyecciones no garantizan ingresos.

## Producto

Conectada significa que existe una operación, no que el proveedor esté desplegado o
verificado. Disponible significa que coinciden las versiones locales. Las piezas sin
una función apropiada en el panel permanecen sin integrar. El inventario se comprueba
con el manifiesto y sus pruebas; no se suman importaciones vacías.

## Privacidad

No se envía telemetría ni se usan CDNs. La sesión y los datos consultados están en
memoria del navegador. Al salir se vacían. El reporte exportado es privado: guárdalo
fuera de Git. No hay un MCP remoto ni hosting público.
