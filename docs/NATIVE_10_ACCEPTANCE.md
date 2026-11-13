# Aceptación de los diez originales, sin confundir CI con producción

La petición es operar **PostHog, GrowthBook, erxes, Mautic, Dittofeed, RudderStack,
OpenReplay, Twenty, Countly y Formbricks** como un sistema integrado.

## Estado verificable al 13 de noviembre de 2026

| Alcance | Evidencia | Resultado |
|---|---|---|
| Ocho originales juntos | [GitHub Actions 43480330686](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43480330686) | `success`, ocho en `verified_originals`, `all_ten_integrated=false` |
| OpenReplay + cuatro originales | [GitHub Actions 43478387447](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43478387447) | `success`, captura de sesión/DOM real, no prueba de nueve juntos |
| PostHog + cuatro originales, API de feature flags | [GitHub Actions 43484231638](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43484231638) | `success` en API autenticada y reinicio, **`event_capture_verified=false`** |
| Nueve originales, incluido OpenReplay | `.github/workflows/native-nine-acceptance.yml` | Exige un solo circuito, captura de sesión y lectura después de reinicio; verificar ejecución |
| Diez originales, PostHog y OpenReplay | `.github/workflows/native-ten-acceptance.yml` | Exige las diez APIs en un solo circuito **y** PostHog Rust/Kafka/ClickHouse + captura DOM de OpenReplay; verificar ejecución |
| Instalación persistente en producción | No existe alojamiento aceptado con diez servicios | **No realizada** |

Ni los cuatro más PostHog ni los cuatro más OpenReplay equivalen a una integración
simultánea de diez. No sumamos éxitos de ejecuciones distintas.

## Código incorporado para los dos últimos

### PostHog

`scripts/native_posthog.py` instala el servidor administrativo original,
configura un proyecto real de pruebas y exige crear y leer una feature flag
autenticada. Se añadió `scripts/native_posthog_capture.py` para ejecutar
servicios originales de captura Rust, bus Kafka/Redpanda, procesador Node de
ingesta y ClickHouse, utilizando las imágenes oficiales identificadas por el
`docker-compose.base.yml` upstream.

El flujo de captura **solo puede aprobar** cuando envía un evento sintético
mediante `/i/v0/e/`, recupera **ese mismo UUID, sujeto, nombre y ruta** desde
`/api/projects/:id/events/` con autenticación, comprueba persistencia tras
reinicio y envía un evento nuevo después del reinicio. Un acuse HTTP 200, un
healthcheck o una feature flag **no bastan**.

Fuentes:
- https://posthog.com/docs/how-posthog-works/ingestion-pipeline
- https://posthog.com/tutorials/api-capture-events
- https://github.com/PostHog/posthog/blob/2e39d0fcde5361b16a1c1223b412f3b062fbb804/docker-compose.base.yml

Las imágenes de Rust, ingesta Node y Redpanda se declaran por tags oficiales;
el harness registra el digest real de la imagen y su ID en cada ejecución,
pero todavía no existe una fijación por digest del trío nuevo en esta rama.
No se afirma compatibilidad hasta una prueba real aprobada.

### OpenReplay

`scripts/native_openreplay_capture.py` ejecuta los servicios de colección,
persistencia y reproducción originales, escribe una sesión sintética y exige
leer el evento y los bytes del DOM grabados. La evidencia anterior aceptó esa
funcionalidad con los cuatro originales, no con los otros ocho.

### Fallos y correcciones sin esconderlos

- Primer ensayo de diez: [43484052679](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43484052679) falló por límite HTTP 429 `toomanyrequests` al descargar imágenes originales de OpenReplay.
- Segundo ensayo: [43484242343](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43484242343) falló por el mismo límite al descargar `or_http`.
- Se incorporó un reintento **acotado, solo para `docker pull`**. Nunca se repite una escritura incierta de contacto/evento para solucionar este problema.
- PostHog administrativo necesitó más tiempo de migración: la prueba del contrato de feature flags finalmente pasó en 43484231638. Ese éxito no certifica el nuevo pipeline completo de captura.

## Cómo reproducir la aceptación

En Linux x86_64 con Docker, acceso a las imágenes originales y recursos
suficientes:

```sh
# Ocho + OpenReplay; requiere el submódulo para su esquema auténtico
git submodule update --init --depth 1 upstream/openreplay
python scripts/native-extensions-acceptance.py \
  --providers dittofeed twenty erxes formbricks openreplay \
  --output evidence/native-nine.json

# Intento de diez originales simultáneos. Falla si algún paso falta.
python scripts/native-extensions-acceptance.py \
  --providers dittofeed twenty erxes formbricks openreplay posthog \
  --output evidence/native-ten.json
```

Estas pruebas usan identidades sintéticas y red interna de Docker sin salida a
Internet para los contenedores. Las llamadas de negocio pasan por las APIs
originales, no por simulaciones. Todo se destruye al terminar el laboratorio;
ninguna prueba de CI instala software 24/7.

## Condiciones separadas para declarar terminado

1. **Nativo:** la ejecución única de diez termina `success`; `verified_originals`
   contiene exactamente los diez, `all_ten_integrated=true`,
   `posthog.event_capture_verified=true`,
   `posthog.event_capture_after_restart_verified=true` y
   `openreplay.recorded_dom_readback_verified=true`.
2. **Operación permanente:** diez servicios desplegados en un entorno autorizado
   con capacidad suficiente, HTTPS, redes privadas, gestión de secretos,
   backups, restauración y monitoreo comprobados.
3. **Producto:** identidad canónica, consentimiento y borrado propagados,
   permisos/tenants, automatizaciones seguras, límites de costo y evidencias
   de resultados comerciales reales. Ningún laboratorio sintético demuestra
   ventas reales ni ingresos.

Actualmente el trabajo **no cumple** todavía las tres condiciones. El PR #14
permanece en borrador y `main` conserva el proyecto previo.
