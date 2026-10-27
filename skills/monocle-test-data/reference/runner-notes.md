# What the runner of step 2 must handle

You do not write the runner, but your README must tell its author exactly what this app needs,
and your expectations must be checkable from what a run produces. These notes come from running
generated scenarios against a live LangGraph agent with Monocle tracing (12 of 15 passed; all three
failures were real app or agent problems).

## Before the run, for each case

1. **World**: copy the base world, apply the case fixture, put it where the seam says (file path,
   env var, patched module attribute, or `mock_tools`). Fresh copy per case — writes leak otherwise.
2. **Per-run config**: some tools read identity from framework config, not from the message
   (LangGraph `config["configurable"]["passenger_id"]`, OpenAI Agents context objects, ADK session
   state). Monocle's runners pass only what they know (for LangGraph: a `thread_id`). Put the value
   in `world.user` and say in the README how to inject it (a small wrapper around the agent object
   that adds the config to every call works without changing the app).
3. **Approval pauses**: apps that pause before writes (`interrupt_before`, human-in-the-loop tools)
   stop silently in a plain run — no write happens and every write case looks failed. Say how to
   resume (LangGraph: invoke again with `None` to approve, or append a denial tool message) and set
   `world.approval` per case.
4. **Import-time side effects**: downloads, embeddings, API clients created at import. Pin
   downloaded documents in `world/` and say which keys are needed even for cases that do not use
   the feature.

## During the run

- **Parallel tool calls**: models may return two tool calls in one message for a combined request.
  An app that routes only the first leaves the second unanswered; the next model call is rejected
  (OpenAI: "tool_calls must be followed by tool messages", HTTP 400). Combined-request scenarios
  find this; mark them so a crash is read as an app finding, not a runner error.
- **Frozen clocks**: if the app fixes "now" in a prompt or a tool, the world's dates must make sense
  relative to that clock, not today.

## After the run: reading tool calls from Monocle traces

- Tool calls are spans with `span.type` = `agentic.tool.invocation`; the tool name is attribute
  `entity.1.name`; the arguments are in the span event `data.input` (attribute `input`, a JSON or
  Python-repr string of the arguments); the result is in event `data.output`.
- Argument text is a string form of a dict (`{'ticket_no': '0060…', 'new_flight_id': 2122}`), so
  `input_contains` substrings should be bare values (`"2122"`, `"BSL"`), not `key=value` forms.
- Tools a graph node calls every turn (not the model) appear as spans in every case.
- The final answer is the last model output; `output_*` checks run on it.
- `end_state` queries run on the case's world copy after the agent finished (and after any
  approval resumes).

## Reading the results

A failure is one of: an **agent** problem (wrong choice, skipped a tool it was told to use), an
**app** problem (a tool bug, a routing crash — often predicted by `blocked_by`), or a **test-data**
problem (a wrong oracle, an argument format the tool never receives). Ask the runner to report which,
and fix test-data problems in the generator, not in single cases.
