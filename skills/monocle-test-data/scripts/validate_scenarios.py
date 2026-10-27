"""Validate a scenario file: Monocle's required fields plus ours.

    python validate_scenarios.py <app>_scenarios.json [--app-root DIR] [--strict]

Checks what Monocle's loader enforces (non-empty scenario/persona/target_description, param
names are identifiers, at least one initial param, unique test names, max_turns >= 1) and our
contract (verbatim cases have input, expect shape, fidelity values, world fixtures exist, the file
is not named scenarios.json). If monocle_test_tools with scenario support is installed, the file is
also loaded with Monocle's own loader. Exit code 1 on any error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
FIDELITY = {"positive", "negative", "invariant"}
SEAMS = {"config", "file_swap", "mock_tools", "patch", None}
MOCK_TYPES = {"tool.adk", "tool.openai", "tool.llama_index", "tool.langgraph", "tool.strands"}
LIST_KEYS = ("tools_called", "tools_not_called", "output_contains", "output_contains_any",
             "output_not_contains", "retrieval_contains", "end_state", "custom")
CHECK_KEYS = LIST_KEYS + ("max_sentences", "judge_only")


def check_block(block: dict, where: str, errors: list[str]) -> None:
    """Validate one expect / expect_soft object against the documented check keys."""
    for key in block:
        if key not in CHECK_KEYS:
            errors.append(f"{where}: unknown check key {key!r}; use a documented key or expect.custom")
    for key in LIST_KEYS:
        if key in block and not isinstance(block[key], list):
            errors.append(f"{where}.{key} must be a list")
    for t in block.get("tools_called", []) or []:
        if not isinstance(t, dict) or not t.get("name"):
            errors.append(f"{where}.tools_called entries need a name")
    for q in block.get("end_state", []) or []:
        if not isinstance(q, dict) or "query" not in q or "expect" not in q:
            errors.append(f"{where}.end_state entries need query and expect")
    for c in block.get("custom", []) or []:
        if not isinstance(c, dict) or not str(c.get("description", "")).strip():
            errors.append(f"{where}.custom entries need a description")
    if "max_sentences" in block and not (isinstance(block["max_sentences"], int) and block["max_sentences"] > 0):
        errors.append(f"{where}.max_sentences must be a positive integer")
    if "judge_only" in block and block["judge_only"] is not True:
        errors.append(f"{where}.judge_only must be true when present")


def check(path: Path, app_root: Path | None) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    if path.name == "scenarios.json":
        errors.append("file is named scenarios.json, Monocle's seed cache name; rename it")
    data = json.loads(path.read_text())
    entries = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return ['top level must be {"scenarios": [non-empty list]}'], warnings, {}

    names = Counter(e.get("test_name") for e in entries)
    errors += [f"duplicate test_name {n!r} ({c}x)" for n, c in names.items() if c > 1]
    root = app_root or path.parent
    stats = Counter()
    for i, e in enumerate(entries):
        where = f"#{i} {e.get('test_name')!r}"
        for field in ("test_name", "scenario", "persona", "target_description"):
            if not isinstance(e.get(field), str) or not e[field].strip():
                errors.append(f"{where}: {field} must be a non-empty string")
        if not isinstance(e.get("max_turns", 10), int) or e.get("max_turns", 10) < 1:
            errors.append(f"{where}: max_turns must be an integer >= 1")
        params = e.get("params", [])
        if not isinstance(params, list):
            errors.append(f"{where}: params must be a list")
            params = []
        for p in params:
            if not IDENT.fullmatch(str(p.get("name", ""))):
                errors.append(f"{where}: param name {p.get('name')!r} is not a Python identifier")
            if "description" not in p or "value" not in p:
                errors.append(f"{where}: param {p.get('name')!r} needs value and description")
        if params and not any(p.get("is_initial") for p in params):
            errors.append(f"{where}: at least one param must have is_initial=true")
        pnames = [p.get("name") for p in params]
        if len(pnames) != len(set(pnames)):
            errors.append(f"{where}: duplicate param names")

        if e.get("verbatim_required") and not (isinstance(e.get("input"), str) and e["input"].strip()):
            errors.append(f"{where}: verbatim_required but no input")
        if not e.get("input"):
            warnings.append(f"{where}: no input; verbatim mode cannot run it")
        if e.get("fidelity") not in FIDELITY:
            errors.append(f"{where}: fidelity must be one of {sorted(FIDELITY)}")
        expect = e.get("expect")
        if not isinstance(expect, dict):
            errors.append(f"{where}: expect must be an object")
        else:
            check_block(expect, f"{where}: expect", errors)
            if not any(expect.get(k) for k in CHECK_KEYS):
                warnings.append(f"{where}: expect has no checks")
        soft = e.get("expect_soft")
        if soft is not None:
            if not isinstance(soft, dict):
                errors.append(f"{where}: expect_soft must be an object")
            else:
                check_block(soft, f"{where}: expect_soft", errors)
        for m in e.get("mock_tools") or []:
            if not m.get("name") or m.get("type") not in MOCK_TYPES or "response" not in m:
                errors.append(f"{where}: mock_tools entries need name, response and type in {sorted(MOCK_TYPES)}")
        world = e.get("world")
        if world:
            if world.get("seam") not in SEAMS:
                errors.append(f"{where}: world.seam must be one of {sorted(s for s in SEAMS if s)}")
            for key in ("base", "fixture"):
                if world.get(key) and not (root / world[key]).exists():
                    errors.append(f"{where}: world.{key} not found: {world[key]}")
        stats[(e.get("scenario_type"), e.get("fidelity"))] += 1
    return errors, warnings, stats


def monocle_load(path: Path) -> str:
    try:
        from monocle_test_tools.scenarios.scenario import scenarios_from
    except ImportError:
        return "monocle_test_tools with scenario support not installed; skipped Monocle loader check"
    scenarios_from(path.name, str(path.parent))
    return "loaded with Monocle's scenarios_from"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file")
    parser.add_argument("--app-root", help="Directory that world paths are relative to (default: the file's directory)")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()
    path = Path(args.file)
    errors, warnings, stats = check(path, Path(args.app_root) if args.app_root else None)
    try:
        note = monocle_load(path) if not errors else "skipped Monocle loader (errors above)"
    except Exception as error:  # Monocle's loader rejected the file
        errors.append(f"Monocle loader: {error}")
        note = "Monocle loader failed"
    for w in warnings[:20]:
        print("WARN ", w)
    if len(warnings) > 20:
        print(f"WARN  ... {len(warnings) - 20} more")
    for e in errors:
        print("ERROR", e)
    total = sum(stats.values())
    print(f"\n{total} scenarios; {len(errors)} errors; {len(warnings)} warnings; {note}")
    for (stype, fid), n in sorted(stats.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        print(f"  {n:4}  {stype}  [{fid}]")
    sys.exit(1 if errors or (args.strict and warnings) else 0)


if __name__ == "__main__":
    main()
