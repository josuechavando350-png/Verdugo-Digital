# Verdugo Digital — diez aplicaciones originales de Growth Engineering

**Estado: integración en desarrollo; NO existe un despliegue permanente de los diez.**
El PR [#14](https://github.com/josuechavando350-png/Verdugo-Digital/pull/14)
conserva `main` y `backup/pre-growth-ten-20261112` para evitar sustituir
el producto anterior antes de la aceptación real.

## Evidencia: separar laboratorio, integración y producción

| Resultado | Estado y prueba |
| --- | --- |
| Diez fuentes originales asociadas al repositorio por SHA | 10/10 referencias Git, no instalaciones |
| Ocho originales funcionando simultáneamente | **Aprobado**: GrowthBook, Mautic, RudderStack, Countly, Dittofeed, Twenty, erxes, Formbricks — [run 43480330686](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43480330686) |
| OpenReplay original, con captura y reproducción | **Aprobado independientemente** con los cuatro originales base — [run 43478387447](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43478387447) |
| PostHog original, API administrativa y persistencia | **Aprobado** con los cuatro originales base — [run 43484231638](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43484231638); su informe marca `event_capture_verified=false` |
| Nueve originales juntos, incluidos los ocho y OpenReplay | **Aprobado**: [run 43488279323](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43488279323), con captura real de sesión/DOM y reinicio |
| Diez originales juntos, incluida captura auténtica PostHog | **Sin aceptación todavía**; [prueba nativa conjunta](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43497144094) |
| Instalación permanente en Railway/Termux | **No realizada** |
| Campañas, clientes o ventas reales demostrados | **No demostrados** |

Una aceptación en laboratorios distintos no se suma para inventar un circuito
conjunto mayor. GitHub Actions crea y luego elimina recursos temporales;
el número de servicios que pasaron sus pruebas NO es un porcentaje de producto terminado.

### Últimas dos aplicaciones

**OpenReplay**: `scripts/native_openreplay_capture.py` utiliza componentes
originales de captura, persistencia y lectura de sesiones, eventos y bytes DOM.
El flujo de nueve en `.github/workflows/native-nine-acceptance.yml` obliga
a ejecutarlo junto con los ocho en el mismo laboratorio.

**PostHog**: `scripts/native_posthog.py` verifica una API administrativa real.
`scripts/native_posthog_capture.py` incorpora la arquitectura original de
**Rust Capture → Redpanda/Kafka → procesador de ingesta Node → ClickHouse**.
La topología de ClickHouse incluye los clústeres de migración originales y
ZooKeeper; la autenticación de réplicas usa un secreto del entorno. Las imágenes
adicionales de PostHog se fijaron por digest observado.
La aceptación requiere escribir y **leer de vuelta** el evento sintético mediante
la API nativa, comprobar el UUID y la ruta, y repetir la captura después de
reiniciar. Ni un acuse HTTP 200 ni crear una feature flag bastan.

La prueba de diez en `.github/workflows/native-ten-acceptance.yml`
falla si cualquier original no pasa o si falta la captura real de PostHog
o OpenReplay. Los límites 429 del registro se reintentan **solo al descargar
imágenes**, nunca al enviar datos de negocio.

### Reproducir en Linux x86_64 con Docker y recursos suficientes

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs

# La prueba de OpenReplay necesita el esquema original exacto:
git submodule update --init --depth 1 upstream/openreplay

# Intento real de nueve originales simultáneos:
python scripts/native-extensions-acceptance.py \
  --providers dittofeed twenty erxes formbricks openreplay \
  --output evidence/native-nine.json

# Intento real de los diez, con verificaciones exhaustivas:
python scripts/native-extensions-acceptance.py \
  --providers dittofeed twenty erxes formbricks openreplay posthog \
  --output evidence/native-ten.json
```

Estos ensayos son **efímeros**, usan credenciales y datos sintéticos,
imágenes originales y redes internas. Los informes se asocian al commit y
ejecución exactos. Un trabajo `success` de CI no equivale a una instalación 24/7.

## Núcleo local de Verdugo

Existe un panel/API propio para registrar prospectos, etapas,
consentimiento y ventas declaradas en SQLite; incorpora idempotencia,
separación por espacio de trabajo y una cola controlada. Los importes no
representan cobros bancarios conciliados ni ingresos reales. El núcleo
no sustituye los diez productos originales.

Para iniciar **solo el núcleo** en Termux, con Node.js >=22.16 y
`node:sqlite` disponible:

```sh
bash scripts/termux-install.sh
node scripts/growth-demo.mjs
bash scripts/termux-run.sh
```

Panel local: `http://127.0.0.1:8177`.
El token está en `~/.config/verdugo/environment`, la base de datos
en `~/.local/share/verdugo/growth.sqlite`. No publicar secretos ni datos
de clientes en el repositorio. Esta instalación **no** levanta los diez upstream.

## Documentación de aceptación

- [Aceptación real de diez y sus bloqueadores](docs/NATIVE_10_ACCEPTANCE.md)
- [Integración de cuatro originales ya aprobada](docs/NATIVE_FOUR.md)
- [Núcleo y límites de su API](docs/GROWTH_CORE.md)
- [Instalación del núcleo en Termux](docs/TERMUX.md)

No fusionar en `main` como solución final hasta comprobar un circuito único
de diez, desplegarlo en infraestructura autorizada y validar seguridad,
licencias, consentimiento, supresión, backups, recuperación y operaciones reales.
