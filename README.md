# Verdugo Digital — Nexus

Núcleo comercial y de análisis para Nexus Bot Studio. Una sola entrada CLI/MCP,
un motor de ejecución, flujos con dependencias, permisos locales, auditoría,
idempotencia y estado SQLite. Versión de ingeniería **0.10.0**.

**La integración operativa de los 100 proyectos NO está terminada.** El inventario
no se usa para inflar el número de funciones ejecutables.

## Estado actual

| Componente | Alcance |
|---|---|
| Fuentes aprobadas y fijadas por commit | 100 |
| Proyectos con una operación implementada | 41: 22 HTTP + 19 de bibliotecas locales |
| Proyectos sin ningún adaptador | 59 |
| Operaciones externas HTTP existentes | 26, con alcance limitado por proveedor |
| Bibliotecas locales con aceptación real | 12; resultados e idempotencia probados con dependencias instaladas |
| Flujo compuesto local | 5 pasos, con persistencia y reanudación después de reiniciar Engine |
| Pruebas unitarias y de contrato del núcleo | 351 en la aceptación v0.9; resultado de cada commit en Actions |
| Herramientas MCP | 21; las nuevas operaciones reutilizan execute/workflow existentes |
| Servicios productivos certificados | 0 |

Las 12 recetas ejecutan Trafilatura, Scrapy, DuckDB, OR-Tools, Optuna,
scikit-learn, CatBoost, Haystack, Great Expectations, Evidently, Presidio y
Playwright. No son importaciones vacías ni resultados simulados. La aceptación
exige resultados específicos y repetición sin reejecutar. El flujo combina
extracción de contenido, redacción limitada de datos personales, búsqueda local,
resumen de campañas y selección bajo un presupuesto declarado.

La aceptación completa de bibliotecas y del flujo pasó en
[Actions 43139596936](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43139596936).
También hay una puerta separada de aceptación para servidores reales Qdrant y
Meilisearch: binarios comunitarios fijados por versión y hash, procesos efímeros,
autenticación, datos sintéticos y namespace de red limitado a loopback. Su resultado
se consulta en el workflow **Verdugo real service acceptance** del commit, nunca
se deduce de las pruebas unitarias ni se convierte en certificación productiva.

## Lote v0.10: siete operaciones nuevas

dlt, LangGraph, LlamaIndex, Ragas, MLflow, DoWhy y EconML reutilizan el mismo
motor. Se añade un flujo de carga → búsqueda → evaluación → clasificación →
registro con persistencia y reanudación. Sus pruebas de aceptación real deben
comprobarse por commit; no se infieren de los contratos unitarios.
[Alcance, límites y fuentes](docs/RUNTIME_V010.md).

## Núcleo sin dependencias adicionales

```sh
python -m unittest discover -s tests -v
python -m verdugo --state :memory: status
python -m verdugo sources
python -m verdugo source-inspect duckdb
python -m verdugo demo
```

La demo del núcleo usa datos ficticios y no llama proveedores. Los comandos
status/source-inspect distinguen recetas HTTP, recetas locales y fuentes sin
adaptador. La consulta graph histórica solo describe las rutas HTTP; no es un
inventario de todos los procesos activos.

## Instalar y comprobar las operaciones locales

Entorno validado: **Linux x86_64, CPython 3.12**, con un entorno virtual dedicado.
No se afirma compatibilidad de estas dependencias nativas con Android/Termux.
El núcleo estándar mantiene sus pruebas de compatibilidad por separado.

```sh
python3.12 -m venv .venv-runtime
. .venv-runtime/bin/activate
python -m pip install -r requirements/runtime.txt
python -m pip check
export PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/verdugo-browsers"
python -m playwright install --with-deps chromium
python -m verdugo runtime-check
VERDUGO_RUNTIME_REQUIRED=1 python -m unittest discover -s tests_runtime -v
```

La instalación del navegador puede requerir permisos administrativos para
bibliotecas del sistema. Las pruebas de aceptación son sintéticas. En CI se
realizan además dentro de un namespace sin red externa. runtime-check solo
inspecciona versiones instaladas: no sustituye la prueba de ejecución.

Las versiones directas y transitivas se fijan al entorno que pasó la aceptación.
Esto no es un lock criptográfico universal ni una auditoría de seguridad de todas
las dependencias. Los informes de instalación conservan los hashes observados.

## Operación mediante el mismo Engine

```sh
python -m verdugo init --out verdugo.local.json
# Revisar licencias, recursos y privacidad, y habilitar únicamente las recetas necesarias.
python -m verdugo --config verdugo.local.json workflow @examples/local-marketing.synthetic.json
python -m verdugo --config verdugo.local.json workflow @examples/local-marketing.synthetic.json --execute
```

La configuración inicial mantiene todos los proveedores apagados. Para una receta
local se requieren enabled, license_reviewed y runtime_reviewed, versión exacta y
un timeout acotado. Playwright requiere browser_path absoluto del operador.
Los indicadores de revisión son responsabilidad del operador, no aprobaciones
legales deducidas del catálogo o de CI. No reutilizar los perfiles sintéticos de
prueba para datos o empresas reales.

[Operaciones, límites y procedimiento v0.9](docs/RUNTIME_V09.md).

## Frontera de confianza

Los adaptadores locales aceptan JSON acotado; no shell, SQL libre, código enviado
por el usuario, rutas de archivos de entrada ni carga de modelos serializados.
El proceso de trabajo no hereda credenciales de proveedores y limita tiempo,
salida y archivos. **No es un sandbox para código nativo hostil ni una cuota total
de memoria o disco.** Para contenido adversarial se necesita aislamiento del
sistema operativo; el namespace sin red de CI no se activa automáticamente en un
host de producción.

SQLite y los roles del proceso no son IAM multiempresa hostil. Los planes y
resultados pueden contener datos personales: directorios privados, cifrado del
host, retención y copias verificadas son responsabilidad operativa pendiente.
Las escrituras HTTP siguen necesitando aprobación separada; los resultados
inciertos no se reintentan ciegamente. No se habilitan comunicaciones, publicidad,
cobros, compras ni servicios permanentes al instalar este código.

## Lo que falta

66 proyectos requieren todavía código de integración apropiado, no solo claves.
Los adaptadores HTTP requieren además aceptación individual contra la versión,
edición y permisos de instancias autorizadas. Una prueba de dos servidores
locales no valida los otros 20 ni todas las funciones de los dos probados.
No hay despliegue productivo, conexión automática de este chat al MCP, operación
24/7, ingresos bancariamente reconciliados ni probabilidad comercial demostrada.

El historial anterior se conserva en [README hasta v0.8](docs/HISTORICAL_README_V08.md).
Guías existentes: [arquitectura](docs/ARCHITECTURE.md),
[control comercial](docs/COMERCIAL_30_DIAS.md), [cola/eventos](docs/EVENTS.md),
[ventas locales](docs/VENTAS_TERMUX_V07.md), [piloto y respaldos](docs/PILOTO_Y_RESPALDOS_V06.md),
[fuentes fijadas](docs/GITHUB_SOURCES_V08.md).
