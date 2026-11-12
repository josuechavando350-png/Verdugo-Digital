# Verdugo Digital — Nexus

Núcleo comercial y de análisis para Nexus Bot Studio. Una sola entrada CLI/MCP,
un motor de ejecución, flujos con dependencias, permisos locales, auditoría,
idempotencia y estado SQLite. Versión de ingeniería **0.11.0**.

**La integración operativa de los 100 proyectos NO está terminada.** Registrar
fuentes, implementar operaciones, probarlas y desplegarlas son etapas distintas.

## Estado del código

| Componente | Alcance |
|---|---|
| Fuentes aprobadas y fijadas por commit | 100 |
| Proyectos con una operación implementada | 49: 30 HTTP + 19 de bibliotecas locales |
| Proyectos sin ningún adaptador | 51 |
| Operaciones HTTP existentes | 34, limitadas por proveedor |
| Operaciones locales implementadas | 19; aceptación de ejecución real exigida por commit |
| Flujos compuestos de aceptación | Dos de cinco pasos; persistencia y reanudación tras reiniciar Engine |
| Pruebas unitarias y de contrato | 369 base v0.10 más pruebas de contrato v0.11; verificar CI por commit |
| Herramientas MCP | 21; las operaciones reutilizan execute/workflow existentes |
| Servicios productivos certificados | 0 |

Los tres workflows de aceptación son **Verdugo verification**, **Verdugo runtime
acceptance** y **Verdugo real service acceptance**. La aprobación debe observarse
para el commit concreto: una prueba del núcleo no sustituye ejecución de las
bibliotecas ni certifica un despliegue productivo. La aceptación usa datos sintéticos.

## Qué añade v0.11

Ocho nuevos adaptadores **HTTP de solo lectura** en el mismo Engine: Novu
(workflows), Superset (dashboards), Supabase (projects), Coolify (servers),
Keycloak (realms), Unleash (projects), Medusa (products) y OpenFGA (stores).

Todas estas rutas permanecen deshabilitadas hasta revisión de licencia,
versión y credencial autorizada. No hay envíos, despliegues ni escrituras.
Los esquemas se verifican y las respuestas incompatibles fallan en lugar de
contarse como lecturas válidas. Su aceptación en loopback no certifica
proveedores reales ni acceso productivo. [Contratos v0.11](docs/READ_PROVIDERS_V011.md).

## Qué añade v0.10

Siete operaciones se conectan al mismo Engine:

- **dlt** carga campañas suministradas en DuckDB temporal y comprueba sumas.
- **LangGraph** clasifica prospectos mediante reglas declaradas, sin contactar personas.
- **LlamaIndex** recupera documentos suministrados mediante búsqueda léxica BM25.
- **Ragas** evalúa precisión contextual contra referencias, sin LLM remoto.
- **MLflow** registra métricas y verifica su lectura en un almacén temporal.
- **DoWhy y EconML** estiman efectos sobre datos suministrados bajo supuestos explícitos; no prueban causalidad real ni rentabilidad.

El flujo nuevo combina carga, búsqueda, evaluación, clasificación y registro.
Los tests comprueban resultados específicos y reanudación sin reejecutar pasos.
[Contratos, límites y fuentes](docs/RUNTIME_V010.md).

Se conservan las doce recetas v0.9: Trafilatura, Scrapy, DuckDB, OR-Tools, Optuna,
scikit-learn, CatBoost, Haystack, Great Expectations, Evidently, Presidio y Playwright.
La aceptación de servidores Qdrant y Meilisearch usa binarios comunitarios fijados,
autenticación y procesos efímeros: no equivale a instalar servicios permanentes.

## Núcleo sin dependencias adicionales

```sh
python -m unittest discover -s tests -v
python -m verdugo --state :memory: status
python -m verdugo sources
python -m verdugo source-inspect duckdb
python -m verdugo demo
```

La demo usa datos ficticios y no llama proveedores. status/source-inspect distinguen
recetas HTTP, locales y fuentes sin adaptador. graph conserva su alcance histórico
HTTP; no es un inventario de procesos activos.

## Instalar las operaciones locales

Plataforma de aceptación: **Linux x86_64, CPython 3.12**. No se afirma compatibilidad
de estas bibliotecas nativas con Android/Termux. El núcleo se prueba por separado.
Ragas requiere un segundo entorno por incompatibilidad de dependencias con Haystack;
no se fuerza una instalación inconsistente. El operador debe revisar licencias,
recursos y privacidad antes de utilizar las funciones con datos reales.

```sh
python3.12 -m venv --copies .venv-runtime
python3.12 -m venv --copies .venv-ragas
.venv-runtime/bin/python -m pip install -r requirements/runtime.txt
.venv-ragas/bin/python -m pip install -r requirements/runtime-ragas.txt
.venv-runtime/bin/python -m pip check
.venv-ragas/bin/python -m pip check
export VERDUGO_RAGAS_PYTHON="$PWD/.venv-ragas/bin/python"
export PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/verdugo-browsers"
.venv-runtime/bin/python -m playwright install --with-deps chromium
.venv-runtime/bin/python - <<'PY'
from llama_index.core.schema import TextNode
from llama_index.retrievers.bm25 import BM25Retriever
BM25Retriever.from_defaults(nodes=[TextNode(text='offline tokenizer preparation')], similarity_top_k=1)
PY
.venv-runtime/bin/python -m verdugo runtime-check
VERDUGO_RUNTIME_REQUIRED=1 .venv-runtime/bin/python -m unittest discover -s tests_runtime -v
```

La preparación descarga paquetes, navegador y recursos de tokenización; puede
requerir privilegios para bibliotecas del sistema. La ejecución de aceptación en
CI se realiza sin privilegios dentro de un namespace sin salida de red. Ese
namespace no se activa automáticamente al operar en otro host.

Las restricciones de versiones reproducen los dos conjuntos instalados y
comprobados con pip. No son un lock criptográfico universal ni una auditoría de
seguridad de todas las dependencias. Los reportes pip conservan los hashes observados.
runtime-check solo consulta metadatos: no sustituye la ejecución real.
[Perfiles y frontera de confianza](docs/RUNTIME_PROFILES_V010.md).

## Operación desde el mismo motor

```sh
.venv-runtime/bin/python -m verdugo init --out verdugo.local.json
# Revisar y habilitar únicamente las recetas necesarias en el archivo privado.
.venv-runtime/bin/python -m verdugo --config verdugo.local.json workflow @examples/local-evidence.synthetic.json
.venv-runtime/bin/python -m verdugo --config verdugo.local.json workflow @examples/local-evidence.synthetic.json --execute
```

Todo comienza deshabilitado. Cada receta local exige enabled, license_reviewed,
runtime_reviewed, versión exacta y timeout acotado. Playwright exige browser_path
absoluto. Las banderas de los fixtures no aprueban licencias comerciales ni deben
copiarse a una configuración real sin revisión. No publicar configuraciones,
secretos o datos de clientes. El ejemplo anterior v0.9 se mantiene en
examples/local-marketing.synthetic.json.

## Límites y pendientes

Se acepta JSON acotado, no shell, SQL libre, código, rutas de entrada ni modelos
serializados del usuario. El worker filtra variables de entorno, limita tiempo,
salida y archivos. **No es un sandbox de código nativo hostil ni una cuota total
de memoria o disco.** El administrador debe proteger sus entornos y el host.

Los almacenes dlt/MLflow son temporales; los resultados verificados persisten en
Engine. SQLite y roles de proceso no constituyen IAM multiempresa hostil. Datos
personales requieren cifrado, retención y respaldos privados. Las escrituras HTTP
siguen requiriendo aprobación separada; no se reintentan resultados inciertos.

**51 proyectos aún requieren código de integración.** Los adaptadores HTTP necesitan
aceptación de versiones/ediciones/permisos por instancia; Qdrant y Meilisearch no
validan los otros 28. No hay despliegue productivo, conexión automática de este
chat al MCP, servicio 24/7, cobros reconciliados ni probabilidad comercial demostrada.
No se activan campañas, contactos, compras ni infraestructura de pago al instalar.

Documentación: [v0.11](docs/READ_PROVIDERS_V011.md), [v0.9](docs/RUNTIME_V09.md), [v0.10](docs/RUNTIME_V010.md),
[perfiles](docs/RUNTIME_PROFILES_V010.md), [arquitectura](docs/ARCHITECTURE.md),
[control comercial](docs/COMERCIAL_30_DIAS.md), [eventos](docs/EVENTS.md),
[piloto y respaldos](docs/PILOTO_Y_RESPALDOS_V06.md), [fuentes](docs/GITHUB_SOURCES_V08.md).
El historial previo se conserva en [README v0.8](docs/HISTORICAL_README_V08.md).
