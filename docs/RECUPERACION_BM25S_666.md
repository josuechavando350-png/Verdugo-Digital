# Recuperación del candidato BM25S — 15 de noviembre de 2026

## Reanudación tras pérdida del entorno de ejecución

El 15 de noviembre de 2026, después de publicar `713e4c0d91811ac0b81c9d20240aeb70545f957a`, el entorno local dejó de estar disponible. La conexión a GitHub siguió operativa. **BM25S no está publicado ni se cuenta como conexión:** los cambios candidatos y la comprobación final estaban en el entorno inaccesible. No se presupone que esos archivos se hayan conservado.

El checkpoint de fuentes de esta continuación no modifica adaptadores, workflows, políticas de permisos ni la pertenencia de A/B. Conserva **Lote A 0/164 · Lote B 0/163**, 282 adaptadores, 56 piezas de construcción, 328 pendientes y `live_verified=0`. Registra el bloqueo adicional de Rustworkx y elimina la descripción obsoleta de Zlib como bloqueo del candidato de Egg. Un bloqueo revisado no suma conexiones.

En `713e4c0d`, verificación y servicios terminaron en `success`; runtime tenía 30 de 31 jobs en `success`, incluido `baseline` con **921 pruebas**, y `pilot666` continuaba compilando. Esta observación corresponde a ese commit, no a su sucesor. El estado del head se consulta por separado:

[![Verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/workflows/verify.yml/badge.svg?branch=feat%2F666-pilot)](https://github.com/josuechavando350-png/Verdugo-Digital/actions/workflows/verify.yml?query=branch%3Afeat%2F666-pilot)
[![Runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/workflows/runtime-acceptance.yml/badge.svg?branch=feat%2F666-pilot)](https://github.com/josuechavando350-png/Verdugo-Digital/actions/workflows/runtime-acceptance.yml?query=branch%3Afeat%2F666-pilot)
[![Servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/workflows/real-services.yml/badge.svg?branch=feat%2F666-pilot)](https://github.com/josuechavando350-png/Verdugo-Digital/actions/workflows/real-services.yml?query=branch%3Afeat%2F666-pilot)

La descripción de PR #25 conserva la observación de los tres workflows y el SHA al que corresponde. No se hereda el verde de un commit anterior.

### Recuperar el candidato BM25S antes de continuar

1. Comprobar el head remoto y el estado local. Si reaparece el entorno anterior, preservar su diff y archivos sin seguimiento antes de actualizar la rama; no descartar el candidato ni sobrescribir las revisiones remotas. Si no reaparece, reconstruir desde las fuentes fijadas.
2. Revisar los candidatos `verdugo/local_bm25s666.py`, `sources/contracts-bm25s666.json`, `tests_runtime/install_bm25s666.py`, `tests_runtime/accept_bm25s666.py` y `tests/test_bm25s666.py`, además de los cambios de integración. **Esos archivos no forman parte de este checkpoint remoto.**
3. Recuperar, si existen, `/tmp/verdugo-bm25s-tests.log` y `/tmp/bm25s666-clean-build.log`. La ejecución completa y la instalación limpia se lanzaron, pero no se recuperó su resultado final después de la pérdida del entorno. No asumir que aprobaron.
4. Repetir la aceptación con el perfil construido desde cero, las aserciones de dependencia entre BM25S y txtai, CLI/MCP, SQLite y replay tras reinicio. Conservar la evidencia antes de aumentar los contadores.
5. Publicar el incremento solo después de verificar fuentes, licencias, instalación y pruebas. El primer adaptador nuevo elevaría A a 1/164 y el total a 283/56/327; esos números son una condición futura, no el estado de este checkpoint. Comprobar los tres workflows del nuevo commit.

### Alcance técnico del candidato, todavía no publicado

BM25S se fijó en `xhluca/bm25s@b335013d0172e8c2aabd1399d60146cc51768458`. El candidato usaba NumPy 1.26.4 (`numpy/numpy@9815c16f449e12915ef35a8255329ba26dacd5c0`) compilado desde fuente; es una resolución distinta del análisis histórico de NumPy 2.2.6. Se revisaron 100 blobs de BM25S y 2111 coincidencias de NumPy; la diferencia documentada de `doc/make.bat` era de empaquetado y no se compilaba. Estos detalles deben recuperarse junto con sus hashes, no reconstruirse como evidencia a partir de este resumen.

La receta limitada `retrieval.check` aceptaba solo el dataset demo, documentos y consulta con identificadores enteros acotados y `k`. Construía tokens sintéticos internamente y usaba el BM25 original con método Lucene, backend NumPy y sin modelos, Scipy, JAX ni Numba. Contrastaba puntuaciones y selección con una referencia escalar independiente, devolviendo únicamente recuentos. La versión 0.0.0 era el fallback original del archivo de fuentes, no una versión publicada inventada.

Hubo una aceptación previa del candidato con seis casos y un flujo BM25S → txtai por Engine. Se corrigió la referencia a `analysis-retrieval.result.matching_documents`. Después se reforzaron las aserciones de consumo del recuento y de cero clientes pagados; la comprobación final de esas aserciones quedó sin recuperar. No se certificó producción ni un cierre completo de todas las herramientas de construcción.
