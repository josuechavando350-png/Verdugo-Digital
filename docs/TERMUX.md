# Termux / Android — compatibilidad de respaldos

La v0.6 inicial suponía que Python exponía `os.link` (hard links); Termux puede omitir esa función. También había dos pruebas que asumían que `mkdir(mode=0o755)` no estaría modificado por `umask=077`. Las dos suposiciones fueron corregidas.

El respaldo conserva la publicación atómica mediante hard link en Linux cuando existe. Si no está disponible, reserva el destino con `O_CREAT | O_EXCL`, copia desde un snapshot SQLite consistente, sincroniza (`fsync`) y vuelve a verificar la copia y SHA-256. **En ese modo, un cierre abrupto durante la copia puede dejar un archivo incompleto visible; es obligatorio ejecutar `verify-backup` antes de utilizarlo**. Una excepción normal intenta borrar el archivo incompleto. No es un mecanismo automático de recuperación.

La prueba de rechazo de hard links se salta con explicación cuando Python/el filesystem no permiten crear uno; las demás comprobaciones de seguridad siguen activas. Los directorios inseguros usados como fixtures se cambian explícitamente a 0755 para que `umask` no invalide la prueba.

## Actualizar desde Termux

No hay que borrar el repositorio ni la base de datos. Desde la carpeta existente del proyecto:

```sh
cd ~/Verdugo-Digital
git pull --ff-only origin feat/verdugo-unified-core
python -m unittest discover -s tests -q
python -m verdugo demo
```

Si ejecutas workers u otros procesos de Verdugo, detenlos y respalda su estado antes de actualizar la versión. No borres ni reinicies claves de operaciones inciertas. Para un proyecto sin datos reales ni workers, las pruebas locales son seguras.

Este parche no instala los 100 productos externos ni conecta APIs reales. No usar respaldos sin cifrar en almacenamiento compartido o en GitHub.
