"""Load public datasets and normalize their rows into RawCase records.

Each Source maps one dataset to a stream of RawCase. The generator attaches the
agent and decides how each RawCase becomes a Monocle test, so adapters stay
agent-agnostic. Only non-gated, parquet-native datasets are wired here; more are
listed in reference/dataset-sources.md.
"""

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Iterator


@dataclass
class RawCase:
    input: str
    intent: str
    slots: list[str] = field(default_factory=list)
    answer: str | None = None


@dataclass
class Source:
    key: str
    domain: str
    license: str
    load: Callable[[int], Iterator[RawCase]]


def _hf_rows(hf_id, split, limit, config=None, shuffle=False):
    from datasets import load_dataset

    stream = load_dataset(hf_id, config, split=split, streaming=True)
    if shuffle:  # the first rows of a dataset are often one category (Do-Not-Answer: one risk area)
        stream = stream.shuffle(seed=7, buffer_size=2000)
    for index, row in enumerate(stream):
        if index >= limit:
            return
        yield row


SCAN_FACTOR = 50


def _flat(
    hf_id, split, intent, config=None, text_key="prompt", answer_key=None, answer_fn=None, keep=None, shuffle=False
):
    def load(limit):
        kept = 0
        for row in _hf_rows(hf_id, split, limit * SCAN_FACTOR if keep else limit, config, shuffle):
            if kept >= limit:
                return
            if keep and not keep(row):
                continue
            text = row.get(text_key)
            if not text:
                continue
            kept += 1
            answer = None
            if answer_key and row.get(answer_key) is not None:
                answer = str(row[answer_key]).strip()
                if answer_fn:
                    answer = answer_fn(answer)
            yield RawCase(str(text).strip(), intent, [], answer)

    return load


def _hermes(limit):
    for row in _hf_rows("NousResearch/hermes-function-calling-v1", "train", limit, "func_calling_singleturn"):
        text = next((turn.get("value") for turn in row.get("conversations") or [] if turn.get("from") == "human"), None)
        if text:
            yield RawCase(str(text).strip(), "tool_call")


def _ssl_context():
    try:
        import ssl

        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


def _tau2(domain_name):
    url = (
        f"https://raw.githubusercontent.com/sierra-research/tau2-bench/main/data/tau2/domains/{domain_name}/tasks.json"
    )

    def load(limit):
        with urllib.request.urlopen(url, timeout=30, context=_ssl_context()) as response:
            tasks = json.loads(response.read())
        for task in tasks[:limit]:
            instructions = (task.get("user_scenario") or {}).get("instructions") or {}
            reason = (instructions.get("reason_for_call") or "").strip().splitlines()
            text = next((line.strip() for line in reason if line.strip()), "")
            if not text:
                continue
            actions = [action.get("name", "") for action in (task.get("evaluation_criteria") or {}).get("actions", [])]
            intent = (
                "book_flight" if domain_name == "airline" and any("book" in name for name in actions) else "offtopic"
            )
            yield RawCase(text, intent)

    return load


SOURCES: list[Source] = [
    Source(
        "do-not-answer", "safety", "Apache-2.0", _flat("LibrAI/do-not-answer", "train", "harmful", text_key="question", shuffle=True)
    ),
    Source(
        "jailbreakbench",
        "safety",
        "MIT",
        _flat("JailbreakBench/JBB-Behaviors", "harmful", "harmful", config="behaviors", text_key="Goal", shuffle=True),
    ),
    Source(
        "toxic-chat",
        "safety",
        "CC-BY-NC-4.0",
        _flat(
            "lmsys/toxic-chat",
            "train",
            "harmful",
            config="toxicchat0124",
            text_key="user_input",
            keep=lambda row: row.get("toxicity") == 1,
        ),
    ),
    Source("hermes-fc", "tools", "Apache-2.0", _hermes),
    Source(
        "gsm8k",
        "math",
        "MIT",
        _flat(
            "openai/gsm8k",
            "test",
            "math",
            config="main",
            text_key="question",
            answer_key="answer",
            answer_fn=lambda value: value.split("####")[-1].strip(),
        ),
    ),
    Source(
        "hotpotqa",
        "qa",
        "CC-BY-SA-4.0",
        _flat("hotpotqa/hotpot_qa", "validation", "qa", config="distractor", text_key="question", answer_key="answer"),
    ),
    Source(
        "truthfulqa",
        "qa",
        "Apache-2.0",
        _flat(
            "truthfulqa/truthful_qa",
            "validation",
            "qa",
            config="generation",
            text_key="question",
            answer_key="best_answer",
        ),
    ),
    Source("tau2-airline", "travel", "MIT", _tau2("airline")),
    Source("tau2-retail", "retail", "MIT", _tau2("retail")),
]

SOURCES_BY_KEY = {source.key: source for source in SOURCES}
