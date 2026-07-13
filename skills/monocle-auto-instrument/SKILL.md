---
name: monocle-auto-instrument
description: >-
  Use when instrumenting a Python agentic app with Monocle telemetry — this is the
  default, deep posture. Beyond placing the setup call and grading traces, when a gap
  turns out to be in Monocle itself this skill fixes Monocle directly against a local,
  writable clone (cloning it from upstream on first use if absent) and proves the fix
  with Monocle's own tests. Triggers: "instrument this with monocle", "add monocle to
  this repo", "set up monocle telemetry", "trace this agent", "deep-instrument this",
  "add monocle support for <framework>" (especially one Monocle does not yet patch,
  e.g. AG2/autogen), "run the cascade across the demo corpus", or any ask to
  structurally extend Monocle (new framework metamodel; refactor span
  handlers/processors/entities; edit the registry).
argument-hint: [app_folder]
allowed-tools:
  - Read
  - Bash
  - Write
  - Edit
  - Glob
  - AskUserQuestion
---

# Monocle Auto-Instrument

This is the default instrumentation skill, run in a **deep posture**: whoever runs it — a Monocle maintainer or an outside contributor — works against a **local, writable Monocle clone** and may change Monocle itself, not just the app. That posture changes three things:

1. **The Monocle source is local and writable** — make real changes there, editable-install them, iterate.
2. **Deep changes are allowed** — add new framework metamodels, refactor span handlers / output processors / entities, restructure the registry. Redesigns are on the table: where a gap genuinely needs one, you do the redesign — carefully, not reflexively.
3. **Safety shifts from "additive-only" to "test-suite-proven."** Because changes are bigger, the bar is: **Monocle's own pytest suite stays green AND you add a test for every fix/new framework.** Zero regression is proven, not assumed.

You run the loop **autonomously with minimal gating**. Token posture is **liberal** — deep investigation, multiple approaches, run the full suite. Do not stop at the first PASS when the goal is a cascade; carry the fix across the whole framework.

## Environment (local Monocle — clone it on first use if absent)

- **Writable clone (ensure this exists before you edit Monocle):** look for a local Monocle checkout — a git root containing `apptrace/src/monocle_apptrace/` (e.g. `~/monocle`). If there isn't one, clone it on first use: `git clone https://github.com/monocle2ai/monocle ~/monocle`. Upstream `monocle2ai/monocle` is the PR target; add your own fork as a named remote for pushing (`git remote add <you> <your-fork-url>`). Package source: `apptrace/src/monocle_apptrace/`.
- **Registry:** `instrumentation/common/wrapper_method.py` → `DEFAULT_METHODS_LIST` + `MONOCLE_SPAN_HANDLERS`.
- **Per-framework:** `instrumentation/metamodel/<fw>/` (`methods.py` + processor + `entities/`).
- **Editable-install into a demo venv:** `uv pip install -e <your-monocle-clone>/apptrace` (then re-run the demo).
- **Run Monocle's tests:** from `apptrace/`, `uv run pytest` (scope to the touched area first, then full suite before committing).
- If any path differs, re-derive it once and proceed — don't ask.

## Reference files (read on demand)

Read from `reference/` (bundled with this skill):
`supported-frameworks.md`, `placement-playbook.md`, `good-trace-recipe.md`, `diagnosis-tree.md`,
`monocle-internals.md`, `per-framework-map.md`, `fix-and-pr-flow.md`.

---

## Gating (lightweight — only two checkpoints)

Only **two** real checkpoints; everything else proceeds without asking:
- 🚦 **Before the first run of a demo that has external side effects** (sends email, hits a paid/prod API, writes outside its dir). Pure local agent runs need no gate — just go.
- 🚦 **Before pushing a branch / opening an upstream PR.** Local commits to a working branch on the fork are fine without asking.

Everything in between — placing the setup call, running local demos, grading, diagnosing, editing Monocle, editable-installing, re-running, running pytest — is **autonomous**.

---

## Phase 0 — Detect framework (and DON'T stop if unsupported)

1. Detect framework(s) from manifests + imports (`reference/supported-frameworks.md`).
2. Branch on support:
   - **Supported** → Phase 1.
   - **Partially supported** (e.g. inference-only) → note it, then in Phase 5 decide whether to deepen the metamodel to add the missing agentic spans.
   - **Unsupported** (e.g. AG2/`autogen`) → **do NOT stop.** Go to **Phase 5-NEW** (build a new framework metamodel from scratch). This is the headline capability of deep mode.

## Phase 1 — Understand the repo & place the setup call

Same as base: build a mental model, insert `setup_monocle_telemetry(workflow_name="<repo-name>")` as early as possible with the marker `# added by monocle claude skill`, exporters **file + console only** (`MONOCLE_EXPORTER=file`), traces to `.monocle/`. Use `reference/placement-playbook.md`. Touch the app minimally — deep changes go in Monocle, never in the user's app.

## Phase 2 — Run the system (no gate unless side effects)

Pick one question calibrated to exercise the agent loop + a tool call. Run it. Locate the trace under `.monocle/`. (Run the demo's hardest realistic question first in cascade mode — see Phase 7.)

## Phase 3 — Grade against the recipe

Run the bundled grader first — `python scripts/grade_trace.py .monocle/*.json` — for the span tree, per-trace verdict, and cross-trace session-anchoring check (structural FAILs vs `? review` flags). Then apply `reference/good-trace-recipe.md`: `workflow → agentic.turn → agentic.invocation(1..N) → {inference.framework→inference.modelapi, agentic.tool.invocation}`, token `metadata` on inference spans, populated entity names (agent + tool `entity.1.name`, model `entity.2.name`), a single `scope.agentic.session` anchoring the run (multiple traces from one trigger must share it). PASS → record and (in cascade mode) move to the next demo. FAIL → Phase 4.

**Explicit input/output check — do this on EVERY grade.** For every `inference`, `agentic.tool.invocation`, AND `agentic.invocation` span, confirm it carries BOTH a non-empty `data.input` and a non-empty `data.output`. Enumerate any span missing either side — don't wave it through (missing I/O is the single most common real gap). Each miss goes to Phase 4 for the decision below.

## Phase 4 — Diagnose: app issue vs Monocle gap

Use `reference/diagnosis-tree.md`. **Read the repo code first** — if the deviation faithfully reflects the app (e.g. the supervisor genuinely loops, or no tool is called), it's expected: report it, don't "fix" Monocle to paper over it. If it's a true Monocle gap (missing span/IO/tokens, wrong nesting, missing session) → Phase 5.

**For a missing `data.input`/`data.output` specifically, walk this order before touching Monocle:**
1. **Is it the app's doing?** Read the code path — did the app pass empty/`None`, did the tool genuinely return nothing, did the call error before producing output? If so it's a code issue, not Monocle. Report and move on.
2. **If not the app's fault — is the absence *accepted*?** Some spans legitimately have no input or no output for a given call (fire-and-forget tool, a node that produces no output for that input, etc.). If the data was never meaningfully there, that's fine — record it as expected behavior, do NOT change Monocle.
3. **Only if the I/O genuinely existed and should have been captured but wasn't** → it's a real Monocle gap → Phase 5. (Same three-step reasoning applies to missing tokens, wrong nesting, or a missing session.)

## Phase 5 — Fix Monocle DEEPLY (autonomous)

1. **Ensure a writable Monocle clone exists** (see Environment) — if this is your first Monocle fix, clone it from upstream now and add your fork as a remote. This is where you start developing on Monocle. Then understand the internals: `reference/monocle-internals.md`, then the framework's metamodel via `reference/per-framework-map.md`.
2. Make the change — **you may go structural**: add/repair accessors, rewrite an output processor, fix span nesting in the handler, extend `entities/`, adjust the registry, or refactor a shared helper if that's the right fix. Keep it idiomatic and as small as the *correct* fix allows — but do not refuse a redesign if the gap genuinely needs one.
   - **Code style — follow the existing structure; keep it tight.** Mirror how the surrounding metamodel files are organized (same patterns, same helpers, same naming) — don't introduce a new style. Be **minimal, especially with comments**: add a comment only where the *why* is non-obvious; never narrate the code, restate what a line does, or leave scaffolding/section-banner comments. A reviewer should see a small, structured diff, not verbose prose.
3. **Editable-install → re-run the same question → re-grade (Phase 3).** Iterate fix→install→run→grade until it PASSES. Multiple loops are expected; that's fine.
4. **Prove zero regression:** add/adjust a test under Monocle's test suite for this fix, then run `uv run pytest` (touched area first, then full). Green is the bar. If your change reds other tests, either fix correctly or revert and rethink — never weaken a test to pass.

## Phase 5-NEW — Add a brand-new framework metamodel (deep mode's flagship)

When the framework is unsupported (e.g. AG2/`autogen`):
1. Identify the framework's agent/tool/LLM entry points (the classes/methods that map to `agentic.turn` / `agentic.invocation` / `agentic.tool.invocation` / `inference`).
2. Scaffold `instrumentation/metamodel/<fw>/`: `methods.py` (wrapper method entries — package/object/method + the span type), an output processor, and `entities/` accessors. **Model it on the closest existing framework** (`per-framework-map.md`) — e.g. AG2's ConversableAgent/GroupChat resembles CrewAI/AutoGen-style turns. Copy that framework's file structure and conventions exactly; keep it minimal and **sparing with comments** (only where the *why* is non-obvious — no narration or boilerplate banners).
3. Register it: add to `DEFAULT_METHODS_LIST` and `MONOCLE_SPAN_HANDLERS` in `wrapper_method.py`.
4. Editable-install, run the demo, grade. Iterate until the new framework produces the full recipe tree.
5. Add a test module for the new framework. Run the full suite. Then (if re-adding the demo) wire a demo back into the corpus.

## Phase 6 — Commit / PR (gate only on push)

1. Once the demo PASSES and pytest is green, commit to a working branch on your fork (`monocle-fix/<feature>`), **DCO-signed** (`git commit -s`). Local/WIP commits need no gate.
2. 🚦 Ask before pushing / opening the upstream PR against `monocle2ai/monocle`. Follow `reference/fix-and-pr-flow.md`: **`[claude-skill]`-prefixed title**, DCO sign-off (`git commit -s`), and the `🤖 Generated with the monocle-auto-instrument skill` footer. Batch related fixes into one coherent PR where sensible.

## Phase 7 — Cascade across a framework (the corpus driver)

This is how you run the whole tool, framework by framework:
1. Pick a framework. Order its demos **hardest-first** (richest span shape / most agents / parallelism).
2. Run the hardest demo through Phases 1–6. Land the Monocle fix on a branch.
3. With that branch still installed, **re-run every remaining demo in the same framework** and grade. They should now PASS on the same fix (the cascade). Any that don't = a new sub-gap → loop back to Phase 4 for that demo.
4. When the whole framework is green, move to the next framework. Keep each framework's fixes on a focused branch.

Recommended framework order: **validate on LangGraph (a clean demo) → new SDKs hardest-first (OpenAI Agents SDK, MS Agent Framework, Strands) where real gaps live → cascade CrewAI + LlamaIndex → AG2 from scratch (Phase 5-NEW).**

## Per-framework base branch + session + PR policy (the cascade contract)

This is how a real cascade run is operated. **One terminal/session per framework — never share a session across frameworks.**

1. **Base branch per framework.** Each framework is tested on a designated **base branch** of the local Monocle clone — usually an *existing contributor branch* we are simultaneously **reviewing** (e.g. a streaming-support branch). Check it out FIRST and use it for **every demo of that framework**. Make all fixes on top of it; do not branch per demo. Some frameworks take a **union** of two branches (merge both, then test on the merge).
2. **Reviewing while testing.** Treat the base branch as code under review: the cascade both *verifies it works on complex apps* and *extends it* where coverage is missing. Your commits land on (or on top of) that branch.
3. **Fresh session per run.** Every demo run uses a **new `scope.agentic.session`** — never reuse a session id across runs or frameworks. (One framework = one terminal; each demo run inside it = its own session.)
4. **Complexity bar.** Only grade against **complex, multi-agent** demos (3+ agents / parallelism / handoffs / tools) — not 1–2-agent toys. The whole point is proving coverage on realistic systems.
5. **Exercise the branch's feature.** If the base branch adds **streaming** support, run the demos in streaming mode so the streaming instrumentation is actually exercised and graded.
6. **One PR per framework.** When a framework's demos all PASS and pytest is green, open **exactly one PR** for that framework's gaps (based on / targeting its base branch). End-of-framework report: "Tested `<framework>` on N complex multi-agent demos (list), coverage confirmed, PR #__."

Remotes: add your fork (and any co-reviewer's fork whose branch you're testing on) as named remotes once, so you can check out and build on their base branch. You're given (or you choose) the exact base branch per framework at the start of a cascade run.

---

## Operating rules (deep mode)

- Autonomy is the default; only the two 🚦 gates above stop you (external side effects, push/PR).
- Deep Monocle changes are allowed — but **every change is backed by a green test suite + a new test**. That is the regression safety: additive-only is not required, proven-zero-regression is.
- Never weaken or delete a Monocle test to make a change pass. Never paper over an app bug by distorting instrumentation.
- Touch the user's app minimally (setup call + marker only); all real work goes into Monocle.
- **Secret hygiene:** never print, log, or commit API keys/tokens. Exporter/provider keys (e.g. `OKAHU_API_KEY`) go in the environment or `~/.monocle/.env`, never in a committed file or an echoed shell command.
- Report honestly per demo: show the actual span tree, name what you changed in Monocle, and show the pytest result. In cascade mode, keep a running table of demo → PASS/FAIL → fix applied.

## Red Flags — STOP

If you catch yourself about to do any of these, stop and re-read the rule it breaks:

- Editing or deleting a Monocle test so a change goes green.
- Adjusting an accessor/processor to *produce* I/O the app never actually emitted (papering over an app bug).
- Committing/pushing before `uv run pytest` is green, or without adding a test for the fix.
- Changing the user's app beyond the `setup_monocle_telemetry` call + marker to make a trace look better.
- Pushing a branch or opening the upstream PR without hitting the 🚦 gate.
- Running a demo with external side effects (email, paid/prod API) without hitting the 🚦 gate.
- Echoing, logging, or committing an API key/token.
- Stopping at the first PASS in cascade mode instead of carrying the fix across the whole framework.

## Rationalizations — and the reality

| Rationalization | Reality |
|---|---|
| "This test is asserting the wrong thing anyway, I'll relax it." | That's weakening a test to pass. Fix the code or the test *correctly*, or revert and rethink — never loosen an assertion to go green. |
| "The trace looks empty; I'll just have the accessor synthesize a value." | If the app never emitted that I/O, synthesizing it is papering over an app bug. Confirm the data genuinely existed (diagnosis-tree Step 2) before touching Monocle. |
| "The fix is obviously correct, I don't need to run the full suite." | Zero regression is *proven, not assumed* — the whole point of deep mode. Run touched-area tests, then the full suite, before committing. |
| "A one-line tweak in the app is easier than fixing Monocle." | App changes beyond the setup call + marker hide the real gap and don't fix Monocle for the next app. All real work goes into Monocle. |
| "I'm mid-flow, pushing now saves a round-trip." | Push and upstream PR are the one hard gate. Local commits are free; crossing to the remote is not. Ask first. |
| "It's just a local demo, the side effect is harmless." | Side effects (email, paid/prod calls) are gated regardless of how local it feels. Confirm before the first run. |
| "This demo passed, the framework is done." | One PASS is one demo. Cascade mode is done when *every* demo in the framework is green on the same fix. |
