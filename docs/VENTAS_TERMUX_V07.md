# Verdugo Digital v0.7 — Operación comercial local en Termux

**No son cien servicios instalados.** Esta función de primera parte funciona sin proveedores, redes, claves ni suscripciones, integrada en el mismo SQLite del resto de Verdugo. No envía mensajes ni verifica cobros bancarios.

## Actualizar Termux

```sh
cd ~/Verdugo-Digital
git pull --ff-only origin feat/verdugo-unified-core
python -m unittest discover -s tests -q
python -m verdugo sales-desk
```

Con una base sin datos, el informe mostrará **0 clientes declarados de pago** y brechas de 6 y 10. Esto no implica que existan cierres o que haya una probabilidad demostrada del 90%.

## Captura y seguimiento en una sola operación

`sales-intake` registra identidad, canal y el próximo seguimiento en una **transacción local**. La etapa `identified` significa solamente que se registró un prospecto: no implica que se le contactó. Cuando exista contacto real, hay que anotarlo por separado con `commercial-record`.

```sh
# Primero: datos ficticios que no cuentan como ingresos reales.
python -m verdugo sales-intake @examples/sales-intake.synthetic.json
python -m verdugo sales-intake @examples/sales-intake.synthetic.json --execute
python -m verdugo sales-desk '{"dataset":"demo"}'
```

Para datos reales no modifiques el ejemplo dentro del repositorio. Prepara un JSON privado fuera de Git, con un `lead_id` propio, nombre y correo proporcionados con autorización, `dataset: "real"`, canal (`referral`, `partner`, `outbound`, `organic`, `paid`, `other`) y una referencia a evidencia privada que **no incluya emails, URLs ni claves**. `followup_due` es opcional y debe usar fecha UTC `YYYY-MM-DD`.

No escribas nombres, correos o secretos directamente en argumentos del shell: usa `@archivo.local.json` con permisos `0600`. El archivo de muestra es sintético. Repetir exactamente el mismo ingreso no duplica datos; cambiar identidad, canal o fecha inicial con el mismo identificador queda bloqueado. Para modificar un seguimiento real se registra un nuevo evento `followup_due` con otra clave, no se reescribe el ingreso.

```sh
python -m verdugo sales-intake @/ruta/privada/prospecto.local.json
python -m verdugo sales-intake @/ruta/privada/prospecto.local.json --execute
python -m verdugo sales-desk
```

Si se rechaza una de las etapas, también se revierte el ingreso completo. El proceso no deduplica por correo cuando se introducen distintos `lead_id`; ese control de identidad sigue pendiente.

## Una vista diaria

```sh
python -m verdugo sales-desk
python -m verdugo sales-desk '{"dataset":"demo","limit":10}'
```

Incluye progreso de 30 días hacia 6 clientes mínimos y 10 de objetivo **declarados**, hitos por canal, cola local, trabajos que requieren conciliación y prospectos con seguimiento pendiente. No devuelve nombres/correos. Los registros personales continúan en SQLite y requieren seguridad del dispositivo y respaldos adecuados.

`commercial-record` permite registrar reunión, propuesta, cierre y pérdida. Un cierre `won` requiere una referencia existente a `core.payment.record` del mismo cliente/dataset, pero ese pago es **una declaración del operador y no una conciliación bancaria**. No se calculan causalidad publicitaria, costos completos ni una probabilidad validada del 90%.

## Seguridad y límites

- No activa conectores externos, campañas, pagos, comunicaciones ni procesos permanentes.
- Los datos de `demo` y `real` no se mezclan. Las empresas se separan lógicamente, sin IAM de producción.
- Se rechazan claves de eventos duplicadas, canales contradictorios y escrituras parciales.
- El MCP expone `verdugo_sales_intake` y `verdugo_sales_desk` bajo los mismos roles. No habilita autoaprobaciones.
- No hay aún sincronización bidireccional ni acceso remoto de este chat al MCP. Termux no garantiza servicio 24/7.
- Permanecen **100 proyectos catalogados, 22 adaptadores HTTP, 78 sin adaptador, 0 proveedores externos validados en vivo**.

Las pruebas verifican idempotencia, concurrencia, rollback, separación entre empresas/datasets, privacidad del resumen y CLI/MCP. Una prueba verde no demuestra ventas reales.
