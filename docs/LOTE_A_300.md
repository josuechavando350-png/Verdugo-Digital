# Lote A: motor y anuncios

Base: `85c1c74` de `main`. Alcance cerrado: 300 piezas libres. Sin despliegue,
comunicaciones, gasto publicitario ni acceso a cuentas reales.

| Medida | Antes | Después del código |
|---|---:|---:|
| Conectadas bajo política | 243 | 244 |
| Componentes sin panel | 56 | 56 |
| Conectores pendientes | 1 | 0 |
| Excluidas por licencia | 22 | 22 |
| HTTP implementados | 103 | 104 |
| Operaciones HTTP | 107 | 108 |
| Operaciones locales | 159 | 159 |
| Herramientas MCP | 26 | 27 |
| Pruebas del núcleo | 731 | 755 |
| Verificadas en vivo | 0 | 0 |

## Funcionamiento

- `scripts/activar.sh --perfiles`: instala explícitamente los perfiles Python
  separados y escribe un entorno privado reutilizable. Sin cambios a postCreateCommand.
- `ads-import @archivo.csv --platform google|meta [--execute]`: vista previa y
  escritura exclusiva del operador; CSV de hasta 5 MiB; encabezados bilingües;
  agregados por fecha, campaña seudonimizada, plataforma, moneda y dataset.
- `ads-report`: periodos, comparación, costo por conversión, ritmo mensual,
  anomalías y línea base opcional. MCP `verdugo_ads_report` es solo lectura.
- `meta-ads / insights.summary`: una cuenta y un periodo revisados en configuración;
  campos fijos; no admite parámetros. Proyección antes de SQLite.
- `.mcp.json` y `examples/codex-config.toml`: proceso local stdio del mismo Engine.

La repetición exacta del CSV no duplica métricas ni eventos. Un cambio corrige sus
claves; filas ausentes no borran datos anteriores. Se rechazan desgloses ambiguos
que repiten gasto, columnas desconocidas, archivos no regulares y monedas mezcladas.
Los nombres de campaña y acciones no se guardan. El reporte nunca trata conversiones
como clientes. `won/paid` son ventas con pago declarado, no comprobación bancaria.
Las ventas no se atribuyen a campañas ni plataformas sin evidencia.

## Contrato Meta y privacidad

Fuente oficial: `meta/facebook-python-business-sdk@b08e5c1d36a2adad3c4ede6578654c8eaca5f225`.

- [session.py](https://github.com/meta/facebook-python-business-sdk/blob/b08e5c1d36a2adad3c4ede6578654c8eaca5f225/facebook_business/session.py): `FacebookSession`, origen Graph y `access_token` en parámetros de requests.
- [api.py](https://github.com/meta/facebook-python-business-sdk/blob/b08e5c1d36a2adad3c4ede6578654c8eaca5f225/facebook_business/api.py): `call`, GET con `params`; no se utiliza su registrador de depuración ni telemetría.
- [adaccount.py](https://github.com/meta/facebook-python-business-sdk/blob/b08e5c1d36a2adad3c4ede6578654c8eaca5f225/facebook_business/adobjects/adaccount.py): `get_insights`, GET `/insights`, `level`, `time_range`, `fields`, `limit`.
- [apiconfig.py](https://github.com/meta/facebook-python-business-sdk/blob/b08e5c1d36a2adad3c4ede6578654c8eaca5f225/facebook_business/apiconfig.py): API v26.0 y SDK v26.0.4.
- [adsinsights.py](https://github.com/meta/facebook-python-business-sdk/blob/b08e5c1d36a2adad3c4ede6578654c8eaca5f225/facebook_business/adobjects/adsinsights.py): campos de gasto, clics, impresiones, fechas y moneda.

El token se añade al construir la ruta de transporte; no entra al plan público,
la huella, eventos ni SQLite. La huella vincula el nombre de la variable de credencial,
la cuenta y el periodo, no el contenido del token. Rotar un token no vuelve a ejecutar
la misma clave; una lectura nueva requiere una clave nueva. Errores HTTP omiten el
cuerpo y la URL. No se siguen redirecciones ni paginación. El origen productivo es
únicamente `https://graph.facebook.com`; loopback existe para pruebas sintéticas.
No hay cambios de licencia ni excepciones; `license_review` sigue pendiente.
No se lanzan anuncios. Requiere cuenta autorizada, permisos mínimos y revisión del operador.

## Evidencia y límites

Baseline observado: **731 pruebas**. Suite nueva: **755 pruebas**, más una prueba
separada en `tests_runtime/test_ads_report.py` que ejecutó PyOD y StatsForecast
originales con agregados importados y rol viewer. Se verificaron anomalía y línea
base de siete días, sin añadir eventos al consultar. El contrato Meta pasó sockets
HTTP locales, privacidad, rechazo de errores y replay. Todo usa datos sintéticos.

Inventario inicial de esta sesión Linux/Python 3.12: **8/159** rutas con versiones
coincidentes. Eso es disponibilidad de metadatos, no aceptación de las 159 rutas.
Instalación observada en este entorno: **32/32 perfiles Python** instalados,
**1,843.71 segundos** sumados por perfil (30 min 43.71 s) y **34,650,744,154 bytes**
de archivos en sus entornos (32.27 GiB; no incluye caché ni bloques del sistema).
Inventario final: **127/159** versiones coincidentes; **32** rutas requieren otros
runtimes, herramientas o versiones. No se probaron aquí las 127 ejecuciones.
Durante la instalación la caché de pip llenó el volumen temporal del usuario;
se limpió esa caché desechable y todos los perfiles finalizaron. El instalador
ahora usa `--no-cache-dir` para no volver a acumularla.
No se operó Codespaces: tiempo, disco e inventario en Codespaces siguen sin observar.
El operador puede reproducirlos con `--perfiles` y consultar los reportes privados.
No se afirma instalación de runtimes npm, Go, R o servidores nativos con este script.

Para revisar: comprobar CI del commit del PR; abrir la rama en Codespaces o laptop,
ejecutar el instalador, revisar permisos y habilitar solo las bibliotecas necesarias.
Conectar cuentas reales y verificar su funcionamiento corresponde al operador.
