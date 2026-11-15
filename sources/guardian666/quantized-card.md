---
pipeline_tag: text-generation
license: apache-2.0
library_name: transformers
tags:
- granite-3.2
- guardian
- gguf
base_model:
- ibm-granite/granite-guardian-3.2-3b-a800m
---

> [!NOTE]
> This repository contains models that have been converted to the GGUF format with various quantizations from an IBM Granite base model.
>
> Please reference the base model's full model card here:
> https://huggingface.co/ibm-granite/granite-guardian-3.2-3b-a800m



# granite-guardian-3.2-3b-a800m-GGUF 

## Model Summary

**Granite Guardian 3.2 3B-A800M** is a fine-tuned Granite 3.2 3B-A800M instruct model designed to detect risks in prompts and responses.
It can help with risk detection along many key dimensions catalogued in the [IBM AI Risk Atlas](https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas).
It is trained on unique data comprising human annotations and synthetic data informed by internal red-teaming.
It outperforms other open-source models in the same space on standard benchmarks.

- **Developers:** IBM Research
- **GitHub Repository:** [ibm-granite/granite-guardian](https://github.com/ibm-granite/granite-guardian)
- **Cookbook:** [Granite Guardian Recipes](https://github.com/ibm-granite/granite-guardian/tree/main/cookbooks/granite-guardian-3.2)
- **Website**: [Granite Guardian Docs](https://www.ibm.com/granite/docs/models/guardian/)
- **Paper:** [Granite Guardian](https://arxiv.org/abs/2412.07724)
- **Release Date**: February 26, 2025
- **License:** [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)


## Usage
### Intended use

Granite Guardian is useful for risk detection use-cases which are applicable across a wide-range of enterprise applications -
- Detecting harm-related risks within prompt text, model responses, or conversations (as guardrails). These present fundamentally different use cases as the first assesses user supplied text, the second evaluates model generated text, and the third evaluates the last turn of a conversation.
- RAG (retrieval-augmented generation) use-case where the guardian model assesses three key issues: context relevance (whether the retrieved context is relevant to the query), groundedness (whether the response is accurate and faithful to the provided context), and answer relevance (whether the response directly addresses the user's query).
- Function calling risk detection within agentic workflows, where Granite Guardian evaluates intermediate steps for syntactic and semantic hallucinations. This includes assessing the validity of function calls and detecting fabricated information, particularly during query translation.