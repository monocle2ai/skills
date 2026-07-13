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

More skills will be added over time.

## Use

Open Claude Code in the Python agentic project you want to trace, then ask:

```
instrument this agentic system with monocle
```

The skill detects the framework, adds the telemetry, runs a representative question, and reports a
graded trace — telling you whether the instrumentation is good and fixing it if it isn't.

## Framework support

- **Supported frameworks** — the skills add and verify instrumentation for the agent frameworks
  Monocle supports today (e.g. LangGraph, CrewAI, LlamaIndex, OpenAI Agents SDK, Strands).
- **Custom frameworks** — when a framework isn't supported yet, the skill can extend Monocle
  itself against a local clone and validate the new instrumentation with Monocle's test suite.
