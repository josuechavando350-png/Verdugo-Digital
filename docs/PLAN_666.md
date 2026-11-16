# Verdugo Digital — Plan de los 666

> **ARCHIVADO (15 nov 2026, decisión del dueño):** Verdugo Digital se queda en **300 piezas libres**. Este catálogo de ampliación no se integra. Se conserva solo como referencia; no es una cola de trabajo. Los PR #24 y #25 quedaron cerrados sin fusionar.

Fecha: 15 de noviembre de 2026. Base: `main` después de la v0.21.1.

## Inventario

| Bloque | Piezas | Fuente | Estado hoy |
|---|---|---|---|
| Catálogo libre (cuerpo) | 300 | `sources/parts/*.json`, `sources/licenses.json` | 243 conectadas, 56 piezas de construcción, 1 pendiente (`meta-ads`) |
| Simulador de mercado (bola de cristal) | 50 | `sources/simulador-mercado.json` | propuesto |
| Cerebro (piloto) | 150 | `sources/cerebro-150.json` | propuesto |
| Últimas 166 | 166 | `sources/final-166.json` | propuesto |
| **Total libre** | **666** | | |

Los 22 excluidos por licencia siguen registrados, pero no cuentan ni se operan.

## Qué es el producto terminado

Un solo sistema que recibe un objetivo de negocio ("20 clientes este mes para este despacho, presupuesto X") y:

1. **Planea**: corteza ejecutiva y razonamiento (cerebro: `ejecutivo`, `razonamiento`, `logica`).
2. **Predice**: simula la estrategia con clientes virtuales calibrados y pronostica demanda (simulador, más `pronostico`, `quien_compra`, `decision`, `prediccion`).
3. **Pide aprobación**: cada acción con costo o efecto externo se muestra en una línea y espera la aprobación del operador (`conciencia`, `juicio`, `cabina`).
4. **Ejecuta**: usa el cuerpo (300), `contenido`, `ventas_voz`, `embudo` y `seo_crecimiento`.
5. **Mide y aprende**: compara lo predicho con lo real, recalibra el simulador y mejora el piloto (`aprendizaje`, `datos_limpios`, `memoria`).
6. **Sigue prendido**: `siempre_prendido` (despliegue, monitoreo, respaldos).

## Reglas que no cambian (AGENTS.md manda)

- Nada de pago. Ningún proveedor de pago, ni como opción por defecto.
- No escribir `license_policy_exception` en nombre del dueño.
- Licencia leída del archivo LICENSE en el commit fijado. En `libre_nucleo` no se usa la parte enterprise, Pro o ee.
- **Pesos de modelos**: antes de descargar cualquier modelo, leer la licencia de los pesos. El código puede ser MIT y los pesos no comerciales. Si los pesos no son libres, la pieza solo se usa con otro modelo libre.
- Contratos tomados del código original en el commit fijado. Si el código no respalda la ruta, la pieza queda pendiente (como `meta-ads`).
- Nada se marca conectado ni verificado sin evidencia. `live_verified` solo con una prueba real contra un servicio real.
- **Acciones con efecto** (publicar, enviar, gastar, crear campañas): siempre detrás de una aprobación explícita del operador, con idempotencia, registro en SQLite y reversión cuando exista. Primero en modo simulación (dry-run). Programar el repo no autoriza a iniciar campañas, enviar comunicaciones a terceros ni contratar hosting.
- Nada de datos privados persistidos; se proyectan solo recuentos.
- Sin raspado que viole términos de servicio, sin suplantar navegadores y sin APIs no oficiales.
- Nada de Cano ni de Vercel. El repo es público: sin secretos ni nombres de clientes.

## Orden de construcción

Cada tanda es de **50 piezas por sesión** y termina con las pruebas, los tres workflows en verde y un PR encadenado. Las 366 piezas nuevas (50 + 150 + 166) más la pendiente suman 8 tandas.

| Tanda | Qué | Piezas | Criterio de terminado |
|---|---|---|---|
| 0 | Registro unificado: llevar el catálogo de 322 a 688 registros (666 libres + 22 excluidos) con commits fijados, política de licencias y mapa de conexión. Actualizar en AGENTS.md la regla de `sources/parts/` (hoy 33 archivos y 322 entradas) a la nueva cuenta. Sin adaptadores todavía. | 0 nuevas operaciones | `licenses` y `connections` reportan 688/666; pruebas actualizadas |
| 1 | Esqueleto del piloto: objetivo → plan → aprobación → ejecución simulada → medición, con `ejecutivo`, `manos`, `juicio` y `conciencia`. Modelo local con `pensamiento`. | 50 | Un objetivo de prueba produce un plan, pide aprobación, corre en dry-run y queda en SQLite con replay |
| 2 | Memoria y lógica: `memoria` y `logica`. El piloto recuerda clientes y campañas, y comprueba sus afirmaciones antes de reportarlas. | 50 | Consultas sobre datos sintéticos; afirmaciones verificadas o rechazadas |
| 3 | Núcleo del simulador: población sintética, clientes virtuales y calibración (los 50 del simulador). | 50 | Simula una oferta sintética y reporta incertidumbre, no un número único |
| 4 | Bola de cristal: `pronostico`, `quien_compra`, `decision` y `prediccion`. | 50 | Pronósticos con intervalos y evaluación retrospectiva sobre datos sintéticos |
| 5 | Auto-mejora y juicio: `aprendizaje`, `datos_limpios`, `explicar` y el resto de `juicio`. | 50 | El piloto se califica, explica cada decisión y registra qué aprendió |
| 6 | Ejecución: `contenido`, `ventas_voz`, `embudo` y `seo_crecimiento`. Todo con aprobación y dry-run por defecto. | 50 | Cada acción con efecto exige aprobación; sin aprobación no sale nada |
| 7 | Operación y cabina: `siempre_prendido`, `cabina`, `tableros` y el resto. Resolver `meta-ads` solo si aparece una fuente original que lo respalde. | 16 + restantes | Instalación reproducible en un servidor Linux y cabina usable desde el teléfono |

## Lo que decide el dueño, no Astra

- **El servidor** donde corre todo, 24/7. Sin servidor no hay producto prendido.
- **Qué acciones pueden ir sin aprobación**, si alguna. Por defecto: ninguna.
- **El primer cliente real** para calibrar el simulador.
