# Estado de la integración nativa — 2026-11-13

La meta del usuario son **los diez proyectos originales instalados y funcionando juntos en un entorno duradero**, no seis referencias de código ni respuestas HTTP simuladas.

## Evidencia de GitHub Actions

| Evidencia | Qué se aceptó | Qué NO se acepta |
| --- | --- | --- |
| [43480330686](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43480330686) · `3250c026` | Circuito de ocho originales en una misma ejecución: GrowthBook, Mautic, RudderStack, Countly, Dittofeed, Twenty, erxes, Formbricks; informe `status=passed` | No son diez ni alojamiento permanente |
| [43478387447](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43478387447) · `443f7e21` | OpenReplay con los cuatro originales del núcleo; lectura real de sesión, evento y datos grabados; `session_capture_verified=true` | No está probado simultáneamente con los ocho |
| [43470960160](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43470960160) · `8b9f1dbb` | Formbricks con los cuatro originales | El mismo Formbricks se incluye en el circuito posterior de ocho; no se cuenta dos veces |
| [43481415427](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43481415427) · `7434bd3d` | Instalación nativa de PostHog iniciada y migraciones Django avanzando | **Fallo** `posthog_migration_timeout`; ninguna aceptación de PostHog |

El circuito de ocho conserva la ruta comprobada desde GrowthBook hasta Countly a través de los demás adaptadores elegidos. Las aceptaciones anteriores se ejecutaron con datos sintéticos, imágenes originales y dependencias reales. Los procesos se eliminaron al acabar. Los cambios posteriores de código **no heredan** automáticamente su aceptación.

## Prueba conjunta de diez

Se añadió `.github/workflows/native-ten-acceptance.yml`, que ejecuta:

```sh
python scripts/native-extensions-acceptance.py \
  --providers dittofeed twenty erxes formbricks openreplay posthog \
  --output evidence/native-ten.json
```

Este workflow **falla cerrado**: además de exigir los diez nombres en `verified_originals`, requiere que los adaptadores originales de PostHog y OpenReplay acrediten captura real de eventos/sesiones. No basta crear una feature flag, un proyecto o recibir `HTTP 200`.

### Bloqueadores conocidos

1. **PostHog:** la migración auténtica excedió el límite anterior de diez minutos. Se amplió el tiempo de espera; se debe observar el nuevo resultado. Aun si la migración finaliza, `scripts/native_posthog.py` hoy comprueba una API de configuración, y fija `event_capture_verified=false`. Falta implementar y leer de vuelta el pipeline nativo de ingesta antes de aprobar los diez.
2. **Recursos del ejecutor:** el runner público estándar de GitHub tiene 4 vCPU, 16 GiB de RAM y 14 GiB de almacenamiento SSD. Diez aplicaciones, múltiples bases y workers podrían superar esos límites; si ocurre, no autoriza reducir la aceptación ni fabricar un resultado.
3. **Alojamiento permanente:** GitHub Actions es efímero. El acceso a Railway del usuario no ha permitido crear el proyecto Verdugo debido al fin de la prueba gratuita; no hay despliegue 24/7 ni una estimación aprobada de consumo para el conjunto.
4. **Operación comercial:** incluso con diez aplicaciones pasando CI, faltarían el control plane de producción, claves segregadas, backups, restauración, vigilancia, protección de datos, acuerdos de licencia y controles de activación de campañas.

## Interpretación obligatoria

- Ocho originales aprobados **juntos** es una aceptación parcial real.
- OpenReplay aprobado **en otro circuito** no convierte el resultado anterior en nueve aprobados juntos.
- PostHog `failed` sigue siendo **no aceptado** aunque sus contenedores arranquen.
- Solo se podrá declarar integración conjunta de diez si el workflow de diez acaba en `success`, su JSON indica `all_ten_integrated=true` y la evidencia identifica la revisión exacta.
- Incluso ese resultado no equivaldría a una instalación permanente, rentabilidad demostrada ni un servicio comercial operativo.

No sustituir `main` ni anunciar producción por una aceptación parcial.
