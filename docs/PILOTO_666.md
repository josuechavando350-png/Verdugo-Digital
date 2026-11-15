# Piloto 666: avance parcial del lote 1

Seis de 183 piezas del primer lote tienen una operación nueva implementada. El segundo lote sigue en cero. Las 666 piezas permitidas están registradas; el producto autónomo de PLAN_666 todavía no está terminado.

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

MetaGPT está bloqueado por su dependencia original ausente. Harness SDK es la siguiente pieza por revisar. Faltan las demás piezas, el modelo local con licencia de pesos revisada, memoria, calibración, pruebas conjuntas de cada perfil y operación con información real autorizada. No se han desplegado servicios, publicado contenidos, enviado mensajes ni gastado presupuesto. `live_verified` sigue en cero. La cola de `registry-666.json` es el snapshot inmutable del registro; `docs/plan_conexion.json` y el inventario calculado reflejan las operaciones implementadas después.

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
