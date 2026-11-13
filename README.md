# Verdugo Digital — integración de aplicaciones originales

**El conjunto de diez aplicaciones todavía no está terminado ni instalado de forma permanente.**
Esta rama conserva el núcleo comercial local y añade laboratorios que instalan y
prueban software original, no simuladores de sus APIs. GitHub Actions ejecuta los
laboratorios temporalmente y elimina sus contenedores al terminar. No se ha
contratado alojamiento ni se ha verificado el teléfono con Termux.

## Resultado nativo comprobado: CUATRO originales juntos

El circuito **GrowthBook → Mautic → RudderStack → Countly**, conectado al núcleo
de Verdugo, aprobó la ejecución
[43390945919](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43390945919)
en el commit `5f45b1a5f5672bb30ec282428fc6a506a81005b4`.

Una configuración realmente creada y leída en GrowthBook pasó a una etiqueta de
un contacto de Mautic derivado de un prospecto leído de Verdugo. La etiqueta leída
de Mautic viajó por el servidor y transformador originales de RudderStack hasta
la API real de Countly. Se comprobó el recuento exacto y la segmentación persistida.
No hubo fallback de envío directo a Countly en este perfil.

Tras reiniciar las aplicaciones y el núcleo se comprobaron los mismos datos.
RudderStack y su base PostgreSQL se reiniciaron en orden de dependencias y después
entregaron **un evento nuevo** a Countly, con lectura posterior del recuento y la
misma segmentación. Las catorce comprobaciones del circuito pasaron. Es una
prueba de reinicio ordenado, no de tolerancia a todas las caídas inesperadas.

Los datos fueron sintéticos; los programas, APIs y bases de datos fueron reales.
Se usaron nueve imágenes oficiales fijadas por digest: representan cuatro de los
diez proyectos y sus dependencias, no nueve proyectos integrados.

[Evidencia extraída del artefacto](evidence/accepted/native-four-43390945919.json).
SHA256 del ZIP original descargado y verificado:
`2a78dc70bf35663ecd343e0c211baa2df5c8fac017eb0cc3018331c67c0992fc`.
La evidencia histórica del circuito de tres está conservada en
[evidence/accepted/native-trio-43386318494.json](evidence/accepted/native-trio-43386318494.json).

| Alcance | Estado |
|---|---|
| Fuentes originales fijadas por submódulo | 10/10 |
| Originales probados juntos en el circuito nativo indicado | 4/10: GrowthBook, Mautic, RudderStack, Countly |
| PostHog, erxes, Dittofeed, OpenReplay, Twenty, Formbricks | Sin aceptación nativa en esta revisión |
| Instalación permanente de los diez | No realizada |
| Ejecución real en el Android del usuario | No verificada |
| Captación de clientes o ingresos reales demostrados | No demostrados |

Una aceptación parcial no equivale a 40 % de avance global ni a 100 % del producto.
Las pruebas unitarias tampoco se cuentan como instalaciones auténticas.

## Reproducir los laboratorios en Linux x86 con Docker

```sh
# Dos aplicaciones originales, datos sintéticos:
python scripts/native-pair-acceptance.py --output native-pair.json
# Circuito de tres:
python scripts/native-pair-acceptance.py --include-growthbook --output native-trio.json
# Circuito de cuatro, incluyendo entrega real por RudderStack:
python scripts/native-pair-acceptance.py --include-rudderstack --output native-four.json
```

Los laboratorios crean recursos temporales propios, usan una red Docker interna
sin salida a Internet y credenciales efímeras, fijan imágenes por digest y exigen
lectura posterior a la escritura. No son un instalador permanente de Termux.
Al terminar, los recursos se destruyen deliberadamente. No se envían campañas ni
mensajes a clientes reales. Los requisitos de Docker/Linux no desaparecen por
haber publicado el código en GitHub.

[Nativo de dos](docs/NATIVE_ACCEPTANCE.md) · [Nativo de tres](docs/NATIVE_TRIO.md) ·
[Circuito de cuatro y evidencia](docs/NATIVE_FOUR.md)

## Núcleo comercial local conservado

Un panel/API registra prospectos, etapas, consentimiento y ventas declaradas en
SQLite. Hay separación por espacio de trabajo, transacciones, eventos idempotentes,
pedidos únicos y una cola que no reintenta automáticamente escrituras inciertas.
Las ventas son declaraciones del operador, no cobros bancarios conciliados ni
utilidad. Los adaptadores opcionales permanecen desactivados por defecto. El
núcleo propio no reproduce todas las funciones de los diez originales.

Requiere Node.js >=22.16 con `node:sqlite` realmente disponible:

```sh
bash scripts/termux-install.sh
node scripts/growth-demo.mjs
bash scripts/termux-run.sh
```

Panel local: `http://127.0.0.1:8177`. Token en
`~/.config/verdugo/environment`; base en `~/.local/share/verdugo/growth.sqlite`,
fuera del repositorio. No publicar esos archivos. El instalador comprueba SQLite;
las pruebas Linux no demuestran por sí solas compatibilidad con Android.

[Termux](docs/TERMUX.md) · [API y límites del núcleo](docs/GROWTH_CORE.md)

## Pruebas y estado del repositorio

```sh
node --test tests/*.test.mjs
python -m unittest discover -s tests -p 'test_*.py' -v
```

La ejecución nativa debe aprobar por separado. `all_ten_integrated`,
`persistent_installation` y `android_verified` permanecen false mientras no
exista evidencia de cada alcance. Los archivos en `evidence/accepted/` conservan
resultados históricos del commit indicado, no garantizan commits posteriores.

`main` y `backup/pre-growth-ten-20261112` se conservan. El PR #14 sigue en borrador.
Faltan integración conjunta de los diez, instalación permanente en un entorno
compatible autorizado y aceptación operativa: privacidad, licencias, seguridad,
retención/borrado, respaldos, recuperación y operación comercial.
