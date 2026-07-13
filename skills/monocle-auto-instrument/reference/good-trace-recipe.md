# Phase 3 — The good-trace recipe (PASS/FAIL rubric)

Derived from a real, known-good Monocle trace (open-swe, LangGraph, single question
"Is LangGraph used in this project?", 18 spans). The `span.type` taxonomy is framework-agnostic, so this
rubric grades CrewAI / LlamaIndex / Haystack / OpenAI-Agents the same way — only leaf entity names differ.

## The shape: one user question → one trace tree

```
workflow                    (span.type=workflow)             root, parent=None, EXACTLY 1
└─ agentic.turn             (span.type=agentic.turn)         ≥1; one per user question
   └─ agentic.invocation    (span.type=agentic.invocation)   1..N; one per agent invoked
      ├─ inference.framework (the LLM call via the framework)
      │  └─ inference.modelapi  (raw provider API call; child of the framework span)
      └─ agentic.tool.invocation  (one per tool call)
```

## Where input/output live — IMPORTANT

Input/output are span **events**, not attributes:
- `data.input` event → `{"input": ...}`
- `data.output` event → `{"response": ...}`
- `inference.framework` also has a `metadata` event → `{"prompt_tokens", "completion_tokens", "total_tokens", "finish_reason"}`
- `inference.modelapi` has **no events** — its payload is carried on its parent `inference.framework` span. Don't flag it for "missing I/O".

Model identity is in attributes: `entity.2.name` (e.g. `gpt-4.1-mini`), `entity.2.type`. Tool identity: `entity.1.name`
(on `agentic.tool.invocation`). Agent identity: `entity.1.name`, `entity.1.type` (e.g. `agent.crewai`) on `agentic.invocation`.
Scope IDs propagate down the tree: `scope.agentic.session`, `scope.agentic.turn`, `scope.agentic.invocation`.

## Every input/output event must be populated — triage each empty one

This is a hard grading rule, not a nicety: **if a span carries a `data.input` or `data.output`
event, that event MUST be non-empty.** An empty event (`{}`, `""`, `"response": ""`, `{"input": ""}`)
is never acceptable on its face — it is a signal to investigate, exactly like a missing span.
(A span that has *no* I/O event at all — e.g. a structural `generic`/`inference.modelapi` span — is
out of scope for this rule; it only governs spans that DO declare the event.)

For each empty I/O event, determine the root cause and act:

1. **Is the data actually available at the instrumented call site?** Probe the real call (spy on the
   method, or add a temporary debug line inside the accessor) and look at what the wrapped method
   genuinely receives/returns.
2. **Data IS available but the event is empty → Monocle bug. Fix Monocle.** Common causes:
   - the value is passed as a **keyword** arg but the accessor reads `args[0]` positionally
     (e.g. `achat(messages=...)` vs `achat(messages)`);
   - the value is a **non-string object** (a Pydantic model, dict, list) returned/accepted as-is, so
     OTEL silently **drops** it — serialize it to a string/JSON in the accessor;
   - the accessor **filters** the value out (e.g. only keeping scalar args and dropping a list/dict).
3. **Data is genuinely NOT there → code or natural behavior → fine.** Legitimate examples:
   - a streaming LLM call where the provider omits token usage unless `include_usage` is set;
   - a library's internal/partial call that really does fire with empty args and no result
     (e.g. structured-output machinery invoking a tool with `{}`);
   - the method's signature simply doesn't carry that datum (it lives on a parent span instead).
   Record it as expected and move on — do **not** distort instrumentation to manufacture a value.

Always say which verdict you reached and why, per empty event. "Empty but expected" is a valid PASS
only with that justification written down.

## PASS — all must hold

1. A `workflow` root span (`parent_id == None`) with `entity.1.type == workflow.<framework>`. One trigger is
   usually one trace, but a system that by design fans out (multi-crew, parallel graphs) may emit several —
   allowed ONLY if they're anchored by a shared session ID (see "Session anchoring is mandatory" below).
2. **≥1** `agentic.turn` under the workflow, each with **non-empty** `data.input` AND `data.output`.
3. **≥1** `agentic.invocation` under a turn, each with **non-empty** `data.input` AND `data.output`,
   AND a populated agent name (`entity.1.name`). (Multiple invocations = multiple agents fired = fine.)
4. Each `inference.framework` has `data.input`, `data.output`, AND a `metadata` event with non-zero token counts;
   `entity.2.name` (model) is populated.
5. Each `agentic.tool.invocation` has **non-empty** `data.input` AND `data.output`; `entity.1.name` populated.
6. Nesting is correct (turn under workflow, invocation under turn, inference/tool under invocation) and the
   `scope.agentic.*` IDs are present and consistent.

## Session anchoring is mandatory

Every run MUST carry a session ID — the `scope.agentic.session` attribute — that ties the trigger's work together.

- **One trigger → one trace:** the session ID is still required; it anchors that trace.
- **One trigger → multiple traces (by design):** every one of those traces MUST share the **same** session ID,
  so they're correlated as one logical run. Multiple traces with **no** shared session ID is a **FAIL**, not "fine."

If multiple traces appear without a session anchor, do not paper over it — go to Phase 4 and decide whether the
fan-out is natural to the code or a sign of confusion/an error:
- **Natural fan-out** → add the session scope app-side (`monocle_trace_scope("agentic.session")`, additive &
  reversible) so all traces share one session ID.
- **Not natural** (spans/traces split when they should be one) → it's a Monocle bug; fix it in Phase 5.

Either way the end state is identical: a session ID is present and correctly anchors the whole run.

## FAIL signals → go to Phase 4 (diagnose)

- Any required `data.input`/`data.output` missing or empty (e.g. `"response": ""`).
- `inference.framework` missing token `metadata`, or model name blank (`entity.2.name`).
- Agent name blank on `agentic.invocation` (`entity.1.name`), or tool name blank on `agentic.tool.invocation`
  (`entity.1.name`) — a nameless agent/tool means the framework's entity accessor isn't resolving identity.
- Broken nesting (turn with no workflow parent; invocation not under a turn; orphaned tool/inference spans).
- **Multiple traces / workflow roots for one trigger with NO shared `scope.agentic.session`** — always
  investigate in Phase 4 (natural fan-out vs. confusion/error). Either way the run MUST end anchored by a single
  session ID: scope it app-side if natural, fix Monocle if it's a bug.
- Zero `agentic.tool.invocation` when the question clearly required a tool — but only a FAIL if the code
  actually has/uses tools for that path; otherwise it's a question-choice problem.

## How to read a trace file

`.monocle/monocle_trace_<workflow>_<traceid>_<timestamp>.json` is a JSON array of spans. Build an id→span map
from `context.span_id`, link via `parent_id`, then walk the tree. Group by `attributes["span.type"]`.
`monocle-apptrace validate <file>` lints structure but does NOT enforce this recipe — apply this rubric yourself.

**Shortcut — run the bundled grader:** `python scripts/grade_trace.py .monocle/*.json`. It prints the span
tree, a per-trace verdict, and the cross-trace session-anchoring check, separating **structural FAILs** (wrong
workflow-root count, missing/split session) from **`? review` flags** (empty `data.input`/`data.output`, missing
token metadata, blank agent/tool/model names). The review flags are NOT auto-fails — triage each with
`diagnosis-tree.md` (faithful app behavior vs. a real Monocle gap) before changing anything.
