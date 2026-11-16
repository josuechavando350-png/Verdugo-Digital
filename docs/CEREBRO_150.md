# El cerebro de Verdugo — 150 repos propuestos

> **ARCHIVADO (15 nov 2026, decisión del dueño):** Verdugo Digital se queda en **300 piezas libres**. Este catálogo de ampliación no se integra. Se conserva solo como referencia; no es una cola de trabajo. Los PR #24 y #25 quedaron cerrados sin fusionar.

Catálogo propuesto para construir el piloto: el sistema que recibe un objetivo, planea, simula, pide aprobación, ejecuta, mide y aprende. No modifica los 322 del catálogo, los 50 del simulador ni el motor. Cada licencia se leyó del archivo LICENSE en el commit fijado en `sources/cerebro-150.json`. Ninguno exige un servicio de pago; los modelos corren en local.

Ya estaban en Verdugo y no se repiten: LangGraph, LangChain, LlamaIndex, CrewAI, Letta, Mem0, Graphiti, Cognee, GraphRAG, DSPy, Outlines, Instructor, Transformers, vLLM, Ollama, Qdrant, Docling, MLflow, Evidently, Guardrails, LLM Guard, NeMo Guardrails, Promptfoo, Langfuse, Ax, OR-Tools, Vowpal Wabbit, Chronos, MAPIE, SHAP, MCP Python/TypeScript SDK, Browser Use, OpenAI Agents, Google ADK, Pydantic AI, smolagents, Haystack, GPT Researcher, STORM, Magentic-UI, Mastra.

## Corteza ejecutiva: planea, reparte y coordina (14)

- `microsoft/semantic-kernel` — MIT
- `agno-agi/agno` — Apache-2.0
- `ag2ai/ag2` — Apache-2.0
- `FoundationAgents/MetaGPT` — MIT
- `langroid/langroid` — MIT
- `griptape-ai/griptape` — Apache-2.0
- `i-am-bee/beeai-framework` — Apache-2.0
- `strands-agents/sdk-python` — Apache-2.0
- `VoltAgent/voltagent` — MIT
- `aiplan4eu/unified-planning` — Apache-2.0
- `FoundationAgents/OpenManus` — MIT
- `bytedance/deer-flow` — MIT
- `langchain-ai/open_deep_research` — MIT
- `BerriAI/litellm` — MIT · libre_nucleo: No usar litellm/enterprise (licencia comercial aparte).

## Razonamiento profundo: pensar antes de actuar y corregirse (13)

- `princeton-nlp/tree-of-thought-llm` — MIT
- `lapisrocks/LanguageAgentTreeSearch` — MIT
- `noahshinn/reflexion` — MIT
- `spcl/graph-of-thoughts` — BSD-3-Clause
- `maitrix-org/llm-reasoners` — Apache-2.0
- `openreasoner/openr` — MIT
- `zou-group/textgrad` — MIT
- `microsoft/Trace` — MIT
- `SylphAI-Inc/AdalFlow` — MIT
- `codelion/openevolve` — Apache-2.0
- `microsoft/PromptWizard` — MIT
- `EvoAgentX/EvoAgentX` — MIT
- `google-deepmind/mctx` — Apache-2.0

## Lógica formal y verdad: demostrar, no adivinar (13)

- `Z3Prover/z3` — MIT
- `potassco/clingo` — MIT
- `SWI-Prolog/swipl-devel` — BSD-2-Clause
- `scallop-lang/scallop` — MIT
- `ML-KULeuven/problog` — Apache-2.0
- `lab-v2/pyreason` — BSD-2-Clause
- `leanprover/lean4` — Apache-2.0
- `lean-dojo/LeanDojo` — MIT
- `egraphs-good/egg` — MIT
- `sympy/sympy` — BSD-3-Clause
- `RDFLib/rdflib` — BSD-3-Clause
- `apache/jena` — Apache-2.0
- `oxigraph/oxigraph` — Apache-2.0+MIT

## Memoria y conocimiento: recordar todo y conectarlo (25)

- `MemTensor/MemOS` — Apache-2.0
- `BAI-LAB/MemoryOS` — Apache-2.0
- `HKUDS/LightRAG` — MIT
- `gusye1234/nano-graphrag` — MIT
- `circlemind-ai/fast-graphrag` — MIT
- `HKUDS/RAG-Anything` — MIT
- `OpenSPG/KAG` — Apache-2.0
- `neo4j-labs/llm-graph-builder` — Apache-2.0
- `microsoft/kernel-memory` — MIT
- `chroma-core/chroma` — Apache-2.0
- `milvus-io/milvus` — Apache-2.0
- `lancedb/lancedb` — Apache-2.0
- `facebookresearch/faiss` — MIT
- `unum-cloud/usearch` — Apache-2.0
- `neuml/txtai` — Apache-2.0
- `infiniflow/ragflow` — Apache-2.0
- `FlagOpen/FlagEmbedding` — MIT
- `michaelfeil/infinity` — MIT
- `stanford-futuredata/ColBERT` — MIT
- `AnswerDotAI/RAGatouille` — Apache-2.0
- `AnswerDotAI/rerankers` — Apache-2.0
- `xhluca/bm25s` — MIT
- `quickwit-oss/tantivy` — MIT
- `Unstructured-IO/unstructured` — Apache-2.0
- `Qiskit/rustworkx` — Apache-2.0

## Decisión bajo incertidumbre: elegir la mejor jugada con datos incompletos (16)

- `pytorch/botorch` — MIT
- `cornellius-gp/gpytorch` — MIT
- `EmuKit/emukit` — Apache-2.0
- `google/vizier` — Apache-2.0
- `facebookresearch/nevergrad` — MIT
- `anyoptimization/pymoo` — Apache-2.0
- `automl/SMAC3` — BSD-3-Clause
- `hyperopt/hyperopt` — BSD-3-Clause
- `coin-or/pulp` — MIT
- `Pyomo/pyomo` — BSD-3-Clause
- `cvxpy/cvxpy` — Apache-2.0
- `ERGO-Code/HiGHS` — MIT
- `TimefoldAI/timefold-solver` — Apache-2.0 · libre_nucleo: No usar la edición enterprise; solo el núcleo Apache-2.0.
- `google-deepmind/open_spiel` — Apache-2.0
- `pgmpy/pgmpy` — MIT
- `pyro-ppl/pyro` — Apache-2.0

## Predicción y causa: ver venir y saber por qué (9)

- `google-research/timesfm` — Apache-2.0
- `SalesforceAIResearch/uni2ts` — Apache-2.0
- `unit8co/darts` — Apache-2.0
- `sktime/sktime` — BSD-3-Clause
- `autogluon/autogluon` — Apache-2.0
- `henrikbostrom/crepes` — BSD-3-Clause
- `IINemo/lm-polygraph` — MIT
- `huawei-noah/trustworthyAI` — Apache-2.0
- `FenTechSolutions/CausalDiscoveryToolbox` — MIT

## Auto-mejora: aprender de cada campaña (18)

- `huggingface/trl` — Apache-2.0
- `huggingface/peft` — Apache-2.0
- `axolotl-ai-cloud/axolotl` — Apache-2.0
- `OpenRLHF/OpenRLHF` — Apache-2.0
- `volcengine/verl` — Apache-2.0
- `hiyouga/LLaMA-Factory` — Apache-2.0
- `huggingface/open-r1` — Apache-2.0
- `Jiayi-Pan/TinyZero` — Apache-2.0
- `PRIME-RL/PRIME` — Apache-2.0
- `NovaSky-AI/SkyThought` — Apache-2.0
- `PrimeIntellect-ai/prime-rl` — Apache-2.0
- `rllm-org/rllm` — Apache-2.0
- `microsoft/agent-lightning` — MIT
- `HumanCompatibleAI/imitation` — MIT
- `DLR-RM/stable-baselines3` — MIT
- `Farama-Foundation/Gymnasium` — MIT
- `thu-ml/tianshou` — MIT
- `pytorch/rl` — MIT

## Juicio y autoevaluación: calificar su propio trabajo (14)

- `EleutherAI/lm-evaluation-harness` — MIT
- `confident-ai/deepeval` — Apache-2.0
- `explodinggradients/ragas` — Apache-2.0
- `truera/trulens` — MIT
- `UKGovernmentBEIS/inspect_ai` — MIT
- `comet-ml/opik` — Apache-2.0
- `Giskard-AI/giskard` — Apache-2.0
- `stanford-crfm/helm` — Apache-2.0
- `huggingface/lighteval` — MIT
- `langchain-ai/openevals` — MIT
- `lmarena/arena-hard-auto` — Apache-2.0
- `THUDM/AgentBench` — Apache-2.0
- `sierra-research/tau-bench` — MIT
- `openlit/openlit` — Apache-2.0

## Conciencia y frenos: ética, seguridad y explicar sus decisiones (8)

- `microsoft/presidio` — MIT
- `invariantlabs-ai/invariant` — Apache-2.0
- `NVIDIA/garak` — Apache-2.0
- `Azure/PyRIT` — MIT
- `ibm-granite/granite-guardian` — Apache-2.0
- `hendrycks/ethics` — MIT
- `interpretml/interpret` — MIT
- `TransformerLensOrg/TransformerLens` — MIT

## Motor de pensamiento: correr modelos propios, gratis y rápido (12)

- `ggml-org/llama.cpp` — MIT
- `sgl-project/sglang` — Apache-2.0
- `mlc-ai/mlc-llm` — Apache-2.0
- `huggingface/candle` — Apache-2.0+MIT
- `LMCache/LMCache` — Apache-2.0
- `huggingface/tokenizers` — Apache-2.0
- `vllm-project/llm-compressor` — Apache-2.0
- `bitsandbytes-foundation/bitsandbytes` — MIT
- `mlc-ai/xgrammar` — Apache-2.0
- `guidance-ai/guidance` — MIT
- `noamgat/lm-format-enforcer` — MIT
- `BoundaryML/baml` — Apache-2.0

## Manos: usar herramientas y no perder el hilo (8)

- `modelcontextprotocol/servers` — Apache-2.0
- `jlowin/fastmcp` — Apache-2.0
- `microsoft/playwright-python` — Apache-2.0
- `dbos-inc/dbos-transact-py` — MIT
- `PrefectHQ/prefect` — Apache-2.0
- `hatchet-dev/hatchet` — MIT
- `inngest/agent-kit` — Apache-2.0
- `ShishirPatil/gorilla` — Apache-2.0

## Descartados en la revisión

- Licencia no libre o mixta: Unsloth (AGPL), PurpleLlama (Llama Community License), AI Scientist (licencia propia con restricciones), Weaviate (parte bajo Weaviate License), ART (incluye textos GPL/LGPL).
- Dependen de un servicio externo de pago o freemium: Composio, Weave, OpenAI Evals.
- Sin licencia: llm-pddl, HEBO, llm_multiagent_debate. Licencia no identificada: OWL.
- Abandonados, archivados o redundantes: Kùzu, TGI, Open Bandit Pipeline, MABWiser, Vigil, Safe-RLHF, ToolBench, BitNet, Dynamo, Swarms, Axelrod, AutoGen (en mantenimiento; su sucesor AG2 sí entra).
