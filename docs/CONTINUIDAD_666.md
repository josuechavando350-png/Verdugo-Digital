# Continuidad de los 666 — 15 de noviembre de 2026

El producto todavía no está terminado. La meta es un sistema conjunto con
componentes distintos y permisos compatibles; contar repositorios o renombrar
una capacidad no demuestra esa integración.

## Estado recuperado

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
| Adaptadores implementados dentro del criterio raíz | 282 |
| Piezas de construcción | 56 |
| Pendientes de adaptador | 328 |
| Nuevas incorporaciones implementadas | 39 de 366 |
| Lote original 1 | 39 de 183 |
| Lote original 2 | 0 de 183 |
| Continuación de 80 | 17 implementadas, 63 pendientes |
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
se vuelve a comprobar contra sus archivos actuales. No se amplió la lista de
licencias ni se creó ninguna excepción.

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
de modificarlo. Los otros 63 candidatos del sublote de 80 siguen pendientes;
sus revisiones acotadas están enlazadas en el informe. Un candidato bloqueado
no se convierte en terminado por añadir una explicación o un nombre distinto.

## Siguiente candidato revisado

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

Egg y SWI-Prolog recibieron revisión adicional acotada; sus hallazgos están en `sources/review-logic-next666.json`. La decisión sobre ampliar licencias permanece pendiente; no se aplicó ninguna excepción. Las nuevas pruebas CI deben observarse en su propio commit.

El control adicional de fuentes comprobó 688 commits fijados distintos, sin grupos con el mismo commit. Esto complementa la identidad GitHub; no certifica que dos árboles con historias distintas o dos capacidades no se solapen. Evidencia del incremento: `evidence/accepted/kag-contract-local-20261115.json`.
