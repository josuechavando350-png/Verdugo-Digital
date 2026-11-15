# Piloto 666: avance parcial del lote 1

Diez de 183 piezas del primer lote tienen una operación nueva implementada. El segundo lote sigue en cero. Las 666 piezas permitidas están registradas; el producto autónomo de PLAN_666 todavía no está terminado.

## Operación delimitada

`semantic-kernel / objective.plan` invoca `Kernel.invoke` y `KernelFunctionFromMethod` originales. Registra exactamente una función local del proyecto que asigna capacidad y presupuesto ficticios entre canales conocidos. Semantic Kernel no inventa el plan, no elige herramientas y no razona con un modelo. La heurística y la simulación son código propio en `verdugo/objectives.py`.

El ejemplo `examples/kernel666.synthetic.json` usa el mismo Engine, CLI, MCP y SQLite existentes:

1. El SDK ejecuta una función determinista sobre un objetivo sintético de 20 clientes.
2. `core / objective.simulate` exige la aprobación exacta de un operador con rol `approver` antes de ejecutar 128 simulaciones binomiales.
3. `core / objective.measure` compara el resultado guardado con recuentos sintéticos de igual exposición. No convierte esos recuentos en clientes reales.
4. Tras cerrar y reabrir SQLite, el flujo devuelve los mismos resultados sin ejecutar de nuevo el SDK ni la simulación.

El presupuesto, los contactos y los resultados son hipotéticos. Los intervalos de Wilson describen los recuentos suministrados; los percentiles de simulación condicionan a tasas fijas y excluyen errores del modelo y cambios del mercado. No constituyen una probabilidad calibrada de éxito comercial.

## Fuente, instalación y prueba

- Repositorio: `microsoft/semantic-kernel`.
- Commit: `ff22ec32ed31096c98ad63376d4ecc9aefe0ff38`; MIT comprobada en el registro.
- Contrato original: `sources/contracts-kernel666.json` conserva rutas, blobs Git y SHA256 de seis archivos revisados.
- Se construye desde el archivo del commit fijado, verificando SHA256. El wheel publicado con la misma versión 1.47.0 difería en dos archivos: se rechazó esa equivalencia. Antes de invocar se comparan los cinco módulos SDK revisados con el contrato.
- Las dependencias transitivas están fijadas en `requirements/runtime-kernel666.constraints.txt`. El SDK arrastra clientes Azure/OpenAI como dependencias, pero esta operación no los configura ni los ofrece como proveedores; ningún proveedor de pago se utiliza.
- El worker elimina el entorno heredado, aplica límites de tiempo/salida y bloquea sockets Python. Eso no es aislamiento de código hostil. La aceptación de GitHub añade un namespace de red del sistema operativo.

Preparación explícita, fuera del motor, con Python 3.12 en Linux:

```sh
python3.12 -m venv --copies /tmp/verdugo-kernel666-venv
/tmp/verdugo-kernel666-venv/bin/python -m pip install -r requirements/runtime-kernel666.txt
/tmp/verdugo-kernel666-venv/bin/python -m pip check
VERDUGO_KERNEL666_PYTHON=/tmp/verdugo-kernel666-venv/bin/python /tmp/verdugo-kernel666-venv/bin/python tests_runtime/accept_pilot666.py --out /tmp/pilot666-execution-evidence.json
```

La aceptación usa exclusivamente fixtures sintéticos, habilita la revisión del runtime de prueba y comprueba aprobación, ejecución original, CLI/MCP y replay. La plantilla normal mantiene la integración desactivada hasta la revisión del operador. El ejemplo `examples/objective666.synthetic.json` permite probar la base determinista sin instalar Semantic Kernel; esa ruta no cuenta como otra integración.

## Pendiente

MetaGPT está bloqueado por su dependencia original ausente. OpenManus es la siguiente pieza por revisar. Faltan las demás piezas, el modelo local con licencia de pesos revisada, memoria, calibración, pruebas conjuntas de cada perfil y operación con información real autorizada. No se han desplegado servicios, publicado contenidos, enviado mensajes ni gastado presupuesto. `live_verified` sigue en cero. La cola de `registry-666.json` es el snapshot inmutable del registro; `docs/plan_conexion.json` y el inventario calculado reflejan las operaciones implementadas después.

## Incremento ejecutivo: Agno y AG2

| SDK | Operación | Alcance probado | Lo que no prueba |
|---|---|---|---|
| Agno 3.2.0 | `objective.plan` | Dos pasos originales `Workflow`/`Step`: heurística fija y comprobación de presupuesto, con telemetría desactivada | Razonamiento o selección autónoma de herramientas |
| AG2 1.3.1 | `actions.check` | Una `FunctionTool` original revisa costos y exposición de acciones sintéticas, usando `MemoryStream` efímero | Aprobación del operador o ejecución de esas acciones |

`examples/executive666.synthetic.json` compone los SDK conectados con referencias de resultados y conserva la aprobación y medición del mismo motor. El flujo conjunto original pasó localmente, incluido el rechazo de un presupuesto insuficiente y replay después de cerrar SQLite. Las 750 pruebas unitarias pasaron. La aceptación CI del incremento se observa por separado.

`requirements/runtime-agno666.txt` y `runtime-ag2666.txt` construyen desde archivos del commit exacto con SHA256; sus constraints fijan dependencias. `sources/contracts-executive666.json` vincula las funciones revisadas a archivos y blobs originales. Cada invocación comprueba los módulos revisados de su instalación. Ningún modelo, extra comercial ni servicio está configurado. Los planes usan la misma matemática propia: no son estimaciones independientes ni una votación de agentes.

## Langroid: comprobar afirmaciones delimitadas

`langroid / claims.check` despacha una única `ToolMessage` por el `Agent` original con LLM, vector store y parser desactivados. Comprueba aritméticamente si aumentó la tasa de conversión, bajó el costo por cliente o los ingresos declarados superan el gasto publicitario. Puede devolver `supported`, `contradicted` o `insufficient_data`; no verifica verdad semántica, causalidad, ganancias netas ni ingresos reales. El ejemplo conjunto contradice las tres afirmaciones sobre sus recuentos sintéticos.

El SDK intenta cargar `cl100k_base` durante la importación, aun con el parser del agente desactivado. `tests_runtime/prepare_tokenizer666.py` prepara explícitamente su caché fuera del motor, con el SHA256 fijado en tiktoken 0.14.0. El motor exige esos bytes y no los descarga. Se revisó MIT del tiktoken original y se guardó su licencia; son reglas de tokenización, no pesos de un LLM. La aceptación offline conjunta pasó localmente; 757 pruebas unitarias pasan.

MetaGPT no tiene adaptador: su `requirements.txt` fijado exige `lancedb==0.4.0`. El resolvedor falla bajo Python 3.11 y el endpoint de esa versión respondió 404; la lista de releases tampoco la contenía el 2026-11-15. La revisión de código y el bloqueo quedan en `sources/contracts-reasoning666.json`; no se sustituyó una dependencia ni se ignoró el fallo.

## Griptape y BeeAI: escenarios y revisión

| SDK | Operación | Código original ejecutado | Límite |
|---|---|---|---|
| Griptape 1.13.0 | `objective.scenarios` | `Pipeline` con dos `CodeExecutionTask` de callbacks fijos y `TextArtifact`; compara dos a cuatro escenarios | La heurística y Pareto son propios; no acepta código del usuario ni demuestra optimalidad real |
| BeeAI 0.1.86 | `review.route` | `Workflow` y estado Pydantic: evaluación y una de tres rutas | Recomienda revisar límites, estrategia o solicitar al operador; nunca concede aprobación |

El contrato `sources/contracts-flow666.json` conserva código original de ambos commits, blobs, SHA256 y archivos instalados comprobados antes de cada ejecución. Los perfiles separados se preparan con `requirements/runtime-griptape666.txt` y `runtime-bee666.txt`. BeeAI conserva `litellm==1.100.4` exigido por su fuente fijada; no se actualiza automáticamente ni se configura como proveedor.

La aceptación conjunta ejecutó seis SDK y ocho pasos por el worker restringido: aprobación exacta, medición, afirmaciones contradichas, comparación de escenarios, revisión y replay SQLite. Las tres ramas de revisión y presupuesto insuficiente se probaron con los SDK originales. Las **761 pruebas** pasan. La aceptación CI del nuevo incremento todavía debe observarse. No hubo modelos, llamadas a proveedores ni efectos externos.

## Strands, Unified Planning y VoltAgent

| SDK | Operación | Alcance ejecutado |
|---|---|---|
| Strands, dentro de Harness SDK | `limits.parallel` | `GraphBuilder` original ejecuta dos comprobaciones propias de presupuesto/capacidad y espera ambas antes de recomendar revisión |
| Unified Planning | `sequence.validate` | Validador secuencial original con cinco etapas y precondiciones fijas; rechaza saltarse revisión, repetir una etapa, no alcanzar medición o incumplir límites |
| VoltAgent | `measurement.review` | Workflow original de dos pasos compara medición sintética y mediana simulada, y recomienda revisión |

Strands usa ejecutores deterministas soportados por el SDK, sin agentes LLM, tokens ni sesiones persistentes. Su build VCS original conserva `1.65.1.dev10+gc8e1351a5a6218c8f5c2417534aedbd021882a76`, construido desde el commit exacto. Unified Planning se construye desde un archivo SHA256 fijado; `0.0.0` es el fallback de metadatos declarado por su propio `hatch-vcs`, **no una versión publicada**. Los módulos ejecutados se comprueban contra blobs y SHA256 de `sources/contracts-planning666.json`.

VoltAgent 2.11.1 usa un perfil Node 24.22.1 separado, lockfile y bundle npm fijados. Diez archivos de su sourcemap coinciden byte a byte con el código original revisado; esto no equivale a demostrar una compilación reproducible. `NODE_ENV=production` evita el refresco de modelos al importar; `voltOpsSync.sampling.strategy=never` elimina los exportadores remotos. Memoria y observabilidad son efímeras. El guard bloquea conexiones y procesos, y CI añade aislamiento de red del sistema operativo. El instalador explícito omite scripts npm.

El flujo conjunto pasó con **nueve SDK, once pasos y 766 pruebas unitarias**, incluyendo cinco rechazos del validador formal, dos rechazos de límites, ambas recomendaciones de medición, aprobación exacta y replay tras reabrir SQLite. Las respuestas del validador son diagnósticas: el booleano hipotético de revisión **no es una aprobación**, no modifica autorizaciones ni verifica resultados comerciales. La aprobación real sigue perteneciendo al operador de Engine. CI de este incremento permanece pendiente hasta observarlo.

### Corrección reproducible de Strands

CI del commit `2b0b8dc594f403674330c9cd90ec964949d137ba` rechazó la versión de Strands: Git abrevió el mismo SHA con nueve caracteres en CI y ocho localmente. El código original coincidía, pero el requisito de versión exacta hizo fallar correctamente la aceptación. La compilación fija ahora `SETUPTOOLS_SCM_PRETEND_VERSION` al identificador completo de arriba; no relaja el control de módulos ni modifica el SDK. Esta variable se requiere al preparar manualmente el perfil y está fijada en el workflow de CI. El checkpoint corregido `1e12900b5c275345d5c27d6adda448c80896232d` pasó los tres workflows, incluido el piloto aislado por red; enlaces en PLAN_666. El fallo anterior permanece documentado.


## OpenManus: seguimiento de etapas fijas

`openmanus / stages.track` usa `PlanningTool` original para crear, marcar y borrar un plan efímero de cinco etapas: plan, límites, revisión del operador, simulación y medición. Acepta únicamente cinco estados de una enumeración fija sobre datos demo; conserva recuentos y diagnósticos de orden. Declarar una etapa completada no demuestra su ejecución ni concede aprobación en Engine. La detección de finalización fuera de orden es una regla propia, no razonamiento del SDK.

La construcción original 0.1.0 omite el namespace `app.sandbox.core` y su configuración. Se conserva el archivo original SHA256 del commit; el worker copia sus 82 archivos `app/` intactos y comprobados a una carpeta privada. Solo allí escribe configuración vacía exigida por Pydantic. No configura ni ofrece proveedores; los logs temporales desaparecen al cerrar el worker. No instancia sandbox, navegador, shell, buscador ni LLM. `sources/contracts-manus666.json` conserva blobs Git y SHA256, diferenciando archivos revisados de archivos solo cotejados.

Preparación explícita: instalar `requirements/runtime-manus666.txt` con Python 3.12 Linux y ejecutar `tests_runtime/prepare_manus666.py` con ese intérprete. Se resuelven las dependencias de `setup.py` y tres imports exigidos por el `requirements.txt` original. Torch usa una rueda CPU con SHA256 fijado; no se descargan CUDA, navegadores ni pesos de modelos. `VERDUGO_MANUS666_PYTHON` selecciona el perfil del operador. El motor no instala ni descarga nada.

El incremento añade comprobaciones de archivo alterado, rutas inesperadas, parámetros no permitidos, finalización fuera de orden y el hecho de que marcar todo completado no autoriza efectos externos. Las 770 pruebas unitarias pasan. La prueba conjunta pasó con diez SDK y doce pasos, con aprobación, CLI/MCP y replay SQLite; CI de este incremento se observa por separado.

## Dependencias que bloquean otras piezas

DeerFlow exige `langgraph-api>=0.8.1`; el archivo LICENSE de la rueda oficial 0.8.1 es Elastic-2.0. Open Deep Research exige `pymupdf>=1.25.3`; COPYING de la rueda oficial 1.25.3 declara AGPL-3.0 o licencia comercial. Esas instalaciones revisadas no cumplen la política de este repo. No se instalaron, no se agregaron excepciones y las dos piezas siguen pendientes. Se guardan fuente del requisito, blob, hash del artefacto y texto de licencia en `sources/contracts-executive-blockers666.json`. Esto no afirma que toda versión futura o integración mínima separada sea imposible.

La instalación CI detectó una URL de Torch duplicada: una copia en constraints no tenía el fragmento SHA256 y pip la consideró distinta de la URL fijada en requirements. Se eliminó esa duplicación; la única referencia restante conserva versión CPU y SHA256 exactos. La resolución completa con pip 25.0.1, igual que CI, pasó localmente; no cambió la dependencia ejecutada.
