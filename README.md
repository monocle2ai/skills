# Monocle — Claude Code Skills

Coding agent skills for instrumenting, tracing and testing agents with Linux Foundation [Monocle2AI](https://github.com/monocle2ai/monocle).

## Install

Two separate steps in Claude Code — run them one at a time, not together.

**1. Add the marketplace:**

```
/plugin marketplace add monocle2ai/skills
```

**2. Install the plugin** (run this as a new command, after step 1 finishes):

```
/plugin install monocle@monocle-skills
```

## Skills

| Skill | Description |
|-------|-------------|
| `monocle-auto-instrument` | Instrument a Python agentic app with Monocle telemetry, run it, and grade the emitted traces against a good-trace rubric. If the instrumentation is missing or incomplete — including when the gap is in Monocle itself — the skill creates the fix and proves it with Monocle's own tests. |
| `monocle-test-data` | Generate test data for an agentic app: read its code, build the world data its tools read, plant scenario conditions, compute the expected results with code, and write a Monocle scenario file with exact checks. The scenarios run with Monocle's scenario harness to produce traces. |

More skills will be added over time.

## Use

Open Claude Code in the Python agentic project you want to trace, then ask:

```
instrument this agentic system with monocle
```

The skill detects the framework, adds the telemetry, runs a representative question, and reports a
graded trace — telling you whether the instrumentation is good and fixing it if it isn't.

To generate test data for the agent, ask:

```
generate monocle test data for this agent
```

The skill writes a folder with the scenario file, the world data and fixtures, and a README for
running the scenarios in Monocle's scenario harness.

## Framework support

- **Supported frameworks** — the skills add and verify instrumentation for the agent frameworks
  Monocle supports today (e.g. LangGraph, CrewAI, LlamaIndex, OpenAI Agents SDK, Strands).
- **Unsupported frameworks** — when a framework isn't supported yet, the skill stops and reports
  it (with a pointer to file an issue on [Monocle](https://github.com/monocle2ai/monocle)) rather
  than instrumenting blindly.
