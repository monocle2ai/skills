# Dataset sources for test generation

This is the catalog the skill searches to turn **public datasets** into Monocle tests for
**any** monocle2ai-instrumented agent. It is agent-agnostic: the skill reads the target
agent's domain and tools (from its code and its existing traces), then picks the datasets
below whose domain overlaps, plus the **universal** safety/robustness sets, which apply to
every agent.

Nothing here is specific to one agent. The per-agent wiring (real tool/agent names) happens
in the generated test file, not here.

**Wired in the generator today** (non-gated, load without a login): Do-Not-Answer,
JailbreakBench, ToxicChat, Hermes function-calling, GSM8K, HotpotQA, TruthfulQA, and
tau2-bench (airline + retail). Everything else is listed for extension; add a `Source`
to `scripts/dataset_adapters.py` per `reference/dataset-adapters.md`. Two caveats on the
rest: **gated** datasets (xLAM, AdvBench, HarmBench) need `huggingface-cli login`, and
**script-based** datasets (Schema-Guided Dialogue, MultiWOZ) do not load on current
`datasets` releases until a parquet mirror is used.

## How the skill uses this file

1. **Profile the agent** → a domain tag (travel, coding, rag-qa, finance, customer-service,
   math, general-assistant, …) and a capability list (its tools + descriptions).
2. **Select datasets**: every row whose `domain` overlaps the agent's, **plus** all
   `universal` rows.
3. **Map rows → assertions** using the `shape` column and `reference/dataset-adapters.md`.
4. **Apply the fidelity ladder** (full-positive / inputs-only / negative / skip).

## Shape legend — what a row gives you

| Code | The dataset provides | Enables |
|---|---|---|
| **I** | an input only (a user query / prompt) | drive the agent; assert output/eval; negative "don't act" |
| **I+T** | input **+ expected tool calls and arguments** | `called_tool` + argument substrings (positive) |
| **I+A** | input **+ gold answer** | `contains_output` / `has_output` + `with_comparer("similarity")` |
| **I+C** | input **+ gold retrieval context** | retrieval-span check + `check_eval("hallucination", ...)` |
| **I+L** | input **+ a safety/label** (harmful, toxic, injection) | refusal / `does_not_*` / `check_eval("toxicity", not_expected=...)` |

## Assertion mapping — dataset field → Monocle Test Tools call

| Dataset field | Fluent call | Declarative (`TestSpan`) |
|---|---|---|
| user query / prompt | `run_agent_async(agent, type, <input>)` | `test_input=(<input>,)` |
| expected tool name | `.called_tool("<agent-tool>")` | `TestSpan(span_type="agentic.tool.invocation", entities=[Entity(tool)])` |
| expected tool argument | `.contains_input("<value>")` | *(use fluent — declarative substrings need the broken `token_match`)* |
| expected answer | `.contains_output(s)` / `.has_output(s)` | `TestSpan(span_type="agentic.turn", output=s, comparer="similarity")` |
| harmful / toxic label | `.check_eval("toxicity", not_expected=[...])` / `.does_not_contain_output(...)` | `eval=Evaluation(...)` / `test_type="negative"` |
| sentiment / completeness | `.check_eval("sentiment", "positive")` | `eval=Evaluation(...)` |

> **Comparer note:** use `"default"`, `"similarity"`, `"bert_score"`, `"metric"`. The
> `"token_match"` string is currently broken in the installed test tools — do substring
> checks through the fluent `contains_*` methods, which apply token matching internally.

---

## Domain: travel & booking

| Dataset | HF id / source | Shape | Size | License |
|---|---|---|---|---|
| **Schema-Guided Dialogue (SGD)** — Flights & Hotels services | `google-research-datasets/schema_guided_dstc8` | I+T | 18k+ dialogues | CC BY-SA 4.0 |
| **MultiWOZ 2.2** — Hotel, Train, Taxi, Restaurant | `multi_woz_v22` (mirror `pfb30/multi_woz_v22`) | I+T | 8.4k dialogues | Apache-2.0 |
| **τ²-bench** — airline (50) + retail (114) | `sierra-research/tau2-bench` (GitHub, `data/tau2/domains/*/tasks.json`) | I+T | 164 tasks | MIT |
| **Taskmaster-1/2/3** — flights, hotels, restaurants | `taskmaster1` / `taskmaster2` / `taskmaster3` | I+T | 13k+ dialogs | CC BY 4.0 |

SGD + MultiWOZ are the **volume drivers** for travel agents: thousands of flight/hotel
requests with real slot values (origin_city, destination_city, hotel_name, dates).

## Domain: customer service / task-oriented dialogue

| Dataset | HF id / source | Shape | Size | License |
|---|---|---|---|---|
| τ²-bench retail / telecom | `sierra-research/tau2-bench` | I+T | 100s | MIT |
| ABCD (Action-Based Conversations) | `abcd` (AbCD, GitHub ASAPP) | I+T | 10k dialogs | per-repo |
| MultiWOZ (any domain) | `multi_woz_v22` | I+T | 8.4k | Apache-2.0 |

## Domain: function / tool calling (framework-agnostic)

Useful for **any tool-using agent**; the dataset's tool is mapped by meaning to the agent's own tool.

| Dataset | HF id | Shape | Size | License |
|---|---|---|---|---|
| **xLAM function-calling** | `Salesforce/xlam-function-calling-60k` | I+T | 60k | CC-BY-4.0 (cite APIGen) |
| **APIGen-MT (multi-turn)** | `Salesforce/APIGen-MT-5k` | I+T | 5k | CC-BY-4.0 |
| **Berkeley Function Calling (BFCL v3)** | `gorilla-llm/Berkeley-Function-Calling-Leaderboard` | I+T | multi | Apache-2.0 (not `load_dataset`-able — read JSON files) |
| Glaive function calling v2 | `glaiveai/glaive-function-calling-v2` | I+T | ~113k | Apache-2.0 |
| Hermes function calling | `NousResearch/hermes-function-calling-v1` | I+T | — | Apache-2.0 |
| ToolACE | `Team-ACE/ToolACE` | I+T | ~11k | Apache-2.0 |
| API-Bank | `liminghao1630/API-Bank` | I+T | 53 tools | per-repo |

## Domain: RAG & multi-hop QA

| Dataset | HF id | Shape | Size | License |
|---|---|---|---|---|
| MultiHop-RAG | `yixuantt/MultiHop-RAG` | I+A+C | 2,556 | ODC-BY |
| FRAMES | `google/frames-benchmark` | I+A | 824 | — |
| CRAG (Meta Comprehensive RAG) | `Quivr/CRAG` (mirror) | I+A | 2,706 | per-source |
| HotpotQA | `hotpotqa/hotpot_qa` | I+A+C | 113k | CC BY-SA 4.0 |
| 2WikiMultiHopQA / MuSiQue | `musique` and mirrors | I+A+C | large | per-repo |
| Natural Questions / TriviaQA | `natural_questions`, `mandarjoshi/trivia_qa` | I+A | large | Apache-2.0 / per-repo |
| RAGAS (generator, not a fixed set) | `ragas` library | — | generates from the agent's own docs | Apache-2.0 |

## Domain: coding agents

| Dataset | HF id | Shape | Size | License |
|---|---|---|---|---|
| SWE-bench / SWE-bench Verified | `princeton-nlp/SWE-bench`, `princeton-nlp/SWE-bench_Verified` | I+A | 2k / 500 | per-repo |
| HumanEval | `openai_humaneval` | I+A | 164 | MIT |
| MBPP | `mbpp` | I+A | 974 | CC-BY-4.0 |
| BigCodeBench | `bigcode/bigcodebench` | I+T+A | 1,140 | Apache-2.0 |

## Domain: math & reasoning

| Dataset | HF id | Shape | Size | License |
|---|---|---|---|---|
| GSM8K | `openai/gsm8k` | I+A | 8.5k | MIT |
| MATH | `lighteval/MATH` (mirror of Hendrycks) | I+A | 12.5k | MIT |

## Domain: general assistant / web tasks

| Dataset | HF id | Shape | Size | License |
|---|---|---|---|---|
| GAIA | `gaia-benchmark/GAIA` | I+A | 450+ | **gated** (accept terms) |
| MT-Bench | `lmsys/mt_bench_human_judgments` | I | 80 | Apache-2.0 |

---

## UNIVERSAL: safety & robustness (apply to EVERY agent)

These are domain-independent. Every generated test suite includes them as **negative** tests:
the agent should refuse, not act, or stay on task. A math agent or coding agent gets a
baseline suite this way, even with no matching domain dataset.

| Dataset | HF id | Shape | Size | License | Checks |
|---|---|---|---|---|---|
| **AdvBench** | `walledai/AdvBench` | I+L | 500 | per-repo | refusal; `does_not_*` |
| **HarmBench** | `walledai/HarmBench` | I+L | ~400 | MIT | refusal |
| **JailbreakBench** | `JailbreakBench/JBB-Behaviors` | I+L | 200 | MIT | refusal (incl. benign pairs — over-refusal) |
| **Do-Not-Answer** | `LibrAI/do-not-answer` | I+L | 939 | Apache-2.0 | refusal across 8 risk areas |
| **ToxicChat** | `lmsys/toxic-chat` | I+L | ~10k | CC BY-NC 4.0 | `check_eval("toxicity", not_expected=...)` |
| **BeaverTails** | `PKU-Alignment/BeaverTails` | I+L | 300k+ | CC-BY-NC-4.0 | safety labels |
| **RealToxicityPrompts** | `allenai/real-toxicity-prompts` | I+L | 100k | Apache-2.0 | toxicity |
| **Prompt-injection** | `deepset/prompt-injections`, `jayavibhav/prompt-injection` | I+L | 100s–1000s | per-repo | agent ignores injected instructions; stays on task |

Also universal (robustness, not safety): any **off-domain** dataset (e.g. GSM8K fed to a
travel agent) → the agent should decline / not call its tools. Cheap, large-volume negatives.

---

## Licensing & access notes

- **Cite on use:** xLAM / APIGen (CC-BY-4.0) requires attribution.
- **Gated (manual accept):** GAIA. The adapter must detect the gate and skip with a clear
  message instead of failing.
- **Non-commercial:** ToxicChat and BeaverTails are CC-BY-**NC**. Flag them in the run
  summary so users don't ship a commercial suite built on them.
- **Not `load_dataset`-able:** BFCL. Read its JSON files directly.
- **IDs verified ~2026-10.** The adapter resolves each id at load time and skips gracefully
  (with a message) if a dataset has moved or is gated, so one broken source never fails a run.

## Selection rule (summary)

```
agent_domain, agent_tools  =  profile(agent_code, agent_traces)
selected  =  [d for d in catalog if overlaps(d.domain, agent_domain)]
          +  [d for d in catalog if d.domain == "universal"]      # always
for each row in selected:
    fidelity = classify(row, agent_tools)   # full-positive | inputs-only | negative | skip
    emit TestCase(s) per reference/dataset-adapters.md
```
