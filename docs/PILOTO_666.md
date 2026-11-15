# Piloto 666: avance parcial del lote 1

Quince de 183 piezas del primer lote tienen una operación nueva implementada. El segundo lote sigue en cero. Las 666 piezas permitidas están registradas; el producto autónomo de PLAN_666 todavía no está terminado.

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

MetaGPT está bloqueado por su dependencia original ausente. DeerFlow, Open Deep Research, DBOS y Prefect conservan bloqueos de dependencias bajo la política del repo; LiteLLM conserva un build fallido. AgentKit conserva un build original fallido; Gorilla, Scrubadub y Garak tienen bloqueos de dependencias documentados. Faltan las demás piezas, el modelo local con licencia de pesos revisada, memoria, calibración, pruebas conjuntas de cada perfil y operación con información real autorizada. No se han desplegado servicios, publicado contenidos, enviado mensajes ni gastado presupuesto. `live_verified` sigue en cero. La cola de `registry-666.json` conserva el checkpoint original de registro; los cambios de identidad oficial se documentan en `registry-666-revisions.json`; `docs/plan_conexion.json` y el inventario calculado reflejan las operaciones implementadas después.

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
