# Control plane y núcleo comercial local

El controlador inicial de consulta se amplió con persistencia y escritura local.
La referencia vigente es [GROWTH_CORE.md](GROWTH_CORE.md); el procedimiento de
instalación está en [TERMUX.md](TERMUX.md).

Se conservan `/healthz`, `/v1/catalog` y `/v1/systems`. Una sonda HTTP 200 sigue
significando únicamente disponibilidad del endpoint, no instalación certificada
ni sincronización de los diez proveedores.

El servidor añade `/v1/capabilities`, `/v1/leads`, `/v1/report`, `/v1/outbox`,
`POST /v1/events` y el despacho manual explícito de eventos opcionales.
Los secretos y datos privados no se sirven con los archivos del panel.

El proceso solo escucha en loopback. La autenticación vincula al operador con
un espacio configurado; las peticiones no pueden cambiarlo. No es un SaaS
multiusuario ni una infraestructura expuesta a Internet.
