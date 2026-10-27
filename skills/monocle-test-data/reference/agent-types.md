# Agent types: what to build, and how the data reaches the tools

Read the section for each class present in the app. An app often mixes classes (for example a
data-backed booking tool plus an external weather tool); treat each tool by its own class.

## The seam

The **seam** is how a case's data reaches a tool at run time, without changing the app's code.
It is the least generic part of the job, so decide it per tool and write it in `profile.yaml`.
Prefer the first option that works:

| Seam | How | Works for |
|---|---|---|
| Config / environment | The app reads a DB URL, file path, base URL or data directory from an env var or config file; point it at the case's copy | DB, files, documents, HTTP services with a fake server |
| File swap | The app opens a fixed path; the runner copies the case's world file to that path before each case (and restores it after) | SQLite, JSON, CSV, document folders |
| Monocle `mock_tools` | Monocle's instrumentation skips the real tool and returns the case's response (`MockTool(name, type, response, raise_error)`; `{{arg}}` placeholders are filled from the tool's arguments). One fixed response per tool per run | Any tool Monocle instruments (ADK, OpenAI, LlamaIndex, LangGraph, Strands), single-call flows, failure injection |
| Patch | The runner replaces a client object or module-level data before the run | In-memory data, SDK clients with no config |
| None possible | Live external service with no sandbox | Use invariants only |

Facts about Monocle's mocks worth knowing: they apply only when the agent runs in the same process
as the test; CrewAI is not supported; MCP tools cannot be mocked (use a fake server through
config); a mock cannot query anything (it returns the same response every call). Monocle's
simulated scenario harness applies a scenario's `mock_tools` on every turn of the conversation,
so the same response holds for the whole conversation.

Rules for mocked cases, in both run modes:

- Compute each mock response from the same facts as the scenario's `params` and `input`. The
  simulated user only states those values, so a response built from them fits whatever order or
  wording the user picks. Use `{{arg}}` placeholders where the response should echo an argument.
- A case that needs a different answer on a later call of the same tool (an empty first search,
  then results; a timeout, then success; a status that changes) cannot run with one fixed
  response. Keep it, set `blocked_by: "monocle: one mock response per tool"`, and list it in
  `coverage.md`.

## stub

Signal: the function returns a constant, or a message that only echoes its arguments.

- No world. The prompt is the only input that changes behaviour.
- Expected: which tools are called, by which agent, with which argument substrings; which tools
  are not called; business rules from the instructions decide argument values.
- Worth checking: arguments the tool *cannot* receive (a date the user gives that no argument
  carries) — that is usually a spec question.

## data-backed (database or files)

Signal: SQL queries, ORM sessions, `open()`/`read_csv`/`json.load` on a path, a local DB URL.

- World: the app's own data if it ships with any (copy it; repeat its preparation steps such as
  date shifts); otherwise a public dataset with the same shape; otherwise generate tables with
  DataDesigner, parents before children.
- Inspect the schema and the queries each tool runs: the tool's SQL tells you exactly which
  columns matter and which rows a request can reach (for example "only the current user's
  tickets", "flights departing after now").
- Planters change a copy: update a row (fill a flight), insert one (a conflicting booking), or
  move a date (a departure in 2 hours). Store each as SQL in `fixtures/<test_name>.sql` so the
  runner can apply it to a fresh copy.
- Oracles query the planted copy for the expected choice (an id) and the expected end state.
- `expect.end_state`: a list of `{"query": "SELECT ...", "expect": <value>}` checked after the
  run against the case's world copy. Write queries that return one scalar.
- Writes matter: tools that write (book, cancel, update) make the end state the most reliable
  check, because it does not depend on how the agent phrased its reply.
- Identity: many apps scope data to a current user (a passenger id in config). Pick the user per
  case, and write the user id into `world` so the runner can set it.

## in-memory

Signal: tools read module-level dicts/lists, dataclass instances, or a context object filled at
startup.

- World: the data as JSON in `world/`, generated or adapted from the module's own sample data.
- Seam: static `mock_tools` per case (precompute each tool's response from the case's world), or a
  patch note in the README naming the module attribute to replace. Both work in both run modes.
- Expected: tool calls plus output facts from the world.

## external

Signal: HTTP clients, cloud SDKs, MCP servers that call live services, search tools.

- You cannot control or predict the live answer. Two options:
  - **Invariants only**: checks that hold whatever the service returns ("the converted amount is
    positive", "the agent calls the currency tool with the two currencies the user named").
  - **Mocked responses**: write realistic responses (from traces if they exist) into `mock_tools`
    and test the agent's handling of them, including errors and empty results. These cases can
    run in simulated mode too; follow the rules for mocked cases above.
- Mark these cases `fidelity: "invariant"` when only invariants are checked.

## retrieval (RAG)

Signal: a retriever, vector store, document loader, `as_retriever()`, an index directory.

- World: the documents. Copy the app's documents; add planted documents that contain unique facts
  ("Store hours on public holidays are 10:00 to 14:00").
- Seam: config or file swap of the document folder; the index must be rebuilt from the case's
  documents (note whether the app persists an index and where — a stale index ignores your plant).
- Expected: the answer contains the planted fact (`expect.output_contains`), and does not contain
  facts from documents that were removed. For questions the documents cannot answer, the agent
  should say it does not know (`fidelity: "negative"`).
- There may be no tool calls at all: retrieval is often a chain step, not a tool. Then
  `expect.tools_called` is empty and output checks carry the case.

## none (no tools)

- Prompts plus output checks (`expect.output_contains`, `expect.output_not_contains`) and the
  generic negatives. Monocle evals (`check_eval`) can be added in step 3.
