# Verdugo Digital — Nexus

Núcleo comercial y de análisis para Nexus Bot Studio. Una sola entrada CLI/MCP,
un motor de ejecución, flujos con dependencias, permisos locales, auditoría,
idempotencia y estado SQLite. Versión de ingeniería **0.21.0**.

**La integración operativa de los 300 proyectos NO está terminada.** Registrar
fuentes, implementar operaciones, probarlas y desplegarlas son etapas distintas.

## Hacia los 666

El plan para llegar a 666 piezas libres (300 del catálogo + 50 del simulador + 150 del cerebro + 166 finales) está en [docs/PLAN_666.md](docs/PLAN_666.md), con las instrucciones por tanda en [docs/PROMPT_ASTRA_666.md](docs/PROMPT_ASTRA_666.md). El registro contiene 688 identidades distintas: 666 permitidas por licencia raíz y 22 excluidas. Treinta y nueve de las 366 incorporaciones tienen una operación implementada: 28 locales y once lecturas HTTP con aceptación sintética; 327 siguen pendientes. La auditoría corrigió cinco alias duplicados y una licencia restringida; evidencia y cola de dos lotes de 183 en [docs/REGISTRO_666.md](docs/REGISTRO_666.md).

OpenManus fue retirado tras detectar su dependencia obligatoria GPL-3.0; vuelve a pendientes. InterpretML incorpora una explicación aditiva sintética. TransformerLens añade diagnóstico de un modelo sin entrenar; Bitsandbytes añade diagnóstico nativo de cuantización; Guidance y LM Format Enforcer comprueban formatos y prefijos sintéticos; TensorZero y Opik añaden lecturas acotadas de registros existentes; MemOS y LightRAG añaden recuentos de tareas y documentos; Kernel Memory, Chroma y Milvus añaden inventarios acotados; USearch añade diagnóstico nativo de vecinos y RAGFlow un inventario comunitario; Rerankers ordena puntuaciones suministradas e Infinity cuenta modelos declarados; SymPy comprueba polinomios, RDFLib comprueba alcanzabilidad, Z3 comprueba factibilidad finita y Jena cuenta datasets de Fuseki; txtai concilia contenido numérico en su almacén efímero original; KAG consulta el estado de una tarea existente mediante su protocolo original; el total vigente llega a 39 incorporaciones con adaptador; las pruebas funcionales históricas no sustituyen revisión de dependencias.

El campo `integration_audit` de `product-status` verifica identidades y pertenencia a los lotes, muestra las revisiones pendientes y conserva el hallazgo de certifi en doce perfiles. `all_666_integrated=false` y `distribution_license_closure_verified=false`: el registro no certifica un producto distribuible. [Continuidad y alcance actual](docs/CONTINUIDAD_666.md).

## Estado del código

| Componente | Alcance |
|---|---|
| Fuentes registradas y fijadas por commit | 688 (322 anteriores + 366 nuevas) |
| Permisos según la licencia raíz; cierre completo de dependencias pendiente | 666 |
| Excluidos por licencia (registrados, sin operar) | 22 |
| Proyectos con una operación implementada | 301: 114 HTTP + 164 bibliotecas locales + 18 CLI + 2 MCP locales + 3 consultas/reglas de datos |
| Conectados bajo la política de licencias | 282 (19 adaptadores HTTP antiguos quedaron bloqueados por licencia) |
| Piezas de construcción (se usan al programar, no vía motor) | 56 |
| Pendientes de conector | 328 (327 nuevas + `meta-ads`) |
| Servicios de pago | 0 (Stripe, Twilio, Mercado Pago, E2B y Composio retirados) |
| Operaciones HTTP existentes | 118, limitadas por proveedor |
| Operaciones locales implementadas | 187; aceptación de ejecución real exigida por commit |
| Flujos compuestos de aceptación | Flujo de 87 operaciones nuevas + métricas locales; persistencia y reanudación tras reiniciar Engine |
| Pruebas unitarias y de contrato | 915 pruebas locales; comprobar los tres workflows del commit vigente en CI |
| Herramientas MCP | 25; product-status/product-run reutilizan el mismo motor |
| Servicios productivos certificados | 0 |

Los tres workflows de aceptación son **Verdugo verification**, **Verdugo runtime
acceptance** y **Verdugo real service acceptance**. La aprobación debe observarse
para el commit concreto: una prueba del núcleo no sustituye ejecución de las
bibliotecas ni certifica un despliegue productivo. La aceptación usa datos sintéticos.

## Plan de lo que falta

Estado actual y alcance de las operaciones, con las identificaciones históricas de las tandas:
[docs/PLAN_CONEXION.md](docs/PLAN_CONEXION.md) (y `docs/plan_conexion.json` para agentes).

## Continuación v0.21: 88 operaciones adicionales

> **Corrección v0.21.1 (revisión):** `google-ads` conserva su lectura con evidencia original añadida (`googleapis/googleapis@97f6460c35`: ruta REST `GET /v26/customers:listAccessibleCustomers` en `customer_service.proto`; encabezado `developer-token` en `google/ads/googleads/interceptors/metadata_interceptor.py` de google-ads-python). `meta-ads` vuelve a pendiente: los SDK oficiales de Meta (Python, Node, PHP, Java y Ruby) envían `access_token` en la URL y ninguno respalda el encabezado Bearer que usaba el contrato. Quedan 87 operaciones de la tanda, 25 contratos HTTP nuevos y 1 pendiente.

La segunda tanda histórica v0.21 incorpora **87 operaciones implementadas y `meta-ads` pendiente** después de la corrección v0.21.1. La aceptación del commit vigente exige los tres workflows completos.
Las últimas 68 incluyen 41 operaciones locales con código original, una comparación propia de reglas NAP originales y 26 lecturas HTTP.
[Alcance, dependencias y evidencia del complemento](docs/ACEPTACION_COMPLEMENTO_V021.md).
Los programas originales comparten Engine, product-run, auditoría y SQLite.
Se agregan perfiles npm y CLI fijados; las operaciones siguen deshabilitadas por defecto.
No se certifica una instalación productiva ni ejecución en Termux de estos binarios Linux.
[Operaciones, dependencias y evidencia](docs/AMPLIACION_V021.md).

## Continuación v0.20: primera ampliación de 87 operaciones

76 operaciones de bibliotecas originales, dos consultas de datos originales fijados
por commit y nueve contratos HTTP nuevos utilizan el mismo Engine, workflow y SQLite.
`product-run` acepta análisis locales y referencias entre resultados, además de las
42 observaciones HTTP acotadas disponibles. El máximo es 127 operaciones seleccionadas
más la instantánea comercial: 128 pasos, con 32 KiB por operación y 1 MiB por manifiesto.

Los SDK de agentes ejecutan una herramienta local fija; no invocan modelos ni crean
agentes autónomos. Whisper calcula características de audio; no transcribe. Las nueve
lecturas HTTP nuevas se prueban con servidores de respuestas sintéticas, sin certificar
sus servidores originales. Todo permanece deshabilitado hasta la revisión del operador.
[Operaciones, perfiles de dependencias y evidencia](docs/AMPLIACION_V020.md).

## Continuación v0.19: una operación conjunta del producto

- `product-status` reúne las 322 piezas, las operaciones disponibles y el estado comercial local.
- `product-run` coordina hasta 33 consultas acotadas disponibles y una instantánea comercial
  dentro del mismo Engine, workflow y SQLite. Revisa todas las conexiones seleccionadas
  antes de comenzar. Un fallo detiene la ejecución y conserva la evidencia ya obtenida.
- El informe identifica resultado nuevo/reutilizado, hora original, clave y huella por paso.
  Reabrir el motor con el mismo ID recupera lo guardado; un ID nuevo solicita otra lectura.
- Cuatro contratos nuevos: Apache Answer, Caddy, SeaweedFS y Dagster. Los tres últimos
  requieren proxy autenticador revisado; todo sigue deshabilitado por defecto.
- 36 pruebas nuevas; el flujo de 33 consultas usa respuestas sintéticas y el flujo HTTP
  de seis servicios usa sockets locales. Caddy original tiene una aceptación separada
  por commit en CI, detrás de un proxy de pruebas con autenticación comprobada.

```sh
python -m verdugo --state :memory: product-status
python -m verdugo --config verdugo.local.json product-run @examples/product-observe.json
python -m verdugo --config verdugo.local.json product-run @examples/product-observe.json --execute
```

El ejemplo requiere seis servicios configurados por el operador. No los instala ni
aprueba: sin configuración devuelve `blocked` sin llamadas externas. Las operaciones
restantes siguen disponibles mediante `workflow`. La revisión v0.19 dejó **175 conectores
pendientes** (88 después de v0.20), no despliega un panel ni acredita ventas. [Alcance y pruebas](docs/PRODUCTO_V019.md).

## Continuación v0.18: dos lecturas del mismo motor

Se conserva la continuación v0.17 del plan de Claude y se implementan dos
operaciones más de la primera tanda. **No son dos despliegues nuevos**:

- `uptime-kuma / monitors.summary`: cuenta monitores habilitados y pausados con
  su API nativa autenticada. Habilitado **no** significa que el sitio esté disponible.
- `gotenberg / health.summary`: resume las comprobaciones de salud de la API,
  solo detrás de un proxy autenticador revisado. No convierte documentos ni prueba PDFs.

Comparten Engine, CLI/MCP, autenticación por empresa, flujo con dependencias,
idempotencia y SQLite. Sus 26 pruebas de contrato y sockets locales usan respuestas
sintéticas; ningún servidor upstream de estos dos fue instalado o certificado.
Se mantienen deshabilitados, sin revisión de licencia ni permisos aprobados por defecto.
[Fuentes fijadas, configuración y límites](docs/TANDA1_V018.md).

## Qué añade v0.17

Continuación del plan de Claude en la primera tanda, sin sustituir su motor:
**OpenRefine**, **Steel Browser**, **Crawl4AI** y **Fides** tienen ahora una consulta
acotada cada uno. Las rutas, formas de respuesta y autenticación se verificaron en
sus commits fijados; se guardan solo recuentos y estados, nunca el cuerpo privado.

OpenRefine, Steel y la ruta elegida de Crawl4AI no autentican nativamente: el motor
exige `auth_mode=reviewed_proxy_bearer` y `proxy_auth_reviewed=true`, que el operador
solo debe habilitar tras revisar su proxy. No se crea ni se presume dicho proxy.
Fides utiliza su OAuth nativo. Los cuatro permanecen deshabilitados por defecto.

Hay 24 pruebas nuevas: rutas, privacidad, credenciales, parámetros prohibidos,
esquemas incompatibles, aislamiento, CLI/MCP y un flujo de cuatro lecturas con
reapertura de Engine y reanudación sin repetir llamadas. Son pruebas sintéticas
con HTTP local, **no instalación ni aceptación de proveedores auténticos**.
También se corrigió `init`: ahora informa las 322 entradas, no las 100 históricas.

Se mantienen 300 permitidas por política, 22 excluidas, 56 piezas de construcción
y 0 proveedores productivos certificados. Pasamos de 59 a 63 conectadas según la
definición del mapa; quedan 181 pendientes. La tanda 1 completa no está terminada.
[Contratos y evidencia v0.17](docs/TANDA1_V017.md).

## Qué añade v0.16

Tres conectores gratuitos más, con ruta y autenticación tomadas del código fuente en el commit
fijado: **Cal** (citas por estado), **Owncast** (personas conectadas al chat del en vivo) y
**Lighthouse CI** (proyectos auditados). Quedan 59 conectadas y 185 pendientes.

## Qué añade v0.15

**Mapa de conexión de las 322 piezas y 13 conectores nuevos de solo lectura, todos gratuitos.**

- `sources/connections.json` clasifica cada pieza: servicio (75), biblioteca (139),
  componente (56), cli (21), mcp (6), protocolo (1), datos (2) y excluido (22). El estado
  no se escribe a mano: `conectado` solo si hay adaptador implementado y licencia libre.
- Conectores nuevos, cada uno con ruta y autenticación tomadas del código fuente en su
  commit fijado: vLLM, Ollama, Label Studio, Grist, Datasette, Svix, Cube, Langflow,
  Android SMS Gateway, SendPortal, CrowdSec, ClickHouse y Dittofeed. Todos `GET`, una página,
  y guardan solo recuentos o estados (nunca correos, nombres, IPs, números ni payloads).
- Sin servicios de pago: Stripe, Twilio, Mercado Pago, E2B y Composio salieron del catálogo y se
  reemplazaron por Android SMS Gateway, Krayin CRM, SendPortal, microsandbox y Huginn (gratuitos
  y autoalojados). El catálogo sigue en 300 libres.
- Nuevo comando `python -m verdugo connections [ID]` y herramienta MCP `verdugo_connections`.
- Resultado: 56 conectadas, 56 piezas de construcción, 188 pendientes, 22 excluidas.
  Ningún proveedor real fue probado. [Evidencia y condiciones](docs/CONECTORES_V015.md).

## Qué añade v0.14

**Un solo catálogo de 322 entradas y una política de licencias que falla cerrada.**

- Se unieron, sin repetir, el núcleo de 100, los 121 libres de la lista de Josue
  (21 ya estaban en el núcleo) y tres bloques nuevos: agentes autónomos (40),
  plataforma de producto (40) y motor de datos propios (42). Total libre: **300**.
- La licencia de cada entrada se leyó del archivo en la raíz del commit fijado y quedó
  en `sources/licenses.json`. Solo cuentan como libres MIT, Apache-2.0, BSD, ISC, CC0,
  Unlicense y PostgreSQL. 12 son libres solo en su núcleo (no usar carpetas enterprise)
  y 3 son libres con una condición escrita.
- 22 entradas del núcleo original (AGPL/GPL/LGPL, Elastic, Sustainable Use y la licencia
  propia de Remotion) quedan **registradas pero excluidas**: el Engine rechaza cualquier
  plan, lectura o escritura sobre ellas (`Excluded by license policy`) antes de llamar a
  nada. Sus adaptadores siguen en el código y en el historial; solo se pueden operar si
  el operador escribe en su configuración privada una excepción con nombre y motivo
  (`license_policy_exception: {approved_by, reason}`). La plantilla nunca la incluye.
- Consecuencia práctica: los ejemplos que usan Twenty, Postiz, Plausible o Matomo
  (`commercial-overview`, `contact-bridge`, `marketing-reads`) quedan bloqueados por
  política. El CRM con escritura necesita un reemplazo con licencia libre.
- Nuevo comando `python -m verdugo licenses [ID]` y herramienta MCP de solo lectura
  `verdugo_license_policy`. `status` y `sources` muestran licencia y política por proyecto.
- Registrar no es integrar: los 222 proyectos nuevos no tienen adaptador todavía.
  [Catálogo completo con licencias](docs/CATALOGO_300.md).

Esto no es asesoría legal: `license_review` sigue `pending` en las 322 entradas.

## Qué añade v0.13

Seis operaciones de consulta en el mismo motor: Postiz (canales), Payload y
Ghost (estado de contenido), Plausible y Matomo (estadísticas agregadas), y
Saleor (catálogo limitado). No publican contenidos ni disparan campañas.

Las lecturas POST se limitan a contratos fijos, no GraphQL o métodos arbitrarios.
El token de Matomo no aparece en URLs ni planes; el JWT de Ghost se renueva sin
romper el replay. Se retienen métricas y recuentos, no cuerpos privados completos.
Hay 21 pruebas nuevas, incluyendo HTTP local, errores, privacidad, aislamiento,
CLI/MCP y un workflow de seis pasos con reapertura de Engine.
[Alcance, fuentes y pruebas](docs/MARKETING_READS_V013.md).

## Qué añade v0.12

Siete nuevos conectores de consulta delimitada: Airbyte Cloud (workspaces),
Infisical (projects), GrowthBook (settings), OpenMeter OSS v1 (meters),
Nango (connections), Trigger.dev (runs) y Documenso v2 (envelopes).

En los siete, un filtro valida la respuesta y descarta el cuerpo original
antes de que Engine persista los resultados. Solo almacena recuentos y,
en Trigger y Documenso, estados reconocidos. Así no conserva etiquetas
personales, payloads de ejecuciones, datos de firmantes o secretos que
puedan venir del proveedor. Son llamadas GET autorizadas, no servicios
instalados ni certificados. [Contratos y evidencia](docs/METADATA_PROVIDERS_V012.md).

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

**328 entradas siguen pendientes de conector.** Los adaptadores HTTP necesitan
aceptación de versiones/ediciones/permisos por instancia; Las aceptaciones de Qdrant, Meilisearch y Caddy
no validan los otros proveedores. No hay despliegue productivo, conexión automática de este
chat al MCP, servicio 24/7, cobros reconciliados ni probabilidad comercial demostrada.
No se activan campañas, contactos, compras ni infraestructura de pago al instalar.

Documentación: [v0.13](docs/MARKETING_READS_V013.md), [v0.12](docs/METADATA_PROVIDERS_V012.md), [v0.11](docs/READ_PROVIDERS_V011.md), [v0.9](docs/RUNTIME_V09.md), [v0.10](docs/RUNTIME_V010.md),
[perfiles](docs/RUNTIME_PROFILES_V010.md), [arquitectura](docs/ARCHITECTURE.md),
[control comercial](docs/COMERCIAL_30_DIAS.md), [eventos](docs/EVENTS.md),
[piloto y respaldos](docs/PILOTO_Y_RESPALDOS_V06.md), [fuentes](docs/GITHUB_SOURCES_V08.md).
El historial previo se conserva en [README v0.8](docs/HISTORICAL_README_V08.md).

### Piloto 666 en construcción

La primera operación nueva usa Semantic Kernel original del commit fijado para invocar una función local determinista. El flujo de ejemplo planea, pide aprobación, simula y compara recuentos sintéticos, conservando el replay en SQLite. No usa un modelo ni demuestra clientes o ingresos reales. Estado y reproducción en [PILOTO_666.md](docs/PILOTO_666.md).
