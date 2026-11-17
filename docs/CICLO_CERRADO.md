# Ciclo cerrado: del clic al cliente que pagó

Verdugo enlaza una referencia recibida por WhatsApp con un prospecto, su pago
registrado y un GCLID encontrado en Google Ads. Prepara la conversión con el
importe **recibido**, la moneda y la hora real del pago. El operador decide la
carga. No cambia campañas, presupuestos ni pujas.

Se reutiliza el conector `google-ads`. No se agrega ningún proyecto al catálogo.
El panel muestra el estado; MCP solo añade `verdugo_closed_loop_status`, de lectura.
La carga se hace exclusivamente por CLI con aprobación local separada.

## Primero: una limitación actual de Google

Revisión documental: 16 de noviembre de 2026. Google indica que desde el
15 de junio de 2026 las implementaciones nuevas de conversiones sin conexión
usan Data Manager API. `UploadClickConversions` queda limitado a proyectos que
cumplen su historial de acceso; un proyecto sin solicitudes entre el 17 de
diciembre de 2025 y el 15 de junio de 2026 puede recibir
`CUSTOMER_NOT_ALLOWLISTED_FOR_THIS_FEATURE`. La misma documentación informa del
retiro de developer tokens el 9 de septiembre de 2026.

Por eso **pedir un developer token gratuito no habilita hoy, por sí solo, este
flujo**. La petición original de obtener ese token se debe contrastar con el
acceso vigente de la cuenta/proyecto. Verdugo conserva OAuth + developer token
como exige el conector fijado y no afirma que Google acepte esas credenciales.
No se agregó Data Manager ni se activó ninguna cuenta. Si la cuenta no admite
la ruta solicitada, no activar `upload_access_reviewed`; usar la alternativa
CSV cuando Google la permita. Encontrar el GCLID sigue necesitando acceso de
lectura a `click_view`; el CSV evita la **API de subida**, no ese acceso previo.

Fuentes oficiales:

- [Reglas actuales y requisitos de importación](https://developers.google.com/google-ads/api/docs/conversions/upload-offline).
- [Cambio de acceso para nuevas implementaciones](https://developers.google.com/ads/blog/posts/2026/05/changes-to-offline-click-conversion).
- [Importación manual y plantilla CSV](https://support.google.com/google-ads/answer/7014069?hl=es).
- [Contrato REST de UploadClickConversions v26](https://developers.google.com/google-ads/api/reference/rpc/v26/ConversionUploadService/UploadClickConversions?transport=rest).

## Qué le toca a Josue

1. Verificar el acceso API real de su proyecto con Google, OAuth y permisos
   mínimos. Revisar el estado del developer token histórico; no pagar a un
   intermediario por obtenerlo ni suponer que solicitar uno nuevo basta.
2. Crear en Google Ads **«Cliente que pagó»**, de importación de clics. Verificar
   que sea la acción adecuada para medir pagos, su ventana de conversión,
   moneda y objetivos de puja. Verdugo no crea ni selecciona objetivos de campañas.
   La cuenta que se configura aquí debe ser dueña de la acción; no se implementa
   la selección automática de acciones compartidas de una cuenta administradora.
3. Instalar el fragmento en la web elegida e integrarlo con su banner de
   consentimiento. Nada de esta entrega se instala automáticamente en sitios.
4. Actualizar el aviso de privacidad: identificadores publicitarios, referencia,
   cookie de hasta 90 días, finalidad, destinatario Google y retirada del
   consentimiento. El hash del teléfono sigue siendo un dato seudonimizado;
   no se presenta como anónimo. Documentar el consentimiento antes de enviar
   teléfonos hash y revisar términos/configuración de conversiones mejoradas.
5. Validar con su cuenta y datos autorizados: clic, WhatsApp, alta, pago,
   coincidencia, aprobación, carga y diagnóstico de Google. Conservar esa
   evidencia fuera del repo, sin secretos ni nombres reales en Git.

## Instalar el fragmento

Archivo: [`snippets/ciclo-whatsapp.js`](../snippets/ciclo-whatsapp.js), sin
bibliotecas, 2.517 bytes sin comprimir. Requiere HTTPS y Web Crypto del navegador.
No usa fetch, píxeles ni un servidor de Verdugo. No lee/guarda la atribución ni
modifica enlaces hasta recibir `consent(true)` explícito. Las UTM soportadas son
`utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`.

- **HTML:** copiarlo al mismo sitio y cargar `<script src="/ciclo-whatsapp.js" defer></script>`.
- **WordPress:** cargar el archivo propio con `wp_enqueue_script`, en el pie de
  página. Conectar el evento real del gestor de consentimiento; no editar el núcleo.
- **Next.js:** colocarlo en `public/ciclo-whatsapp.js` y cargarlo con
  `next/script`, estrategia `afterInteractive`, desde un componente cliente.
  El callback `onLoad` debe aplicar el consentimiento actual del banner.

En las tres plataformas, el adaptador del banner debe ejecutar esto **al cargar
el fragmento y cada vez que cambie la decisión**; `permisoPublicidad` debe venir
del banner real, nunca de una constante que acepte por defecto:

```javascript
await window.VerdugoCiclo.consent(permisoPublicidad === true);
```

Si el script aún no está cargado, guardar la decisión en memoria y aplicarla al
terminar su carga. No asumir que el usuario aceptó por visitar la página. Usar
`consent(false)` cuando retire o rechace el permiso: borra la cookie y restaura
los enlaces que el fragmento modificó. Verificarlo también en navegación SPA.

La cookie `verdugo_ciclo` es del host propio, `Path=/`, `SameSite=Lax`, `Secure`
en HTTPS, sin `Domain`. Guarda GCLID/GBRAID/WBRAID/UTM y vencimiento. Una nueva
URL con atribución reemplaza la anterior. Leerla en otra página no prolonga
su vencimiento. El navegador puede eliminarla antes de 90 días.

Con GCLID, el mensaje de `wa.me` o `api.whatsapp.com` termina en `Ref: ABC234`
(ejemplo ficticio). La referencia real son los primeros seis caracteres de
base32 RFC 4648, en mayúsculas, de SHA-256 del GCLID. No se usa base64 ni se
recorta el GCLID. GBRAID/WBRAID sin GCLID se conservan con consentimiento pero
**no generan referencia ni se suben por este flujo**. Un clic anterior a que
termine el hash puede salir sin referencia; no se retrasa ni se bloquea WhatsApp.

Comprobar en el sitio de pruebas: rechazar no crea cookie/ref; aceptar conserva
los parámetros y el texto original; retirar elimina cookie/ref; enlaces
creados dinámicamente funcionan; no aparece ninguna solicitud de red propia
del fragmento. Instalar una copia por página y no cambiar el destino WhatsApp.

## Preparar el tenant privado

Trabajar en el mismo directorio privado de la instalación local. Respaldar el
estado antes de actualizar. No guardar config, entradas de prospectos, planes,
CSV, SQLite ni credenciales dentro de Git. Directorios `0700`, archivos `0600`.
Ejemplo **sintético** del bloque `services.google-ads` de `cliente-demo`:

```json
{
  "enabled": false,
  "license_reviewed": false,
  "version": "f253b400dc5924b731fcb42dbcd99e485200581e",
  "base_url": "https://googleads.googleapis.com",
  "auth_mode": "native_oauth_developer_token",
  "oauth_scope_reviewed": false,
  "token_env": "VERDUGO_CLIENTE_DEMO_GOOGLE_ADS_TOKEN",
  "developer_token_env": "VERDUGO_CLIENTE_DEMO_GOOGLE_ADS_DEVELOPER_TOKEN",
  "closed_loop": {
    "customer_id": "1234567890",
    "conversion_action_id": "123",
    "conversion_name": "Cliente que pagó",
    "account_timezone": "America/Mexico_City",
    "privacy_reviewed": false,
    "upload_access_reviewed": false
  }
}
```

Los valores de revisión empiezan en `false`: el operador los cambia solo al
comprobarlos. El token OAuth debe estar vigente; el conector no hace renovación
automática. `login_customer_id` es opcional dentro de `closed_loop` si requiere
acceso mediante administrador. Cuenta, acción, nombre y zona horaria salen
exclusivamente de este archivo, nunca de params ni del MCP. Usar IDs sin guiones.
Un tenant con suscripción apagada no puede planear, empatar, exportar ni subir.

## Recorrido por CLI y panel

Ejemplos de comandos, con rutas privadas y tenant explícito:

```bash
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" --tenant cliente-demo sales-intake @/ruta-privada/prospecto.json --execute
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" --tenant cliente-demo sales-win @/ruta-privada/pago.json --execute
```

El JSON de alta conserva los campos habituales (`lead_id`, `name`, `email`,
`dataset`, `channel`, `evidence_ref`) y admite `ref_code`, `phone` y
`ads_user_data_consent`. Ejemplo sintético opcional:
`"ref_code":"ABC234","phone":"+1 (555) 000-0000","ads_user_data_consent":false`.
El teléfono exige `+` y país; elimina espacios, paréntesis y guiones, valida
E.164 y guarda solamente SHA-256. No adivina un país. Evitar poner números en
argumentos del shell; preferir el panel o un JSON privado y eliminarlo conforme
a la política del operador. No copiar teléfonos a nombres, notas ni evidencias.

El pago usa `amount_minor` (centavos), `currency` y `paid_at` ISO 8601 con zona,
por ejemplo `2026-11-16T10:30:00-06:00`. Se conserva en UTC. La hora no se inventa
con la hora del registro. Las ventas anteriores sin hora permanecen fuera del
plan hasta registrar la misma venta/pago con su hora comprobada. Un replay con
una hora diferente se rechaza. El panel ofrece los mismos campos; `datetime-local`
se interpreta con la zona horaria del dispositivo. Verificarla antes de guardar.

Después, consultar cada día de clic pertinente, uno a la vez (ejemplo):

```bash
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" closed-loop-match --tenant cliente-demo --day 2026-11-16 --execute
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" closed-loop-plan --tenant cliente-demo --key ciclo-001
```

`closed-loop-match` sin `--execute` solo muestra la lectura prevista. Usa GAQL
fijo de `click_view`, por día y dentro de 90 días. Completa todas las páginas
antes de guardar; falla cerrado ante páginas incompletas. Solo persiste empates
y marcas de ambigüedad, nunca el reporte completo. Dos GCLID con la misma ref
se rechazan, incluso si la colisión aparece en distintas páginas/días. Repetir
el mismo GCLID no es una colisión. Si se registra el prospecto después de leer
el día, volver a leer ese día. La referencia de seis caracteres no es única
ni prueba de identidad; no se puede detectar un clic ausente del reporte.

El plan lista hasta 50 pagos elegibles con GCLID, valor, hora, moneda y, solo
con consentimiento, hash de teléfono. Excluye demo, falta de hora o empate,
ambigüedad, reservas previas y clics vencidos. El límite de 90 días usa el inicio
del día del clic en la zona de la cuenta: puede excluir parte del último día,
porque `click_view` no aporta la hora exacta. Un hash de teléfono de un clic
mayor de 63 días no se envía; el GCLID puede seguir elegible para importación
tradicional según la acción. Google puede aplicar ventanas menores.

Revisar el plan y copiar su `fingerprint` exacto. Una persona con rol `approver`
lo aprueba mediante el mecanismo existente, por tiempo limitado:

```bash
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" --tenant cliente-demo --role approver approve ciclo-001 FINGERPRINT_DEL_PLAN --ttl 600
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" closed-loop-run --tenant cliente-demo --key ciclo-001 --execute
```

Sin aprobación vigente no hay subida. Una modificación del plan/configuración
exige otro plan y aprobación. `event_id` se usa como `orderId` y reserva local;
no reusar una venta con otro evento para intentar cobrar dos conversiones.
El envío usa `partialFailure=true`. Cada fila queda `uploaded` o `uncertain`;
se conservan las aceptadas y se concilian las restantes. Una aceptación API no
certifica atribución, fecha de aparición en informes ni mejoras de rendimiento.

## Alternativa CSV y conciliación

```bash
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" closed-loop-export --tenant cliente-demo --to /ruta-privada/conversiones.csv
```

Genera un archivo nuevo `0600` dentro de un directorio `0700`, con columnas
oficiales `Google Click ID, Conversion Name, Conversion Time, Conversion Value,
Conversion Currency`, fecha con zona e importes decimales. No sobrescribe un
archivo existente ni incluye teléfonos. Revisar e importar en Google por cuenta
del operador. Exportar reserva los eventos: **no se marcan subidos** ni se dejan
reenviar automáticamente por API. Verificar la cuenta/acción al subir el archivo.
La plantilla de cinco columnas no lleva `orderId`; conservar esta base local
y no volver a importar el mismo CSV fuera de Verdugo.

Errores parciales, cortes de red/proceso, exportaciones o escritura fallida de
archivo requieren verificar el diagnóstico/recibo privado antes de conciliar:

```bash
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" --role approver closed-loop-reconcile --tenant cliente-demo --event-id venta-demo --outcome uploaded --evidence private:recibo-demo --execute
```

Usar `not_uploaded` solo con evidencia de que **no** se cargó: libera ese evento
para un nuevo plan/aprobación. `uploaded` conserva el bloqueo contra duplicados.
No se hace una llamada de comprobación a Google por este comando; registra una
declaración humana auditada. No resuelve un envío que sigue activo. Los respaldos
con filas pendientes bloquean la restauración operativa hasta su revisión offline;
los respaldos resueltos conservan atribución e idempotencia y restauran servicios
apagados/aprobaciones anuladas. No restaurar una copia vieja para reenviar ventas.

## Leer el reporte sin inventar resultados

```bash
python -m verdugo --config "$VERDUGO_HOME/config.json" --state "$VERDUGO_HOME/estado.sqlite" closed-loop-report --tenant cliente-demo --start-date 2026-11-01 --end-date 2026-11-16
```

También aparece en **Embudo → datos reales**, y en MCP mediante
`verdugo_closed_loop_status` con `params.start_date/end_date`. No hay herramienta
MCP de match, plan, exportación, aprobación, conciliación o subida del ciclo.

- **Clics WhatsApp con referencia:** `null / no medidos`. Un fragmento que no
  envía nada no puede comunicar todos esos clics a Verdugo. No se sustituye este
  dato por prospectos ni se agrega telemetría sin autorización.
- **Prospectos/empatados:** altas reales del periodo UTC, con referencia y,
  respectivamente, un empate único vigente en el registro local.
- **Ganados/subidos/valor:** periodo de la hora real de pago UTC. Ganados cuenta
  prospectos únicos con referencia; subidos cuenta eventos, incluidos los
  confirmados por conciliación humana. El dinero se separa por moneda.
- **Costo por cliente pagado:** gasto real importado de anuncios (todas las
  plataformas), dividido por clientes únicos del canal `paid` con fecha de pago
  en el periodo y la misma moneda. No atribuye causalidad a Google. Sin gasto
  importado o sin clientes con esa moneda devuelve «Sin datos», nunca cero
  inventado. Los días de gasto son los del archivo del anunciante.

Estos conteos tienen bases temporales distintas; no son una única cohorte de
conversión. Un registro local «real» es declarado por el operador; no hay
verificación bancaria. Software probado, cuenta Google habilitada y ventas
conseguidas son tres cosas diferentes. No se prometen 15 ventas ni dominio de tráfico.

## Evidencia técnica y límites

[`evidence/ciclo-cerrado-contract.json`](evidence/ciclo-cerrado-contract.json)
identifica los archivos y SHA Git de `google-ads-python` en el commit fijado.
Las pruebas verifican la forma JSON REST equivalente a sus protobufs, OAuth +
developer token, consulta fija, posiciones de errores parciales y resultados.
No ejecutan el SDK original ni hacen llamadas reales a Google.

```bash
python -m unittest discover -s tests -v
node --test tests_snippets/*.test.cjs
python -m unittest discover -s tests_panel -v
npm run check --prefix panel
npm test --prefix panel
npm run e2e --prefix panel
```

La línea base antes de cambios fue 796 pruebas Python correctas. La revisión
actual debe comprobarse en los tres workflows de CI del PR. Ningún resultado
sintético sustituye la validación del operador ni permite declarar listo un
servicio Google que no se haya probado con autorización.
