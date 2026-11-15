# Continuidad de los 666 — 15 de noviembre de 2026

El producto todavía no está terminado. La meta es un sistema conjunto con
componentes distintos y permisos compatibles; contar repositorios o renombrar
una capacidad no demuestra esa integración.

## Reanudación vigente

**BM25S recuperado y aceptado localmente:** Lote A 1/164 · Lote B 0/163; 283 adaptadores, 56 piezas de construcción, 327 pendientes y `live_verified=0`. La instalación limpia y seis casos del flujo BM25S → txtai aprobaron por Engine, CLI/MCP, SQLite y replay. Pasan 926 pruebas. Ver [BM25S_666.md](BM25S_666.md) y comprobar los tres workflows del nuevo commit; no heredar el verde de otro.

### Checkpoint anterior a BM25S

Rama `feat/666-pilot`, PR #25 en borrador sobre `feat/666-registry` (PR #24). El fallo de privacidad de `4dbd055` se corrigió en `486a271` mediante comparación completa de campos y un timestamp que reproduce la colisión. Los tres workflows de ese commit terminaron en `success` antes de agregar otro adaptador. La evidencia por workflow figura en [PLAN_666.md](PLAN_666.md).

**Lote A 0/164 · Lote B 0/163**: membresía exacta en `sources/resume-666.json/rebatch`, validada por `integration_audit`. Las 39 incorporaciones previas no se cuentan de nuevo. El orden conserva 63 pendientes del antiguo sublote de 80, 81 del siguiente y 183 del lote 2. `meta-ads` queda fuera y bloqueada. Se mantiene el total de 282/56/328 y cero verificaciones productivas.

Por decisión del dueño se aprobaron Zlib, BSL-1.0 (Boost, no Business Source) y Unicode-3.0. La reevaluación con hashes está en `sources/review-license-decision666.json`. Esos bloqueos concretos de BM25S, Rustworkx, Clingo y Candle dejan de aplicar; el cierre completo y aceptación siguen pendientes. La revisión ampliada de Candle encontró `target-lexicon 0.13.6` (`Apache-2.0 WITH LLVM-exception`) en las dependencias de build del perfil fijado; esa expresión tampoco se aprobó. Evidencia original y árbol activo en `sources/review-candle-dependencies666.json`. La revisión nativa de Clingo comprobó nueve archivos fuente comprimidos y sus licencias raíz, y conserva pendiente el alcance del aviso GPL con excepción de los analizadores Bison (`sources/review-clingo-dependencies666.json`); no se compiló ni se reclasificó el proyecto completo. Tokenizers mantiene el bloqueo MPL-2.0. Pasan 921 pruebas locales; consultar CI del commit vigente antes de conectar más piezas.

## Checkpoint de recuperación

La revisión adicional de **Rustworkx** confirma que su núcleo requiere `priority-queue 2.7.0`, con `LGPL-3.0-or-later OR MPL-2.0`; ninguna opción está aprobada. El perfil Python también requiere `target-lexicon 0.13.5` a través de PyO3, con `Apache-2.0 WITH LLVM-exception`. Los nueve archivos originales de manifiestos, lock y licencias conservan commit, blob SHA y SHA256 en `sources/review-rustworkx-dependencies666.json`. El núcleo sigue pendiente; no se sustituyeron dependencias ni se añadió una excepción. Para Egg, el hallazgo anterior de `foldhash` Zlib queda resuelto por la misma decisión; aún faltan resolución completa, build y aceptación.

El entorno de ejecución quedó inaccesible durante la validación final de BM25S. **El candidato no está publicado ni contado**; no se recuperaron los resultados finales de su suite y build limpio. Antes de seguir, leer [RECUPERACION_BM25S_666.md](RECUPERACION_BM25S_666.md), preservar cualquier diff local que reaparezca y conciliarlo con el head remoto. Este checkpoint mantiene A 0/164, B 0/163 y 282/56/328.

En `713e4c0d`, verificación y servicios aprobaron; runtime seguía en curso a las 22:45 UTC, con `baseline` aprobado y `pilot666` pendiente. Cada commit posterior requiere su propia CI; consultar el estado vivo en [PLAN_666.md](PLAN_666.md) y la descripción de PR #25.

## Estado recuperado anterior

La conversación anterior publicó `1dc6bd7a116a6ebdb8dbc55732993ebf4efe25a8`,
árbol `c8e6ddf725d85cde70c180329dc29ca9046c2a06`, en `feat/666-pilot`, PR #25.
Ese árbol ya incorpora SymPy, RDFLib, Z3 y Jena; la captura aportada corresponde
a un punto anterior. Se retomó ese árbol sin perder sus fuentes ni pruebas.

## Recuento vigente

| Concepto | Cantidad |
|---|---:|
| Identidades GitHub distintas registradas | 688 |
| Permitidas por el criterio de licencia raíz | 666 |
| Excluidas por licencia raíz | 22 |
| Adaptadores implementados dentro del criterio raíz | 283 |
| Piezas de construcción | 56 |
| Pendientes de adaptador | 327 |
| Nuevas incorporaciones implementadas | 40 de 366 |
| Lote original 1 | 40 de 183 |
| Lote original 2 | 0 de 183 |
| Continuación de 80 | 18 implementadas, 62 pendientes |
| Continuación de 81 | 0 implementadas, 81 pendientes |
| Servicios certificados en producción | 0 |

Las 22 incorporaciones anteriores a los sublotes no se vuelven a sumar.
`product-status.integration_audit` calcula estas cifras desde el registro, las
operaciones y la pertenencia a los lotes. No lee contadores de un informe viejo.

## Duplicados y permisos

La revisión de identidades verifica tanto el ID numérico de GitHub como el
nombre canónico, y rechaza pertenencia repetida entre lotes. La revisión previa
retiró cinco alias: Ragas, Presidio, FastMCP, Recommenders y Great Expectations.
Este incremento no añade identidades: implementa el txtai ya registrado.
Dos repositorios distintos pueden tener funciones parecidas; la comprobación
de identidades no certifica ausencia total de solapamiento funcional.

La cifra 666 se refiere a licencias raíz. No certifica el cierre de dependencias,
pesos ni permiso de distribución de todo el producto. El informe conserva los
bloqueos y las preparaciones pendientes con ruta y SHA256 de su evidencia.
El hallazgo anterior sobre `certifi 2026.10.23` sigue presente en doce perfiles;
se vuelve a comprobar contra sus archivos actuales. Las tres adiciones autorizadas no permiten MPL-2.0 ni resuelven este hallazgo; no se creó ninguna excepción.

Se conservan los avisos y licencias originales. Un repositorio sin licencia
no se interpreta como código libre para incorporar.

## Incremento probado

`txtai / content.reconcile` usa la edición mínima que ofrece su propio
`setup.py`, sin modificar fuentes ni retirar dependencias obligatorias.
Su perfil no tiene dependencias runtime de Python. El contrato conserva
commit, archivo, blob SHA y SHA256; verifica 277 archivos instalados y rechaza
módulos y distribuciones adicionales.

La operación inserta hasta 32 registros numéricos sintéticos, ejecuta una
agregación fija, elimina los índices solicitados y comprueba el borrado
repetido. Contrasta todo con una referencia independiente. El almacén es
efímero y los resultados numéricos pasan por el Engine, CLI/MCP y SQLite
comunes. No es búsqueda semántica, memoria productiva ni ejecución de un LLM.

La instalación limpia y cuatro casos con cero, negativos, eliminación total
y límites máximos pasaron. También pasaron el reinicio y replay del producto,
la ausencia de texto interno en SQLite y el rechazo de fuentes/dependencias
añadidas. Pasaron 904 pruebas unitarias y de contrato. La aceptación conjunta pasó con 28 componentes originales y 30 pasos,
aprobación, referencias desde medición a txtai y replay después del reinicio.
La evidencia está en `evidence/accepted/content666-joint-local-20261115.json`.
Los tres workflows deben observarse en el commit correspondiente; una prueba
local no se presenta como CI aprobado.

## Continuar desde aquí

Leer `AGENTS.md`, `docs/PLAN_666.md` y `sources/resume-666.json`. Consultar
`product-status` para el estado calculado y comprobar el head de PR #25 antes
de modificarlo. Los otros 62 candidatos del sublote de 80 siguen pendientes;
sus revisiones acotadas están enlazadas en el informe. Un candidato bloqueado
no se convierte en terminado por añadir una explicación o un nombre distinto.

## Revisión anterior de BM25S (superada por la decisión de licencias)

BM25S sigue pendiente. El candidato de dependencia NumPy 2.2.6 incluye
libdivide Zlib. Es una licencia permisiva sin pago, pero no pertenece a la
lista cerrada heredada en AGENTS.md; no se equipara con una licencia
comercial restrictiva. La evidencia exacta y sus límites están en
`sources/review-numeric-next666.json`. No se ha descartado toda versión
alternativa de NumPy ni se intentó compilar este candidato.

## Corrección observada en CI

La verificación de `96af2b94c68605bf912896ef604009a76b1c5a39` pasó
las 904 pruebas y el control de cierres SQLite, pero falló después en
`Registry truth checks`: el workflow conservaba los contadores anteriores
299/389/280. Se actualizan a 300/388/281 y el mapa a 281/56/329/22.
La ejecución fallida permanece en el historial; el commit corregido necesita
su propia observación de CI.

## Continuación KAG

Se implementó `kag / task.summary` sin cambiar la lista de licencias. Son 39 incorporaciones: 28 locales y 11 lecturas HTTP. Pasaron 915 pruebas y el flujo de 78 observaciones HTTP sintéticas del producto, con reinicio/replay. Los cinco casos con módulos originales de solicitud y caché no equivalen a ejecutar el servidor KAG completo. La operación, las restricciones de autenticación, la privacidad y los límites están en [KAG_666.md](KAG_666.md).

Egg y SWI-Prolog recibieron revisión adicional acotada; sus hallazgos están en `sources/review-logic-next666.json`. En ese checkpoint la ampliación de licencias seguía pendiente; la decisión vigente está al inicio de este documento. No se aplicó ninguna excepción. Las nuevas pruebas CI deben observarse en su propio commit.

El control adicional de fuentes comprobó 688 commits fijados distintos, sin grupos con el mismo commit. Esto complementa la identidad GitHub; no certifica que dos árboles con historias distintas o dos capacidades no se solapen. Evidencia del incremento: `evidence/accepted/kag-contract-local-20261115.json`.
