# v0.21 — punto de control de la segunda tanda

Se continúa el PR #19, commit `38752542fb452033e8100ddcb008a0a9e3bedb5e`.
Se implementaron 18 de las 88 operaciones pendientes. **Faltan 70**: este punto
no termina la segunda tanda ni acredita un despliegue productivo.

| Programa original | Operación implementada | Límite explícito |
|---|---|---|
| geo-lint | Revisar contenido proporcionado con reglas nativas | Sin ranking ni rastreo |
| site-md | Convertir HTML proporcionado a Markdown | Sin descargar páginas |
| SEO Graph | Construir breadcrumbs JSON-LD | Sin publicar en sitios |
| Adobe structured-data-validator | Validar breadcrumbs | Sin garantía de elegibilidad en buscadores |
| Chronos | Cuantizar y reconstruir una serie proporcionada | Sin modelo ni pronóstico |
| GLiNER | Evaluar anotaciones de entidades contra referencias | Sin inferencia de entidades |
| Graphiti | Formar grupos que cubren todos los pares de elementos | Sin construir un grafo externo ni llamar modelos |
| OpenBB | Validar precios OHLCV contra su esquema original | Sin obtener ni certificar cotizaciones |
| people-also-ask | Extraer preguntas de HTML proporcionado | Sin consultar Google |
| JobSpy | Limpiar descripciones HTML | Sin buscar empleos ni extraer contactos |
| Gitleaks | Detectar patrones de secretos en texto proporcionado | Sin probar credenciales |
| Restic | Respaldar, recuperar y verificar datos en repositorio efímero | No crea respaldo duradero |
| Syft | Inventariar registros npm proporcionados | No inspecciona instalaciones del usuario |
| Grype | Comparar versiones npm contra snapshot original fijado | No prueba explotabilidad; base del 14/11/2026 |
| SOPS + age | Cifrar y descifrar datos con clave efímera | No conserva archivos cifrados ni claves |
| Vale | Revisar palabras de énfasis con regla fija | No es revisión editorial completa |
| DVC | Versionar y recuperar archivo temporal | Sin configurar almacenamiento remoto |
| dnstwist | Generar variantes por omisión y transposición | Sin DNS, WHOIS ni navegación |

Todas las operaciones pasan por `local_runtime`, el worker existente, Engine,
workflow/product-run y SQLite. Los nuevos procesos aceptan únicamente argumentos
fijos; el usuario no puede proporcionar comandos, rutas, claves, modelos ni URLs.
Los tres flujos con referencias son HTML → lint, breadcrumbs → validador y
Syft → Grype. Las demás operaciones pueden incluirse en la misma ejecución.
La reanudación debe recuperar resultados sin volver a ejecutar los programas.

Los parámetros `secret_text` se eliminan de planes públicos y de la persistencia;
los hashes/resultados resumidos pueden conservarse. Se agregó sanitización a
`workflow.ordered_steps`, además de la sanitización ya presente en Engine.

## Versiones y preparación explícita

Los seis binarios Go se compilan desde los commits del catálogo y se comprueba
`vcs.revision` y `vcs.modified=false`. Sus SHA-256, el de age-keygen y el de la
base de Grype forman parte del vínculo de ejecución. La base ocupa aproximadamente
3.44 GB; su descarga se verifica contra el SHA-256 publicado del archivo original.
No se descarga ni actualiza desde una operación del motor.

Los cuatro paquetes npm se instalan con `npm ci --ignore-scripts` desde el lock
incluido. El perfil usa Node 24.22.1. Las seis bibliotecas y dos CLI Python usan
perfiles separados con versiones y restricciones fijadas, y `pip check`.

Preparación **explícita del administrador/CI**, fuera del producto:

```sh
python tests_runtime/install_final.py --group content021
python tests_runtime/install_final.py --group entities021
python tests_runtime/install_final.py --group pycli021
python tests_runtime/install_final.py --group node
```

Los grupos `cli-security` y `cli-storage` preparan sus respectivos binarios en
un entorno Linux x86_64 limpio, separados en CI para limitar disco y compilación.
`accept_final.py --group GRUPO` ejecuta las operaciones y la composición/reinicio
exigiendo que estén instaladas. CI usa un espacio de red deshabilitado del sistema
operativo. Los bloqueos Python/Node son defensa adicional, no un sandbox contra
código nativo hostil. El operador debe confiar en el perfil y sus dependencias.

Los perfiles se seleccionan únicamente mediante variables de entorno administradas:
`VERDUGO_CONTENT021_PYTHON`, `VERDUGO_ENTITIES021_PYTHON`,
`VERDUGO_PYCLI021_PYTHON`, `VERDUGO_NATIVE_ROOT` y `VERDUGO_CLI_ROOT`.
No son parámetros de herramientas ni del MCP. Todo permanece deshabilitado hasta
la revisión local de licencia y runtime. No se aceptaron licencias automáticamente.

## Evidencia

Fuentes por commit y SHA Git en `sources/contracts-v021-{native,content,cli}.json`.
Pruebas de contrato en `tests/test_*v021.py`; aceptación contra programas originales
en `tests_runtime/test_libraries.py` y `test_final_product.py`.
Los resultados locales se registran en `docs/evidence/v021-local.json` cuando
termina la verificación. El estado de CI debe consultarse por commit; preparar
un workflow no significa que haya aprobado.

El perfil de binarios descrito es Linux x86_64. **No se ha probado en Android/Termux**.
Tampoco se instaló un servicio permanente ni se acreditaron ingresos o clientes.

## Integridad de la base Grype después de importar

El cliente original verifica el SHA-256 fijado del archivo descargado. Su
importación reconstruye índices y migra el esquema (Hydrater, db.go); por ello
el SHA-256 físico de SQLite después de importar no se compara entre máquinas.
Se verifica el estado con grype db status, el origen exacto y la versión de
cliente del import.json. Después se fija el SHA-256 local resultante en el
manifiesto. El runtime sigue recalculando ese SHA-256 y rechaza cambios posteriores.
El manifiesto conserva también el hash del archivo original descargado.

## Dos operaciones de preparación adicionales

MCP-Agent 0.2.6, con MCP 1.30.0, ejecuta una función de totales de campañas
registrada en su Agent, con servidores, modelos y telemetría desactivados.
NeMo Guardrails 0.24.1 compila pares de diálogo proporcionados, con etiquetas
generadas y texto entrecomillado, sin admitir código Colang/YAML del usuario.
No ejecuta conversaciones ni acredita protección contra ataques a prompts.

Estas dos operaciones ya se probaron con Engine antes de la interrupción local;
la nueva integración exige repetir la aceptación, persistencia y replay en CI
con perfiles separados. El estado actual es 20 operaciones en esta revisión y
68 pendientes; la evidencia local de 18 operaciones conserva su alcance histórico.
