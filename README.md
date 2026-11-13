# Verdugo Digital — Growth Engineering (reconstrucción)

Rama de trabajo dedicada exclusivamente a 10 proyectos upstream de Growth Engineering. La rama `main` conserva el producto anterior y `backup/pre-growth-ten-20261112` conserva un respaldo idéntico de su estado inicial.

## Estado comprobable

| Evidencia | Resultado |
|---|---|
| Repositorios upstream identificados | 10/10 |
| Referencias Git submodule registradas y fijadas por SHA | 10/10 |
| Submódulos descargados y dependencias instaladas | **0/10 verificados** |
| Servicios levantados y conectados por API | **0/10 verificados** |
| Pruebas reales E2E entre proveedores | **0/10 verificadas** |
| Despliegues productivos certificados | **0/10** |

**Nota:** un submódulo Git incorpora una referencia al código original y un commit exacto; **no** instala ni ejecuta el servicio y no demuestra compatibilidad. El archivo `stack/catalog.json` refleja el estado operativo, no el número de repositorios enlazados.

## Código upstream

Los diez proyectos están vinculados en `upstream/` como Git submodules. Son PostHog, GrowthBook, erxes, Mautic, Dittofeed, RudderStack (rudder-server), OpenReplay, Twenty, Countly (countly-server) y Formbricks. Las versiones quedan fijadas por gitlinks del commit de esta rama, evitando actualizaciones involuntarias.

En un equipo con Git y conexión a Internet:

```sh
git clone --filter=blob:none https://github.com/josuechavando350-png/Verdugo-Digital.git
cd Verdugo-Digital
git switch feat/growth-engine-ten-clean-20261112
git submodule update --init --recursive --depth 1
git submodule status
python3 -m unittest discover -s tests -v
```

**Advertencia:** la descarga puede requerir bastante espacio, memoria y ancho de banda; algunos proyectos poseen submódulos internos o dependencias grandes. Clonar submódulos tampoco equivale a instalar sus requisitos de servicio.

## Qué significa convertirlo en un solo producto

1. Especificar versiones, licencias y requisitos operativos de los diez sistemas.
2. Desplegarlos en infraestructura autorizada con configuraciones y secretos independientes.
3. Construir un control plane Nexus, identidad canónica, esquemas de eventos y contratos por API.
4. Definir **una autoridad** para CRM (Twenty vs. erxes), analítica (PostHog vs. Countly) y envíos (Mautic vs. Dittofeed).
5. Probar transacciones consentidas de extremo a extremo con servicios **reales**, incluyendo deduplicación, cancelación de consentimientos, reintentos, recuperación y seguridad.
6. Habilitar la interfaz única y el despliegue productivo solo si la prueba de aceptación demuestra comunicación entre los diez.

El plan de componentes y responsabilidades está en `docs/ARCHITECTURE.md`.

## Verificación local y CI

```sh
python3 -m unittest discover -s tests -v
```

La prueba de catálogo verifica diez proyectos, el manifiesto de submódulos y diez referencias Git fijadas. No simula pruebas de servicios reales ni certifica operaciones comerciales. CI está definido en `.github/workflows/catalog-validation.yml`.
