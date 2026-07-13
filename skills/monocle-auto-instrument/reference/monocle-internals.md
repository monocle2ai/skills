# Phase 5a — How Monocle instrumentation works

Read this before touching Monocle source. Paths are relative to the package root
`monocle/apptrace/src/monocle_apptrace/` in the clone (see `monocle-source-locations` memory for the absolute path).

## The one public entry point

`instrumentation/common/instrumentor.py` → `setup_monocle_telemetry(...)`:

```python
def setup_monocle_telemetry(
    workflow_name: str = None,
    span_processors: List[SpanProcessor] = None,
    span_handlers: Dict[str, SpanHandler] = None,
    wrapper_methods: List[Union[dict, WrapperMethod]] = None,
    union_with_default_methods: bool = True,
    monocle_exporters_list: str = None,
) -> MonocleInstrumentor
```

Called once at startup. `workflow_name` → `MONOCLE_WORKFLOW_NAME` env → calling file's basename. Returns a
`MonocleInstrumentor` (has `.uninstrument()`). Duplicate calls with same args are a no-op.

## Auto-instrumentation = monkeypatching via `wrapt`

There are **no required decorators**. `MonocleInstrumentor._instrument()` walks `DEFAULT_METHODS_LIST` and calls
`wrapt.wrap_function_wrapper(package, object.method, wrapper)` for each entry. When the app later calls e.g.
`CompiledStateGraph.invoke`, the wrapper intercepts it, opens a span, runs the original, records I/O, closes the
span. The app's own code is untouched. (Manual decorators like `@monocle_trace_method` exist for user code but
are not what we rely on here.)

## The metamodel registry — the thing you'll edit in Phase 5

`instrumentation/common/wrapper_method.py`:
- Imports every `<FRAMEWORK>_METHODS` list and concatenates them into `DEFAULT_METHODS_LIST`.
- Defines `MONOCLE_SPAN_HANDLERS: Dict[str, SpanHandler]` mapping handler names → handler instances.

Each method entry (in `metamodel/<fw>/methods.py`) is a dict:

```python
{
    "package": "langgraph.graph.state",      # module to patch
    "object":  "CompiledStateGraph",         # class
    "method":  "invoke",                     # method (and a separate entry for "ainvoke")
    "wrapper_method": task_wrapper,          # task_wrapper (sync) / atask_wrapper (async)
    "span_handler": "langgraph_agent_handler",  # key into MONOCLE_SPAN_HANDLERS
    "output_processor": AGENT,               # extracts span attributes + input/output (see entities/)
    "scope_name": "agent.invocation",        # optional scope propagated to children
}
```

So three knobs decide what a span looks like:
1. **methods.py entry** — *what* gets wrapped and *which* handler/processor/scope it uses.
2. **span handler** (`<fw>_processor.py`) — framework-specific span enrichment, naming, status, scope wiring.
3. **output processor** (`entities/*.py`) — pulls `data.input`/`data.output`/`metadata` and entity attributes
   out of the call's args/return. **Most "empty input/output" bugs live here.**

## Span types & what sets them

`span.type` (workflow / agentic.turn / agentic.invocation / agentic.tool.invocation / inference.framework /
inference.modelapi) is assigned by the handler + output processor for that method entry. The recipe in
`good-trace-recipe.md` is the contract these must satisfy.

## Exporters

`exporters/monocle_exporters.py` → `monocle_exporters` dict: `file, console, okahu, s3, blob, gcs, otlp, memory, …`.
Selection precedence: `monocle_exporters_list` arg → `MONOCLE_EXPORTER(S)` env → default `file`. For this skill we
use **file + console** only. File traces: `.monocle/monocle_trace_<workflow>_<traceid>_<ts>.json`.

## Verifying programmatically (useful in smoke tests)

```python
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
mem = InMemorySpanExporter()
setup_monocle_telemetry(workflow_name="t", span_processors=[SimpleSpanProcessor(mem)])
# ... run ...
spans = mem.get_finished_spans()   # assert types/attributes against the recipe
```
