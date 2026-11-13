# Portfolio de 50: un producto, no 50 instalaciones declaradas

Esta revisión integra una nueva sección en el **mismo servidor, token, espacio de
trabajo y base SQLite** del núcleo de Verdugo. No borra los originales ni modifica
`main`. Tampoco declara terminado el alcance de 50 servicios.

## Recuento corregido

La selección final de 31 + 19 contiene exactamente 50 identidades. Solo seis son
parte de los diez originales: PostHog, GrowthBook, Mautic, RudderStack, Twenty y
Formbricks. Por tanto hay **44 identidades nuevas**, no 40. Countly, Dittofeed,
erxes y OpenReplay se preservan como compatibilidad, sin contarlos dos veces ni
eliminarlos automáticamente. No son 54 módulos nuevos ni 50 servicios funcionando.

`stack/portfolio50.json` especifica la función principal de cada candidato.
Asignar responsabilidades diferentes no significa que sus funciones no se solapen.
La verificación de fuentes registra la revisión Git y evidencia de licencia; no
aprueba el uso comercial, ejecuta código de terceros ni certifica instalaciones.

## Flujo implementado

`POST /v1/portfolio/opportunities` ejecuta con librerías originales:

1. `email-validator`: validar y normalizar correo **sin DNS/SMTP**. Es dependencia
   auxiliar, no un candidato adicional ni un reemplazo de libphonenumber.
2. MarkItDown: convertir el fragmento HTML proporcionado a Markdown. No descarga
   páginas, admite rutas a archivos o habilita plugins externos.
3. spaCy: segmentar texto en español con `blank('es')` y sentencizer. No descarga
   un modelo NER y no inventa detección de intención de compra.
4. La API existente de `GrowthStore` registra el prospecto con el mismo UUID,
   consentimiento y espacio. El resto del núcleo puede consultar ese registro.

Las transiciones y comprobantes de distribución/versión sobreviven al reinicio.
Repetir el mismo ID y contenido no repite la captura. Reutilizar un ID con contenido
distinto devuelve conflicto. Un trabajo fallido no aparece como completado.
Los trabajos interrumpidos no se reejecutan ciegamente. No se propagan los datos a
los otros 50 candidatos ni se habilita publicidad o contacto automáticamente.

El cuerpo del documento permanece en memoria y no se guarda en el comprobante;
el registro comercial de nombre/correo sigue las limitaciones del núcleo existente:
SQLite local privado, **sin cifrado de disco, política de retención o borrado
productivo certificada**. La huella del contenido no garantiza anonimización.

## Recepción de comprobantes autenticados

`POST /v1/portfolio/receipts` permite al operador importar un callback de Stripe
o Twilio y validarlo con sus SDK originales. Requiere el token de Verdugo y un
secreto configurado en el entorno; ese secreto no se acepta desde el cuerpo HTTP.

- Stripe: `provider`, `raw_body`, `signature`; secreto
  `VERDUGO_STRIPE_WEBHOOK_SECRET`. Se rechazan firma inválida, secreto ausente y
  timestamps demasiado antiguos **o futuros**. Se registra el ID del evento sin
  duplicarlo; **no se considera conciliación bancaria ni ingreso realizado**.
- Twilio: `provider`, `parameters`, `signature`; configuración
  `VERDUGO_TWILIO_AUTH_TOKEN` y `VERDUGO_TWILIO_WEBHOOK_URL`. La URL firmada es
  configuración del operador, no del solicitante. No realiza llamadas ni mensajes.

No hay endpoint de webhooks público certificado: el servidor sigue en loopback.
Estos son receptores/verificadores locales, no cuentas Stripe/Twilio activadas.
Una prueba con firmas sintéticas demuestra el uso del SDK, no actividad comercial.

## Interfaz única

Abrir `http://127.0.0.1:8177/portfolio` después de iniciar el núcleo. Usa el mismo
token existente; los datos privados permanecen detrás de autenticación, protección
de Host/origen y límite de cuerpo. El panel identifica módulos pendientes sin
pintarlos como instalados. Las rutas anteriores siguen disponibles.

```sh
bash scripts/install-portfolio.sh
# Usar la ruta que imprime el instalador:
VERDUGO_PYTHON="$HOME/.local/share/verdugo/python/bin/python" bash scripts/termux-run.sh
```

El instalador crea un virtualenv e instala cinco distribuciones originales
versionadas. **No instala los 50 servidores.** Python 3.12/Linux es el entorno
probado por CI; no se presupone compatibilidad con Android, spaCy o sus wheels.
No se usa curl-pipe-shell, no se ejecuta instalación durante cada petición HTTP.

## API de coordinación

- `GET /v1/portfolio`: 50 candidatos, responsabilidad, operaciones locales,
  disponibilidad observada de paquetes y ejecuciones del espacio autenticado.
- `POST /v1/portfolio/plan`, `{ "objective": "discover" }`: selecciona módulos
  por función (`discover`, `attract`, `convert`, `measure`, `operate`). Es un plan,
  no una ejecución de servicios pendientes.
- `POST /v1/portfolio/opportunities`: pipeline local descrito arriba.
- `POST /v1/portfolio/receipts`: validación de comprobantes firmados descrita arriba.

Todos los adaptadores externos no implementados permanecen explícitamente
`adapter_pending`. Las licencias, credenciales y pruebas en vivo no se sustituyen
por un healthcheck o la presencia de un repositorio.

## Aceptación reproducible y sus límites

El workflow `portfolio-acceptance.yml` separa dos comprobaciones:

1. Resolver los 50 repositorios, revisión Git y evidencia de licencia mediante
   consultas de solo lectura a GitHub. Guarda un lock de **fuentes**, no un lock de
   runtime ni una prueba de instalación de 50.
2. Instalar las distribuciones originales, probar validación y firmas inválidas,
   y ejecutar **el mismo servidor/API/SQLite de Verdugo** con HTML y contactos
   sintéticos. Exige lectura, deduplicación, comprobantes y persistencia tras
   cerrar/reabrir la base. No utiliza APIs simuladas para las librerías.

`tests/portfolio.test.mjs` incluye pruebas de contrato con un almacén/worker
fixture, etiquetadas como tales. No se cuentan como prueba nativa. El comprobante
nativo es `evidence/portfolio-runtime.json` del commit exacto que ejecutó CI.
`requirements-portfolio.txt` fija versiones directas; el informe de pip conserva
la resolución y hashes, pero aún falta un lock transitivo completo aprobado.

## Pendiente para cumplir los 50

Construir, configurar y aceptar cada adaptador restante, desplegar los servicios
originales en infraestructura autorizada, completar el circuito general y probar
consentimiento/supresión transversal, aislamiento multiusuario, backups,
restauración, licencias y costos. Los seis originales retenidos siguen sujetos a
sus pruebas nativas históricas; esta capa no termina por sí sola PostHog ni los 50.
`all_fifty_integrated` y `production_ready` permanecen **false**.

No se contrató infraestructura, modificó facturación, publicó campañas ni se
contactó a ninguna persona. La evidencia local o de CI no demuestra ventas.

## Fuentes de contratos

- https://pypi.org/project/email-validator/2.3.0/
- https://github.com/microsoft/markitdown
- https://spacy.io/api/sentencizer
- https://docs.stripe.com/webhooks/signatures
- https://www.twilio.com/docs/usage/security
