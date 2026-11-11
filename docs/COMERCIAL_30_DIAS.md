# Verdugo Digital — control comercial verificable en 30 días (v0.5)

Objetivo operativo: **al menos seis clientes nuevos de pago declarados en 30 días**, con un objetivo de trabajo de diez. **No existe una probabilidad comprobada del 90%**, ni conciliación de bancos. Toda cifra de ventas en esta versión es una afirmación del operador, vinculada a un registro de pago del núcleo, no un ingreso auditado.

## El flujo mínimo

1. Ingresar prospectos en `core.lead.capture` o aceptar eventos canónicos firmados hacia `lead.capture`; las recepciones públicas requieren una infraestructura de producción que todavía no existe. No se aceptan mensajes no firmados desde formularios públicos.
2. Registrar `contacted`, `meeting_booked`, `meeting_held`, `proposal_sent` o `followup_due` en `commercial-record`, con ID de evidencia interno. Nunca guardar nombres, emails, tokens ni URLs con credenciales en `evidence_ref`.
3. Registrar un pago declarado en `core.payment.record` con `dataset=real` y referencia privada. Para declarar `won`, el registro comercial debe incluir el `payment_id` de ese mismo prospecto y dataset. Verdugo comprueba la existencia y correspondencia local, **no la realidad del depósito**.
4. Consultar `commercial-report` y `commercial-next` desde CLI o las herramientas MCP. La lista de seguimiento no envía emails ni hace llamadas.
5. Antes de hablar de dinero comprobado: incorporar verificación bancaria y conciliación contable de montos, devolución, impuestos y comisiones. No contamos ninguna demostración como venta.

## Ejecución local en la rama de desarrollo

```bash
python -m verdugo init --out verdugo.local.json
# La configuración inicial trae todos los servicios y entradas de eventos deshabilitados.
python -m verdugo --config verdugo.local.json commercial-report
python -m verdugo --config verdugo.local.json commercial-next
```

Registrar acciones con JSON controlado por un operador:

```json
{
  "event_id": "empresa-001-contacto-01",
  "lead_id": "empresa-001",
  "kind": "contacted",
  "channel": "outbound",
  "evidence_ref": "crm:nota-1001"
}
```

```bash
python -m verdugo --config verdugo.local.json commercial-record @evento.local.json
python -m verdugo --config verdugo.local.json commercial-record @evento.local.json --execute
python -m verdugo --config verdugo.local.json commercial-report '{"dataset":"real","window_days":30,"goal_min":6,"goal_target":10}'
```

El `lead_id` debe existir primero en el mismo tenant. El periodo es una ventana móvil medida con la fecha de **registro en el servidor**, no una fecha libre que pueda enviarse como parámetro. Por defecto se observan 30 días. El canal es inmutable por prospecto para impedir reatribuciones oportunistas. Repetir el mismo `event_id` con el mismo contenido devuelve replay; cambiarlo produce error. `won` y `lost` son terminales.

Los canales aceptados son `referral`, `partner`, `outbound`, `organic`, `paid`, `other`; son etiquetas explícitas, no inferencia causal. Los hitos aceptados son `contacted`, `meeting_booked`, `meeting_held`, `proposal_sent`, `followup_due`, `won`, `lost`. Un `followup_due` usa fecha UTC `YYYY-MM-DD`. La hora y el huso no se infieren. Un evento con la misma fecha no figura como atrasado hasta el siguiente día UTC.

## Métricas y límites

- `reported_paid_clients`: prospectos distintos con hito `won` y un pago **declarado** previamente. No representa clientes bancariamente conciliados.
- `reported_receipts_by_currency_minor`: los pagos referenciados por esos hitos, como montos enteros en unidades menores de cada moneda; no se mezclan monedas ni se declara utilidad.
- `stage_leads`: prospectos distintos con cada hito dentro de la ventana; los hitos no son una secuencia estricta ni un embudo causal.
- `reported_paid_by_channel`: atribución declarada, un solo canal fijo por prospecto. No es incremento causado por publicidad.
- `gap_to_min` y `gap_to_target`: diferencia entre el objetivo configurado y el número de clientes declarados. No estiman la probabilidad de cumplirlo.
- `commercial_success_probability`: `null`. Solo podrá calcularse tras definir cohortes, tasas observadas, incertidumbre y un modelo validado con datos suficientes.
- `commercial-next`: prospectos abiertos ordenados por vencimiento, sin hacer contactos ni modificar agendas. Incluye prospectos capturados sin un evento comercial (`untracked`) para evitar olvidarlos.

Todos los datos se guardan en la base SQLite local, con separación lógica por tenant. No hay permisos remotos IAM, aceptación de consentimiento verificada, CRM en vivo ni aplicación web accesible desde Internet. El operador debe cumplir requisitos de privacidad, autorización y conservación de datos en el entorno de despliegue.

## Prueba de aceptación exigida para avanzar

- Suites locales y CI completas, con datos sintéticos, escenarios duplicados y carreras concurrentes.
- Un recorrido real autorizado: prospecto con consentimiento → CRM → seguimiento → propuesta → pago real → conciliación independiente → reporte. No se ha ejecutado aún.
- Cálculo por cliente de costos de adquisición, entrega, soporte, devoluciones e impuestos antes de decir que el sistema es rentable.
- Solo después de períodos suficientes y validación fuera de muestra discutir un objetivo probabilístico de 90%.

El sistema no envía mensajes, no contrata publicidad y no gasta dinero por ejecutar estos comandos. El estado `real` significa **entorno declarado por el operador**, no ingreso bancario probado.
