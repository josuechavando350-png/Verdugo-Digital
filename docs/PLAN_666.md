# Verdugo Digital — Plan de los 666

Fecha: 15 de noviembre de 2026. Base: `main` después de la v0.21.1.

## Inventario

| Bloque | Piezas | Fuente | Estado hoy |
|---|---|---|---|
| Catálogo libre (cuerpo) | 300 | `sources/parts/*.json`, `sources/licenses.json` | 243 conectadas, 56 piezas de construcción, 1 pendiente (`meta-ads`) |
| Simulador de mercado (bola de cristal) | 50 | `sources/simulador-mercado.json` | registrado; adaptador pendiente |
| Cerebro (piloto) | 150 | `sources/cerebro-150.json` | 19 operaciones locales; 131 pendientes |
| Últimas 166 | 166 | `sources/final-166.json` | registrado; adaptador pendiente |
| **Total libre** | **666** | | |

Los 22 excluidos por licencia siguen registrados, pero no cuentan ni se operan.

## Avance comprobado de esta continuación

- **Tanda 0: terminada y aceptada en CI.** 688 identidades GitHub distintas, 666 permitidas por política y 22 excluidas. Se conservan 69 partes: 68 de diez y una de ocho.
- Cinco propuestas eran alias de proyectos ya registrados (Ragas, Presidio, FastMCP, Recommenders y Great Expectations). TEN Framework tiene restricciones adicionales: no se contó como Apache libre. Las seis sustituciones y su alcance constan en [REGISTRO_666.md](REGISTRO_666.md).
- **Estado actual: 262 conectadas; 56 de construcción; 348 pendientes; certificadas en producción: 0.** Semantic Kernel, Agno, AG2, Langroid, Griptape, BeeAI, Strands/Harness SDK, VoltAgent, Unified Planning, el servidor MCP de memoria, Monty, Playwright para Python, Hatchet, Invariant, PyRIT, llama.cpp, Granite Guardian, InterpretML y TransformerLens añaden diecinueve operaciones locales limitadas; registrar las otras piezas no añade adaptadores.
- **Lote 1 (183): 19 operaciones implementadas y probadas conjuntamente; aceptación CI de este incremento pendiente. Lote 2 (183): 0 implementadas. Ninguno de los dos lotes está terminado.** Orden completo, sin duplicados, en `sources/registry-666.json/work_queue`.
- Registro aceptado en `b95f8be09e2a34ff12f163b6f872287eed3afd26`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43690692125), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43690692198) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43690692157), los tres `success`. PR #24 permanece sin fusionar.
- El primer checkpoint del piloto (`77670600a4ee083413f5838b1e36991ddbff2347`) pasó [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43692332291), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43692332306) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43692332315). Esa evidencia cubre Semantic Kernel; no certifica cambios posteriores.
- El checkpoint ejecutivo `e914b2622e430ee72121fefc1e256e0adabc126d` pasó [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43693358786), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43693358773) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43693358774), cubriendo tres SDK. El checkpoint posterior de Langroid también está aceptado.
- Checkpoint de cuatro SDK `5f864e01916af4fc5aaeda0ed81562b53f0bdcab`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43694523478), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43694523526) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43694523516), los tres `success`. Griptape y BeeAI pasan la aceptación local conjunta y las 761 pruebas; su CI se comprueba en el siguiente commit.
- Checkpoint de seis SDK `4da9ac282fbb8ecc46142586379ff7636151f1dc`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43695503872), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43695503842) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43695503909), los tres `success`. Los nueve SDK pasan la aceptación local conjunta y 766 pruebas unitarias; su CI debe observarse en el siguiente commit.
- Checkpoint de nueve SDK `1e12900b5c275345d5c27d6adda448c80896232d`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43697622379), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43697622401) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43697622377), los tres `success`. La aceptación del piloto pasó con aislamiento de red del sistema operativo. OpenManus se valida en el siguiente checkpoint.
- **DeerFlow y Open Deep Research permanecen pendientes:** sus instalaciones revisadas incluyen dependencias obligatorias Elastic-2.0 y AGPL/comercial, respectivamente. Evidencia original y límites de esta conclusión en `sources/contracts-executive-blockers666.json`.
- **LiteLLM permanece pendiente:** la compilación nativa del commit 1.111.0 terminó SIGKILL también con un solo proceso; no se contó como instalado ni se cambió de versión.
- Checkpoint de diez SDK `9b95b92926382838f23ff771168a584f1a391385`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43699726433), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43699726429) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43699726435), los tres `success`. El servidor MCP de memoria pasa el flujo conjunto local de once piezas y trece pasos; su CI pertenece al siguiente checkpoint.
- Checkpoint de once SDK `cdc6fb18f5584ff23736185fd8c3dcc802d3ac7c`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43700616662), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43700616677) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43700616710), los tres `success`. El incremento Monty/Playwright pasa localmente el flujo de trece SDK y quince pasos y las 780 pruebas. CI del nuevo incremento debe observarse por separado.
- Checkpoint de trece SDK `0bccfaa96d854e34ed11316c55f49907eda6849b`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43705124458), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43705124459) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43705124550), los tres `success`. Monty se compiló desde fuentes y el flujo pasó con aislamiento de red del sistema operativo. Hatchet añade el incremento local de catorce SDK, dieciséis pasos y 783 pruebas; su CI corresponde al siguiente commit.
- Checkpoint de catorce SDK `0d46dd060fc427bb326b6b035dbe72f3f4f811b6`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43706478079), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43706478082) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43706478135), los tres `success`. Esta evidencia incluye Hatchet; el incremento de Invariant requiere su propio CI.
- Checkpoint de quince SDK `4a70eb273023c3c83d8ef551ceab3bbf412a8356`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43708865468), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43708865461) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43708865462), los tres `success`. Incluye Invariant; PyRIT se acepta por separado.
- Checkpoint de dieciséis componentes `2d5986c3a6c0fd3cf34f737c7fab26bb14668221`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43711840601), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43711840533) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43711840589), los tres `success`. Incluye PyRIT y el flujo aislado de red.
- **DBOS permanece pendiente:** el código fijado exige Psycopg; el wheel 3.3.9 revisado contiene LGPL-3.0. No se omitieron requisitos ni se habilitó enterprise. Evidencia en `sources/contracts-executive-blockers666.json`.
- **Prefect permanece pendiente:** la resolución inspeccionada exige `python-slugify` → `text-unidecode`; la licencia original GPL/Artistic queda fuera de la lista permitida del proyecto. Esto no reclasifica el núcleo Apache ni es una conclusión legal. Evidencia de wheels y metadatos en `contracts-executive-blockers666.json`.
- **Hatchet añade `policy.compile`:** mezcla valores por defecto y serializa políticas con el SDK original, en borrador local. Se comprobaron catorce SDK y dieciséis pasos; no hay cola, despacho ni reintentos reales.
- **Invariant añade `trace.check`:** analizador local original, tres reglas fijas sobre trazas sintéticas. El patrón lectura privada → envío es temporal, no prueba de filtración. No ejecuta herramientas ni concede aprobación.
- **AgentKit permanece pendiente:** cinco archivos del mapa de fuentes npm difieren del commit. El build original con Inngest 3.54.0 falla en tipos/API; 3.43.1 declara una advertencia crítica de seguridad y no se aceptó como solución.
- **Gorilla y Scrubadub permanecen pendientes:** las rutas originales revisadas requieren respectivamente `html2text` GPL-3.0 y `python-stdnum` LGPL-2.1. No se omitieron dependencias ni se cambiaron las reglas de licencia.
- **MetaGPT permanece pendiente:** instalación original bajo Python 3.11 bloqueada por `lancedb==0.4.0`, ausente en la lista de versiones de PyPI consultada el 15 de noviembre. No se ignoraron dependencias ni se declaró conectado.
- **PyRIT añade `tools.audit`:** valida relaciones entre llamadas/respuestas sintéticas y cuenta tipos de herramientas con invocación registrada. No ejecuta herramientas ni demuestra finalización. La migración oficial Azure → microsoft conserva identidad, posición en cola y evidencia anterior en `sources/registry-666-revisions.json`.
- **Garak permanece pendiente:** su dependencia obligatoria `mikeshardmind-base2048` 1.0.4 contiene MPL-2.0, fuera de la lista permitida. El experimento local no se cuenta como integración; el perfil instalado se retiró. Este hallazgo no equivale a una auditoría completa de dependencias de los demás perfiles.
- **llama.cpp añade `tokens.check` y Granite Guardian `risk.assess`:** tokenizer nativo y una inferencia CPU con pesos oficiales Apache-2.0 fijados por SHA256. Dos afirmaciones sintéticas con controles repetidos; se conserva el falso positivo observado bajo otra configuración. No hay calibración ni aprobación automática. Flujo local de 18 componentes y 20 pasos; 797 pruebas. CI de este incremento debe observarse por separado.
- **ETHICS permanece pendiente:** el README original enlaza pesos externos cuya licencia no se ha verificado. No se presume que la MIT del código cubra esos pesos; tampoco se afirma que sean privativos. No se descargaron.
- **Corrección de revisión: OpenManus vuelve a pendiente.** Su `setup.py` exige `html2text~=2024.2.26`, GPL-3.0. Se había contado después de una prueba funcional sin detectar esa incompatibilidad. Se retiró de las operaciones del motor y de CI; el módulo rechazado falla antes de importar el SDK. La clasificación MIT del código no cambia.
- **InterpretML añade `prediction.explain`:** fit/predict/eval_terms originales, núcleo C++ compilado y entrenamiento efímero sobre números sintéticos. La suma de términos reconstruye las predicciones; no demuestra causalidad ni precisión fuera de muestra. Instalador limpio y dos conjuntos de datos ejecutados por Engine. El total permanece en 18 componentes y 20 pasos, con 803 pruebas; CI de esta corrección se observa por separado.
- Checkpoint corregido de dieciocho componentes `506d62616466f585b94c0b18f8fa34a9efd75f54`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43715707063), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43715707032) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43715707044), los tres `success`. Incluye InterpretML y la retirada de OpenManus; TransformerLens necesita su propio CI.
- **TransformerLens añade `activations.check`:** código original construye un transformer nativo sin entrenar de 936 parámetros. Captura de activaciones, intervención fija, máscara causal y restauración comprobadas. Flujo local de 19 componentes y 21 pasos; 807 pruebas. No explica un LLM real ni añade pesos preentrenados.
- **SGLang permanece pendiente:** el perfil CPU x86_64 exige `intel-openmp`; el wheel revisado 2026.2.0 contiene Intel EULA, fuera de la política. No se instaló ni ejecutó; no se descartaron otras rutas originales sin examinarlas.
- **Fase 1: parcial.** El esqueleto sintético recorre plan → aprobación → simulación → medición por CLI/MCP y SQLite. El modelo local añadido revisa afirmaciones sintéticas; la planificación sigue siendo una heurística fija. Faltan las otras 31 piezas de la fase y calibración real. [Detalle del piloto](PILOTO_666.md).
- `meta-ads` sigue pendiente. El registro no ejecuta modelos ni proveedores. El incremento de Guardian prepara un modelo local revisado; no se lanzaron campañas ni desplegaron proveedores.

## Qué es el producto terminado

Un solo sistema que recibe un objetivo de negocio ("20 clientes este mes para este despacho, presupuesto X") y:

1. **Planea**: corteza ejecutiva y razonamiento (cerebro: `ejecutivo`, `razonamiento`, `logica`).
2. **Predice**: simula la estrategia con clientes virtuales calibrados y pronostica demanda (simulador, más `pronostico`, `quien_compra`, `decision`, `prediccion`).
3. **Pide aprobación**: cada acción con costo o efecto externo se muestra en una línea y espera la aprobación del operador (`conciencia`, `juicio`, `cabina`).
4. **Ejecuta**: usa el cuerpo (300), `contenido`, `ventas_voz`, `embudo` y `seo_crecimiento`.
5. **Mide y aprende**: compara lo predicho con lo real, recalibra el simulador y mejora el piloto (`aprendizaje`, `datos_limpios`, `memoria`).
6. **Sigue prendido**: `siempre_prendido` (despliegue, monitoreo, respaldos).

## Reglas que no cambian (AGENTS.md manda)

- Nada de pago. Ningún proveedor de pago, ni como opción por defecto.
- No escribir `license_policy_exception` en nombre del dueño.
- Licencia leída del archivo LICENSE en el commit fijado. En `libre_nucleo` no se usa la parte enterprise, Pro o ee.
- **Pesos de modelos**: antes de descargar cualquier modelo, leer la licencia de los pesos. El código puede ser MIT y los pesos no comerciales. Si los pesos no son libres, la pieza solo se usa con otro modelo libre.
- Contratos tomados del código original en el commit fijado. Si el código no respalda la ruta, la pieza queda pendiente (como `meta-ads`).
- Nada se marca conectado ni verificado sin evidencia. `live_verified` solo con una prueba real contra un servicio real.
- **Acciones con efecto** (publicar, enviar, gastar, crear campañas): siempre detrás de una aprobación explícita del operador, con idempotencia, registro en SQLite y reversión cuando exista. Primero en modo simulación (dry-run). Programar el repo no autoriza a iniciar campañas, enviar comunicaciones a terceros ni contratar hosting.
- Nada de datos privados persistidos; se proyectan solo recuentos.
- Sin raspado que viole términos de servicio, sin suplantar navegadores y sin APIs no oficiales.
- Nada de Cano ni de Vercel. El repo es público: sin secretos ni nombres de clientes.

## Orden de construcción

El plan original dividía el trabajo en tandas de hasta 50. La organización vigente usa dos lotes de 183, con pruebas, los tres workflows observados en verde y PR encadenados. Las fases funcionales originales se conservan abajo. Por instrucción del dueño del 15 de noviembre, la ejecución se agrupa en **dos lotes de 183**, en el orden explícito de `sources/registry-666.json/work_queue`. El registro (tanda 0) sigue siendo previo.

| Tanda | Qué | Piezas | Criterio de terminado |
|---|---|---|---|
| 0 | Registro unificado: llevar el catálogo de 322 a 688 registros (666 libres + 22 excluidos) con commits fijados, política de licencias y mapa de conexión. Regla actualizada a 69 archivos y 688 entradas en AGENTS.md. Sin adaptadores todavía. | 0 nuevas operaciones | `licenses` y `connections` reportan 688/666; pruebas actualizadas |
| 1 | Esqueleto del piloto: objetivo → plan → aprobación → ejecución simulada → medición, con `ejecutivo`, `manos`, `juicio` y `conciencia`. Modelo local con `pensamiento`. | 50 | Un objetivo de prueba produce un plan, pide aprobación, corre en dry-run y queda en SQLite con replay |
| 2 | Memoria y lógica: `memoria` y `logica`. El piloto recuerda clientes y campañas, y comprueba sus afirmaciones antes de reportarlas. | 50 | Consultas sobre datos sintéticos; afirmaciones verificadas o rechazadas |
| 3 | Núcleo del simulador: población sintética, clientes virtuales y calibración (los 50 del simulador). | 50 | Simula una oferta sintética y reporta incertidumbre, no un número único |
| 4 | Bola de cristal: `pronostico`, `quien_compra`, `decision` y `prediccion`. | 50 | Pronósticos con intervalos y evaluación retrospectiva sobre datos sintéticos |
| 5 | Auto-mejora y juicio: `aprendizaje`, `datos_limpios`, `explicar` y el resto de `juicio`. | 50 | El piloto se califica, explica cada decisión y registra qué aprendió |
| 6 | Ejecución: `contenido`, `ventas_voz`, `embudo` y `seo_crecimiento`. Todo con aprobación y dry-run por defecto. | 50 | Cada acción con efecto exige aprobación; sin aprobación no sale nada |
| 7 | Operación y cabina: `siempre_prendido`, `cabina`, `tableros` y el resto. Resolver `meta-ads` solo si aparece una fuente original que lo respalde. | 16 + restantes | Instalación reproducible en un servidor Linux y cabina usable desde el teléfono |

## Lo que decide el dueño, no Astra

- **El servidor** donde corre todo, 24/7. Sin servidor no hay producto prendido.
- **Qué acciones pueden ir sin aprobación**, si alguna. Por defecto: ninguna.
- **El primer cliente real** para calibrar el simulador.
