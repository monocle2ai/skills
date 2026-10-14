---
name: monocle-test-gen
description: "Generate a pytest test file that uses the Monocle Test Tools fluent API (`monocle_trace_asserter`) to drive an agent under instrumentation and assert against the emitted traces. USE FOR: any request phrased as 'write/create/generate a Monocle test', 'add a fluent test for <agent>', 'test that <agent> calls <tool> with <input>', 'validate that <agent> produces <output>', or any description that names (a) an agent or workflow to run, (b) an input, and (c) something to validate about the resulting traces (tools called, agents invoked, output content, token/duration limits, evaluation results), or to generate many tests at once from public datasets (HuggingFace, tau2-bench); triggers 'generate tests from a dataset', 'pull a dataset and test my agent', 'make as many tests as possible' (see Dataset mode below). DO NOT USE FOR: declarative `@monocle_testcase`-style parameterized tests (those are a separate pattern — use only when the user explicitly asks for declarative/parameterized tests), or for writing instrumentation/exporter code under `apptrace/`."
metadata:
  author: prasad@okahu.ai
  version: "1.0.0"
---

# Generate a Monocle fluent test

You are translating a natural-language description into a runnable pytest file that uses `monocle_trace_asserter` (the fluent API from `monocle_test_tools`) to (1) run an agent under Monocle instrumentation and (2) assert against the traces it emits.

## Workflow

0. **Load the test plan.** Before anything else, look for a `{project}_test_plan.md` file in the working directory — where `{project}` is the project/agent name (e.g. `lg_travel_agent_test_plan.md`), falling back to a plain `test_plan.md` if no project-prefixed file exists. Use Bash `ls`/Glob to find it (e.g. `ls *_test_plan.md test_plan.md 2>/dev/null`). If found, READ it and treat it as the primary source for the three things below — the agent topology, exact agent/tool names, inputs, and validation scenarios are usually already enumerated there (e.g. in scenario tables grouped by ID). The user's request then selects WHICH scenario(s) from the plan to generate as tests. If no test plan file exists, fall back to extracting everything from the user's description.

1. **Extract three things from the test plan (preferred) or the user's description.** If any is missing or ambiguous, ASK before generating code — guessing here produces tests that compile but assert the wrong thing.
   - **Agent under test** — the Python import path of the agent/crew/workflow object, AND which framework it belongs to (maps to an `agent_type` string — see table below).
   - **Input** — the prompt/message/dict passed to the agent. Preserve it verbatim from the test plan / description.
   - **What to validate** — one or more of: a tool was called (with optional input/output substring), an agent was invoked, the final output contains/equals a string, token/duration limit, an Okahu/BERTScore eval result.

2. **Pick the framework runner string** from the agent's framework:

   | `agent_type` string | Framework |
   |---|---|
   | `google_adk` | Google ADK |
   | `langgraph` | LangGraph |
   | `crewai` | CrewAI |
   | `llamaindex` | LlamaIndex |
   | `strands` | Strands Agents |
   | `openai` | OpenAI Agents |
   | `msagent` | Microsoft Agent Framework / Semantic Kernel |

3. **Decide sync vs async.** Default to `async` + `run_agent_async` + `@pytest.mark.asyncio` unless the user explicitly says the agent is synchronous. Almost every framework runner in this repo is async.

4. **Locate the file.** Place new tests under `test_tools/tests/integration/` with filename `test_<agent_name>_fluent.py`. If a file matching the framework + agent already exists there, ADD a new `async def test_...` function to it rather than creating a duplicate file. Use Bash `ls` / Grep to check first.

5. **Generate the test** following the template below. Then run it (or at least `pytest --collect-only` the file) to confirm it parses, unless the user said not to.

## Test template

```python
import pytest
from monocle_test_tools import TraceAssertion
from <agent module> import <agent object>

@pytest.mark.asyncio
async def test_<descriptive_name>(monocle_trace_asserter: TraceAssertion):
    # 1. Run the agent under instrumentation
    await monocle_trace_asserter.run_agent_async(
        <agent object>, "<agent_type>", "<input string>"
    )

    # 2. Assertions — one chained call per logical check.
    # Chaining narrows context: called_agent(A).called_tool(T) means "tool T inside agent A".
    monocle_trace_asserter \
        .called_agent("<agent_name>") \
        .called_tool("<tool_name>") \
        .contains_input("<substring expected in tool input>") \
        .contains_output("<substring expected in tool output>")

    # 3. Optional: end-to-end output / performance
    monocle_trace_asserter.contains_output("<substring expected in final response>")
    monocle_trace_asserter.under_token_limit(1_000_000)
```

For a sync agent, drop `@pytest.mark.asyncio`, drop `await`, and call `run_agent(...)`.

## Fluent API cheat sheet

Assertion methods return `self`. Span selectors (`called_tool`, `called_agent`, and their `does_not_*` counterparts) **narrow the span context** for every subsequent assertion in the chain — that's how you say "this tool, called inside this agent, received this input."

Every assertion accepts an optional `message="..."` kwarg for a clearer failure string.

### Run / load

| Call | Use |
|---|---|
| `await asserter.run_agent_async(agent, agent_type, *args, session_id=None)` | Drive an async agent |
| `asserter.run_agent(agent, agent_type, *args)` | Drive a sync agent |
| `asserter.load_spans(JSONSpanLoader.from_json("traces/x.json"))` | Offline: load pre-recorded spans instead of running |

### Span selectors (narrow context)

| Call | Use |
|---|---|
| `.called_tool(tool_name, agent_name=None)` | Assert tool was called; optionally only inside that agent |
| `.does_not_call_tool(tool_name, agent_name=None)` | Assert tool was NOT called |
| `.called_agent(agent_name)` | Assert agent was invoked |
| `.does_not_call_agent(agent_name)` | Assert agent was NOT invoked |

### Input / output content

| Exact | Substring |
|---|---|
| `.has_input(s)` / `.has_output(s)` | `.contains_input(s)` / `.contains_output(s)` |
| `.has_any_input(*s)` / `.has_any_output(*s)` | `.contains_any_input(*s)` / `.contains_any_output(*s)` |
| `.does_not_have_input(s)` / `.does_not_have_output(s)` | `.does_not_contain_input(s)` / `.does_not_contain_output(s)` |
| `.does_not_have_any_input(*s)` / `.does_not_have_any_output(*s)` | `.does_not_contain_any_input(*s)` / `.does_not_contain_any_output(*s)` |

`with_comparer("similarity" \| "default" \| "bert_score" \| "metric" \| "token_match")` overrides equality for `has_*` (not `contains_*`).

### Performance

| Call | Use |
|---|---|
| `.under_token_limit(N)` | Total tokens across selected spans < N |
| `.under_duration(N, units="seconds"\|"ms"\|"minutes", span_type="workflow"\|"agent_invocation"\|"tool_invocation"\|"agent_turn"\|"inference")` | Each matching span under N |

### Evaluation

| Call | Use |
|---|---|
| `.with_evaluation("okahu")` or `.with_evaluation("bert_score")` | Configure evaluator (Okahu needs `OKAHU_API_KEY`) |
| `.check_eval(name, expected=..., not_expected=..., fact_name="traces")` | Run eval and assert. `expected` / `not_expected` accept str or list[str]. `fact_name` ∈ `traces`, `inferences`, `agentic_turns`, `agentic_sessions`, `agent_invocation`, `tool_execution`. |

Common Okahu templates: `sentiment` → `"positive"`, `toxicity` (use `not_expected=["highly_toxic", ...]`), `hallucination` → `"no_hallucination"`, `pii_leakage` (use `not_expected`), `conversation_completeness` → `"complete"`.

## Span model quick reference

Useful when picking `span_type` for `under_duration` or reasoning about what gets emitted:

| Span | Meaning |
|---|---|
| `agentic.turn` | One end-to-end agent request/response |
| `agentic.invocation` | One agent invocation |
| `agentic.tool.invocation` | A tool call from an agent |
| `agentic.delegation` | Agent → agent handoff |
| `inference` | Single LLM call |

## Worked examples

### "Test that the ADK travel agent books a flight to Mumbai"

```python
import pytest
from monocle_test_tools import TraceAssertion
from test_common.adk_travel_agent import root_agent

@pytest.mark.asyncio
async def test_books_flight_to_mumbai(monocle_trace_asserter: TraceAssertion):
    await monocle_trace_asserter.run_agent_async(
        root_agent, "google_adk",
        "Book a flight from San Francisco to Mumbai for 26th Nov 2025"
    )
    monocle_trace_asserter \
        .called_agent("adk_flight_booking_agent_5") \
        .called_tool("adk_book_flight_5") \
        .contains_input("Mumbai")
    monocle_trace_asserter.contains_output("flight")
```

### "Verify the CrewAI hotel agent does not hallucinate and stays under 5k tokens"

```python
import pytest
from monocle_test_tools import TraceAssertion
from test_common.crewai_travel_agent import create_crewai_travel_crew

@pytest.mark.asyncio
async def test_hotel_agent_no_hallucination(monocle_trace_asserter: TraceAssertion):
    request = "Book a hotel at Marriott in New York for 2 nights starting Dec 1st 2025"
    crew = create_crewai_travel_crew(request)
    await monocle_trace_asserter.run_agent_async(crew, "crewai", request)

    monocle_trace_asserter \
        .called_tool("crew_book_hotel", "CrewAI Hotel Booking Agent") \
        .contains_output("success")

    monocle_trace_asserter.under_token_limit(5000)
    monocle_trace_asserter \
        .with_evaluation("okahu") \
        .check_eval("hallucination", expected="no_hallucination")
```

### "Test that the parallel ADK agent runs both flight and hotel bookings"

```python
import pytest
from monocle_test_tools import TraceAssertion
from test_common.adk_travel_agent import root_agent_parallel

@pytest.mark.asyncio
async def test_parallel_flight_and_hotel(monocle_trace_asserter: TraceAssertion):
    await monocle_trace_asserter.run_agent_async(
        root_agent_parallel, "google_adk",
        "Book a flight to Mumbai and a hotel at Marriott for 4 nights."
    )

    monocle_trace_asserter.called_agent("adk_parallel_booking_coordinator_5")
    monocle_trace_asserter.called_tool("adk_book_flight_5", "adk_flight_booking_agent_5")
    monocle_trace_asserter.called_tool("adk_book_hotel_5",  "adk_hotel_booking_agent_5")
    monocle_trace_asserter.contains_output("flight")
    monocle_trace_asserter.contains_output("hotel")
```

## Common pitfalls — avoid these

- **Don't invent agent/tool names.** If the user gave a description but not exact identifiers, grep the codebase (e.g. `grep -r "name=" --include="*.py" <agent file>`) to find the registered names. ADK/CrewAI/LlamaIndex agents and tools have explicit string names that must match exactly.
- **Don't omit `@pytest.mark.asyncio` on async tests.** Without it, the coroutine is never awaited and the test silently passes.
- **Don't chain unrelated checks on the narrowed context.** After `called_tool(T)`, an `under_token_limit` applies only to that tool's spans. If you want a workflow-wide token limit, call it on a fresh `monocle_trace_asserter` line (not chained).
- **`contains_*` ignores the configured comparer.** It always does substring matching. Use `has_*` + `with_comparer("similarity")` for semantic matching.
- **Don't write declarative `TestCase` lists in a fluent test.** Those are the `@monocle_testcase` style — a different skill. The fluent file should contain only `async def test_...` functions using `monocle_trace_asserter`.
- **The pytest plugin is auto-loaded.** If running outside the repo where `monocle_test_tools` is installed, the user's `conftest.py` must register `pytest_plugins = ["monocle_test_tools.pytest_plugin"]` — the repo root and `test_tools/tests/integration/conftest.py` already do this, so new tests in that directory need no extra setup.

## After generating

1. Print the file path you wrote to.
2. Show the user the suggested command to run it, e.g. `pytest test_tools/tests/integration/test_<name>_fluent.py -v`.
3. Do NOT run the test automatically unless the user asked — most agent runs hit live LLM APIs and cost money.

## Dataset mode — generate many tests from public datasets

Use this when the user wants broad coverage from public datasets ("generate tests from huggingface", "make as many tests as possible", "pull a dataset and test my agent") instead of one hand-described test. It works for any monocle2ai-instrumented agent.

Scripts live in `scripts/`: `dataset_adapters.py` loads datasets, `generate_dataset_tests.py` emits the test file. References: `reference/dataset-sources.md` (the catalog of datasets by domain) and `reference/dataset-adapters.md` (field mapping, the fidelity ladder, and the profile schema).

The agent's environment needs `pip install datasets certifi`.

### Steps

1. **Profile the agent.** Read its code for the framework (which gives `agent_type`), the registered tool and agent names, and the domain. Confirm the real names against the agent's monocle traces (`.monocle/*.json` or Okahu). Write a profile JSON (schema in `reference/dataset-adapters.md`).

2. **Dry-run.** Generate without running the agent, then report the counts:

       python scripts/generate_dataset_tests.py profile.json --out tests/ --limit-per-source 50

   Show the per-source and per-fidelity totals and the non-commercial-license note. Nothing has run.

3. **Pick a live cap.** Each case is a live agent call. Regenerate with `--max-cases N` to cap, and tell the user the cost before running.

4. **Run.** `pytest tests/test_monocle_dataset.py -v`. Do not run automatically.

### What it maps

- A dataset in the agent's domain whose intent matches one of the agent's tools → positive test (tool called, arguments checked).
- Safety and off-domain datasets → negative tests (the agent must not act).
- QA/math rows with a gold answer → output check.
- Rows that need tools the agent lacks, or multi-turn traps → skipped, not flattened.

A dataset's own tool name (for example tau2-bench's `book_reservation`) is mapped by meaning to the agent's tool (`book_flight`); it is never copied into the test.

### Worked example (LangGraph travel agent)

Profile domain `["travel"]`, with `book_flight` and `book_hotel` mapped to the agent's registered names. The dry-run pulls tau2-bench (bookings plus cancel/complaint negatives) and the universal safety and tool-calling sets, then writes `test_monocle_dataset.py` and `monocle_dataset_cases.json` next to the profile.
