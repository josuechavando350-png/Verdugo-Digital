# Piloto 666: avance parcial del lote 1

Treinta y nueve de 183 piezas del primer lote tienen una operación nueva implementada: 28 locales y once lecturas HTTP con aceptación sintética. El segundo lote sigue en cero. Las 666 piezas permitidas están registradas; el producto autónomo de PLAN_666 todavía no está terminado.

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

MetaGPT está bloqueado por su dependencia original ausente. DeerFlow, Open Deep Research, DBOS y Prefect conservan bloqueos de dependencias bajo la política del repo; LiteLLM conserva un build fallido. AgentKit conserva un build original fallido; Gorilla, Scrubadub y Garak tienen bloqueos de dependencias documentados. Faltan las demás piezas, planificación guiada por un modelo, memoria duradera, calibración, pruebas conjuntas de cada perfil y operación con información real autorizada. El modelo local de Guardian solo revisa las afirmaciones sintéticas descritas abajo. No se han desplegado servicios, publicado contenidos, enviado mensajes ni gastado presupuesto. `live_verified` sigue en cero. La cola de `registry-666.json` conserva el checkpoint original de registro; los cambios de identidad oficial se documentan en `registry-666-revisions.json`; `docs/plan_conexion.json` y el inventario calculado reflejan las operaciones implementadas después.

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


## OpenManus (retirado del motor): seguimiento de etapas fijas

**Corrección posterior:** esta integración fue retirada al comprobar `html2text` GPL-3.0 obligatorio en `setup.py`. El módulo falla antes de importar el SDK; CI ya no instala ese perfil. Lo siguiente conserva el alcance de la prueba histórica y no describe una operación disponible.

`openmanus / stages.track` usa `PlanningTool` original para crear, marcar y borrar un plan efímero de cinco etapas: plan, límites, revisión del operador, simulación y medición. Acepta únicamente cinco estados de una enumeración fija sobre datos demo; conserva recuentos y diagnósticos de orden. Declarar una etapa completada no demuestra su ejecución ni concede aprobación en Engine. La detección de finalización fuera de orden es una regla propia, no razonamiento del SDK.

La construcción original 0.1.0 omite el namespace `app.sandbox.core` y su configuración. Se conserva el archivo original SHA256 del commit; el worker copia sus 82 archivos `app/` intactos y comprobados a una carpeta privada. Solo allí escribe configuración vacía exigida por Pydantic. No configura ni ofrece proveedores; los logs temporales desaparecen al cerrar el worker. No instancia sandbox, navegador, shell, buscador ni LLM. `sources/contracts-manus666.json` conserva blobs Git y SHA256, diferenciando archivos revisados de archivos solo cotejados.

Preparación explícita: instalar `requirements/runtime-manus666.txt` con Python 3.12 Linux y ejecutar `tests_runtime/prepare_manus666.py` con ese intérprete. Se resuelven las dependencias de `setup.py` y tres imports exigidos por el `requirements.txt` original. Torch usa una rueda CPU con SHA256 fijado; no se descargan CUDA, navegadores ni pesos de modelos. `VERDUGO_MANUS666_PYTHON` selecciona el perfil del operador. El motor no instala ni descarga nada.

El incremento añade comprobaciones de archivo alterado, rutas inesperadas, parámetros no permitidos, finalización fuera de orden y el hecho de que marcar todo completado no autoriza efectos externos. Las 770 pruebas unitarias pasan. La prueba conjunta pasó con diez SDK y doce pasos, con aprobación, CLI/MCP y replay SQLite; CI de este incremento se observa por separado.

## Dependencias que bloquean otras piezas

DeerFlow exige `langgraph-api>=0.8.1`; el archivo LICENSE de la rueda oficial 0.8.1 es Elastic-2.0. Open Deep Research exige `pymupdf>=1.25.3`; COPYING de la rueda oficial 1.25.3 declara AGPL-3.0 o licencia comercial. Esas instalaciones revisadas no cumplen la política de este repo. No se instalaron, no se agregaron excepciones y las dos piezas siguen pendientes. Se guardan fuente del requisito, blob, hash del artefacto y texto de licencia en `sources/contracts-executive-blockers666.json`. Esto no afirma que toda versión futura o integración mínima separada sea imposible.

La instalación CI detectó una URL de Torch duplicada: una copia en constraints no tenía el fragmento SHA256 y pip la consideró distinta de la URL fijada en requirements. Se eliminó esa duplicación; la única referencia restante conserva versión CPU y SHA256 exactos. La resolución completa con pip 25.0.1, igual que CI, pasó localmente; no cambió la dependencia ejecutada.


## Servidor MCP original: grafo temporal de etapas

`servers / graph.audit` construye el servidor `memory` original 2.1.1 desde `modelcontextprotocol/servers`, commit `e1dc4b18dbb948921da37f3d4224a628730b43b0`, con TypeScript 5.9.3 y Node 24.22.1 fijados. El cliente MCP original 2.3.1 ejecuta seis llamadas: crear entidades, crear relaciones, buscar, leer después de reabrir el servidor, borrar entidades y comprobar el grafo vacío. El transporte en memoria del SDK es de desarrollo; no se presenta como transporte MCP productivo.

La entrada solo admite hasta 16 estados sintéticos, 64 pares de índices y una consulta de estado enumerada. Nunca acepta texto libre, nombre de archivo, herramienta, URL ni credencial. Se proyectan recuentos de entidades, relaciones incidentes y duplicados omitidos. Una relación incidente puede conectar con un nodo fuera de la búsqueda: no se describe como subgrafo inducido. El JSONL temporal desaparece al cerrar el worker; Engine conserva únicamente recuentos y evidencia. Esto no ofrece memoria duradera entre ejecuciones ni razonamiento de un agente.

`sources/contracts-memory666.json` vincula seis archivos originales con sus blobs y SHA256, la compilación reproducida, el binario Node de la distribución oficial y el lock npm. Tres archivos de sourcemap del SDK cliente/servidor/transporte coinciden con su commit `fcef852f6cdafea07f36cf6fae69b37c8adf85be`; sus licencias de código Apache/MIT se leyeron. El perfil recién preparado pasó la comprobación de sus 35 artefactos. Preparación explícita: `python tests_runtime/install_memory666.py`; selección: `VERDUGO_MEMORY666_ROOT=/tmp/verdugo-memory666`. El motor no prepara perfiles.

LiteLLM permanece pendiente. Se intentó construir el archivo del commit fijado con maturin y luego con `CARGO_BUILD_JOBS=1`; ambos intentos terminaron con procesos Rust SIGKILL. La presión de recursos es una explicación plausible, no una causa del sistema operativo demostrada. No hay instalación ni operación validadas, y no se sustituyó por otra versión. Evidencia del build original en `sources/contracts-executive-blockers666.json`.

El incremento de memoria pasó localmente el flujo conjunto de once SDK y trece pasos, con reanudación SQLite, aprobación del operador y ausencia del grafo crudo en la base. El checkpoint previo de diez SDK `9b95b92926382838f23ff771168a584f1a391385` está aceptado en los tres workflows. El incremento de memoria quedó aceptado en los tres workflows del commit `cdc6fb18f5584ff23736185fd8c3dcc802d3ac7c`; enlaces en PLAN_666.

Las 773 pruebas unitarias y de contrato pasan en el incremento de memoria.

## Monty y Playwright para Python: operaciones locales limitadas

`monty / budget.evaluate` ejecuta una fórmula propia fija dentro del `Monty` y el proceso `monty` originales. Suma costes/contactos sintéticos y contrasta presupuesto/capacidad; no acepta código, imports, callbacks, montajes, rutas ni destinos. Activa comprobación de tipos y límites explícitos de tiempo, memoria, recursión y suspensiones. Los parámetros son únicamente números acotados y `dataset=demo`. Un diagnóstico favorable nunca concede aprobación.

El commit `a34e0f689cfa26f6c689fb96bd96d533cf92a926` declara 1.6.0, pero tiene 14 commits posteriores al tag publicado de igual versión. Se compilaron cliente y ejecutable desde el archivo SHA256 fijado, con Rust 1.100.0, maturin 1.15.0 y el Cargo.lock original. El primer build terminó SIGKILL; el segundo pasó desactivando LTO y optimización, con un solo proceso de compilación y los flags registrados. No se modificó el código upstream. Los 21 archivos del contrato diferencian revisión de contenido y comprobación de hashes; ocho archivos Python instalados coinciden byte a byte. El recibo por perfil detecta cambios en los binarios compilados: **no es una certificación independiente ni prueba de compilación binaria reproducible**. No se presenta este build sin optimización como una medición de rendimiento.

`playwright-python / cookies.check` usa `sync_playwright`, dos `APIRequestContext`, `storage_state` y `dispose` originales. Solo admite slots y flags sintéticos enumerados; los nombres, valores y dominio reservados son constantes internas. Comprueba eliminación de entradas caducadas, reemplazo por el mismo slot y aislamiento de un contexto nuevo. Guarda recuentos y flags de evidencia, nunca cookies crudas. No instala ni abre un navegador, no navega y no envía solicitudes HTTP. El comportamiento del almacén de cookies de APIRequestContext **no certifica la seguridad ni las restricciones de cookies de Chromium**.

El cliente Python procede de `86a5f5a81010b1dbd155263e99782442b61d0cb2` y el driver del commit upstream `8534271f0413bae6a455b7cf43b2637391bc614b` exigido por `DRIVER_VERSION`. El identificador de desarrollo fija el SHA completo para evitar abreviaturas Git variables. El contrato verifica 104 archivos Python originales y 225 artefactos instalados. El Node 26.13.1 incluido coincide con el binario de la distribución oficial cuyo archivo SHA256 se verificó. La preparación omite scripts npm y descargas de navegadores; ejecuta los scripts de build originales. El guard Node bloquea APIs de red y procesos; CI añade aislamiento de red del sistema operativo.

Preparación explícita con Python 3.12 en Linux x86_64, fuera de Engine:

```sh
python tests_runtime/install_monty666.py
python tests_runtime/install_browserstate666.py
```

Perfiles: `VERDUGO_MONTY666_PYTHON=/tmp/verdugo-monty666-venv/bin/python` y `VERDUGO_BROWSERSTATE666_PYTHON=/tmp/verdugo-browserstate666-venv/bin/python`. El instalador Monty usa rustup para el toolchain fijado. El motor no instala dependencias.

DBOS conserva estado pendiente: el `pyproject.toml` original exige `psycopg[binary]>=3.1`; el wheel Psycopg 3.3.9 inspeccionado contiene LGPL-3.0, fuera de la política permisiva de este repositorio. El LICENSE principal de DBOS sigue siendo MIT; no se reclasificó el registro ni se instaló el paquete enterprise. Los bytes y hashes de la dependencia se conservaron en `contracts-executive-blockers666.json`. Esta conclusión se limita al camino de instalación revisado.

La aceptación conjunta local pasó con trece SDK originales y quince pasos, sin SDK simulados: tres casos de límites Monty, caducidad/reemplazo de cookies, contexto nuevo vacío, aprobación exacta y replay tras reiniciar SQLite. También se verificó que el valor y los nombres internos de cookies no aparecen en SQLite. Una preparación limpia con `install_browserstate666.py` reprodujo los 225 artefactos y ejecutó la operación por Engine. Las 780 pruebas unitarias y de contrato pasan. El namespace de red local no está disponible; CI aporta esa comprobación del sistema operativo y todavía debe observarse para este incremento.


## Hatchet: borrador de política de despacho

`hatchet / policy.compile` usa el SDK original 2.0.0a1, commit `ee6d34ecd0baf10908a1a621b9b5324721026f25`. `compute_task_parameters` combina valores por defecto y una sobreescritura explícita de reintentos. `ConcurrencyStrategy` y `StatusBasedIdempotencyConfig` producen protobuf, que se serializa y se decodifica antes de conservar únicamente valores permitidos y un digest.

El código propio exige conciliación para estados `running` o `uncertain` y propone cero reintentos para cualquier escritura. Las lecturas fallidas admiten un borrador de hasta tres reintentos. Ningún resultado autoriza a ejecutarlos: `tasks_dispatched=0`, `retries_executed=0`, `approvals_granted=0`. No se crea cliente Hatchet, cola, servidor, proceso embedded, tarea ni comunicación. La retención y concurrencia propuestas no prueban que un servidor las esté haciendo cumplir.

El archivo fuente SHA256 está fijado, 413 archivos concuerdan con blobs Git y los 411 módulos Python instalados se verifican antes de usar el SDK. Esto no significa auditoría semántica de todos los archivos; el contrato distingue lo leído de lo comprobado por hash. Preparación mediante `requirements/runtime-hatchet666.txt`, perfil `VERDUGO_HATCHET666_PYTHON`, fuera del motor. El núcleo MIT está documentado; no se habilitan extras ni servicios de pago.

La aceptación local conjunta de catorce SDK y dieciséis pasos pasó con el perfil Playwright reconstruido desde cero, aprobación y reanudación SQLite sin repetir operaciones. Incluye cuatro casos adicionales de estado/tipo de operación en Hatchet. El incremento de trece SDK falló inicialmente en CI porque PEP 517 no encontraba el ejecutable `maturin` del venv; la corrección incorpora ese directorio al PATH y se comprobó generando metadatos desde el código original. La compilación completa y el aislamiento de red de CI deben observarse por commit.

Prefect sigue pendiente: el wheel original `python-slugify==9.1.0` exige `text-unidecode>=1.3`; el wheel 1.3 ofrece GPL o Artistic, fuera de la lista permitida del repo. No se quitaron dependencias ni se aprobó una excepción. La conclusión se limita a la ruta de dependencias inspeccionada.

El checkpoint de trece SDK `0bccfaa96d854e34ed11316c55f49907eda6849b` terminó con los tres workflows en `success`: compilación nativa y flujo conjunto con aislamiento de red incluidos. Esa evidencia no se extiende automáticamente a Hatchet; el nuevo incremento debe pasar su propia CI.


## Invariant: análisis local de trazas sintéticas

`invariant / trace.check` ejecuta `LocalPolicy.from_string` y `analyze` del commit `2340fe2d9cd619f73d5b67fa05bf8a08c7cad515`. Tres reglas fijas detectan envío sin revisión hipotética, envío con un estado previo incierto/en curso y lectura privada anterior al envío. La entrada admite hasta doce eventos con enums y booleanos; nunca acepta código de políticas, argumentos de herramientas, mensajes privados ni destinos. Se guardan recuentos y un digest de política, no trazas ni rangos.

El tercer patrón solo describe orden temporal: no demuestra causalidad ni filtración de datos. Un resultado sin coincidencias tampoco aprueba la acción. `LocalPolicy` elige explícitamente el motor local; no se usa el cliente remoto, ningún modelo ni detectores que requieren pesos. Cero llamadas de herramientas y cero autorizaciones.

El núcleo `invariant-ai==0.3.5` y su dependencia obligatoria `invariant-sdk==0.0.11` se construyen desde commits oficiales con archivos SHA256 fijados. El wheel publicado del segundo omite la licencia y un archivo difiere del commit inspeccionado: se instaló el fuente Apache original `bda28da6e3aa88caf1f06459b11949c3a2acc458`, sin omitir dependencias. `contracts-trace666.json` registra 111 archivos con blobs Git; 80 archivos instalados se verifican antes de cada análisis. El marcador de revisión distingue lectura parcial de comprobación de bytes.

La aceptación conjunta incluye quince SDK, diecisiete pasos, aprobación y replay CLI/MCP/SQLite. Siete casos adicionales prueban ausencia de alertas, orden inverso, revisión ausente, conciliación y multiplicidad de pares. Las 786 pruebas unitarias pasaron localmente. El checkpoint anterior de catorce SDK tiene sus tres workflows verdes; el incremento actual se valida por separado en CI.

AgentKit sigue pendiente: cinco archivos del mapa de fuentes npm no equivalen al commit fijado; con Inngest 3.54.0, el build original `tsc && tsup` falla por tipos incompatibles y `ctx` ausente. La versión de desarrollo 3.43.1 declara una advertencia crítica y no se conservó como alternativa. Gorilla/BFCL exige `html2text` GPL-3.0; Scrubadub exige `python-stdnum` LGPL-2.1. La evidencia original y los textos de licencia están en `contracts-executive-blockers666.json`; el bloqueo se limita a las rutas inspeccionadas. También se corrigió allí el blob de `pyproject.toml` de Prefect para eliminar un salto de línea añadido al guardar la evidencia.


## PyRIT: auditar registros sintéticos de herramientas

`pyrit / tools.audit` usa `MessagePiece`, `Message`, `ToolExecutionMetadata`, `validate_tool_conversation` y `match_message_tool_calls` originales. Acepta de una a ocho filas con herramientas y resultados de una enumeración fija; construye mensajes efímeros, comprueba vínculos y cuenta tipos de herramientas cuya invocación consta en el registro. Una respuesta ausente no prueba que no hubo ejecución; una invocación registrada no demuestra finalización. Los mensajes simulados no cuentan como invocaciones reales. No se ejecuta ninguna herramienta ni se concede aprobación.

El repositorio anterior `Azure/PyRIT` contiene un aviso oficial de migración, sin implementación Python. Se conserva ese aviso con blob/hash y el registro anterior; el mismo identificador apunta ahora a `microsoft/PyRIT`, commit `c91ba04c127d56229f3559c8a6146506844bc45c`, MIT leída. No cambian las 688 identidades ni la posición en cola. `contracts-toolaudit666.json` conserva 951 archivos originales; 946 módulos instalados se comprueban por hash. Eso no es revisión semántica completa.

`tests_runtime/install_pyrit666.py` ejecuta el build original 1.3.0.dev0, incluido el frontend obligatorio y su comprobación de procedencia, con Node 24.22.1 oficial y dependencias fijadas. El instalador limpio pasó y verificó la marca upstream de commit/versión/árbol sin cambios. El motor no instala paquetes ni sirve el frontend. Perfil explícito: `VERDUGO_PYRIT666_PYTHON=/tmp/verdugo-pyrit666/bin/python`.

La aceptación local conjunta cubre dieciséis SDK y dieciocho pasos con CLI, MCP, aprobación y reanudación SQLite. Ocho casos adicionales comprueban formatos chat/responses, invocaciones simuladas, respuestas ausentes, no invocadas, fuera de orden, duplicadas y sin llamada correspondiente. Las 790 pruebas unitarias pasaron. Los tres workflows del checkpoint de quince SDK están verdes; el incremento PyRIT requiere su propia aceptación CI.

Garak se instaló y pasó un experimento local antes de descubrir `mikeshardmind-base2048==1.0.4`, dependencia obligatoria MPL-2.0. Se retiró ese perfil y no se implementó ni contó un adaptador. La licencia MIT de `base2048`, dependencia distinta de PyRIT, se comprobó por separado. Los bloqueos de dependencia documentados son hallazgos acotados, no certificación exhaustiva de todas las licencias transitivas de los perfiles.


## Modelo local: vocabulario nativo y revisión sintética

`llama-cpp / tokens.check` usa `llama-tokenize` original en modo de solo vocabulario. Renderiza la plantilla oficial de Guardian para dos frases fijas sobre presupuestos numéricos sintéticos; devuelve recuentos y comprueba que caben entrada más 12 unidades de salida en un contexto acotado. La unidad se identifica como `tokens` y los campos públicos son `input_units`/`output_unit_limit`, para que el filtro de credenciales no los confunda con tokens secretos. No acepta mensajes, plantillas, comandos, rutas ni modelos del usuario.

`granite-guardian / risk.assess` usa esos mismos bytes con `llama-completion`, cargando pesos oficiales `ibm-research/granite-guardian-3.2-3b-a800m-GGUF`, revisión `920ae12a30dc3a5b0fed158a98cd5c25d506b418`, Q4_K_M, SHA256 `72735ad1cb9832df3141a4477cb1035228ba029e0b9076802305a07c870ccfb5`. Ambas fichas oficiales fijadas declaran Apache-2.0 y enlazan su texto completo, leído antes de descargar los 2.02 GB. La plantilla original procede del modelo base, revisión `3de033d89b499a18d9a573b5192bf3b967ef48c5`. Las fichas, configuración, plantilla y licencia se conservan con hashes y blobs en `sources/guardian666/` y `contracts-guardian666.json`.

La estructura de mensajes `context`/`assistant`, el riesgo `groundedness` y la semántica Yes/No se leyeron en `evaluation/models/granite_guardian_3.py` del commit fijado del proyecto Guardian. Se ejecuta el modelo cuantizado con su plantilla original; **no se afirma ejecutar el adaptador vLLM de ese archivo**. La inferencia CPU usa contexto 512, salida 12, temperatura cero, dos hilos, batch/ubatch 128 y repacking desactivado. No hay servidor ni API remota. El texto generado se interpreta y descarta: solo quedan booleanos, recuentos y hashes. La etiqueta verbal High no se convierte en una probabilidad.

El núcleo MIT de llama.cpp se recompiló desde `6d3568e31d4e4b1e4db4acb8f6ceaad0084932f3`, archivo SHA256 fijado, CMake 4.1.3 y 33 archivos ligados a blobs. La lectura de contenido fue selectiva; el resto tiene comprobación de integridad. El instalador `tests_runtime/install_guardian666.py` pasó una construcción completa y genera un recibo de artefactos del operador. Ese recibo no es certificación independiente ni prueba de reproducibilidad binaria. Perfil: `VERDUGO_GUARDIAN666_PYTHON=/tmp/verdugo-guardian666/bin/python`. El motor no descarga ni compila.

Cada worker nuevo verifica el SHA256 completo del modelo. Dentro del mismo proceso se reutiliza el digest solo mientras permanecen iguales dispositivo, inode, tamaño, propietario, permisos, mtime y ctime; la prueba incluye modificar contenido restaurando mtime. Eso reduce comprobaciones repetidas sin presentar el perfil confiado del operador como protección contra un administrador malicioso. El primer replay CLI excedió 60 segundos por verificaciones repetidas. La aceptación final conserva 60 segundos por worker y permite 180 para repetir el flujo completo de veinte pasos.

La aceptación local pasó con **18 componentes, 20 pasos y 797 pruebas**, aprobación exacta, CLI/MCP, reinicio/replay SQLite, rechazo de contexto insuficiente y controles del modelo para 200/200 y 200/900 pesos, incluido un control repetido. Hay un modelo de lenguaje en esta aceptación. Un experimento previo con batch 32 produjo un falso positivo con etiqueta High; otro con repacking terminó con salida 137 después de imprimir una respuesta. Ambos se conservan en el contrato y no se cuentan como pruebas satisfactorias. Los controles elegidos no estiman precisión ni calibración; una respuesta favorable nunca concede autorización. El checkpoint de dieciséis componentes tiene sus tres workflows verdes; el incremento actual requiere su CI.

ETHICS sigue pendiente: el aviso original apunta a pesos externos cuya licencia todavía no se ha verificado. Esto es evidencia incompleta, no una reclasificación de su código MIT ni una declaración de que los pesos sean privativos.


## InterpretML y corrección del inventario

`interpret / prediction.explain` usa `ExplainableBoostingRegressor.fit`, `predict` y `eval_terms` originales, commit `003136ef4c8beb24dd30a4b5626871b788be9acd`, versión 0.7.8 MIT. Acepta 8–32 filas de entrenamiento y 1–4 consultas numéricas sintéticas sobre contactos, gasto y clientes observados. El modelo tiene dos variables, cero interacciones, una bolsa, 16 rondas, semilla 666 y un solo proceso. Se entrena y descarta en el worker; no admite callbacks, modelos externos, archivos ni datos de clientes reales.

El resultado conserva tamaños y contribuciones absolutas medias, y comprueba que intercepto más términos reconstruye `predict`. Esa igualdad es una propiedad técnica del modelo aditivo: no demuestra una explicación causal, buen pronóstico, calibración ni exactitud fuera de muestra. La aceptación ejercita datos variables y datos constantes en cero.

El instalador explícito `tests_runtime/install_explain666.py` compila el `build.sh -release_64` original y el `npm run build-prod` original con Node 24.22.1 y lock de dependencias fijado. Copia los artefactos al wheel exactamente como exige `setup.py` para builds desde un checkout. Los 305 archivos fuente se cotejaron con Git; 82 módulos Python instalados coinciden. El contrato identifica qué contenido se leyó y qué solo se verificó por hash. El recibo vincula la biblioteca nativa y los dos artefactos de visualización; el worker rechaza candidatos alternativos del cargador. No se sirve la visualización ni se abre un navegador.

La primera reconstrucción limpia terminó con salida 137 al compilar JavaScript mientras había otras cargas. Tras retirar cachés temporales y repetir por separado, el mismo instalador pasó sin alterar el fuente upstream. Los recibos no constituyen certificación independiente ni prueba de reproducibilidad binaria. Perfil del operador: `VERDUGO_INTERPRET666_PYTHON=/tmp/verdugo-interpret666/bin/python`.

Al revisar el perfil anterior de OpenManus se detectó `html2text~=2024.2.26` obligatorio tanto en `setup.py` como en `requirements.txt`. Su COPYING GPL-3.0 coincide por SHA256 con la licencia ya leída de esa dependencia para Gorilla. Fue un error de la revisión anterior contarlo sin resolverlo. La corrección retira el adaptador del registro de operaciones y del flujo, bloquea su receta y preparación directa, elimina la instalación de CI y devuelve el proyecto a pendientes. La licencia MIT de OpenManus no se reclasifica; no se omitieron dependencias ni se habilitó una excepción. Se preservan commits, blobs, licencia y resultados históricos para explicar la corrección.

La aceptación actual pasó con **18 componentes operativos y 20 pasos**, aprobación, CLI/MCP y replay SQLite; **803 pruebas** pasan. Incluye un modelo de lenguaje Guardian y un modelo aditivo efímero, ambos sin calibración comercial. InterpretML añade una operación y la retirada de OpenManus resta otra: el total no aumenta. La aceptación CI de este conjunto corregido debe observarse en su propio commit.


## TransformerLens: diagnóstico nativo sin pesos preentrenados

`transformerlens / activations.check` usa `TransformerLensOrg/TransformerLens@284e35b4ee2deea0924894c221a3be8ad519474d`. La versión `0.0.0` es el metadato literal de ese código, no una publicación. `TransformerBridge.boot_native` construye el modelo original de 936 parámetros, una capa, dos cabezas, vocabulario de 16 símbolos, contexto ocho, CPU float32 y semilla 666. No se descargan pesos ni tokenizadores de modelos. La API antigua `HookedTransformer` fue retirada por upstream y no se utiliza.

La operación acepta únicamente de dos a seis índices sintéticos y una intervención enumerada. `run_with_cache` captura tres nombres originales (cinco entradas por alias); `run_with_hooks` aplica opcionalmente una función fija que pone a cero el residual. Una tercera evaluación verifica restauración exacta y ausencia de hooks residuales. Se comprueban formas, finitud, filas de atención normalizadas y máscara causal. Solo se conservan recuentos y diagnósticos numéricos; no se guardan logits, activaciones ni modelos.

Contrato con 392 archivos Git y comprobación de los 375 módulos Python instalados en `sources/contracts-lens666.json`; lectura semántica limitada a los archivos señalados. Todas las dependencias obligatorias se resolvieron en un perfil separado. Torch CPU 2.9.1 se reutilizó localmente desde su wheel previamente verificado, copiando únicamente sus entradas a un entorno nuevo y retirando el entorno OpenManus rechazado; CI descarga el wheel oficial fijado por SHA256. Esto no afirma una auditoría completa de las dependencias.

La aceptación conjunta pasó con **19 componentes, 21 pasos y 807 pruebas**. Incluye un LLM Guardian, un EBM efímero y este transformer de juguete sin entrenar. `llm_calls=0` en esta receta se acompaña de `toy_forward_passes=3`: no hubo inferencia de un modelo de lenguaje preentrenado. No hay explicación de razonamiento real, calibración, rendimiento productivo ni autorización automática. Los controles sin intervención en longitudes mínima y máxima conservaron salida y máscara causal. CI debe observarse para el nuevo commit.


## Bitsandbytes y candidatos nativos no aceptados

`bitsandbytes / quantization.check` ejecuta `quantize_blockwise` y `dequantize_blockwise` originales, commit `a616886cacf86701514f0cb1d6be760f967481c0`, MIT. Acepta 1–512 enteros sintéticos de −1000 a 1000, float32 CPU y bloque fijo de 64. Verifica biblioteca nativa cargada, escalas por bloque, tipo y forma de arrays, finitud y reconstrucción frente al diccionario con aritmética escalar. No admite pesos, modelos, GPU, plugins de backend ni tamaño de bloque del usuario.

El resultado informa error absoluto y bytes de la matriz cuantizada, las escalas y el diccionario de 256 valores. Para 64 valores: 256 bytes originales frente a 1092 bytes representados, incluyendo 1024 de diccionario. Para 512 valores extremos: 2048 frente a 1568, con error máximo 7.03125. No incluye objetos Python ni asignador de memoria, no mide velocidad y no estima precisión de un modelo.

`tests_runtime/install_quant666.py` usa el build CMake upstream CPU, C++ original, OpenMP y AVX512 desactivados expresamente. Se verifican 76 archivos Git y 48 archivos instalados. Perfil `VERDUGO_QUANT666_PYTHON=/tmp/verdugo-bnb666/bin/python`, Torch CPU 2.9.1 oficial y dependencias fijadas. Localmente se reconstruyó desde una extracción nueva sobre el perfil ya preparado; CI crea el perfil desde cero. El recibo vincula opciones, compilador y hash nativo, pero no es atestación independiente ni prueba de reproducibilidad binaria. El worker comprueba que el perfil no cambió desde la planificación.

La aceptación de ese checkpoint pasó con **20 componentes y 22 pasos**, aprobación, CLI/MCP y replay SQLite; **821 pruebas** pasan. Los controles de cero, un elemento, bloque parcial y extremos también pasaron. Conserva tres modelos: Guardian entrenado, EBM efímero y transformer de juguete; esta receta no añade modelos. El checkpoint anterior de 19 componentes tiene sus tres workflows verdes; consultar el CI propio del nuevo commit.

Candle completó dos builds CPU y una prueba conjunta de 20 componentes antes de revisar dependencias nativas. Tokenizers completó su rebuild con el Cargo.lock original y pruebas de codificación sintética. El primer intento limpio sufrió SIGKILL y una prueba CLI simultánea agotó diez segundos; el mismo instalador pasó tras retirar artefactos temporales y repetir por separado. El lock regenerado inicial se descartó. Estos éxitos técnicos no resolvieron las licencias detectadas después: `colored` MPL-2.0 en Tokenizers; `foldhash` Zlib y `yoke` Unicode-3.0 en Candle. Las dos últimas son permisivas, pero no están incluidas en la lista explícita del proyecto.

Ambos candidatos conservan fuentes, contratos y pruebas de integridad para revisión, pero `SPECS` está vacío, las recetas y los instaladores fallan antes de importar o descargar, no tienen perfil de motor y no se ejecutan en CI. Se retiraron los perfiles locales; no se cuentan como conexiones. La aceptación experimental de 21 componentes fue interrumpida y no se conserva como aceptación vigente. Los hallazgos de dependencias siguen siendo acotados, no auditoría exhaustiva de todo el portafolio.


## Formatos y prefijos: Guidance y LM Format Enforcer

`guidance / schema.check` usa `guidance-ai/guidance@21b1d90dfbebff4b141df70c714c8af15aa5f4af`, MIT, versión 0.3.2. `guidance.json` construye la gramática y el `ByteParser` original consume casos con decisiones y cantidades enumeradas. El worker verifica 78 archivos instalados contra 82 fuentes Git y 22 archivos de las dependencias `llguidance==1.6.1` y `guidance-stitch==0.1.5`. LLGuidance es el wheel nativo original fijado por hash, no una recompilación propia. Se conservaron sus licencias MIT y BSD-3. Los casos cubren valores válidos, decisión no permitida, aprobación verdadera, campo extra, cantidad como texto y documento truncado. Los ejecutores de los parsers se cierran también al rechazar; quedan cero hilos.

`lm-format-enforcer / prefix.check` usa `noamgat/lm-format-enforcer@817f944fcc8851917c40300a47f62d1defc3ffc3`, MIT, versión 0.11.3. El parser original comprueba cada carácter permitido y si la secuencia puede terminar. Un lenguaje independiente de dos documentos compactos comprueba viabilidad, finalización y primer desplazamiento rechazado. Se verifican 23 fuentes Git, 21 archivos instalados y 7 archivos del wheel original de Interegular 0.3.3, MIT. La configuración fija alfabeto, orden de campos y límites; no acepta texto, esquemas ni modelos arbitrarios. El analizador opcional que requiere NumPy no está instalado ni se usa; todas las dependencias obligatorias sí están instaladas.

Perfiles `VERDUGO_SCHEMA666_PYTHON` y `VERDUGO_PREFIX666_PYTHON`; requisitos en `requirements/runtime-schema666.txt` y `requirements/runtime-prefix666.txt`. Ambos se reinstalaron en entornos separados y pasaron `pip check`. El flujo conjunto contiene **22 componentes y 24 pasos**, con **829 pruebas** locales. La validez sintáctica no significa verdad, resultado comercial ni permiso de ejecución. No se añadieron pesos ni llamadas a modelos.

La primera aceptación de Guidance detectó que un nombre de campo que contenía `authorization` era ocultado por el filtro de privacidad; se corrigió el nombre del diagnóstico y se repitió el flujo sin cambiar el filtro. Una comprobación adicional del ensayo usaba por error `ok` en vez del contrato `state == succeeded`; también se corrigió y se repitió la aceptación completa. La preparación de LM Format Enforcer también corrigió la captura de dependencias para invocar el Python del entorno, sin resolver el enlace al intérprete base. Los requisitos finales contienen únicamente sus ocho dependencias obligatorias resueltas.

El checkpoint anterior de 20 componentes tiene sus tres workflows verdes, enlazados en PLAN_666. Los resultados del incremento de 22 se verifican en su propio commit. LLM Compressor y XGrammar conservan preparación pendiente con fuentes verificadas en `sources/review-runtime-next666.json`; no son adaptadores ni fallos de compilación demostrados. La revisión de BAML (posición 42) detectó `colored 2.2.0` MPL-2.0 en la ruta legacy `baml-py`, verificado contra el Cargo.lock original. La ruta nueva `baml_bridge` requiere revisión independiente; no se instaló ni compiló ninguna. La continuación queda en `lm-evaluation-harness`, posición 43: licencia MIT y empaquetado revisados, pero operación y dependencias aún pendientes. Torch es opcional en el extra `hf` de ese commit; no se instaló ni ejecutó ningún modelo. Los bloqueos anteriores siguen abiertos.


## Vecinos sintéticos y recuentos de RAGFlow

`usearch / neighbors.check` compila USearch 3.0.0rc1 desde `840374af1a1dd5d411826bc62fdfe5ef6e41e1de`, con NumKong, StringZilla, ForkUnion, SmashTable y yyjson fijados. Las licencias originales son Apache-2.0 y MIT. El núcleo Python original no declara dependencias runtime; las herramientas de construcción quedan en un entorno temporal separado. El perfil usa GCC 14, un proceso, CPU monoversionada, almacenamiento BF16 y el backend nativo; `USEARCH_BUILD_STUB` permanece desactivado.

Dos casos fijos insertan cinco u ocho vectores efímeros. La búsqueda por grafo y el recorrido exhaustivo se comparan con `math.dist` independiente, incluyendo empates; también se comprueba la alcanzabilidad del grafo. Solo persisten cantidades, error numérico y controles. Esto no mide recall de un corpus, relevancia semántica ni rapidez. El recibo vincula el binario instalado, seis interfaces Python y seis archivos comprimidos de fuentes descargados por SHA256; no es atestación independiente ni demuestra builds idénticos bit a bit.

La instalación limpia inicial recibió SIGKILL al compilar en `/tmp`, respaldado por memoria en el entorno local. La repetición desde disco completó el mismo código y opciones, con `pip check` aprobado. Preparación: `python tests_runtime/install_usearch666.py`; perfil del operador `VERDUGO_USEARCH666_PYTHON`. El flujo conjunto de 23 componentes y 25 pasos pasó localmente, con aprobación, CLI/MCP y replay tras reiniciar SQLite; los tres workflows del commit nuevo deben observarse por separado.

`ragflow / datasets.summary` consulta `/api/v1/datasets?page=1&page_size=100` en el servidor comunitario original Go del commit fijado. La autenticación nativa enlaza usuario y tenant, y el checker de permisos filtra el inventario. La edición comunitaria devuelve `nil` para el servicio de facturación; no se activa enterprise. Solo se guardan tamaño de página y total declarado. Las pruebas HTTP son sintéticas, con CLI/MCP, privacidad, errores y reinicio; no se ejecutó el servidor RAGFlow.

## Ordenación sintética y recuento de modelos

`rerankers / results.rank` usa AnswerDotAI/rerankers `5b9cbb073335b0246bc33e939600f51f934c460d`, Apache-2.0, versión 0.10.0 sin dependencias runtime obligatorias. Acepta 1–16 enteros o valores ausentes y selecciona por score descendente o rank ascendente. No admite consultas, documentos, imágenes, modelos o proveedores externos. Los valores son suministrados por la prueba, no calculados por inferencia. `RankedResults.top_k` y las búsquedas por identificador se contrastan con ordenación independiente; los empates conservan orden. Se verifican 22 archivos originales instalados y la huella del entorno antes de planificar, ejecutar y reutilizar resultados. Perfil `VERDUGO_RANKING666_PYTHON`; preparación explícita con `requirements/runtime-ranking666.txt`.

El primer flujo conjunto rechazó el worker porque el hash del intérprete dependía de si coincidía con `sys.executable`. Se corrigió para incorporar siempre el ejecutable y `pyvenv.cfg`. La aceptación posterior pasó con 24 componentes, 26 pasos y cuatro casos numéricos de Rerankers, además de aprobación, CLI/MCP y reinicio. No hubo llamadas a modelos ni efectos externos nuevos.

`infinity / models.summary` usa michaelfeil/infinity `f25b80850a7fc9736310496b64faf9903c01ac97`, MIT. Se limita al servidor Python `infinity_emb` 0.0.80 y su `/models` sin prefijo adicional; no al backend nativo v3. Exige autenticación Bearer nativa configurada y revisión de instancia dedicada. Valida el contenedor OpenAIModelInfo y las filas ModelInfo, descarta identificadores/estadísticas y conserva solo cantidad de modelos. Los siete tests nuevos cubren rutas, autenticación, esquemas, límites, privacidad, HTTP real con respuestas sintéticas, CLI/MCP y replay. No se instaló el servidor original, no se consultó una instancia real y no se descargaron pesos.

El conjunto pasa 879 pruebas locales y el paso del workflow que exige 76 observaciones. La CI del commit publicado se informa por separado; ningún lote se declara terminado.


## Álgebra y grafos sintéticos

`sympy / polynomial.check` usa `sympy/sympy@bad9365d788889cdf450cd9a24a734004b876e2b`, BSD-3-Clause. Acepta hasta seis coeficientes enteros y ocho puntos enteros acotados; crea un `Poly` univariado sobre ZZ, deriva, evalúa y factoriza. La referencia independiente comprueba evaluación, derivada y producto de factores. No demuestra irreducibilidad de forma independiente ni permite expresiones, funciones, símbolos o dominios enviados por el usuario.

La versión `1.15.0.dev3540+gbad9365d7` se obtuvo compilando el commit original con metadatos Git; etiqueta y commit constan en `sources/sympy-version666.json`. El instalador del archivo fuente usa esa misma versión explícita mediante la opción original de setuptools-scm. `sympy/release.py` es un archivo generado y se verifica por separado: no se presenta como copia literal del archivo Git. Los 1,572 módulos originales instalados y los 87 de `mpmath 1.3.0` se verifican por SHA256; también se conservaron las licencias incluidas.

`rdflib / reachability.check` usa `RDFLib/rdflib@114dd59d48fc75aea7fcb3276bd0f13e4f3103b4`, BSD-3-Clause, versión `8.0.0a0`. Construye un `Memory` y un grafo de hasta ocho nodos y dieciséis aristas, con URN sintéticas fijas. Contrasta triples únicos y cierre transitivo con una referencia de adyacencia; el origen se incluye aunque esté aislado. No llama a `parse`, `query` ni almacenes remotos. Verifica 135 módulos originales y trece de `pyparsing 3.2.5`, MIT.

Ambas operaciones usan `VERDUGO_SYMBOLIC666_PYTHON`; `python tests_runtime/install_symbolic666.py` prepara el perfil explícitamente, fuera del motor. Se comprobó una instalación limpia. Los resultados son números y recuentos sintéticos, sin documentos, modelos, causalidad ni resultados comerciales. Z3 se incorpora después de comprobar la ejecución nativa descrita debajo.


## Factibilidad finita con Z3 original

`z3 / constraints.check` usa `Z3Prover/z3@f46b3c58e41c0f9531cbb7cbab243b8cd2a98250`, MIT, versión nativa y Python `5.4.2.0`. El perfil compila el código original con GCC 14 y CMake 4.1.3, sin GMP ni bindings opcionales. Los primeros dos intentos recibieron SIGKILL; el tercero continuó con un proceso después de liberar almacenamiento temporal respaldado por memoria. Se conservó el mismo código y configuración `-O1 -DNDEBUG -g0`; no se sustituyó por un wheel ajeno al commit.

El solver examina tres variables enteras de cero a tres, con costos y rendimientos sintéticos fijos y tres límites numéricos. Su resultado SAT/UNSAT y cualquier testigo se comprueban contra las 64 combinaciones enumeradas independientemente. Una respuesta desconocida falla; hay límites fijos de tiempo y recursos. No se aceptan SMT, expresiones, funciones ni opciones del solver desde parámetros; tampoco se prueba optimalidad o veracidad comercial.

`python tests_runtime/install_logic666.py` prepara el perfil `VERDUGO_LOGIC666_PYTHON` fuera del motor. Verifica fuentes, opciones CMake, nueve módulos originales instalados y los archivos Python generados y bibliotecas nativas registrados por el build. El recibo detecta cambios posteriores y se vincula a aprobación/replay; no constituye atestación independiente ni prueba de reproducibilidad binaria. El pipeline reconstruye desde cero y amplía su límite a 120 minutos por la compilación nativa.

## Inventario de Jena/Fuseki

`jena / datasets.summary` consulta exclusivamente `GET /$/server` de `apache/jena@d5b47b73e3e260bf1db62c776efb960bc758a93d`, versión fuente 6.3.0-SNAPSHOT, Apache-2.0 con texto BSD incluido. `FMod_Admin`, `ActionServerStatus`, `JsonDescription` y las constantes originales respaldan la ruta y respuesta. Conserva recuentos de datasets, estados, servicios y endpoints; elimina nombres, descripciones, fechas y versión. No envía SPARQL ni inspecciona datos.

La plantilla mantiene la integración desactivada. Exige `api_surface=self_hosted_fuseki_admin`, `auth_mode=native_basic`, instancia dedicada y las revisiones `native_auth_enforced_reviewed`, `dedicated_instance_reviewed` y `status_route_basic_auth_reviewed`. La credencial privada es un único `usuario:contraseña` ASCII; el encabezado Basic se construye internamente. La configuración Shiro original incluye `/$/server = anon`: debe comprobarse una protección Basic efectiva de esa ruta, por ejemplo mediante el mecanismo Jetty de autenticación para todo el servidor respaldado por el código. Una configuración predeterminada o solo una contraseña configurada sin proteger la ruta no satisface la revisión.

Las siete pruebas usan respuestas sintéticas, sockets locales, CLI/MCP, SQLite y reinicio. Cubren respuestas inválidas, duplicados, límites, cambios de credencial/revisión y ausencia de datos privados persistidos. El servidor original y sus dependencias Java no se instalaron ni ejecutaron; `live_verified=false` y producción certificada continúa en cero.


## txtai: conciliación de contenido acotada

`content.reconcile` usa el almacén original SQLite de la distribución oficial `txtai_minimal`, construida con `MINIMAL=1` desde el commit fijado. No modifica ni omite dependencias obligatorias: ese perfil original no declara ninguna. Solo admite hasta 32 pares de segmento y cantidad enteros y una lista de índices por eliminar; la consulta SQL es fija, no hay destinos, modelos ni texto del usuario. Contrasta agrupaciones y borrados contra una referencia escalar, cierra el almacén efímero y conserva solo resultados numéricos en Engine. No demuestra recuperación semántica ni memoria comercial permanente.

Preparación: `python tests_runtime/install_content666.py`. Perfil: `VERDUGO_CONTENT666_PYTHON=/tmp/verdugo-content666/bin/python`. Aceptación: `python tests_runtime/accept_content666.py --out /tmp/content666-evidence.json`. El instalador exige un destino nuevo; la huella verifica los 277 archivos instalados, el intérprete, la configuración y la ausencia de paquetes o módulos adicionales. El mismo servicio participa en `product-run`, MCP y el flujo conjunto del piloto.

En el flujo conjunto, `content_reconcile` recibe mediante referencias los contactos y clientes de la etapa `measure`. No vuelve a introducir esas mediciones a mano. La aceptación independiente del componente y sus límites se conserva en `evidence/accepted/content666-local-20261115.json`.

## KAG: consulta de una tarea existente

`kag / task.summary` entra al mismo Engine, doctor y product-run. Se conserva únicamente el estado resumido de la tarea configurada por el operador; no admite enviar tareas, elegir modelos ni consultas de texto. El identificador queda fuera de planes, CLI/MCP y SQLite. El contrato HTTP se prueba con sockets sintéticos; dos módulos originales de solicitud y caché pasan cinco casos adicionales, sin ejecutar el servidor o solver completo. [Alcance y preparación](KAG_666.md).
