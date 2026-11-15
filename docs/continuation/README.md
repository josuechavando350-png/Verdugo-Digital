# Continuación después de la interrupción del entorno (2026-11-15)

Base publicada: PR #20, rama feat/v0.21-final88, commit 3e1a9415739d251e6e2eab1ec669d5daa208606b.
Este checkpoint conserva trabajo incompleto; NO registra nuevas operaciones ni modifica los conteos.

## Estado confirmado
- 18 nuevas operaciones publicadas; 70 pendientes; 660 pruebas locales.
- Flujo de 18 operaciones + instantánea comercial: 19 pasos, 156.402 s, SQLite, reinicio, replay sin workers y sin secret_text persistido.
- La primera revisión de CI falló al borrar módulos Go de solo lectura. El commit citado añade go clean -modcache con GOTOOLCHAIN=local antes de borrar la carpeta temporal.
- Verificar los tres workflows del commit citado; no asumir resultados pendientes.

## Trabajo posterior probado localmente pero no integrado en esta rama
- MCP-Agent 0.2.6 con mcp==1.30.0, perfil VERDUGO_MCPAGENT021_PYTHON. mcp 2.x rompe FastMCP.
- La operación campaigns.tool ejecutó Agent.call_tool con una función local fija y MCPApp: resultado {spend_minor:50,revenue_minor:200,leads:4,conversions:2}; sin servidores, modelos, telemetría u OTEL.
- NeMo Guardrails 0.24.1, perfil VERDUGO_RAILS021_PYTHON: RailsConfig.from_content compiló un par request/response, 1 flujo, 1 intención, 1 respuesta, 0 modelos. No ejecuta diálogos ni certifica seguridad.
- Ambos pasaron aceptación a través de Engine y replay: 8.856 s. pip check pasó en ambos perfiles.
- STORM knowledge-storm==1.1.1: código de citations.audit preparado, NO verificado. Dos intentos de pip fueron terminados con SIGKILL durante instalación/resolución. Se inició uv con torch==2.15.0+cpu; no se observó su resultado.
- El entorno se volvió unavailable; exec-server no pudo recuperarse. No se afirmó finalización ni validación de STORM.
- Se conserva el módulo candidato en planning_candidate.py.txt, fuera del runtime.

## Integración necesaria al recuperar un entorno
1. Reproducir los dos perfiles y fijar freeze/constraints. Resolver e inspeccionar STORM sin paquetes CUDA innecesarios.
2. Copiar el candidato a verdugo/local_planning.py; añadir SPECS/EXTRA/validate/run, archivo al fingerprint, y PROFILES en runtime_profile.
3. Añadir fixtures, pruebas de límites/inyección y aceptación original. Actualizar conteos SOLO si las tres pasan.
4. Ampliar install_final/accept_final, product conjunto y fuentes por commit; ejecutar CI.
5. Continuar las restantes. No llamar terminada la segunda tanda por publicar un checkpoint.

## Fuentes oficiales inspeccionadas
- lastmile-ai/mcp-agent f62d849350816588b1c6294e7914bbe4d8b84072: pyproject.toml, src/mcp_agent/agents/agent.py, app.py, config.py, core/context.py.
- NVIDIA-NeMo/Guardrails 5d7f4c1ca62fb6155066e6c581379d1a5ec11338: pyproject.toml, nemoguardrails/rails/llm/config.py.
- stanford-oval/storm fb951af7744dab086e34962e9bc6fe878e145f83: setup.py, knowledge_storm/utils.py.
- A2A 4d7cda4b1754ed410e41bf3be7ad9ebc62afe3d3: specification/a2a.proto inspeccionado; NO implementado.
