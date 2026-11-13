# Verdugo Digital — 50 fuentes seleccionadas, integración parcial verificable

**No están los 50 programas instalados ni funcionando juntos. No existe un
despliegue permanente de los 50.** Esta rama añade un portfolio de fuentes
originales y operaciones concretas dentro del mismo núcleo de Verdugo. El
[PR #14](https://github.com/josuechavando350-png/Verdugo-Digital/pull/14) permanece
en borrador; `main`, el respaldo y los diez submódulos originales se conservan.

## Qué se incorporó realmente

La lista final de 31 + 19 contiene **50 repositorios distintos**. Seis ya estaban
entre los diez originales; por eso se incorporaron **44 nuevas referencias de
código** en `components/`. Countly, Dittofeed, erxes y OpenReplay se mantienen
como compatibilidad en `upstream/`, sin contarlos dentro de los 50 seleccionados.

Hay 54 gitlinks conservados: 50 seleccionados y cuatro anteriores. Un gitlink
fija el repositorio y commit original; **no instala dependencias ni ejecuta la
aplicación**. `stack/portfolio-pins.json` fija los 50 commits. Se preservaron los
SHAs de los seis originales retenidos, sin actualizarlos silenciosamente.

[Catálogo y funciones](stack/portfolio50.json) ·
[Fuentes y versiones](docs/PORTFOLIO_SOURCES.md)

## Un flujo nuevo conectado al núcleo existente: APROBADO

En el commit `54d1fc35f0f99e76dd7d396badf55c9b366239e9`, la
[ejecución 43526734384](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43526734384)
aprobó ambos trabajos: resolución de las 50 fuentes e instalación/prueba de
librerías originales. También aprobó la
[regresión del núcleo 43526734408](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43526734408).

El circuito probado fue:

**Correo proporcionado → email-validator → MarkItDown → spaCy → API de Verdugo →
registro persistente de prospectos de GrowthStore.**

Usa el mismo servidor, token, espacio de trabajo y base SQLite del producto
anterior. La prueba envió HTML y contactos sintéticos a la API, exigió conversión
con las librerías originales, verificó un único prospecto y sus comprobantes,
repitió el evento sin duplicarlo, cerró/reabrió el servidor y la base y volvió a
leer los datos. Las seis comprobaciones de aceptación pasaron.

Se instalaron cinco distribuciones originales: email-validator 2.3.0,
MarkItDown 0.1.9, spaCy 3.8.18, Stripe 17.0.0 y Twilio 9.13.0. email-validator es
una dependencia auxiliar, no un candidato adicional. Los SDK de Stripe y Twilio
pasaron pruebas de firmas válidas e inválidas con datos sintéticos; **no se
realizaron cobros, llamadas ni conexiones a cuentas comerciales**. Una firma
válida no se considera conciliación bancaria.

La primera corrida falló por tratar un Event de Stripe 17 como diccionario.
Se corrigió usando su `to_dict()` original, sin eliminar controles de firmas,
antigüedad de timestamps, secretos o conciliación.

[Informe original de aceptación](evidence/accepted/portfolio-runtime-43526734384.json).
El ZIP del artefacto 14085716053 fue descargado y comprobado con SHA256
`6c5ecca6021033d50c7366cb1da92055a670830a2a13a1b520689db395e78417`.
`all_fifty_integrated=false` permanece explícito en el informe.

## Usar la ampliación local

Requiere el núcleo previo, Node.js con `node:sqlite` y Python compatible con las
distribuciones. La prueba de aceptación fue Linux/Node 22.16/Python 3.12, **no
Android**. El instalador no afirma compatibilidad no comprobada con Termux.

```sh
bash scripts/install-portfolio.sh
VERDUGO_PYTHON="$HOME/.local/share/verdugo/python/bin/python" bash scripts/termux-run.sh
```

Abrir `http://127.0.0.1:8177/portfolio` en el mismo equipo y usar el token local
existente. La vista comercial anterior sigue en `/`. La configuración y la base
siguen fuera de Git; no publicar secretos ni datos de clientes.

El panel muestra los 50 módulos y sus responsabilidades, pero mantiene los no
implementados como `adapter_pending`. No convierte disponibilidad de paquetes,
planes o enlaces a fuentes en pruebas de operación. No envía automáticamente
los datos de un prospecto a los 50 sistemas.

[Contrato y límites del portfolio](docs/PORTFOLIO_50.md) ·
[API del núcleo](docs/GROWTH_CORE.md) · [Termux](docs/TERMUX.md)

## Lo que todavía falta

Construir y aceptar las operaciones restantes de los módulos, revisar licencias,
configurar cuentas autorizadas, desplegar servicios originales en infraestructura
compatible y probar el circuito comercial completo de 50. También quedan
consentimiento y supresión transversal, segregación de clientes, secretos,
retención, respaldos, restauración y controles de costos. No se han demostrado
clientes nuevos, pagos reales ni rentabilidad con esta ampliación.

Las versiones Git de fuente y las versiones de paquetes ejecutadas se registran
por separado: no se afirma que sean equivalentes. El lock transitivo completo
con hashes de todas las dependencias de runtime aún está pendiente.

## Laboratorios originales preservados

Los laboratorios históricos de nueve originales y el intento de diez permanecen
sin sustituirlos por esta capa local. Su evidencia corresponde a sus propios
commits y no se suma al nuevo flujo para inventar un resultado de 50 aplicaciones
conjuntas. Esta revisión no termina ni certifica por sí sola la captura de PostHog.

[Alcance original de diez](docs/NATIVE_10_ACCEPTANCE.md) ·
[Circuito de cuatro aceptado históricamente](docs/NATIVE_FOUR.md)

## Verificación

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
node scripts/portfolio-acceptance.mjs
```

El último comando exige las librerías originales instaladas y genera evidencia
sintética, no datos comerciales. Las pruebas unitarias con fixtures están
etiquetadas y no se cuentan como instalaciones reales. No fusionar este PR como
producto terminado hasta aceptar el alcance completo y su despliegue real.
