# Verdugo Digital v0.6.2 — ciclo de vida SQLite en Termux

## Qué se corrigió

En la prueba de respaldos de v0.6.1 se utilizaba `with sqlite3.connect(path) as db` para consultar snapshots. El context manager de SQLite confirma o revierte la transacción, **pero no cierra la conexión**. Python 3.14 en Termux informa de `ResourceWarning: unclosed database`. Las lecturas de prueba ahora utilizan `contextlib.closing(sqlite3.connect(...))` y se comprueba el cierre explícito.

El constructor de `Engine` también protege toda su inicialización de SQLite (PRAGMAs y esquemas), cerrando la conexión si ocurre una excepción después de `sqlite3.connect`. Antes protegía únicamente la creación de la guardia local.

## Validación

Se ejecuta la suite completa con advertencias de `sqlite3.Connection` inspeccionadas, y una segunda ronda que simula `umask=077` y ausencia de `os.link`. GitHub Actions incluye un job adicional con Python 3.14. Una prueba nueva fuerza error de esquema y comprueba que la conexión quedó cerrada.

Esta corrección **no cambia el esquema**, no introduce servicios externos, no elimina datos ni permite reintentos de escrituras inciertas. Se mantiene el control de recuperaciones v0.4.1 y el respaldo v0.6.1. No resuelve la falta de proveedores reales ni valida ventas.

## Comandos de actualización en Termux

```sh
cd ~/Verdugo-Digital
git pull --ff-only origin feat/verdugo-unified-core
python -m unittest discover -s tests -q
python -m verdugo demo
```

Resultado previsto: `OK (skipped=1)` si el entorno no implementa hard links. Una advertencia de SQLite, un error o una prueba fallida es un bloqueo para utilizar datos reales; no debe ignorarse.

No compartir la base `.state/`, contactos, tokens ni snapshots privados por este chat o por GitHub.
