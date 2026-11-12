# Verdugo Digital v0.10 — datos y evidencia local

## Alcance implementado; aceptación real pendiente por commit

Esta entrega incorpora siete operaciones al mismo Engine, sus workflows,
CLI/MCP, aislamiento lógico por empresa, permisos, planes e idempotencia.
No añade un agente paralelo ni habilita proveedores automáticamente.

| Proyecto | Operación | Resultado delimitado |
|---|---|---|
| dlt 1.32.0 | campaigns.load | Extrae, normaliza y carga filas suministradas en DuckDB temporal; comprueba conteos y sumas. |
| LangGraph 1.2.20 | leads.route | Ejecuta un grafo de clasificación y resumen con reglas declaradas; no predice ventas ni contacta personas. |
| LlamaIndex BM25 0.8.0 | documents.rank | Ordena documentos suministrados mediante BM25; no llama LLM ni descarga modelos de embeddings. |
| Ragas 0.4.3 | retrieval.evaluate | Evalúa precisión contextual por similitud léxica frente a referencias; no certifica verdad semántica. |
| MLflow Skinny 3.18.0 | experiment.record | Registra métricas escalares en SQLite temporal, termina el run y verifica su lectura. |
| DoWhy 0.14 | effect.estimate | Estimación lineal con un grafo causal fijo de covariables, tratamiento y resultado. |
| EconML 0.17.0 | effect.estimate | LinearDML con validación cruzada interna; estima un efecto bajo supuestos declarados. |

Las dos recetas causales requieren reconocimiento explícito de los supuestos.
No demuestran ausencia de confusión no observada, solapamiento ni causalidad real.
Rechazan diseños deficientes en rango o mal condicionados; el reconocimiento
no sustituye revisión del diseño del estudio. No producen una probabilidad
comercial del 90% ni recomendaciones automáticas de gasto.

## Ejecución

Entorno de aceptación: Linux x86_64 y CPython 3.12. No se afirma soporte de las
bibliotecas nativas en Android/Termux. El núcleo sigue sin dependencias de terceros.

~~~sh
python -m unittest discover -s tests -v
python -m verdugo --state :memory: status
python -m verdugo runtime-check
# En venv dedicada, después de revisar versiones/licencias del uso previsto:
python -m pip install -r requirements/runtime.txt
python -m pip check
~~~

El ejemplo examples/local-evidence.synthetic.json compone cinco operaciones:
carga dlt, búsqueda LlamaIndex, evaluación Ragas, clasificación LangGraph y
registro MLflow. Los valores de un paso alimentan el siguiente mediante el
workflow existente. Los tests vuelven a abrir Engine y comprueban que reanudar
no ejecute nuevamente los pasos terminados.

La configuración generada mantiene todas las integraciones deshabilitadas y
las revisiones de licencia/runtime pendientes. Habilitar solamente las recetas
necesarias y revisadas; nunca publicar el archivo de configuración ni datos reales.

## Fronteras y persistencia

Se aceptan estructuras JSON acotadas, no rutas, SQL libre, código, URLs remotas,
modelos serializados ni callbacks suministrados por el usuario. El proceso hijo
no hereda secretos del entorno, tiene presupuesto de tiempo, salida limitada,
limpieza del grupo de procesos y guardia Python de red. No es un sandbox para
código hostil. La aceptación de CI utiliza namespace de red de sistema operativo.

Los almacenes de dlt y MLflow son temporales y se eliminan al concluir. El resultado
comprobado queda persistido por Engine, no por un warehouse o servidor MLflow
productivo. Un límite por archivo no es una cuota total de disco. Datos reales
siguen exigiendo seguridad del host, cifrado y política de retención.

El inventario queda en **41 proyectos con operación implementada (22 HTTP +
19 locales), 59 sin adaptador y cero proveedores certificados en producción**.
La disponibilidad de un paquete o un test unitario no se contabiliza como ejecución
real. La aceptación completa debe comprobarse en Actions para cada commit.

## Fuentes técnicas revisadas

- dlt: https://dlthub.com/docs/general-usage/pipeline y https://dlthub.com/docs/dlt-ecosystem/destinations/duckdb
- LangGraph: https://reference.langchain.com/python/langgraph/graph/state/StateGraph
- LlamaIndex: https://developers.llamaindex.ai/python/framework/integrations/retrievers/bm25_retriever/
- Ragas: https://docs.ragas.io/en/v0.4.3/concepts/metrics/available_metrics/context_precision/
- MLflow: https://mlflow.org/docs/latest/api_reference/python_api/mlflow.client.html
- DoWhy: https://www.pywhy.org/dowhy/main/getting_started/index.html y https://pypi.org/project/dowhy/0.14/
- EconML: https://www.pywhy.org/EconML/_autosummary/econml.dml.LinearDML.html

Las fuentes upstream fijadas en sources/parts no equivalen a los wheels de PyPI.
El reporte pip y la lista de versiones resueltas son evidencia separada. Las
banderas license_reviewed de los fixtures no aprueban uso comercial ni certifican
licencias de todas las dependencias transitivas.
