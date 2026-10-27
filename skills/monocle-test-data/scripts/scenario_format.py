"""Helpers to build and write a scenario file (Monocle's format plus our fields).

    from scenario_format import param, scenario, write_scenarios

See reference/scenario-format.md for every field.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PERSONAS = {
    "plain": (
        "An experienced user who has read the docs. Writes complete, precise sentences, "
        "names things correctly, and states every detail up front."
    ),
    "casual": (
        "A first-time user who has not read anything. Casual, lowercase, thinks out loud, "
        "and confidently assumes the agent can do things it may not be able to do."
    ),
    "terse": (
        "Answers in as few words as possible, gives exactly one detail at a time, and never elaborates unless asked."
    ),
}
VERBATIM_PERSONA = "A user who sends exactly one message and nothing else."


def param(name: str, value: Any, description: str, is_initial: bool = True, required: bool = True) -> dict:
    """One detail of the request. ``is_initial=False`` holds it back until the agent asks."""
    return {"name": name, "value": value, "description": description, "is_initial": is_initial, "required": required}


def scenario(
    *,
    test_name: str,
    scenario_text: str,
    persona: str,
    target_description: str,
    input_text: str,
    expect: dict,
    scenario_type: str,
    params: list[dict] | None = None,
    success_criteria: str | None = None,
    max_turns: int = 6,
    verbatim_required: bool = False,
    mock_tools: list[dict] | None = None,
    world: dict | None = None,
    source: str = "synthetic",
    fidelity: str = "positive",
    license: str | None = None,
    facts: dict | None = None,
    spec_question: str | None = None,
    expect_soft: dict | None = None,
    blocked_by: str | None = None,
) -> dict:
    """Build one entry with Monocle's fields first, then ours."""
    return {
        "test_name": test_name,
        "scenario": scenario_text,
        "persona": persona,
        "params": params or [],
        "success_criteria": success_criteria,
        "max_turns": max_turns,
        "target_description": target_description,
        "input": input_text,
        "verbatim_required": verbatim_required,
        "expect": expect,
        "expect_soft": expect_soft,
        "mock_tools": mock_tools or [],
        "world": world,
        "scenario_type": scenario_type,
        "source": source,
        "fidelity": fidelity,
        "license": license,
        "facts": facts or {},
        "spec_question": spec_question,
        "blocked_by": blocked_by,
    }


def file_hash(path: str | Path) -> str:
    """sha256 of a world file, to pin scenarios to the world they were computed against."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def write_scenarios(path: str | Path, scenarios: list[dict]) -> None:
    """Write ``{"scenarios": [...]}``; refuses duplicate test names and the reserved file name."""
    path = Path(path)
    if path.name == "scenarios.json":
        raise ValueError("scenarios.json is Monocle's seed cache name; use <app_name>_scenarios.json")
    names = [s["test_name"] for s in scenarios]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ValueError(f"duplicate test_name: {duplicates}")
    path.write_text(json.dumps({"scenarios": scenarios}, indent=2, default=str) + "\n")
