# Perfiles de dependencias v0.10

Ragas 0.4.3 y Haystack 3.5.0 no comparten un conjunto compatible de dependencias transitivas en la prueba inicial. No se utiliza --no-deps ni se fuerza una instalación inconsistente. El núcleo sigue siendo uno; Ragas ejecuta el mismo worker fijo en un segundo entorno virtual provisionado por el operador.

```sh
python3.12 -m venv --copies /ruta/privada/runtime
/ruta/privada/runtime/bin/python -m pip install -r requirements/runtime.txt
python3.12 -m venv --copies /ruta/privada/ragas
/ruta/privada/ragas/bin/python -m pip install -r requirements/runtime-ragas.txt
export VERDUGO_RAGAS_PYTHON=/ruta/privada/ragas/bin/python
/ruta/privada/runtime/bin/python -m verdugo runtime-check
```

La variable la configura el administrador del host, no un argumento CLI/MCP. Solo selecciona el intérprete de Ragas; no permite redirigir otros servicios ni ejecutar un comando arbitrario. Se exige un ejecutable absoluto con nombre Python y una configuración de venv local; no se instalan paquetes automáticamente. El operador debe proteger todo el entorno y confiar en sus dependencias: no es un sandbox contra un administrador malicioso.

El plan vincula la ruta, el binario, pyvenv.cfg y la implementación; las versiones requeridas se consultan con un proceso de metadatos acotado y se vuelven a comprobar antes de ejecutar. El worker conserva las validaciones, límites, filtrado de variables, auditoría e idempotencia existentes. Los datos JSON no eligen intérprete, módulos ni rutas.

La aceptación exige ejecutar las 19 recetas y los dos flujos compuestos con salida de red bloqueada por namespace. CI crea el namespace y devuelve la ejecución al usuario propietario sin privilegios; no debilita las comprobaciones de dueño/permisos para ejecutar como root. El reporte de pip y las versiones resueltas se publican como evidencia; no son una aprobación comercial de licencias ni certificación productiva.

## Restricciones de versiones

requirements/runtime.constraints.txt fija 277 distribuciones observadas en el entorno principal. requirements/runtime-ragas.constraints.txt fija las 98 del perfil Ragas. Son conjuntos separados; no se suman como 375 paquetes únicos. Su origen es la instalación y pip check aprobados del run 43147411273, artifact 13912117669. La aceptación funcional de ese run falló por la identidad root de CI; no se presenta como aprobación de los dos flujos. La corrección de identidad y la aceptación completa se comprueban en el run del nuevo commit.

Estas restricciones no verifican hashes al instalar y no son portables automáticamente a Android ni a otros Python/SO. Para reproducir resultados hay que conservar el entorno de aceptación y comprobar los tres workflows del commit. No aceptar que un inventario de metadatos se presente como evidencia de ejecución.
