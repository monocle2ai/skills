---
name: monocle-test-data
description: Generate test data for an agentic app so Monocle can run it and test it. Reads the agent's code, classifies how it gets information (stub tools, database or file-backed tools, in-memory state, external APIs, retrieval over documents), builds the world data its tools read, plants scenario conditions, computes expected results with code, and writes a Monocle scenario file (the monocle_scenario_testcase format plus exact `expect` checks). Use this whenever someone wants test cases, test scenarios, synthetic or evaluation data, a regression suite, or realistic inputs to produce traces for an agent, multi-agent system, chatbot, or RAG app (LangGraph, Google ADK, CrewAI, OpenAI Agents, LlamaIndex, Strands, LangChain) — even if they do not say "Monocle" or "dataset". Not for writing the pytest test file itself; that is monocle-test-gen.
metadata:
  author: akshay.yadav@okahu.ai
  version: "1.0.0"
---

# Agent test data

You produce the **test data** for an agent app: what to send it, what world it should see, and
what it must do. You do **not** run the agent — running it to produce traces is the next step,
done with Monocle's scenario harness by whoever owns that step. Your output is a folder they can
use without reading the app's code.

The value of this data comes from one rule: **code decides what is correct; an LLM only writes
text.** Sample the facts first, derive the expected behaviour from the facts with code (rules,
queries), and only then write the user message from the same facts. A test whose expected result
was guessed by an LLM, or copied from what the agent did, cannot catch the agent's mistakes.

## Ground rules

- Do not modify the app's code or its original data files. Work on copies.
- Do not call the app's agent or its model. No API key for the app is needed.
- Every tool with side effects (book, pay, send, delete, update) must, in every case, either be
  pointed at a copy of the data or get a mock. A tool left untouched runs its real code.
- Write each guess you make about intended behaviour into `spec_questions.md`. Do not guess quietly:
  an unclear specification is a finding, often the most useful one.

## Inputs

- **Required:** the app's code (a path).
- **Optional:** existing Monocle traces (`.monocle/*.json`, Okahu), the app's data (a DB file,
  documents), the number of cases, and the mode. **Interactive** (default) stops at the two
  checkpoints. **Autopilot** ("just do it", "make reasonable assumptions") records its assumptions
  in `spec_questions.md` and continues.

## Output folder

Default: `monocle_test_data/<app_name>/` next to the app, unless the user names another place.

```
profile.yaml           what the app is: framework, agents, tools, data access, rules (phase 1-2)
spec_questions.md      open questions and assumptions
world/                 base world, its build script, world_report.md        (only if a world exists)
fixtures/<test_name>.* per-case changes to the world                          (only if a world exists)
generate.py            code that builds the scenarios: facts, planters, oracles, text
<app_name>_scenarios.json   the scenario file (never name it scenarios.json — see format reference)
coverage.md            counts per scenario type, fidelity and source
README.md              how step 2 runs it: run modes, how the world reaches the tools
```

## Phase 1 — Discover

Read the code that defines the agents and tools; read traces if they exist (they show the exact
names Monocle records and real tool responses). Record in `profile.yaml`:

- `framework` and Monocle's `agent_type` string: `google_adk`, `langgraph`, `crewai`,
  `llamaindex`, `strands`, `openai`, `msagent`. A plain LangChain chain has no agent runner;
  note it.
- How to get the runnable object: import path plus attribute or factory function.
- Agents: names exactly as the framework registers them.
- Tools: name as registered, arguments, what it returns, side effects, and **where its data
  comes from** (read the function body, not only the docstring — they often disagree).
- Rules: everything the instructions, prompts, policy documents or code enforce ("only book a
  hotel if asked", "changes need 24 hours notice"). Rules produce the best scenarios.
- Scope: what the agent is for and what it should decline.
- Run-time needs the next step must meet: per-run config the tools read (a user id, a tenant),
  human-approval pauses before writes, import-time side effects (downloads, embeddings), a frozen
  or real clock. These decide whether a generic runner can drive the app at all, so record them.
- Tools the framework or a graph node calls on every turn (not chosen by the model). They show up
  in traces for every case, so never list them in `expect.tools_not_called`.

## Phase 2 — Classify how the agent gets information

The agent never sees a database; it only sees what its tools (or its retriever) return. So the
way each tool gets data decides what you must build. Classify every tool, and the app as a whole:

| Class | Signal in the code | What you build |
|---|---|---|
| stub | Returns a fixed or argument-echo value | Prompts + expected tool calls and arguments |
| data-backed | Reads/writes a DB or files | A world (copy or generated) + planted conditions + query-based expected results + end state |
| in-memory | Reads module-level dicts/lists or context objects | Small world as data + per-case mocks or patch notes |
| external | HTTP/SDK/MCP call to a live service | Prompts + invariants only, or mocked responses |
| retrieval | Retriever / vector store over documents | Document world + planted facts + answer checks |
| none | No tools, plain model call | Prompts + output checks |

Then read `reference/agent-types.md` for each class present. It explains, per class, how the
test data reaches the tools at run time (the **seam**) — the part that differs most between apps.
Prefer seams that need no code change: a config value or environment variable, then swapping a
data file, then Monocle `mock_tools`, then patching. Record the seam per tool in `profile.yaml`.

### Checkpoint 1

Show the profile, the classes, the seams and the spec questions so far. In interactive mode, wait
for the user. In autopilot, write your assumptions to `spec_questions.md` and continue.

## Phase 3 — World (data-backed, in-memory and retrieval classes only)

1. **Source**, in this order: data the user gave → seed or dev data in the repo or its setup
   scripts → a public dataset (`reference/dataset-sources.md`) → synthesis with DataDesigner
   (`reference/datadesigner-patterns.md`). A realistic existing world is better than a generated
   one; generate when there is none or when you need conditions it lacks.
2. **Copy, never edit in place.** Build `world/` from a copy. Repeat any preparation the app's
   setup does (for example shifting stored dates to the present) as a script in `world/`.
3. **Inspect.** For SQLite run `scripts/inspect_sqlite.py <db>`: tables, row counts, samples, date
   ranges. Know the world before writing scenarios against it.
4. **Check** integrity (keys resolve, no impossible values) and write `world/world_report.md`.
   Record a hash of the base world; scenarios carry it.

## Phase 4 — Plan scenarios

Read `reference/scenario-taxonomy.md`. Derive scenario types from the tools × the rules × the
ways things go wrong: happy paths per capability, partial requests, each rule, missing details,
out-of-scope, tool failures, conflicting or ambiguous requests, adversarial input, multi-turn.
Give each type a count. Plan the generic negatives from public datasets too (safety and off-domain
prompts; `scripts/gen_dataset_negatives.py`, which also works for apps without tools) — every agent
should get them. Include combined requests (two capabilities in one message): models often emit
two tool calls in one turn, and many apps route only one of them — a live run crashed exactly there.

### Checkpoint 2

Show the plan (types, counts, two or three fully worked examples). Interactive: wait. Autopilot:
continue.

## Phase 5 — Build the cases

Write `generate.py`. For each scenario type, the same loop:

1. **Facts** — sample from the world (real ids, names, dates) or from samplers.
2. **Planter** (if a world exists) — code that changes a copy of the world so the condition holds
   ("the cheapest flight is full"). Save the change as `fixtures/<test_name>.*` (SQL, JSON patch).
3. **Oracle** — code that computes the expected result from the facts and the planted world
   (a query, a rule). Never ask an LLM what the right answer is.
4. **Expectations** — `expect.tools_called` (tool name as registered + substrings that will appear
   in the tool's arguments), `expect.tools_not_called`, and for worlds `expect.end_state` (queries
   with the expected value after the run). Think about the argument format the tool actually
   receives (an id, not a name; the date format the tool takes) or the check can never pass.
   Split the checks by what a failure would mean:
   - `expect` — **correctness**: a failure means the user got a wrong or harmful result (wrong
     flight booked, data of another user shown, a write that should not happen).
   - `expect_soft` — **instruction-following and style**: a failure is worth a look but the result
     may still be right (did not consult the policy tool, answer longer than asked). In a live run an
     agent answered a policy question correctly from its own knowledge without calling the policy
     tool; as a hard check that reads as a broken agent, as a soft check it reads as a grounding risk.
   Use only the check keys in `reference/scenario-format.md`. If a case needs a check that has no
   key, put it in `expect.custom` with a plain-language description — a key nobody documented is a
   check no runner will apply.
5. **Text** — the user message (`input`) and the scenario sentence, written from the same facts.
   Templates are enough to start; an LLM column can rewrite them for natural wording later.
6. **`success_criteria`** — the expected behaviour in one or two plain sentences, for Monocle's
   LLM judge in simulated runs.

Use DataDesigner when you need many combinations of facts (`reference/datadesigner-patterns.md`);
plain Python is fine for a few dozen cases. Write the file with `scripts/scenario_format.py`.

## Phase 6 — Validate

- `uv run --no-project python scripts/validate_scenarios.py <scenario file> [--app-root <dir>]` —
  checks Monocle's required fields, our fields, unique names, fixture files, and the file name. Fix
  every error. With `monocle_test_tools` installed (`--with monocle_test_tools`), it also loads the
  file with Monocle's own loader.
- Oracle sanity: every expected id or value exists in that case's world; every fixture applies
  cleanly to a fresh copy. If you cannot apply a fixture, the case is wrong — drop or fix it.
- **Replay** (when tools write to a world): on a fresh copy of each case's world, call the app's
  **real** tool functions with the expected arguments — import them from the app; stub only what
  they need from the framework (a config object, an env var) — then run the `end_state` queries.
  A case whose expected end state cannot be reached even by the right calls is either a wrong
  oracle (fix the generator) or an app bug (keep the case, set `blocked_by`, and write it up in
  `spec_questions.md`). Copying the tool code instead of importing it hides exactly these bugs.
  Import with `python -B` (or `PYTHONDONTWRITEBYTECODE=1`) so no `__pycache__` lands in the app.
- Read five cases end to end as a reviewer would: does the message ask for what the facts say,
  and would a correct agent do exactly what `expect` says? Fix the generator, not single cases.
- Write `coverage.md`.

## Phase 7 — Package

Write `README.md` for the person running step 2: the run modes (verbatim with `input` and
`mock_tools`; simulated with Monocle's harness, which applies `mock_tools` itself), how the world
and fixtures reach the tools for each case, the required environment, and the open spec
questions. Read
`reference/runner-notes.md` first: it lists what a runner has to handle (per-run config, approval
pauses, parallel tool calls, reading tool calls from Monocle spans) and what was learned running
generated scenarios against a live agent. Then summarize for the user:
counts, what each class of tool got, what could not be covered and why, and the spec questions.

## The scenario file, in short

A JSON object `{"scenarios": [...]}` that `MonocleValidator().monocle_scenario_testcase(path)`
loads as written. Each entry has Monocle's fields (`test_name`, `scenario`, `persona`, `params`,
`success_criteria`, `max_turns`, `target_description`) plus ours (`input`, `verbatim_required`,
`expect`, `expect_soft`, `mock_tools`, `world`, `scenario_type`, `source`, `fidelity`, `license`,
`facts`, `spec_question`, `blocked_by`). Full field rules, the list of check keys, and an example:
`reference/scenario-format.md`.

## Environment notes

- `scripts/...` and `reference/...` are inside this skill's folder. Run a script as
  `uv run --no-project python <skill folder>/scripts/<name>.py`. To use `scenario_format` from
  `generate.py`, add `<skill folder>/scripts` to `sys.path` before the import.
- DataDesigner: the `data-designer` package (`uv run --with data-designer python ...`). Samplers
  and expressions need no API key; LLM columns do.
- Public datasets need the Hugging Face `datasets` library and a Python built with `lzma`. If
  `import lzma` fails, use a uv-managed Python, which includes it, e.g.
  `uv run --no-project --python 3.13 --with datasets python ...`.
