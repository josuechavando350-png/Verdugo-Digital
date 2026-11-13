# Circuito nativo de tres originales — aceptación acotada

El perfil `--include-growthbook` amplía el laboratorio Mautic/Countly con
GrowthBook 5.2.0, fijado al digest observado en el laboratorio auténtico anterior.
No sustituye ninguna aplicación por código propio o servidores simulados.

## Flujo que debe probar

1. Instalar imágenes oficiales e inmutables de GrowthBook, Mautic y Countly,
   junto con MySQL/MongoDB, en la misma red Docker interna sin salida a Internet.
2. Crear la cuenta, organización, clave API y feature de GrowthBook a través
   de sus endpoints originales; leer el valor recién guardado.
3. Capturar un prospecto sintético en Verdugo y leerlo de su API persistente.
4. Crear en Mautic el contacto derivado del registro de Verdugo, etiquetado
   con el valor realmente leído de GrowthBook; volver a leer el contacto.
5. Tomar la etiqueta leída de Mautic, no una copia asumida, y registrarla como
   segmentación `route` del evento de Countly. Exigir recuento igual a uno y
   lectura de esa segmentación mediante las APIs originales de Countly.
6. Reiniciar las tres aplicaciones y Verdugo; volver a comprobar las mismas
   identidades, feature, etiqueta, evento, segmentación e idempotencia local.
7. Eliminar los recursos efímeros creados por la ejecución.

Las direcciones privadas se vuelven a descubrir después del reinicio para no
confundir una IP antigua con otro servicio. Las claves son temporales, se
ocultan en los logs y no se incluyen en el informe. No se habilitan envíos
comerciales ni se utilizan personas o correos reales.

## Ejecutar en un entorno Linux x86 con Docker autorizado

```sh
python scripts/native-pair-acceptance.py --include-growthbook --output native-trio.json
```

La ruta sin ese argumento conserva la aceptación original de Mautic y Countly.
El workflow nuevo `Native originals — Unified GrowthBook Mautic Countly flow`
exige las once comprobaciones del perfil ampliado. Las 18 pruebas Python de
contrato/seguridad del código son pruebas unitarias, no prueba de instalación.
Solo el resultado del workflow nativo para el commit concreto acredita el flujo.

## Evidencia anterior, independiente del circuito nuevo

- Mautic/Countly: ejecución 43383607174, head
  `a08daabdfc322763f0180f817c90d9042aea42c9`, checkout del PR
  `39b3aaf688e6c6d7a691a90690d4c6f0d1735065`: aprobada, seis comprobaciones.
  ZIP de evidencia SHA256:
  `e5cd0f7985db200da3e7e883996ab1144e0414f6c69b57f27b8f1a98aac5a509`.
- GrowthBook/Mautic: ejecución 43385160817, commit
  `82755036c0bf14f486b85790a82ccece67feec0e`: aprobada, incluyendo reinicio
  de aplicaciones y bases de datos. ZIP de evidencia SHA256:
  `bc17aa5885c6dcc7cf8698fb787ea19b66c8ded3f5968dc42ae9f28b2ff2f6ba`.

Esas dos aceptaciones separadas no se presentan como una aceptación del nuevo
circuito de tres ni del conjunto de diez. El resultado del circuito ampliado
queda pendiente de observar después de publicar esta revisión.

## Límites que no cambian

`all_ten_integrated`, `persistent_installation` y `android_verified` permanecen
false incluso si el circuito de tres aprueba. No es una instalación permanente
en el teléfono, ni un producto de diez aplicaciones terminado, ni una prueba de
rentabilidad o captación de clientes. Son versiones oficiales de imágenes,
no una afirmación de equivalencia con los commits Git de los submódulos.

Contrato de segmentación Countly:
https://github.com/Countly/countly-server/blob/0816e218e45f9a15d225b44503fa6ae40993d7ee/test/3.api.write/5.write.app.events.js

La prueba sigue sin contratar infraestructura externa ni modificar `main`.
