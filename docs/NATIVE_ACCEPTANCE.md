# Aceptación de programas originales: Mautic y Countly

Esta revisión deja de usar servidores simulados para **esta prueba concreta**.
No declara terminado el alcance de diez aplicaciones y no cambia el entorno
previsto del usuario ni contrata alojamiento.

## Qué ejecuta

El workflow `Native originals — Mautic and Countly acceptance` utiliza una máquina
Linux x86 de GitHub Actions durante un trabajo acotado. Descarga las imágenes
oficiales de Mautic, Countly API y Countly frontend, además de MySQL y MongoDB.
Cada imagen se resuelve a su ID inmutable antes de ejecutarse; el informe conserva
el digest observado. Los tags de Countly son `latest`: no se afirma que equivalgan
a los commits de los submódulos. Las versiones exactas son las del informe de cada
corrida; no constituye todavía un lock de producción entre distintas corridas.

Crea bases de datos vacías y credenciales efímeras. Los servicios están en una red
Docker interna, sin salida externa. No hay cron/worker de marketing habilitado.
Los puertos expuestos se vinculan solo a 127.0.0.1. No se usan cuentas de clientes,
credenciales del usuario, dominios nuevos, pagos ni correos reales.

El flujo exigido para aprobar es:

1. Guardar un prospecto sintético a través de la API real de Verdugo y leerlo.
2. Crear desde ese registro un contacto mediante la API real de Mautic y volver
   a leer su ID y correo sintético, comprobando igualdad.
3. Registrar en la API real de Countly un evento derivado del contacto de Mautic.
4. Leer el recuento persistido mediante `/o/analytics/events`: debe existir
   exactamente una ocurrencia del identificador de evento.
5. Reiniciar Mautic, Countly API y Verdugo; comprobar nuevamente los registros
   y la idempotencia local de la captura en Verdugo.
6. Eliminar únicamente contenedores y red creados por esta ejecución.

La inicialización de Mongo crea solamente el administrador temporal de Countly.
Los contactos y los eventos de aceptación **no se inyectan en las bases**: deben
atravesar las APIs de los productos originales. Los datos son sintéticos; los
programas, bases de datos y solicitudes HTTP son reales cuando el workflow pasa.

## Lo que no demuestra

No instala de forma permanente los diez programas. No certifica Android, Termux,
licencias comerciales, multiusuario, seguridad de producción, facturación,
recuperación ante desastre ni envíos reales de marketing. No es todavía un
adaptador general con replay distribuido: el script no repite escrituras inciertas.
La integración de negocio probada se limita al flujo anterior.

`all_ten_integrated`, `persistent_installation` y `android_verified` permanecen
**false incluso si esta prueba pasa**. Solo un resultado `passed` del commit
concreto permite afirmar aceptación temporal de Mautic y Countly. Las pruebas
unitarias de `test_native_acceptance.py` no cuentan como servicios instalados.

## Ejecución local autorizada en Linux con Docker

```sh
python scripts/native-pair-acceptance.py --output native-acceptance.json
```

No ejecutar como supuesto instalador de Termux. Sin Docker, el programa devuelve
código 2 y `docker_engine_unavailable`; no inventa una instalación. El host debe
disponer de espacio y memoria para las cinco imágenes y los procesos indicados.
La red y los contenedores son temporales y se eliminan al terminar.

## Fuentes primarias de los contratos

- https://github.com/mautic/docker-mautic (imagen oficial y roles de ejecución).
- https://docs.mautic.org/en/6.0/getting_started/how_to_install_mautic.html
  (instalación por CLI y opciones).
- https://github.com/Countly/countly-server/blob/0816e218e45f9a15d225b44503fa6ae40993d7ee/docker-compose.yml
  (imágenes oficiales y configuración de los servicios).
- https://github.com/Countly/countly-server/blob/0816e218e45f9a15d225b44503fa6ae40993d7ee/test/2.api/08.create.app.js
  (creación y lectura de aplicación).
- https://github.com/Countly/countly-server/blob/0816e218e45f9a15d225b44503fa6ae40993d7ee/test/3.api.write/5.write.app.events.js
  (ingesta y lectura verificable de recuentos de eventos).

## Bloqueo para completar los diez originales en el entorno solicitado

PostHog documenta 4 vCPU, 16 GB RAM y más de 30 GB de almacenamiento para su
instalación autohospedada; OpenReplay exige arquitectura x86 y documenta 8 GB RAM
y 50 GB de almacenamiento. PRoot no proporciona los namespaces/cgroups del kernel
que requieren esos despliegues Docker habituales. Estos requisitos no son una
estimación de la suma total de los diez. GitHub Actions sirve aquí como entorno
temporal de pruebas, no como instalación permanente del producto.

Fuentes: https://posthog.com/docs/self-host ;
https://docs.openreplay.com/en/deployment/deploy-docker/ ;
https://github.com/termux/proot-distro ;
https://docs.github.com/en/actions/reference/runners/github-hosted-runners .
