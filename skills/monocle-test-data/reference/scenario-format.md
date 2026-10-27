# Scenario file format

The base is Monocle test_tools' scenario format. Our fields are added to each entry. Monocle's models ignore fields they do not know, so
`MonocleValidator().monocle_scenario_testcase("<file>.json")` loads the file as written, and the
test step reads our fields from the same file by `test_name`.

## File

- One JSON object: `{"scenarios": [ ... ]}`.
- **Never name it `scenarios.json`.** Monocle uses that name as the cache of scenarios it generates
  from a seed, and overwrites it when the seed changes. Use `<app_name>_scenarios.json`.

## Monocle's fields (required unless noted)

| Field | Rule |
|---|---|
| `test_name` | Unique, stable across regenerations of the same case; becomes the pytest id and the Monocle test scope |
| `scenario` | Non-empty. The request in plain words, for the simulated user |
| `persona` | Non-empty. Who the simulated user plays |
| `params` | List of `{name, value, description, is_initial, required?}`. `name` must be a Python identifier (it becomes a tool name). If the list is not empty, at least one entry has `is_initial: true`. `is_initial: false` holds a detail back until the agent asks |
| `success_criteria` | Plain sentences for Monocle's LLM judge. Optional (`null` means nothing is judged) |
| `max_turns` | Integer ≥ 1. Use 1 for single-message cases, 4–8 for conversations |
| `target_description` | What the agent does, one sentence |

## Our fields

| Field | Meaning |
|---|---|
| `input` | The exact user message for verbatim runs (string). Required when `verbatim_required` |
| `verbatim_required` | `true` when the exact wording is the point (dataset prompts, attack text, style variants); a simulated user would rewrite it |
| `expect` | **Correctness checks** — a failure means a wrong or harmful result. Keys below |
| `expect_soft` | **Instruction-following / style checks** — same keys as `expect`; a failure is reported, not fatal |
| `mock_tools` | List of `{name, type, response, raise_error?, error_message?}`; `type` is Monocle's tool type (`tool.adk`, `tool.openai`, `tool.llama_index`, `tool.langgraph`, `tool.strands`) |
| `world` | `null`, or `{base, fixture, hash, seam, user?, approval?}`: base world path, this case's fixture path, the base world's hash, the seam (`config`, `file_swap`, `mock_tools`, `patch`), per-case identity the runner must set, and how to answer approval pauses (`approve_all`, `deny`) |
| `scenario_type` | Our scenario type (Monocle's `scenario` field is the request text, so ours is renamed) |
| `source` | `synthetic`, or the public dataset key |
| `fidelity` | `positive`, `negative`, or `invariant` |
| `license` | Dataset license, or `null` |
| `facts` | The sampled and derived facts, for humans and debugging |
| `spec_question` | Set when the app's instructions do not decide the expected result |
| `blocked_by` | Set when a known app bug makes the expected result unreachable (the replay showed it), or when a missing Monocle feature does (`"monocle: one mock response per tool"`); the case is kept and expected to fail until it is fixed |

## Check keys (for `expect` and `expect_soft`)

Use only these keys. A runner implements each once; an undocumented key is a check nobody applies.

| Key | Value | Passes when |
|---|---|---|
| `tools_called` | list of `{name, agent?, input_contains?, input_not_contains?, min_calls?, max_calls?}` | Some call of the tool (by that agent, if given) has every `input_contains` substring and none of `input_not_contains`; call count within bounds |
| `tools_not_called` | list of tool names | None of them is called (never list tools the framework calls on every turn) |
| `output_contains` | list of strings | The final answer contains every string (case-insensitive) |
| `output_contains_any` | list of strings | The final answer contains at least one (use for "says it does not know" phrasings) |
| `output_not_contains` | list of strings | The final answer contains none |
| `max_sentences` | integer | The final answer has at most this many sentences |
| `retrieval_contains` | list of strings | The retrieved context (retrieval span output) contains every string |
| `end_state` | list of `{query, expect}` | Each query, run on the case's world after the run, returns `expect` |
| `judge_only` | `true` | No exact check is possible; only `success_criteria` (Monocle's judge) decides. Use rarely |
| `custom` | list of `{description, ...}` | A check with no key above, described in plain words for the runner author |

## Example (data-backed)

```json
{"scenarios": [{
  "test_name": "change_flight_target_full_007",
  "scenario": "Move my flight to the next available flight on the same route.",
  "persona": "A frequent traveller who states the request once and expects the agent to handle it.",
  "params": [{"name": "ticket_no", "value": "7240005432906569", "description": "the ticket number", "is_initial": true}],
  "success_criteria": "The agent moves the ticket to flight 1234, the next flight with free seats, not to flight 1201, which is full.",
  "max_turns": 6,
  "target_description": "An airline customer-support agent that manages flights, hotels and car rentals.",
  "input": "Can you move ticket 7240005432906569 to the next flight on the same route? The one after mine looks full.",
  "verbatim_required": false,
  "expect": {
    "tools_called": [{"name": "update_ticket_to_new_flight", "input_contains": ["7240005432906569", "1234"]}],
    "tools_not_called": ["cancel_ticket"],
    "end_state": [{"query": "SELECT flight_id FROM ticket_flights WHERE ticket_no = '7240005432906569'", "expect": 1234}]
  },
  "mock_tools": [],
  "world": {"base": "world/travel.sqlite", "fixture": "fixtures/change_flight_target_full_007.sql", "hash": "sha256:…", "seam": "file_swap", "user": {"passenger_id": "3442 587242"}},
  "scenario_type": "change_flight_target_full",
  "source": "synthetic", "fidelity": "positive", "license": null,
  "facts": {"route": "BSL → SHA", "full_flight": 1201, "next_open_flight": 1234},
  "spec_question": null
}]}
```

## Run modes (for the README)

| Mode | How | Use for |
|---|---|---|
| Verbatim | `run_agent_async(agent, agent_type, s["input"])`, with each `mock_tools` entry applied through `with_mock_tool`, world prepared per `world` | Exact wording; every `verbatim_required` case |
| Simulated | `monocle_scenario_testcase(<file or filtered list>)` + `test_scenario_async(agent, agent_type, scenario)`; the harness applies the scenario's `mock_tools` on every turn; needs `MONOCLE_TEST_AGENT_MODEL` or `model="local"` | Conversations, held-back details |

In both modes, the world for a case is prepared before the run (copy base, apply fixture, set the
seam) and the end state is read after it.
