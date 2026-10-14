# Dataset adapters and the fidelity ladder

How a dataset row becomes a Monocle test. `scripts/dataset_adapters.py` turns rows
into `RawCase` records; `scripts/generate_dataset_tests.py` turns each `RawCase`
into a test case against the target agent.

## RawCase: the common shape

Every adapter yields the same record, so the generator treats all datasets alike:

| Field | Meaning |
|---|---|
| `input` | the user request fed to the agent |
| `intent` | what the row asks for: `book_flight`, `book_hotel`, `tool_call`, `qa`, `math`, `harmful`, `offtopic` |
| `slots` | argument/entity values to assert as input substrings (may be empty) |
| `answer` | the gold answer, when the dataset has one |

The adapter never names the agent's tools. The dataset's own tool name is dropped;
the generator maps `intent` to the agent's real tool through the profile.

## The agent profile

The skill writes this after reading the agent's code and traces. The generator reads it.

```json
{
  "agent_import": "lg_travel_agent",
  "agent_factory": "setup_agents",
  "agent_type": "langgraph",
  "domain": ["travel"],
  "tools": {
    "book_flight": "okahu_demo_lg_tool_book_flight",
    "book_hotel": "okahu_demo_lg_tool_book_hotel"
  }
}
```

- `agent_object` names a ready agent attribute; `agent_factory` (+ optional `factory_args`) names a callable that returns one (awaited if it is a coroutine). Use one.
- `tools` maps a dataset `intent` to the agent's registered tool name.

## Selection

A dataset is used when its `domain` is in the profile's `domain`, **or** its domain is
`safety` or `tools` (the universal sets every agent gets).

## The fidelity ladder

Each `RawCase` becomes one of four outcomes:

| Condition | Fidelity | Emitted assertion |
|---|---|---|
| `intent` is in the profile's `tools` | **positive** | `called_tool(mapped_tool)` + `contains_input(slot)` per slot |
| `intent` is `harmful` or `offtopic` | **negative** | `does_not_call_tool` for every agent tool |
| `answer` present, dataset domain matches, domain is `qa`/`math` | **inputs-only** | `contains_output(answer)` |
| dataset domain not in the agent's domain | **negative** | `does_not_call_tool` for every agent tool |
| otherwise | **skip** | — |

Negative cases need the agent to have at least one tool; without tools they are skipped.

## Adding a dataset

Append one `Source` to `SOURCES` in `dataset_adapters.py`:

```python
Source("my-dataset", "qa", "MIT",
       _flat("owner/my-dataset", "train", "qa", text_key="question", answer_key="answer"))
```

`_flat` covers any dataset with a text column (and optional answer column). For nested
rows (dialogues, conversations), write a small `load(limit)` generator that yields
`RawCase`, like `_hermes` and `_tau2`.

## Caveats

- **Requirements:** `pip install datasets certifi`. The τ² adapter fetches JSON over HTTPS and uses `certifi` for the CA bundle.
- **Gated datasets** (xLAM, AdvBench, HarmBench) need `huggingface-cli login`. They are not wired by default; the generator skips any source that fails and reports why.
- **Script-based datasets** (Schema-Guided Dialogue, MultiWOZ) do not load on current `datasets` releases, which dropped loader scripts. They stay in `dataset-sources.md` for when a parquet mirror is used.
- **Non-commercial** licenses (ToxicChat, BeaverTails) are flagged in the run summary.
- **Comparer:** substring checks go through the fluent `contains_*` methods; the declarative `"token_match"` comparer string is broken in the installed test tools.
