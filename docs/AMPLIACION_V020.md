# Ampliación v0.20: 87 operaciones del mismo producto

Base: `b98f5cc8edd1543b08188c36459f01154ef00c48` (v0.19, PR #18).
El catálogo conserva 322 entradas: **156 conectadas bajo política, 88 pendientes,
56 piezas de construcción y 22 excluidas**. Hay 175 adaptadores implementados;
19 HTTP históricos están bloqueados por licencia. Una operación delimitada no
representa toda la funcionalidad del proyecto original.

## Resultado comprobado localmente

- 634 pruebas de núcleo y contratos, todas aprobadas en Python 3.12.
- Las 87 operaciones nuevas juntas en un `product-run`: 88 pasos persistidos,
  contando la instantánea comercial. Duración observada: 443,581 segundos.
- 76 bibliotecas originales instaladas con versiones exactas y dos datos originales
  vendorizados, verificados por SHA de blob Git antes de cada consulta.
- Nueve contratos HTTP probados contra respuestas sintéticas por sockets locales.
  **Cero servidores originales nuevos probados** en esta ampliación.
- Reapertura de SQLite y reanudación completa: sin repetir bibliotecas ni HTTP,
  conservando resultados y fecha original de cada observación.
- Datos de prueba `demo`; cero clientes de pago reportados. Ninguna prueba se
  ejecutó en el teléfono ni acredita despliegue, captación o ingresos.

La evidencia local está en [evidence/v020-local.json](evidence/v020-local.json).
Las ejecuciones de GitHub Actions son evidencia adicional por commit: no se
presumen aprobadas por el resultado local. La matriz de aceptación ejecuta grupos
48/20/10 de bibliotecas y datos; el flujo completo de 87 se selecciona aparte.

## Uso conjunto

`product-status` describe las 42 rutas HTTP de observación y 97 operaciones locales
actuales. `product-run` coordina selecciones de ambas, con dependencias `$ref`,
preparación previa de todos los contratos, la auditoría e idempotencia del Engine
existente y una única SQLite por empresa. Un fallo conserva lo ejecutado; el mismo
ID recupera el resultado guardado. Un nuevo ID solicita una nueva ejecución.

Ejemplo de análisis que alimenta al siguiente, sin servicios externos:

```json
{"id":"documento-demo","dataset":"demo","currency":"MXN","services":[],
 "analyses":[
  {"id":"convertir","service":"markitdown",
   "params":{"dataset":"demo","html":"<h1>Informe</h1><p>Resultado de ejemplo.</p>"}},
  {"id":"segmentar","service":"spacy","depends_on":["analysis-convertir"],
   "params":{"dataset":"demo","text":{"$ref":"analysis-convertir.result.markdown"}}}
 ]}
```

Revisar la configuración privada de ambos servicios antes de ejecutarlo: `enabled`,
`license_reviewed`, `runtime_reviewed` y versión exacta. Primero ejecutar sin
`--execute` para revisar el plan. El motor no instala dependencias ni servidores.

El límite del flujo es 128 pasos, incluido el cierre comercial: hasta 127
operaciones seleccionadas. Cada operación conserva un máximo de 32 KiB de
parámetros; el manifiesto completo tiene un límite de 1 MiB. No se aceptan rutas,
credenciales, comandos, modelos descargables ni SQL arbitrario desde parámetros.

## Dependencias reproducibles

Las incompatibilidades de pandas, protobuf, MCP y otros paquetes obligan a usar
14 entornos separados; todos son trabajadores del mismo Engine. Los requisitos
exactos y sus restricciones están en `requirements/runtime-*.txt`. Los commits
de evidencia de API y las versiones de paquetes son campos distintos: no se
presenta un wheel como si hubiera sido compilado desde el commit del catálogo.

En Python 3.12, el instalador de aceptación prepara perfiles exclusivamente en
el proceso de CI/desarrollo; no está expuesto por CLI/MCP del producto:

```sh
python tests_runtime/install_expansion.py --group expansion
python tests_runtime/install_expansion.py --group interop
python tests_runtime/install_expansion.py --group knowledge
VERDUGO_RUNTIME_REQUIRED=1 python tests_runtime/accept_expansion.py --group expansion
VERDUGO_RUNTIME_REQUIRED=1 python tests_runtime/accept_expansion.py --group interop
VERDUGO_RUNTIME_REQUIRED=1 python tests_runtime/accept_expansion.py --group knowledge
```

Para el flujo completo, definir las 14 variables `VERDUGO_<PERFIL>_PYTHON` según
la tabla siguiente, activar `VERDUGO_RUNTIME_ALL=1` y ejecutar
`PYTHONPATH=tests_runtime:. python -m unittest test_expanded_product.ExpandedProduct.test_all_87_share_one_engine_and_database -v`.
El worker desactiva red Python y descarga de modelos. En CI se añade aislamiento
de red del sistema operativo; un entorno virtual por sí solo no es un sandbox.

## Operaciones locales añadidas

Cada fila identifica la acción realmente ejecutada. Las salidas son transformaciones
acotadas de los datos entregados; no prueban por sí mismas calidad predictiva,
causalidad, identidad, veracidad semántica ni utilidad comercial.

### Análisis tabular y estadístico

| Proyecto | Operación | Paquete / versión | Variable de entorno |
|---|---|---|---|
| `markitdown` | `html.markdown` | `markitdown` `0.1.9` | `VERDUGO_ANALYTICS_PYTHON` |
| `spacy` | `text.segment` | `spacy` `3.8.18` | `VERDUGO_ANALYTICS_PYTHON` |
| `arrow` | `campaigns.aggregate` | `pyarrow` `26.0.1` | `VERDUGO_ANALYTICS_PYTHON` |
| `polars` | `campaigns.aggregate` | `polars` `2.1.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `ibis` | `campaigns.aggregate` | `ibis-framework` `12.0.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `networkx` | `dependencies.analyze` | `networkx` `3.7` | `VERDUGO_ANALYTICS_PYTHON` |
| `sqlglot` | `campaigns.query` | `sqlglot` `30.31.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `faker` | `fixtures.generate` | `Faker` `40.54.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `statsmodels` | `regression.fit` | `statsmodels` `0.15.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `shap` | `regression.explain` | `shap` `0.54.1` | `VERDUGO_ANALYTICS_PYTHON` |
| `causal-learn` | `independence.test` | `causal-learn` `0.1.4.8` | `VERDUGO_ANALYTICS_PYTHON` |
| `numpy-financial` | `cashflows.discount` | `numpy-financial` `1.0.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `datasketch` | `sets.compare` | `datasketch` `2.0.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `nashpy` | `game.equilibria` | `nashpy` `0.0.43` | `VERDUGO_ANALYTICS_PYTHON` |
| `pymcdm` | `alternatives.rank` | `pymcdm` `1.4.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `h3` | `locations.aggregate` | `h3` `4.5.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `mlxtend` | `baskets.patterns` | `mlxtend` `0.25.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `lifelines` | `retention.estimate` | `lifelines` `0.30.3` | `VERDUGO_ANALYTICS_PYTHON` |
| `pyod` | `anomalies.score` | `pyod` `3.6.8` | `VERDUGO_ANALYTICS_PYTHON` |
| `mapie` | `regression.intervals` | `mapie` `1.6.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `pandera` | `data.validate` | `pandera` `0.36.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `great-tables` | `campaigns.render` | `great-tables` `1.1.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `river` | `stream.summarize` | `river` `0.27.0` | `VERDUGO_ANALYTICS_PYTHON` |
| `statsforecast` | `series.baseline` | `statsforecast` `2.1.1` | `VERDUGO_ANALYTICS_PYTHON` |

### Investigación, audio y protocolos

| Proyecto | Operación | Paquete / versión | Variable de entorno |
|---|---|---|---|
| `advertools` | `links.summarize` | `advertools` `0.18.0` | `VERDUGO_RESEARCH_PYTHON` |
| `pywikibot` | `wiki.clean` | `pywikibot` `11.10.0` | `VERDUGO_RESEARCH_PYTHON` |
| `splink` | `records.link` | `splink` `5.0.0` | `VERDUGO_RESEARCH_PYTHON` |
| `iceberg` | `table.snapshot` | `pyiceberg` `0.12.0` | `VERDUGO_RESEARCH_PYTHON` |
| `feast` | `features.materialize` | `feast` `0.68.0` | `VERDUGO_RESEARCH_PYTHON` |
| `openlineage` | `lineage.serialize` | `openlineage-python` `1.55.0` | `VERDUGO_RESEARCH_PYTHON` |
| `causalml` | `effect.estimate` | `causalml` `0.18.0` | `VERDUGO_RESEARCH_PYTHON` |
| `ydata-profiling` | `data.profile` | `ydata-profiling` `4.18.4` | `VERDUGO_RESEARCH_PYTHON` |
| `opendp` | `privacy.calibrate` | `opendp` `0.16.0` | `VERDUGO_RESEARCH_PYTHON` |
| `flaml` | `regression.search` | `flaml` `2.8.0` | `VERDUGO_RESEARCH_PYTHON` |
| `recommenders` | `ranking.evaluate` | `recommenders` `1.2.1` | `VERDUGO_RESEARCH_PYTHON` |
| `vowpal` | `regression.online` | `vowpalwabbit` `9.11.9` | `VERDUGO_RESEARCH_PYTHON` |
| `py-ecomplexity` | `trade.structure` | `ecomplexity` `0.5.3` | `VERDUGO_RESEARCH_PYTHON` |
| `osmnx` | `routes.shortest` | `osmnx` `2.1.1` | `VERDUGO_RESEARCH_PYTHON` |
| `mesa` | `capacity.simulate` | `mesa` `3.5.2` | `VERDUGO_RESEARCH_PYTHON` |
| `langchain` | `text.chunk` | `langchain-text-splitters` `1.1.3` | `VERDUGO_RESEARCH_PYTHON` |
| `pydantic-ai` | `messages.inspect` | `pydantic-ai-slim` `2.68.0` | `VERDUGO_LANGUAGE_PYTHON` |
| `dspy` | `answers.evaluate` | `dspy` `3.5.0` | `VERDUGO_LANGUAGE_PYTHON` |
| `docling` | `html.document` | `docling` `2.150.1` | `VERDUGO_LANGUAGE_PYTHON` |
| `pipecat` | `audio.mix` | `pipecat-ai` `1.16.0` | `VERDUGO_LANGUAGE_PYTHON` |
| `whisper` | `audio.features` | `openai-whisper` `20250625` | `VERDUGO_LANGUAGE_PYTHON` |
| `financetoolkit` | `liquidity.calculate` | `financetoolkit` `2.3.4` | `VERDUGO_LANGUAGE_PYTHON` |
| `a2a-python` | `artifact.serialize` | `a2a-sdk` `1.3.0` | `VERDUGO_PROTOCOL_PYTHON` |
| `mcp-python-sdk` | `result.serialize` | `mcp` `2.3.0` | `VERDUGO_PROTOCOL_PYTHON` |

### Herramientas de SDK y contenido

| Proyecto | Operación | Paquete / versión | Variable de entorno |
|---|---|---|---|
| `crewai` | `campaigns.tool` | `crewai` `1.15.41` | `VERDUGO_LEGACY_AGENTS_PYTHON` |
| `openai-agents` | `campaigns.tool` | `openai-agents` `0.24.0` | `VERDUGO_AGENTS_PYTHON` |
| `google-adk` | `campaigns.tool` | `google-adk` `2.14.1` | `VERDUGO_AGENTS_PYTHON` |
| `agent-framework` | `campaigns.tool` | `agent-framework-core` `1.26.0` | `VERDUGO_AGENTS_PYTHON` |
| `smolagents` | `campaigns.tool` | `smolagents` `1.26.0` | `VERDUGO_AGENTS_PYTHON` |
| `camel` | `campaigns.tool` | `camel-ai` `0.2.90` | `VERDUGO_CAMEL_PYTHON` |
| `any-agent` | `campaigns.tool` | `any-agent` `1.18.0` | `VERDUGO_ANYAGENT_PYTHON` |
| `fastmcp` | `campaigns.tool` | `fastmcp` `4.2.0` | `VERDUGO_AGENTS_PYTHON` |
| `guardrails` | `campaign.validate` | `guardrails-ai` `0.11.0` | `VERDUGO_LEGACY_AGENTS_PYTHON` |
| `instructor` | `campaign.validate` | `instructor` `1.17.0` | `VERDUGO_AGENTS_PYTHON` |
| `outlines` | `campaign.validate` | `outlines` `1.3.3` | `VERDUGO_AGENTS_PYTHON` |
| `llm-guard` | `text.filter` | `llm-guard` `0.3.16` | `VERDUGO_GUARD_PYTHON` |
| `sentence-transformers` | `vectors.compare` | `sentence-transformers` `6.3.0` | `VERDUGO_SEMANTICS_PYTHON` |
| `transformers` | `text.encode` | `transformers` `5.23.0` | `VERDUGO_SEMANTICS_PYTHON` |
| `bertopic` | `classes.weight` | `bertopic` `0.17.4` | `VERDUGO_SEMANTICS_PYTHON` |
| `ax` | `threshold.select` | `ax-platform` `1.3.1` | `VERDUGO_SEMANTICS_PYTHON` |
| `geo-optimizer` | `html.meta` | `geo-optimizer-skill` `4.23.0` | `VERDUGO_DISCOVERY_PYTHON` |
| `parsedmarc` | `report.summarize` | `parsedmarc` `11.3.0` | `VERDUGO_DISCOVERY_PYTHON` |
| `cdx-toolkit` | `captures.summarize` | `cdx-toolkit` `0.9.39` | `VERDUGO_DISCOVERY_PYTHON` |
| `news-please` | `html.article` | `news-please` `1.6.16` | `VERDUGO_DISCOVERY_PYTHON` |

### Memoria, grafos y modelos

| Proyecto | Operación | Paquete / versión | Variable de entorno |
|---|---|---|---|
| `langgraph-supervisor` | `handoff.prepare` | `langgraph-supervisor` `0.0.31` | `VERDUGO_KNOWLEDGE_PYTHON` |
| `mem0` | `history.materialize` | `mem0ai` `2.2.1` | `VERDUGO_KNOWLEDGE_PYTHON` |
| `pysd` | `curve.interpolate` | `pysd` `3.14.3` | `VERDUGO_MODELING_PYTHON` |
| `pymc-marketing` | `media.adstock` | `pymc-marketing` `1.4.0` | `VERDUGO_MODELING_PYTHON` |
| `graphrag` | `graph.cluster` | `graphrag` `3.3.0` | `VERDUGO_GRAPH_FORECAST_PYTHON` |
| `forecasting-tools` | `distribution.interpolate` | `forecasting-tools` `0.3.7` | `VERDUGO_GRAPH_FORECAST_PYTHON` |
| `indexnow-for-python` | `sitemap.inspect` | `index-now-for-python` `1.1.2` | `VERDUGO_KNOWLEDGE_PYTHON` |
| `waybackpy` | `capture.describe` | `waybackpy` `3.0.6` | `VERDUGO_KNOWLEDGE_PYTHON` |

### Consultas de datos originales

| Proyecto | Operación | Paquete / versión | Variable de entorno |
|---|---|---|---|
| `ipranges` | `address.match` | `verdugo-bundled-data` `d4ea6c582a509538907480e641bcee6821746bc3` | `Python del motor` |
| `the-great-gpt-firewall` | `domains.observe` | `verdugo-bundled-data` `60b2214d7b2cbd2c1b9d175afb31ad3024c085bb` | `Python del motor` |

## Límites relevantes de las operaciones locales

Los ocho SDK CrewAI, OpenAI Agents, Google ADK, Agent Framework, smolagents, CAMEL,
any-agent y FastMCP registran e invocan realmente una herramienta fija de totales
de campañas. No llaman a modelos, crean campañas ni ejecutan agentes autónomos.
LangGraph Supervisor prepara una instrucción nativa de traspaso; no ejecuta al
agente destino. A2A y MCP serializan estructuras nativas; no las envían.

Whisper produce características log-Mel sin descargar pesos y sin transcribir;
Pipecat mezcla PCM suministrado. Transformers usa un vocabulario local entregado;
Sentence Transformers compara vectores ya calculados; BERTopic pondera frecuencias
por clase. No se atribuye inferencia de modelos a estas operaciones.

PyMC Marketing aplica adstock con parámetros suministrados, PySD interpola una
curva y forecasting-tools interpola percentiles. Causal-learn prueba independencia,
CausalML requiere supuestos explícitos y OpenDP calcula una relación de privacidad
sin liberar datos ni gestionar un presupuesto real. Los intervalos de MAPIE usan
calibración separada. Ax selecciona el mejor umbral observado, no el óptimo futuro.

Feast, Iceberg y Mem0 utilizan almacenes temporales; la evidencia durable queda en
Engine. GraphRAG ejecuta agrupación de un grafo entregado, sin extracción por LLM.
IndexNow analiza un sitemap sin enviarlo. Waybackpy describe metadatos de una
captura suministrada sin descargarla ni autenticarla. El filtro de LLM Guard
seleccionado solo trata el patrón de correo definido; no garantiza eliminar PII.

`ipranges` comprueba pertenencia a 41 rangos IPv4 de Googlebot de la instantánea
fijada; no autentica un robot ni modifica un firewall. `the-great-gpt-firewall`
consulta observaciones mensuales por dominio: no concede permiso de rastreo.
Se incluyen sus licencias y hashes de origen junto a los archivos.

## Nueve contratos HTTP añadidos

Todos requieren configuración revisada, versión exacta y credenciales por empresa.
Permanecen apagados por defecto. La proyección elimina las cargas privadas antes
de guardarlas. Una página observada no es una exportación completa.

| Proyecto | Operación y ruta fija | Autenticación y alcance |
|---|---|---|
| DataHub | `datasets.count` · GET `/openapi/v1/entities/dataset/count` | Bearer nativo con enforcement revisado; recuentos, posible caché. |
| Jitsu | `ingest.configuration` · GET `/health` | Proxy Bearer revisado; presencia de configuración Kafka, no conectividad ni entrega. |
| Magentic UI | `sessions.summary` · GET `/api/sessions/` | Bearer de sesión nativo y usuario fijo revisado; solo recuentos. |
| Operately | `companies.summary` · GET `/api/external/v1/companies/list` | API Bearer nativo; el proveedor actualiza el último uso de la clave. |
| SigNoz | `dashboards.summary` · GET `/api/v2/dashboards` | Clave nativa `SIGNOZ-API-KEY`; primera página de 50. |
| Bifrost | `providers.summary` · GET `/api/providers` | Bearer administrativo con enforcement revisado; sin inferencia. |
| Kill Bill | `accounts.summary` · GET `/1.0/kb/accounts/pagination` | Proxy Bearer revisado que fija usuario y tenant nativos; primera página de 50. |
| Taguette | `annotations.summary` · GET `/api/project/<id>/document/<id>` | Cookie firmada nativa; proyecto y documento fijos, recuentos de anotaciones. |
| ckanapi / CKAN | `packages.count` · GET `/api/action/package_search` | Clave CKAN nativa; consulta fija, `rows=0`, sin descargar recursos. |

No se crean proxies ni se presume su existencia a partir de una marca de configuración.
Las 16 pruebas nuevas de HTTP comprueban autenticación, datos inválidos, límites,
privacidad y flujo con reinicio. Su proveedor es sintético, incluido el flujo de 87.

## Fuentes

Los manifiestos conservan repositorio, commit, archivo y SHA de blob revisado:

- [Analítica](../sources/contracts-v020.json).
- [Investigación](../sources/contracts-v020-research.json).
- [SDK y contenido](../sources/contracts-v020-interop.json).
- [Conocimiento y datos](../sources/contracts-v020-knowledge.json).
- [Plataformas HTTP y autenticación](../sources/contracts-v020-platforms.json).

`sources/parts` conserva sus 33 archivos originales y 322 registros; el plan de
continuación conserva las notas históricas en `implemented_v020` y las 88 piezas
que todavía necesitan trabajo en `items`.
