"""Load public datasets and normalize their rows into RawCase records.

Each Source maps one dataset to a stream of RawCase. The generator attaches the
agent and decides how each RawCase becomes a Monocle test, so adapters stay
agent-agnostic. Only non-gated, parquet-native datasets are wired here; more are
listed in reference/dataset-sources.md.
"""
import json
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Optional


@dataclass
class RawCase:
    input: str
    intent: str
    slots: List[str] = field(default_factory=list)
    answer: Optional[str] = None


@dataclass
class Source:
    key: str
    domain: str
    license: str
    load: Callable[[int], Iterator[RawCase]]


def _hf_rows(hf_id, split, limit, config=None):
    from datasets import load_dataset

    stream = load_dataset(hf_id, config, split=split, streaming=True)
    for index, row in enumerate(stream):
        if index >= limit:
            return
        yield row


def _flat(hf_id, split, intent, config=None, text_key="prompt", answer_key=None, answer_fn=None):
    def load(limit):
        for row in _hf_rows(hf_id, split, limit, config):
            text = row.get(text_key)
            if not text:
                continue
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
        import certifi
        import ssl

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


def _tau2(domain_name):
    url = (
        "https://raw.githubusercontent.com/sierra-research/tau2-bench/main/"
        f"data/tau2/domains/{domain_name}/tasks.json"
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
            intent = "book_flight" if domain_name == "airline" and any("book" in name for name in actions) else "offtopic"
            yield RawCase(text, intent)

    return load


SOURCES: List[Source] = [
    Source("do-not-answer", "safety", "Apache-2.0", _flat("LibrAI/do-not-answer", "train", "harmful", text_key="question")),
    Source("jailbreakbench", "safety", "MIT", _flat("JailbreakBench/JBB-Behaviors", "harmful", "harmful", config="behaviors", text_key="Goal")),
    Source("toxic-chat", "safety", "CC-BY-NC-4.0", _flat("lmsys/toxic-chat", "train", "harmful", config="toxicchat0124", text_key="user_input")),
    Source("hermes-fc", "tools", "Apache-2.0", _hermes),
    Source("gsm8k", "math", "MIT", _flat("openai/gsm8k", "test", "math", config="main", text_key="question", answer_key="answer", answer_fn=lambda value: value.split("####")[-1].strip())),
    Source("hotpotqa", "qa", "CC-BY-SA-4.0", _flat("hotpotqa/hotpot_qa", "validation", "qa", config="distractor", text_key="question", answer_key="answer")),
    Source("truthfulqa", "qa", "Apache-2.0", _flat("truthfulqa/truthful_qa", "validation", "qa", config="generation", text_key="question", answer_key="best_answer")),
    Source("tau2-airline", "travel", "MIT", _tau2("airline")),
    Source("tau2-retail", "travel", "MIT", _tau2("retail")),
]

SOURCES_BY_KEY = {source.key: source for source in SOURCES}
