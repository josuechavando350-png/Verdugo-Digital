# Operaciones locales v0.9

## Qué ejecuta el motor

| ID | Operación | Resultado delimitado |
|---|---|---|
| trafilatura | html.extract | Texto de artículo a partir de HTML proporcionado; no navega |
| scrapy | html.inspect | Título, encabezados y enlaces del HTML; no sigue URLs |
| duckdb | campaigns.aggregate | Agrupación por canal de gasto, ingreso declarado, leads y conversiones |
| or-tools | selection.solve | Selección de elementos bajo presupuesto y cupo, sin gastar |
| optuna | threshold.optimize | Umbral que optimiza F1 en los datos suministrados; no validación independiente |
| scikit-learn | classifier.score | Clasificador logístico, holdout y puntuaciones para nuevas filas |
| catboost | classifier.score | Clasificador CPU, holdout y puntuaciones para nuevas filas |
| haystack | documents.search | Recuperación BM25 de documentos locales; no llama un LLM |
| great-expectations | data.validate | Comprobaciones de nulos y límites numéricos |
| evidently | drift.report | Comparación de distribuciones entre referencia y datos actuales |
| presidio | text.redact | Redacción de email, teléfono y tarjeta mediante patrones; no exhaustiva |
| playwright | html.audit | Revisión estática móvil/escritorio con JavaScript y recursos de red bloqueados |

Estas recetas se invocan por Engine y por sus entradas run/workflow/MCP existentes.
No existe una segunda ruta de ejecución que omita roles, claves de idempotencia,
planificación, historial o persistencia. Las bibliotecas se importan en un proceso
separado; el núcleo sigue funcionando sin instalar estas dependencias opcionales.

## Evidencia observada

La ejecución 43139596936 comprobó las 12 bibliotecas instaladas, sus resultados
esperados y repetición idempotente. El flujo de cinco pasos conservó resultados
al cerrar y reabrir el motor y no volvió a ejecutar las bibliotecas. Ambos se
probaron con datos sintéticos dentro de un namespace de red sin acceso externo.
Las pruebas unitarias y de contrato del núcleo sumaron 351.

La evidencia distingue los siguientes niveles: código presente, versión instalada,
ejecución real de la operación, validación en una instancia concreta y operación
productiva. Ningún contador del catálogo sustituye estos niveles. Los resultados
actuales de cada commit están en Actions. Las pruebas no certifican ingresos,
calibración comercial, privacidad exhaustiva ni seguridad integral del upstream.

## Instalación reproducible dentro del entorno probado

Usar Linux x86_64 y Python 3.12 en un venv nuevo; no mezclar este entorno con otras
aplicaciones. requirements/runtime.txt selecciona las bibliotecas directas y
runtime.constraints.txt fija 190 versiones observadas en la instalación aprobada.
No se seleccionan dependencias flotantes para resolver el problema conocido de
Evidently 0.7.23 con pandas 3.1: pandas se fija a 2.3.3. Las restricciones son de
versión, no un lock universal por hashes ni una garantía para otras plataformas.

```sh
python3.12 -m venv .venv-runtime
. .venv-runtime/bin/activate
python -m pip install -r requirements/runtime.txt
python -m pip check
export PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/verdugo-browsers"
python -m playwright install --with-deps chromium
python -m verdugo runtime-check
VERDUGO_RUNTIME_REQUIRED=1 python -m unittest discover -s tests_runtime -v
```

No iniciar una instalación de producción desde estos comandos sin revisar
licencias, recursos, protección de datos y operación del host. Las comprobaciones
básicas del núcleo no requieren el venv opcional. No se afirma que los paquetes
nativos tengan wheels compatibles con Termux/Android.

## Configuración y uso

Generar un perfil privado con init. Para cada servicio local que se vaya a utilizar,
el operador debe revisar los requisitos de uso y después configurar:

```json
{
  "enabled": true,
  "license_reviewed": true,
  "runtime_reviewed": true,
  "version": "1.5.6",
  "timeout_seconds": 45
}
```

El ejemplo corresponde a DuckDB, no a otros servicios. El campo version debe
coincidir con la distribución esperada por el adaptador. Las revisiones no son una
licencia otorgada por Verdugo y las banderas de pruebas sintéticas no son un perfil
comercial reutilizable. Playwright requiere también browser_path absoluto que
apunte a una instalación administrada del navegador.

Una orden de análisis puede utilizar la misma interfaz de cualquier otra acción:

```json
{
  "service": "duckdb",
  "operation": "campaigns.aggregate",
  "key": "analisis-demo-001",
  "params": {
    "dataset": "demo",
    "currency": "MXN",
    "rows": [
      {"channel": "organic", "spend_minor": 100, "revenue_minor": 500,
       "leads": 4, "conversions": 1}
    ]
  }
}
```

Guardar el archivo fuera de Git; usar @archivo.local.json, no datos personales en
la línea de comandos. Primero planificar con run sin --execute. Reutilizar una
clave idéntica devuelve el resultado persistido, no una observación fresca.
Cambiar entradas, versión, timeout o código de receta invalida el plan previo.
Una nueva ejecución requiere una clave nueva. No borrar registros para forzarla.

## Flujo compuesto

examples/local-marketing.synthetic.json ejecuta cinco pasos: extracción,
redacción, búsqueda, agregación de campañas y selección presupuestaria. Los tres
primeros se enlazan por referencias a resultados del mismo workflow. Los otros
dos son análisis independientes del ejemplo, no una atribución causal conjunta.
Los datos de demo nunca se contabilizan como ventas reales.

## Aceptación de servidores

El workflow Verdugo real service acceptance instala binarios comunitarios
Qdrant 1.20.0 y Meilisearch 1.56.2 desde releases oficiales, comprueba SHA-256 antes
de ejecutarlos y limita la red a loopback. Provisiona únicamente una colección o
índice sintético en directorios nuevos, comprueba la lectura mediante Engine,
rechazo de credenciales incorrectas y repetición sin otra llamada HTTP. Después
termina los procesos y elimina los datos. Es un arnés de prueba, no un instalador
productivo accesible a agentes ni una autorización de despliegue permanente.
Su aprobación se observa por commit; el código del test por sí solo no acredita
un resultado exitoso. No valida escrituras comerciales ni todas las APIs.

Fuentes de configuración y artefactos:
- https://qdrant.tech/documentation/operations/configuration/
- https://qdrant.tech/documentation/security/
- https://github.com/qdrant/qdrant/releases/tag/v1.20.0
- https://github.com/meilisearch/meilisearch/releases/tag/v1.56.2
- https://specs.meilisearch.dev/specifications/text/0119-instance-options.html

## Límites de seguridad y disponibilidad

El worker usa un comando fijo, no shell. No hereda las credenciales del proceso
padre y limita CPU, tiempo de pared, JSON de entrada/salida y tamaño por archivo.
Chromium necesita hasta 128 MiB por archivo temporal; otros workers usan 2 MiB;
la salida JSON sigue limitada a 1 MiB. No es una cuota total de disco o memoria.
Los hooks de sockets de Python no confinan código nativo. El aislamiento de red
de CI es una defensa adicional, no algo instalado automáticamente en producción.

No se cargan modelos pickle, Python del usuario, SQL arbitrario, rutas de lectura
ni destinos de red proporcionados en las entradas. HTML y documentos son datos
no confiables, no instrucciones para agentes. Los resultados pueden contener
información personal aunque la respuesta de errores esté reducida a tipos.
Deben protegerse el host, los perfiles, SQLite, temporales y respaldos.

## Trabajo aún no realizado

Hay 66 proyectos sin adaptador. Requieren implementación, contratos y pruebas,
no solamente credenciales. Los 22 adaptadores HTTP tienen un alcance parcial;
la aceptación de dos servidores no acredita a los restantes. No existe hosting
productivo, supervisor 24/7, IAM hostil multiempresa ni reconciliación bancaria.
Las licencias de los 100 proyectos de fuente permanecen pendientes de revisión
individual para el uso comercial concreto.
