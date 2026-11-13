# Cuarto original: RudderStack como transporte real

Este perfil añade el servidor original RudderStack, su transformador original y
PostgreSQL al circuito auténtico GrowthBook -> Mautic -> Countly. No sustituye
RudderStack por un endpoint Python ni simula Countly.

## Contrato

La feature se crea y lee en GrowthBook. Su valor viaja en una etiqueta de Mautic;
la etiqueta realmente leída del contacto se convierte en segmentación del evento.
El evento se entrega a `POST /v1/track` del servidor RudderStack original usando
una write key temporal. Una configuración local soportada conecta esa fuente a
la integración HTTP original del transformador: mapea la solicitud al formato
FORM requerido por la API real de Countly.

En este perfil **no existe fallback de envío directo a Countly**. Un `ok` del
gateway RudderStack no prueba entrega. Para aprobar se exige leer en Countly el
recuento exacto y la misma segmentación, conservarlos después del reinicio y
entregar un evento nuevo por RudderStack después de reiniciarlo con su base.
También se exige que el gateway rechace peticiones sin autenticación.

```sh
python scripts/native-pair-acceptance.py --include-rudderstack --output native-four.json
```

El argumento implica GrowthBook. Los perfiles previos de dos y tres originales
se conservan. La ejecución usa solamente una red Docker interna y el núcleo de
Verdugo en loopback; no se habilitan campañas ni comunicaciones con personas.
Countly tiene un alias DNS privado estable para evitar IPs de destino obsoletas.

## Versiones y corrección observada

Las nueve imágenes están fijadas por digest. Los tres digests de RudderStack,
su transformador y PostgreSQL se observaron en la ejecución 43388266789. Esa
corrida inició todos los contenedores, pero falló porque la prueba esperaba
incorrectamente `OK`: el contrato original del gateway devuelve `ok` en minúsculas.
La corrección conserva la exigencia de HTTP 200 y del cuerpo exacto, más todas las
lecturas posteriores de Countly; no convierte un simple acuse en aceptación E2E.
El transformador debe responder a `/features` antes de iniciar el gateway.

Fijar las identidades de las imágenes no significa que la integración esté aprobada,
ni equipara las imágenes con los commits Git de los submódulos.

## Estado de aceptación

El circuito de TRES originales aprobó realmente en la ejecución 43386318494,
commit `f13aee46293a164968064fad666bc3a06ee94700`. Sus once checks son true y el
ZIP descargado coincide con SHA256
`452448bb77cbd83f162077b34dded8c91bdf7104bb187aa15b1950555d7a306e`.
La evidencia extraída está en `evidence/accepted/native-trio-43386318494.json`.

El perfil nuevo de CUATRO queda **pendiente de su propia ejecución nativa** al
publicar esta corrección. Sus pruebas unitarias no cuentan como aplicaciones
instaladas. Tampoco se mezclan éxitos de dos perfiles para afirmar uno mayor.

Incluso si el perfil de cuatro aprueba, `all_ten_integrated`,
`persistent_installation` y `android_verified` permanecen false. Los servicios
son efímeros y se eliminan al terminar; no hay instalación permanente en Termux.

## Fuentes primarias

- https://github.com/rudderlabs/rudder-server/blob/46504088bef2f70bf0d650e8202c0f7c54f33f11/rudder-docker.yml
- https://github.com/rudderlabs/rudder-server/blob/46504088bef2f70bf0d650e8202c0f7c54f33f11/backend-config/types.go
- https://github.com/rudderlabs/rudder-server/blob/46504088bef2f70bf0d650e8202c0f7c54f33f11/gateway/response/response.go
- https://github.com/rudderlabs/rudder-transformer/blob/55bc61f15179931c740c6b0fa547ee012cfcd930/test/integrations/destinations/http/common.ts
- https://www.rudderstack.com/docs/get-started/rudderstack-open-source/control-plane-lite/
- https://www.rudderstack.com/docs/rudder-cli/destination-types/http-webhook/
