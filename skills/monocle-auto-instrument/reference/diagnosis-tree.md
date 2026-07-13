# Phase 4 — Diagnosis: code issue vs Monocle issue

A FAIL from Phase 3 does **not** automatically mean Monocle is broken. Walk this tree in order. The cardinal
rule: **read the user's code before blaming Monocle.**

## Step 1 — Is the placement actually correct?

Before anything, rule out your own Phase-1 work:
- Did `setup_monocle_telemetry` run **before** the framework objects were built? (If a `workflow` span never
  appears at all, the setup probably ran too late or in the wrong process.)
- Is the framework one Monocle actually patches (Phase 0)? Partially-supported (AG2) explains missing agentic spans.
- Were `.monocle/` traces even written? No file → exporter/env not set, or the run errored before any span closed.

If placement is wrong, fix it and re-run — this is not a Monocle bug.

## Step 2 — Is the deviation explained by the CODE?

Read the repo and ask whether the trace faithfully reflects what the code does:

| Observed deviation | Could be EXPECTED because… |
|---|---|
| N>1 `workflow` roots for one question | the app starts N independent top-level runs (e.g. a loop over sub-tasks, parallel graphs). |
| Many `agentic.invocation` spans | it's genuinely multi-agent — one invocation per agent is correct. |
| No `agentic.tool.invocation` | the code didn't call a tool for this question (pick a question that forces a tool). |
| Sparse output on a span | the framework method legitimately returned little/streamed (verify against the code path). |
| Missing turn for a sub-call | that call isn't a user turn in the code's model. |

If the trace is a faithful mirror of the code → **EXPECTED, not a bug.** Report it; optionally pick a better
question to demonstrate a fuller tree.

### Multiple traces for one trigger — always resolve to a session ID

When one trigger yields multiple traces, don't stop at "expected/not expected" — decide the cause AND guarantee
a session anchor. A session ID should **always** be present:
1. Is the fan-out natural to the code (genuinely multiple crews/graphs per trigger)?
   - **YES** → the traces MUST be anchored by a shared session ID. If they aren't, add it app-side with
     `monocle_trace_scope("agentic.session")` (additive, reversible). Not optional.
   - **NO** (traces/spans split that should have been one) → that's a Monocle gap/error → fix it in Phase 5.
2. End state in both cases: every trace from the trigger carries the **same** `scope.agentic.session`.

## Step 3 — Not explained by code + placement correct → MONOCLE GAP

Conclude "Monocle issue" only when all hold:
1. Placement is correct and a `workflow` span is produced.
2. The framework is (at least partially) supported.
3. The deviation is **not** a faithful reflection of the code.

Typical real Monocle gaps:
- A span type that should exist for this framework is missing (e.g. tool calls happen in code but no
  `agentic.tool.invocation` is emitted) → a missing/incorrect entry in `metamodel/<fw>/methods.py`.
- `data.input` or `data.output` present but **empty/garbled** → the output processor / accessor for that
  method is reading the wrong field (an `entities/` or processor bug).
- Token `metadata` missing on inference → the inference handler isn't extracting usage for this
  provider/version.
- Wrong nesting / scope IDs not propagating → a span-handler or scope-name issue.

Write down the **precise symptom** (which span type, which field, which method/package) — Phase 5 needs it to
target a small fix. Then proceed to Phase 5 (after the 🚦 gate).
