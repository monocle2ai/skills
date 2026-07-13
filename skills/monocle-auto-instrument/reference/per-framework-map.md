# Phase 5b — Where each framework's instrumentation lives

All paths under `monocle/apptrace/src/monocle_apptrace/instrumentation/metamodel/<fw>/`. A framework dir typically
has `methods.py` (the registry), `<fw>_processor.py` (span handlers), and `entities/` (output processors). When
fixing a gap, the symptom from Phase 4 tells you which of the three to edit:

- missing/extra **span** → `methods.py` (add/remove/fix a method entry)
- empty/wrong **input or output** → `entities/*.py` output processor (and sometimes the handler)
- wrong **naming / status / scope / nesting** → `<fw>_processor.py` span handler

## Packages each framework patches (verified against source)

| Framework | dir | packages.objects patched |
|---|---|---|
| LangGraph | `langgraph/` | `langgraph.graph.state.CompiledStateGraph.{invoke,ainvoke,astream,…}`; tools via `langchain_core.tools.{simple,structured}` |
| CrewAI | `crew_ai/` | `crewai.crew`, `crewai.agent`, `crewai.task`, `crewai.tools.base_tool`, `crewai.tools.structured_tool` |
| LlamaIndex | `llamaindex/` | `llama_index.core.agent*` (incl. `workflow.function_agent`, `workflow.multi_agent_workflow`), `llama_index.core.base.base_query_engine`, `llama_index.core.indices.base_retriever`, `llama_index.core.tools.function_tool`, `llama_index.llms.{openai,anthropic,gemini,mistralai}` |
| Haystack | `haystack/` | `haystack.core.pipeline.pipeline`, `haystack.components.generators.{openai,chat.openai}`, `haystack.components.retrievers.in_memory`, `haystack_integrations.components.{generators,retrievers}.*` |
| OpenAI Agents SDK | `agents/` | `agents.run`, `agents.tool` |
| MS Agent Framework | `msagent/` | `agent_framework._agents`, `._tools`, `._workflows.{_agent_executor,_function_executor,_workflow}` |
| OpenAI (provider) | `openai/` | `openai.resources.chat.completions`, `openai.resources.responses`, `openai.resources.embeddings` |
| Anthropic | `anthropic/` | `anthropic.*` |
| Gemini | `gemini/` | google-genai |
| LiteLLM | `litellm/` | `litellm` |
| Google ADK | `adk/` | — |
| Strands | `strands/` | — |
| Teams AI | `teamsai/` | — |
| MCP / FastMCP | `mcp/`, `fastmcp/` | MCP client/server |
| HTTP/infra | `flask/`, `fastapi/`, `requests/`, `aiohttp/`, `botocore/`, `azfunc/`, `lambdafunc/` | web/cloud transports |

Handler names are registered in `instrumentation/common/wrapper_method.py` `MONOCLE_SPAN_HANDLERS`
(e.g. `langgraph_agent_handler`, `langgraph_tool_handler`, `crew_ai_agent_handler`, `crew_ai_task_handler`,
`crew_ai_tool_handler`, `openai_handler`). The `methods.py` entry's `"span_handler"` string must match a key there.

## Adding a NEW framework (large change — usually decline per Phase 5)

Only if the user explicitly wants it and it's genuinely a small surface: create `metamodel/<fw>/methods.py`
(+ processor + entities), then register in `wrapper_method.py` (import `<FW>_METHODS`, add to
`DEFAULT_METHODS_LIST`, add handlers to `MONOCLE_SPAN_HANDLERS`). A from-scratch framework (e.g. AG2/AutoGen)
is NOT a small gap-fill — flag it as a redesign-scale contribution and stop unless told otherwise.
