# Perfiles de dependencias v0.10

Ragas 0.4.3 y Haystack 3.5.0 no comparten un conjunto compatible de dependencias transitivas en la prueba inicial. No se utiliza --no-deps ni se fuerza una instalación inconsistente. El núcleo sigue siendo uno; Ragas ejecuta el mismo worker fijo en un segundo entorno virtual provisionado por el operador.

```sh
python3.12 -m venv /ruta/privada/runtime
/ruta/privada/runtime/bin/python -m pip install -r requirements/runtime.txt
python3.12 -m venv /ruta/privada/ragas
/ruta/privada/ragas/bin/python -m pip install -r requirements/runtime-ragas.txt
export VERDUGO_RAGAS_PYTHON=/ruta/privada/ragas/bin/python
/ruta/privada/runtime/bin/python -m verdugo runtime-check
```

La variable la configura el administrador del host, no un argumento CLI/MCP. Solo selecciona el intérprete de Ragas; no permite redirigir otros servicios ni ejecutar un comando arbitrario. Se exige un ejecutable absoluto con nombre Python y una configuración de venv local; no se instalan paquetes automáticamente. El operador debe proteger todo el entorno y confiar en sus dependencias: no es un sandbox contra un administrador malicioso.

El plan vincula la ruta, el binario, pyvenv.cfg y la implementación; las versiones requeridas se consultan con un proceso de metadatos acotado y se vuelven a comprobar antes de ejecutar. El worker conserva las validaciones, límites, filtrado de variables, auditoría e idempotencia existentes. Los datos JSON no eligen intérprete, módulos ni rutas.

La aceptación exige ejecutar las 19 recetas y los dos flujos compuestos con salida de red bloqueada por namespace. El reporte de pip y las versiones resueltas se publican como evidencia; no son una aprobación comercial de licencias ni certificación productiva.
