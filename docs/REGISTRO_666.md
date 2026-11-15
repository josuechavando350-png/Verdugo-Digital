# Registro de los 666: evidencia y límites

Observación: 15 de noviembre de 2026. Base: `a5caa9e` (plan 666 incorporado en main).

El catálogo contiene **688 identidades GitHub distintas: 666 permitidas por la
política técnica de licencias y 22 excluidas históricas**. Esta modificación añade
366 registros y **cero operaciones**. Los comandos `licenses`, `connections`,
`sources`, `status`, `product-status` y la plantilla comparten el mismo catálogo.

## Qué se comprobó

- Los 366 commits propuestos permiten recuperar su archivo de licencia original.
- Se resolvieron 34 cambios de nombre/propietario entre las propuestas; se guardó
  el ID numérico de GitHub para evitar duplicar repositorios trasladados.
- Se contrastaron las identidades de los 322 registros anteriores con las nuevas.
  Cinco propuestas eran alias de entradas existentes.
- TEN Framework incluye condiciones adicionales que restringen la competencia con
  Agora y el despliegue en dispositivos de usuarios. Su licencia en el commit
  propuesto no cumple la política de licencias permisivas del repositorio.
- Cada incorporación conserva repositorio canónico, commit de 40 caracteres,
  archivo de licencia, blob SHA de Git, SHA256 y bytes originales. Los cuatro
  casos con dos licencias conservan ambos archivos. Los textos de licencia no son
  código ejecutable ni pesos de modelos.
- El lector verifica las identidades, la cola, la vinculación a los commits y los
  hashes sin red. El motor no instala, importa ni ejecuta estos proyectos.

## Correcciones de la propuesta

Los cinco originales duplicados conservan sus IDs y adaptadores anteriores. Las
siguientes incorporaciones cubren funciones relacionadas; no se afirma que sean
equivalentes en toda su funcionalidad.

| Propuesta | Problema | Incorporación distinta | Alcance previsto |
|---|---|---|---|
| explodinggradients/ragas | Ya es vibrantlabsai/ragas | tensorzero/tensorzero | Evaluación local/autohospedada, sin proveedores de pago |
| microsoft/presidio | Ya es data-privacy-stack/presidio | LeapBeyond/scrubadub | Detección local de información personal |
| jlowin/fastmcp | Ya es PrefectHQ/fastmcp | pydantic/monty | Intérprete OSS local con operaciones fijas; sin servidor comercial |
| microsoft/recommenders | Ya es recommenders-team/recommenders | lenskit/lkpy | Recomendación sobre datos sintéticos propios; excluir data/ |
| great-expectations/great_expectations | Ya es fivetran/great_expectations | frictionlessdata/frictionless-py | Validación de tablas locales |
| TEN-framework/ten-framework | Licencia con restricciones adicionales | wiseman/py-webrtcvad | Detección local de actividad de voz; no es un conversador completo |

Las evidencias de las propuestas rechazadas también se conservan. TEN no se añade
al catálogo operativo ni a la lista histórica de 22 exclusiones. No se creó
ninguna excepción de política. La alternativa `pydantic/mcp-run-python` fue
descartada tras leer que upstream la retiró por problemas de aislamiento; no forma
parte de las 666.

## Archivos y reproducción

- `verdugo/catalog.py`: IDs estables; las 322 entradas anteriores mantienen orden.
- `sources/parts/`: 69 archivos; los primeros 68 contienen diez entradas y el
  último ocho. Los 322 pins anteriores se conservan.
- `sources/registry-666.json`: identidades, correcciones, evidencias y cola de trabajo.
- `sources/license-texts/`: bytes originales con nombre SHA256, deduplicados por contenido.
- `sources/licenses.json`: política por entrada; `license_review` sigue pendiente.
- `sources/connections.json`: clasificación de conexión prevista, no despliegue.

```sh
python -m unittest discover -s tests -v
python -m verdugo licenses
python -m verdugo connections
python -m verdugo sources
python -m verdugo --state :memory: status
```

Los límites esperados son 688 registrados, 666 permitidos, 243 conectados bajo
política, 56 piezas de construcción, 367 pendientes y cero servicios productivos
certificados. Las nuevas entradas no pueden ejecutar operaciones inventadas,
incluso si su configuración se habilita.

## Trabajo que sigue pendiente

La cola `work_queue` distribuye exactamente 366 IDs distintos en **183 + 183**,
conservando las prioridades funcionales del plan. Cada entrada sigue en
`pending_contract`; su asignación a un lote no demuestra integración. Las fases
son 50, 50, 50, 50, 41, 50 y 75 piezas. La fase 3 contiene exactamente los 50
proyectos del simulador. Los sobrantes funcionales se conservan en la fase 7.

Faltan contratos tomados del código original, adaptadores acotados, versiones de
paquetes y perfiles reproducibles, pruebas con bibliotecas originales, flujo
conjunto, modelo local con licencia de pesos comprobada y aceptación por commit.
Ninguna ruta API fue inventada para completar el registro. No se bajaron modelos,
se enviaron mensajes, se crearon campañas ni se aprovisionó infraestructura.

Los tres workflows deben observarse en el commit del PR antes de declarar
terminada la aceptación de la tanda 0. Una suite unitaria aprobada no sustituye
la aceptación de ejecución real ni demuestra un producto 24/7.
