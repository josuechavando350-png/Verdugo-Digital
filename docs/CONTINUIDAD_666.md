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
| Adaptadores implementados dentro del criterio raíz | 281 |
| Piezas de construcción | 56 |
| Pendientes de adaptador | 329 |
| Nuevas incorporaciones implementadas | 38 de 366 |
| Lote original 1 | 38 de 183 |
| Lote original 2 | 0 de 183 |
| Continuación de 80 | 16 implementadas, 64 pendientes |
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
añadidas. Pasaron 904 pruebas unitarias y de contrato. La aceptación del flujo
conjunto y los tres workflows deben observarse en el commit correspondiente;
una prueba local no se presenta como CI aprobado.

## Continuar desde aquí

Leer `AGENTS.md`, `docs/PLAN_666.md` y `sources/resume-666.json`. Consultar
`product-status` para el estado calculado y comprobar el head de PR #25 antes
de modificarlo. Los otros 64 candidatos del sublote de 80 siguen pendientes;
sus revisiones acotadas están enlazadas en el informe. Un candidato bloqueado
no se convierte en terminado por añadir una explicación o un nombre distinto.
