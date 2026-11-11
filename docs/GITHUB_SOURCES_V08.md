# Nexus / Verdugo v0.8 — Evidencia de 100 fuentes GitHub

## Qué se incorporó

Se agregó un registro **bloqueado por SHA de commit** para los 100 proyectos aprobados
en verdugo/catalog.py. Los archivos sources/parts/01.json a sources/parts/10.json
contienen diez proyectos cada uno, su identificador, repositorio, SHA observado
mediante la API pública de GitHub, y el estado explícito de licencia
**pendiente de revisión**. La observación se realizó el 11 de noviembre de 2026.
No se descargó ni copió código de terceros a este repositorio.

La capa verdugo/source_evidence.py verifica **sin conexión de red** que existan
exactamente 100 fuentes, que sus nombres y orden coincidan con el catálogo
aprobado, que los SHA sean de 40 caracteres hexadecimales y que no haya
afirmaciones de licencia aprobada. Ante cualquier alteración, aborta.

## Comandos

~~~sh
python -m verdugo sources
python -m verdugo source-inspect twenty
python -m verdugo source-inspect restic
python -m unittest discover -s tests -v
~~~

verdugo_source_evidence ofrece la misma consulta **solo lectura** al cliente
MCP stdio ya existente. La salida enumera capacidades de interfaz realmente
implementadas en Verdugo, no capacidades asumidas del repositorio remoto.

## Niveles de preparación: no son equivalentes

| Nivel | Estado en esta entrega |
|---|---|
| Proyectos aprobados y catalogados | 100 |
| Referencias de fuente con commit SHA observado | 100 |
| Licencias revisadas/aprobadas para este uso | 0 |
| Adaptadores HTTP implementados en Verdugo | 22 |
| Proyectos sin adaptador HTTP | 78 |
| Proveedores externos validados en entorno real | 0 |
| Proveedores desplegados por esta entrega | 0 |

**Un repositorio bloqueado por SHA no es un servicio instalado, un adaptador
operativo ni una licencia de redistribución.** No se hace git clone, descarga
de dependencias, ejecución de scripts upstream, pagos, envíos ni despliegues.
Los repositorios incluyen bibliotecas, aplicaciones, SDK, herramientas de
seguridad y proyectos de infraestructura con requisitos incompatibles entre
sí. No se pueden tratar todos como APIs HTTP.

El SHA observado indica qué código fuente revisar posteriormente, pero no
certifica la integridad de cada paquete de publicación, la seguridad del
upstream ni el derecho a usarlo comercialmente. El campo license_review sigue
en pending hasta contar con revisión individual.

## Siguiente puerta de integración funcional

Para cada uno de los 78 proyectos sin adaptador hay que decidir si corresponde
un cliente HTTP, biblioteca local, tarea CLI, servicio desplegado o componente
de infraestructura; después comprobar versión/licencia, contrato, permisos,
costos, ejecución controlada, pruebas, observabilidad y compatibilidad con
el núcleo Verdugo. Para los 22 adaptadores HTTP ya escritos faltan credenciales,
instancias autorizadas y certificación por proveedor. La integración debe seguir
los controles de Engine, sin ejecutar comandos remotos arbitrarios ni
autoaprobar acciones externas.

Esta entrega añade **procedencia verificable para las 100 fuentes**, no
declaraciones falsas de integración productiva terminada.
