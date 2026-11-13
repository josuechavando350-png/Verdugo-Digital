# Fuentes de los 50: código vinculado, no 50 instalaciones

Las 44 fuentes nuevas están vinculadas como submódulos Git en `components/`.
Los diez originales en `upstream/` se preservan con sus mismos SHAs. La selección
final usa seis originales y 44 nuevos; los otros cuatro originales permanecen
como compatibilidad. Por eso `.gitmodules` contiene 54 enlaces, pero el producto
seleccionado tiene exactamente 50 candidatos, no 54 componentes nuevos.

`stack/portfolio-pins.json` fija los 50 commits seleccionados. Para las 44 fuentes
nuevas se usaron los commits resueltos realmente por el job `source-identity` de
la ejecución GitHub Actions 43525660396, commit
`112d47f84df3431eb73a6c47f050f30760e8ece5`. El ZIP descargado de evidencia,
artefacto 14085465531, tiene SHA256
`07247ca208d817c9ab835aeef24a532aeab6be36cb99c90a7dc481a4364bd421`.
Se comprobó que los 50 IDs canónicos de repositorio fueran distintos. Los seis
SHAs anteriores conservados no se actualizan automáticamente a sus heads actuales.

Git puede obtener una fuente individual mediante `git submodule update --init
--depth 1 components/markitdown`, por ejemplo. Obtenerla no instala dependencias
ni inicia el servicio. No se descargan los 54 proyectos completos por defecto:
varios son grandes y tienen requisitos incompatibles con un teléfono convencional.

Las distribuciones Python instaladas para el flujo real se fijan por sus versiones
de paquete en `requirements-portfolio.txt`; no se afirma que esos paquetes sean
idénticos a los heads Git recién observados. Son dos identidades distintas que
se documentan por separado. La aceptación de ejecución está en el informe nativo,
no en el registro de submódulos.

Los módulos pendientes permanecen bloqueados. No hay activación de publicidad,
llamadas, cobros o nuevos servicios remotos. Licencias y condiciones comerciales
siguen pendientes de revisión por módulo. `all_fifty_integrated=false`.
