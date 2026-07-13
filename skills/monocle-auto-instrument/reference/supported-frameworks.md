# Phase 0 — Supported frameworks & detection

Monocle auto-instruments a framework only if it ships a **metamodel** for it (a `methods.py` registry of
package/object/method wrappers). If there's no metamodel, agentic spans won't be produced — gate out.

## How to detect

Read the dependency manifest first (`pyproject.toml`, `requirements*.txt`, `poetry.lock`, `uv.lock`), then
confirm with imports in the source. Match the **pip package** below; the **import package** is what Monocle
actually patches (useful in later phases).

## Fully supported (dedicated agentic metamodel)

| Framework | pip package(s) | key import package Monocle patches |
|---|---|---|
| LangChain | `langchain`, `langchain-core` | `langchain_core.language_models`, `langchain_core.tools` |
| LangGraph | `langgraph` | `langgraph.graph.state`, `langchain_core.tools.{simple,structured}` |
| LlamaIndex | `llama-index*` | `llama_index.core.agent*`, `llama_index.core.base.base_query_engine`, `llama_index.llms.*` |
| Haystack | `haystack-ai` | `haystack.core.pipeline.pipeline`, `haystack.components.generators.*` |
| CrewAI | `crewai` | `crewai.{crew,agent,task}`, `crewai.tools.{base_tool,structured_tool}` |
| OpenAI Agents SDK | `openai-agents` | `agents.run`, `agents.tool` |
| MS Agent Framework | `agent-framework` | `agent_framework._agents`, `._tools`, `._workflows.*` |
| Google ADK | `google-adk` | (see `metamodel/adk`) |
| Strands | `strands-agents` | (see `metamodel/strands`) |
| Microsoft Teams AI | `teams-ai` | (see `metamodel/teamsai`) |

## LLM/provider & infra (inference + I/O spans, no agentic orchestration of their own)

OpenAI (`openai`), Anthropic (`anthropic`), Gemini (`google-genai`), Mistral (`mistralai`),
Azure AI Inference, LiteLLM (`litellm`), HuggingFace, Bedrock/AgentCore (`botocore`), Flask, FastAPI,
Requests, aiohttp, MCP / FastMCP, A2A, Azure Functions, AWS Lambda.

## Partially supported / NOT a dedicated metamodel — call it out

- **AG2 / AutoGen** (`ag2`, `autogen`, `pyautogen`): **no `autogen` metamodel exists.** You'll still get
  `inference.*` spans from its underlying OpenAI/Anthropic calls, but **no `agentic.turn`/`agentic.invocation`/
  tool spans**. Tell the user this is inference-only and let them decide whether to continue. (A dedicated
  metamodel would be a Phase-5 contribution, but that's a from-scratch add, not a small gap-fill.)

## Ground truth

The authoritative list is `DEFAULT_METHODS_LIST` in
`monocle/apptrace/src/monocle_apptrace/instrumentation/common/wrapper_method.py`, and the metamodel dirs under
`monocle/apptrace/src/monocle_apptrace/instrumentation/metamodel/`. If unsure whether something is supported,
read those — don't guess. (See `monocle-source-locations` memory for the exact path on this machine.)
