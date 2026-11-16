# Oxigraph: caminos finitos en un grafo sintético

`oxigraph / paths.check` usa el código original de
[`oxigraph/oxigraph@78734be853a4bec714ba09bbfad790e64f3a1150`](https://github.com/oxigraph/oxigraph/tree/78734be853a4bec714ba09bbfad790e64f3a1150),
versión declarada `0.6.0-dev`. Comparte Engine, CLI/MCP, workflow, auditoría y
SQLite. Requiere revisión explícita del operador y está deshabilitado por defecto.

## Operación delimitada

La entrada contiene `dataset=demo`, hasta 32 aristas y hasta ocho pares para
retirar. Solo se aceptan índices enteros de 0 a 7. El driver crea el almacén
original en memoria, inserta las aristas y ejecuta una consulta SPARQL fija con
un camino de longitud positiva. Después retira los pares indicados y repite
la misma consulta. Los duplicados siguen la semántica de conjunto de RDF.

La referencia independiente recorre cada grafo con una búsqueda acotada.
Compara los 64 pares posibles antes y después, además del número exacto de
aristas. Verifica direccionalidad, caminos indirectos, ciclos, autorreferencias,
duplicados y borrados ausentes o repetidos. Solo devuelve recuentos de aristas,
caminos y comprobaciones. No acepta SPARQL, programas, IRIs, rutas, servidores,
modelos ni almacenamiento persistente suministrados por el usuario.

El plan SQLite conserva recuentos y SHA256 de la entrada; el grafo y las
matrices solo existen en memoria. La huella de idempotencia sigue vinculada
al contenido completo, por lo que dos grafos con los mismos recuentos no
pueden reutilizar una clave de ejecución. Las licencias originales y los
archivos de construcción viven fuera del estado de negocio.

## Fuente y dependencias elegidas

El contrato `sources/contracts-oxigraph666.json` conserva el archivo fuente
por SHA256 y sus 913 blobs originales, incluyendo el contenido de los enlaces
simbólicos del repositorio. Registra API, commit, ruta, blob SHA y SHA256,
los tres archivos del driver, el lock de Cargo y el grafo activo en Linux
`x86_64-unknown-linux-gnu` con Rust 1.100.0.

La opción original `default-features=false` permite el almacén en memoria
sin RocksDB ni cliente HTTP. No se modifica el proyecto original ni se
eliminan requisitos obligatorios. Se verifican los archivos de crates.io y
las licencias originales de sus 91 paquetes activos antes de compilar.
Se seleccionan MIT, Zlib, Boost Software License 1.0 y Unicode-3.0, según las
alternativas que permite cada original. Cinco paquetes de otras plataformas
permanecen fijados en el lock, pero no forman parte de este build ni de su
revisión de licencias.

La primera resolución elegía `psm 0.1.32`, que incorpora `ar_archive_writer`
con `Apache-2.0 WITH LLVM-exception`, fuera de la lista literal autorizada.
Ese perfil nunca se compiló. El manifiesto original de `stacker 0.1.25`
permite `psm ^0.1.7`; el lock selecciona el original `psm 0.1.24`, bajo MIT
o Apache-2.0, cuyos requisitos no incluyen ese componente. Se conservan ambos
manifiestos originales y el aviso del perfil descartado. Es una selección
compatible de versión, sin modificar código upstream ni aprobar otra licencia.

El LICENSE de `allocator-api2 0.2.21` se empaqueta con CRLF; el original Git
tiene LF. Se comprueban ambos hashes y la igualdad exacta después de normalizar
únicamente esos saltos de línea. Se conserva la diferencia de empaquetado.
Chumsky se verifica en su repositorio original de Codeberg, con commit fijado.

La revisión no certifica compilador, biblioteca estándar de Rust, sistema
operativo, funciones opcionales ni cierre de distribución de los 666.
`distribution_license_closure_verified=false` permanece visible.

## Construcción y aceptación

En Linux x86_64 con Rust 1.100.0 y Python 3.12 preparados por el operador:

```bash
python tests_runtime/install_oxigraph666.py --prefix /tmp/verdugo-oxigraph666
python tests_runtime/install_egg666.py
python tests_runtime/install_content666.py
VERDUGO_OXIGRAPH666_ROOT=/tmp/verdugo-oxigraph666 \
VERDUGO_EGG666_ROOT=/tmp/verdugo-egg666 \
VERDUGO_CONTENT666_PYTHON=/tmp/verdugo-content666/bin/python \
python tests_runtime/accept_oxigraph666.py --out /tmp/oxigraph666-evidence.json
```

El instalador exige un prefijo nuevo. Descarga fuentes verificadas, comprueba
licencias y el grafo activo, compila con Cargo offline y lock fijo, comprueba
las dependencias ELF y conserva binario, avisos y recibo. El runtime verifica
sus hashes y permisos. El recibo depende del administrador; no es atestación
independiente ni prueba de reproducibilidad binaria.

La instalación limpia pasó. La aceptación ejecuta siete casos por Engine,
200 comparaciones deterministas independientes, seis rechazos nativos y
alteraciones de binario/recibo. El flujo Egg → Oxigraph → txtai concilia recuentos
por CLI/MCP, comprueba los campos concretos de los planes SQLite, cero clientes
pagados y replay después de reiniciar Engine sin repetir la operación.

Evidencia local: `evidence/accepted/oxigraph666-*-local-20261116.json`.
No afirma aislamiento de red del sistema operativo. El job `oxigraph666`
repite la aceptación bajo `unshare --net` y conserva artefactos por commit.
Los estados de los tres workflows por SHA se mantienen en PR #25 y los
indicadores vivos de `PLAN_666.md`. `live_verified=0`; no hubo consultas a
servidores reales, campañas, mensajes, gastos ni hosting.
