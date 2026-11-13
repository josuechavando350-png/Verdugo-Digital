# Cuatro originales: aceptación conjunta aprobada

**Resultado observado: success** en
[run 43390945919](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43390945919),
commit `5f45b1a5f5672bb30ec282428fc6a506a81005b4`, árbol
`f99b602e58c112506d9a906b738e830b0dfb52d1`.
Trabajo `native-four-originals`, ID `131770407829`.

El circuito instala el servidor original RudderStack, su transformador original
y PostgreSQL junto al circuito auténtico GrowthBook → Mautic → Countly. No
sustituye RudderStack por un endpoint Python ni simula Countly.

## Flujo comprobado

La feature se crea y lee en GrowthBook. Su valor viaja en una etiqueta de Mautic;
la etiqueta realmente leída del contacto se convierte en segmentación del evento.
El evento se entrega a `POST /v1/track` del servidor RudderStack original usando
una write key temporal. Una configuración local soportada conecta esa fuente a
la integración HTTP original del transformador: mapea la solicitud al formato
FORM requerido por la API real de Countly.

En este perfil **no existe fallback de envío directo a Countly**. Un `ok` del
gateway RudderStack no prueba entrega. La ejecución aprobada verificó en Countly
el recuento exacto y la misma segmentación, los conservó después del reinicio y
entregó un evento nuevo por RudderStack después de reiniciarlo con su base.
También comprobó el rechazo de peticiones sin autenticación.

Las catorce comprobaciones del informe son verdaderas. Los cuatro originales
aprobados son `growthbook`, `mautic`, `rudderstack` y `countly`. Nueve contenedores
incluyen sus dependencias: no son nueve de los diez proyectos solicitados.

## Evidencia retenida

[Informe original extraído](../evidence/accepted/native-four-43390945919.json).
Artefacto GitHub ID `14021220713`, nombre `native-four-43390945919`.
SHA256 del ZIP descargado y comprobado:
`2a78dc70bf35663ecd343e0c211baa2df5c8fac017eb0cc3018331c67c0992fc`.

El informe confirma `mock_providers=false`, `synthetic_data=true`,
`resources_removed=true`, `status=passed`. El núcleo Verdugo mantuvo un único
prospecto ante el replay; Countly mantuvo exactamente una ocurrencia de cada
identificador probado. El segundo evento prueba entrega nueva después del reinicio,
no la repetición ciega del primer evento.

## Reproducir

```sh
python scripts/native-pair-acceptance.py --include-rudderstack --output native-four.json
```

Requiere Linux x86 con Docker autorizado. El argumento implica GrowthBook.
Los perfiles previos de dos y tres originales se conservan. Se usa únicamente
una red Docker interna y el núcleo de Verdugo en loopback. Countly tiene un alias
DNS privado estable para evitar IPs de destino obsoletas. No se habilitan campañas
ni comunicaciones con personas reales. Los recursos se eliminan al terminar.

## Versiones y correcciones verificadas

Las nueve imágenes están fijadas por digest. Identificarlas no las equipara con
los commits Git de los submódulos, y una versión fija tampoco demuestra seguridad
productiva por sí sola.

La corrida 43388266789 inició los contenedores pero falló porque nuestra prueba
esperaba incorrectamente `OK`: el gateway original devuelve `ok` en minúsculas.
Se corrigió el acuse sin retirar las comprobaciones posteriores de Countly.

La corrida 43389686730 probó la entrega inicial y su persistencia, pero iniciar
el gateway antes de reiniciar PostgreSQL provocó un fallo de arranque al apagarse
la base. La corrección para la corrida aprobada detiene gateway/transformador,
reinicia PostgreSQL y espera disponibilidad, arranca el transformador y espera
`/features`, y finalmente arranca el gateway y espera `/health`.

Es un **reinicio ordenado con dependencias**, no una prueba de recuperación de
toda caída inesperada. Las bases no se reinicializan ni los datos de negocio se
reinyectan para hacer pasar las lecturas.

## Límites pendientes

`all_ten_integrated`, `persistent_installation` y `android_verified` permanecen
false. El laboratorio no deja una instalación permanente ni ejecutó Termux.
Faltan aceptación conjunta de PostHog, erxes, Dittofeed, OpenReplay, Twenty y
Formbricks, operación general del producto, seguridad/privacidad/licencias,
backups y recuperación, y despliegue en un entorno compatible autorizado.

El resultado del commit probado es histórico: una modificación posterior del
código requiere una nueva ejecución. El PR #14 sigue en borrador y `main` no se
ha sustituido.

## Fuentes primarias de los contratos

- https://github.com/rudderlabs/rudder-server/blob/46504088bef2f70bf0d650e8202c0f7c54f33f11/rudder-docker.yml
- https://github.com/rudderlabs/rudder-server/blob/46504088bef2f70bf0d650e8202c0f7c54f33f11/backend-config/types.go
- https://github.com/rudderlabs/rudder-server/blob/46504088bef2f70bf0d650e8202c0f7c54f33f11/gateway/response/response.go
- https://github.com/rudderlabs/rudder-transformer/blob/55bc61f15179931c740c6b0fa547ee012cfcd930/test/integrations/destinations/http/common.ts
- https://www.rudderstack.com/docs/get-started/rudderstack-open-source/control-plane-lite/
- https://www.rudderstack.com/docs/rudder-cli/destination-types/http-webhook/
