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
| `monocle-test-gen` | Write Monocle Test Tools tests for an agent. From one description it writes a single fluent test; in dataset mode it pulls public datasets and generates many tests at once for any instrumented agent. |

More skills will be added over time.

## Use

Open Claude Code in the Python agentic project you want to trace, then ask:

```
instrument this agentic system with monocle
```

The skill detects the framework, adds the telemetry, runs a representative question, and reports a
graded trace — telling you whether the instrumentation is good and fixing it if it isn't.

## Generate tests from public datasets

`monocle-test-gen` can mass-generate tests from public datasets for any
monocle2ai-instrumented agent. It reads your agent's tools and domain, pulls the datasets
that match plus a universal safety set, and writes a parametrized pytest file. Generation
never runs your agent, so you choose how many tests to run after seeing the counts.

### Datasets

Wired now (non-gated, load without a login):

- **Safety (every agent):** Do-Not-Answer, JailbreakBench, ToxicChat
- **Tool calling:** Hermes function-calling
- **Travel:** tau2-bench airline, tau2-bench retail
- **QA:** HotpotQA, TruthfulQA
- **Math:** GSM8K

Listed for extension: SWE-bench, HumanEval, MBPP, MultiHop-RAG, FRAMES, CRAG,
Schema-Guided Dialogue, MultiWOZ, xLAM, BFCL, AdvBench, HarmBench, and more. The full
catalog (~50 datasets across coding, RAG, travel, math, and safety) with domains and
licenses is in
[`skills/monocle-test-gen/reference/dataset-sources.md`](skills/monocle-test-gen/reference/dataset-sources.md).

### How to use

Open Claude Code in your agent project and ask:

```
generate tests for my agent from public datasets
```

The skill reads your agent, writes a profile, and runs a dry-run that reports how many
tests each dataset produces. Then run them yourself:

```
pip install datasets certifi
pytest tests/test_monocle_dataset.py -v
```

Each test is a live agent call, so start with a small number.

## Framework support

- **Supported frameworks** — the skills add and verify instrumentation for the agent frameworks
  Monocle supports today (e.g. LangGraph, CrewAI, LlamaIndex, OpenAI Agents SDK, Strands).
- **Unsupported frameworks** — when a framework isn't supported yet, the skill stops and reports
  it (with a pointer to file an issue on [Monocle](https://github.com/monocle2ai/monocle)) rather
  than instrumenting blindly.
