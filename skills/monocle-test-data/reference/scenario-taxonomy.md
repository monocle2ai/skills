# Scenario taxonomy

Derive scenario types from **capabilities × rules × failure modes**, not from a fixed list. This
taxonomy is a checklist to make sure nothing obvious is missed. For each type: how to find it in
the app, and what the expected behaviour usually looks like.

| Type | Find it from | Expected (typical) | Fidelity |
|---|---|---|---|
| Happy path | Each capability (each write tool, each main read) | The right tools, right arguments, right end state | positive |
| Combined request | Two capabilities in one message | Both done, in a sensible order; nothing extra. Models often emit both tool calls at once; apps that route one crash | positive |
| Instruction-following | Tools the prompt says to use for a kind of question ("search company policies") | The tool is consulted — put this in `expect_soft`; the answer's facts go in `expect` | positive |
| Partial request | A capability the agent could over-apply ("only a flight") | The unrequested tool is **not** called | positive |
| Rule | Each rule in instructions, policies, code checks | Behaviour the rule demands, including refusals | positive |
| Rule boundary | Numeric/date limits in rules ("24 hours", "max 3") | Just inside → allowed; just outside → refused | positive |
| Choice by data | Requests that need the world to decide ("cheapest", "next available") | The id the oracle computes | positive |
| Planted obstacle | What the world can make impossible (full, cancelled, missing) | The agent notices and does not proceed blindly | positive |
| Missing detail | Arguments the agent needs but the user did not give | The agent asks (simulated mode: hold the detail back with `is_initial: false`) | positive |
| Ambiguity | Requests that match several records | The agent asks which one, or picks by a stated rule | positive or spec question |
| Wrong premise | The user asserts something the world contradicts ("my flight tomorrow" when none exists) | The agent corrects, does not act on the premise | positive |
| Tool failure | Each side-effecting tool erroring or returning empty | No claim of success; a clear message | positive |
| Out of scope | Neighbouring requests the agent should decline | No tool called; polite decline | negative |
| Safety / off-domain | Public datasets (`scripts/gen_dataset_negatives.py`) | No tool called | negative |
| Adversarial | Instructions to ignore rules, act for another user, reveal the prompt | Rules still hold; no cross-user data | negative |
| Live / external | Tools backed by live services | Invariants only | invariant |

## Counts

Start with roughly: every rule × 2–3 cases, every capability × 3–5 cases, every planted obstacle × 3,
plus 30–70 generic negatives. Fewer good cases beat many weak ones; the coverage report should make
gaps visible rather than hide them behind volume.

## Personas and styles

Vary how the user writes independently of what they ask: plain, casual, terse, verbose, typos,
another language, relative dates ("next Friday"). For simulated runs, map styles to Monocle
personas, for example:

- plain → "An experienced user who has read the docs. Writes complete, precise sentences, names
  things correctly, and states every detail up front."
- casual → "A first-time user who has not read anything. Casual, lowercase, thinks out loud, and
  confidently assumes the agent can do things it may not be able to do."
- terse → "Answers in as few words as possible, gives exactly one detail at a time, and never
  elaborates unless asked."
