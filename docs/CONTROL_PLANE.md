# Verdugo — Control Plane inicial

Se añadió un servicio HTTP propio, de solo lectura, que expone una **interfaz API única** para el catálogo y la conectividad básica de los diez proveedores.

## Funciones comprobadas

- `GET /healthz`: verifica únicamente que la capa Nexus responde.
- `GET /v1/catalog`: devuelve los diez proyectos, bajo autenticación.
- `GET /v1/systems`: prueba los endpoints configurados y devuelve `reachable`, `http_error`, `unreachable` o `not_configured`.
- Cada proveedor lleva `integration_verified=false` y `production_certified=false` hasta completar pruebas reales.

Este servicio **no** despliega PostHog, GrowthBook, erxes, Mautic, Dittofeed, RudderStack, OpenReplay, Twenty, Countly ni Formbricks. Tampoco unifica sus datos o realiza envíos; un HTTP 200 no demuestra que las APIs funcionen juntas.

## Ejecutar localmente

Requiere Node.js 22+, sin dependencias NPM.

```sh
export VERDUGO_CONTROL_TOKEN="$(openssl rand -hex 32)"
node lib/control-plane.mjs
curl -H "Authorization: Bearer $VERDUGO_CONTROL_TOKEN" http://127.0.0.1:8177/v1/systems
```

Los servicios se declaran opcionalmente por archivo, no por parámetros aportados desde solicitudes HTTP:

```json
{
  "posthog": "https://posthog.example.org/health",
  "growthbook": "https://growthbook.example.org/health"
}
```

```sh
export VERDUGO_ENDPOINTS_JSON=/ruta/privada/endpoints.json
node lib/control-plane.mjs
```

Los endpoints del ejemplo no existen. Deben configurarse tras instalar los proveedores, revisar sus APIs y autorizar sus destinos. Solo se admite HTTPS o HTTP a loopback. El servidor escucha en `127.0.0.1` salvo configuración explícita.

## Prueba ejecutada

```sh
node --test tests/control-plane.test.mjs
```

Cinco pruebas locales con un servidor HTTP ficticio comprueban diez sondas, autenticación, registro y validación de endpoints. **Estas pruebas son contratos locales, no pruebas E2E con los diez proveedores reales.**

## Pendiente para integración real

Se deben implementar por proveedor: autenticación, rutas API versionadas, escrituras/lecturas comprobadas, consentimiento, mapeos de eventos, esquema de identidad y pruebas cruzadas. No se deben activar campañas, mensajes ni escribir contactos reales antes de la aceptación y revisión de privacidad.
