# Verdugo Digital — Plan de los 666

Fecha: 15 de noviembre de 2026. Base: `main` después de la v0.21.1.

## Inventario

| Bloque | Piezas | Fuente | Estado hoy |
|---|---|---|---|
| Catálogo libre (cuerpo) | 300 | `sources/parts/*.json`, `sources/licenses.json` | 243 conectadas, 56 piezas de construcción, 1 pendiente (`meta-ads`) |
| Simulador de mercado (bola de cristal) | 50 | `sources/simulador-mercado.json` | registrado; adaptador pendiente |
| Cerebro (piloto) | 150 | `sources/cerebro-150.json` | registrado; adaptador pendiente |
| Últimas 166 | 166 | `sources/final-166.json` | registrado; adaptador pendiente |
| **Total libre** | **666** | | |

Los 22 excluidos por licencia siguen registrados, pero no cuentan ni se operan.

## Avance comprobado de esta continuación

- **Tanda 0: terminada y aceptada en CI.** 688 identidades GitHub distintas, 666 permitidas por política y 22 excluidas. Se conservan 69 partes: 68 de diez y una de ocho.
- Cinco propuestas eran alias de proyectos ya registrados (Ragas, Presidio, FastMCP, Recommenders y Great Expectations). TEN Framework tiene restricciones adicionales: no se contó como Apache libre. Las seis sustituciones y su alcance constan en [REGISTRO_666.md](REGISTRO_666.md).
- **Estado actual: 253 conectadas; 56 de construcción; 357 pendientes; certificadas en producción: 0.** Semantic Kernel, Agno, AG2, Langroid, Griptape, BeeAI, Strands/Harness SDK, VoltAgent, Unified Planning y OpenManus añaden diez operaciones locales limitadas; registrar las otras piezas no añade adaptadores.
- **Lote 1 (183): 10 operaciones implementadas y probadas conjuntamente; aceptación CI de este incremento pendiente. Lote 2 (183): 0 implementadas. Ninguno de los dos lotes está terminado.** Orden completo, sin duplicados, en `sources/registry-666.json/work_queue`.
- Registro aceptado en `b95f8be09e2a34ff12f163b6f872287eed3afd26`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43690692125), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43690692198) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43690692157), los tres `success`. PR #24 permanece sin fusionar.
- El primer checkpoint del piloto (`77670600a4ee083413f5838b1e36991ddbff2347`) pasó [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43692332291), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43692332306) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43692332315). Esa evidencia cubre Semantic Kernel; no certifica cambios posteriores.
- El checkpoint ejecutivo `e914b2622e430ee72121fefc1e256e0adabc126d` pasó [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43693358786), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43693358773) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43693358774), cubriendo tres SDK. El checkpoint posterior de Langroid también está aceptado.
- Checkpoint de cuatro SDK `5f864e01916af4fc5aaeda0ed81562b53f0bdcab`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43694523478), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43694523526) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43694523516), los tres `success`. Griptape y BeeAI pasan la aceptación local conjunta y las 761 pruebas; su CI se comprueba en el siguiente commit.
- Checkpoint de seis SDK `4da9ac282fbb8ecc46142586379ff7636151f1dc`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43695503872), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43695503842) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43695503909), los tres `success`. Los nueve SDK pasan la aceptación local conjunta y 766 pruebas unitarias; su CI debe observarse en el siguiente commit.
- Checkpoint de nueve SDK `1e12900b5c275345d5c27d6adda448c80896232d`: [verificación](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43697622379), [runtime](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43697622401) y [servicios](https://github.com/josuechavando350-png/Verdugo-Digital/actions/runs/43697622377), los tres `success`. La aceptación del piloto pasó con aislamiento de red del sistema operativo. OpenManus se valida en el siguiente checkpoint.
- **DeerFlow y Open Deep Research permanecen pendientes:** sus instalaciones revisadas incluyen dependencias obligatorias Elastic-2.0 y AGPL/comercial, respectivamente. Evidencia original y límites de esta conclusión en `sources/contracts-executive-blockers666.json`.
- **MetaGPT permanece pendiente:** instalación original bajo Python 3.11 bloqueada por `lancedb==0.4.0`, ausente en la lista de versiones de PyPI consultada el 15 de noviembre. No se ignoraron dependencias ni se declaró conectado.
- **Fase 1: parcial.** El esqueleto sintético recorre plan → aprobación → simulación → medición por CLI/MCP y SQLite. Falta el modelo local, las otras 40 piezas de la fase y calibración real. [Detalle del piloto](PILOTO_666.md).
- `meta-ads` sigue pendiente. No se instalaron modelos, lanzaron campañas ni desplegaron proveedores por este registro.

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

El plan original dividía el trabajo en tandas de hasta 50. La organización vigente usa dos lotes de 183, con pruebas, los tres workflows observados en verde y PR encadenados. Las fases funcionales originales se conservan abajo. Por instrucción del dueño del 15 de noviembre, la ejecución se agrupa en **dos lotes de 183**, en el orden explícito de `sources/registry-666.json/work_queue`. El registro (tanda 0) sigue siendo previo.

| Tanda | Qué | Piezas | Criterio de terminado |
|---|---|---|---|
| 0 | Registro unificado: llevar el catálogo de 322 a 688 registros (666 libres + 22 excluidos) con commits fijados, política de licencias y mapa de conexión. Regla actualizada a 69 archivos y 688 entradas en AGENTS.md. Sin adaptadores todavía. | 0 nuevas operaciones | `licenses` y `connections` reportan 688/666; pruebas actualizadas |
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
