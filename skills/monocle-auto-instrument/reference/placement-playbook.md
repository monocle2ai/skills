# Phase 1 — Placement playbook

Goal: get `setup_monocle_telemetry(workflow_name="<repo>")` to execute **once, before any framework object is
constructed**, in the process that actually runs the agent.

## Step 1 — find the entry point (deterministic signals, in priority order)

1. `pyproject.toml` → `[project.scripts]` / `[tool.poetry.scripts]` → the `module:function` it points to.
2. `setup.py` / `setup.cfg` → `console_scripts`.
3. `if __name__ == "__main__":` blocks (often `main.py`, `app.py`, `run.py`, `src/<pkg>/main.py`).
4. `langgraph.json` → the `graphs` entries (for `langgraph dev` apps — there is no `__main__`; see special case).
5. Web server: `app = FastAPI()` / `Flask(__name__)` → the module that builds the app, or its `lifespan`/startup hook.
6. `Dockerfile` / `Procfile` / Makefile `CMD`/targets → the literal launch command.

Confirm by reading the file and tracing imports: the setup call must run before the framework's objects
(graph compile, `Crew(...)`, agent/index construction) are created.

## Step 2 — insert in place

Add, as early as the chosen module allows (top of `main()`, top of module, or the server's startup/lifespan):

```python
from monocle_apptrace.instrumentation.common.instrumentor import setup_monocle_telemetry

# added by monocle claude skill
setup_monocle_telemetry(workflow_name="<repo-name>")
```

Rules:
- The marker comment must be exactly `# added by monocle claude skill` (so it's greppable and removable).
- `workflow_name` = the repo/app name (becomes `workflow.name` on every span and the trace filename).
- Place it **above** framework imports/initialization where practical; at minimum above the first
  graph/crew/agent construction.

## Step 3 — exporters: file + console only

Monocle reads `MONOCLE_EXPORTER` (and writes file traces to `.monocle/`). Set both before running:

```bash
export MONOCLE_EXPORTER=file
export MONOCLE_CONSOLE=true        # also echo spans to stdout for live confirmation
```

(Or pass `monocle_exporters_list="file,console"` to `setup_monocle_telemetry`.) Do **not** configure okahu/s3/otlp.

## Special case — `langgraph dev` / LangGraph Studio (no __main__)

These apps are loaded by the langgraph server from `langgraph.json`; there's no script entry to edit. Two options:
- Put the setup call at the **top of the graph module** named in `langgraph.json` (module import time runs before
  the graph serves) — preferred, still "in place".
- Fallback wrapper-entry: a tiny module that calls `setup_monocle_telemetry(...)` then imports the graph, and
  point `langgraph.json` at it.

## Fallback — wrapper-entry pattern (only if no clean in-place edit exists)

Create `monocle_entry.py` next to the real entry:

```python
from monocle_apptrace.instrumentation.common.instrumentor import setup_monocle_telemetry
setup_monocle_telemetry(workflow_name="<repo-name>")   # added by monocle claude skill
from <real_entry_module> import main   # import AFTER setup
main()
```

Run `python monocle_entry.py` instead of the original. Reversible by deleting the file. Prefer in-place editing;
use this only when the entry can't be edited cleanly.

## Reversal

To undo everything: remove the line(s) marked `# added by monocle claude skill` (and any `monocle_entry.py`),
and delete the `.monocle/` directory the run created.
