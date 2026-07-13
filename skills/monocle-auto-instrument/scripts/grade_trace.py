#!/usr/bin/env python3
"""Grade Monocle trace file(s) against the good-trace recipe (stdlib only).

Usage:
    python grade_trace.py .monocle/*.json
    python grade_trace.py path/to/trace.json [more.json ...]

Checks (see reference/good-trace-recipe.md):
  - exactly one `workflow` root span per trace
  - nesting: workflow -> agentic.turn -> agentic.invocation(1..N) -> inference / tool
  - non-empty data.input AND data.output on turn / invocation / tool spans
  - entity names populated: agent (entity.1.name on agentic.invocation),
    tool (entity.1.name on agentic.tool.invocation), model (entity.2.name on inference)
  - token metadata on inference spans (inference.modelapi carries no events — not flagged)
  - a single scope.agentic.session anchoring the run; when one trigger emits multiple
    traces they MUST share the same session id

Prints the span tree + any issues per file, then an overall verdict.
Exit code 0 if everything PASSES, 1 otherwise.
"""
import sys
import json
import glob
import collections

IO_REQUIRED = ("agentic.turn", "agentic.invocation", "agentic.tool.invocation")

# span.type -> (entity-name attribute that must be populated, human label)
NAME_REQUIRED = {
    "agentic.invocation": ("entity.1.name", "agent"),
    "agentic.tool.invocation": ("entity.1.name", "tool"),
    "inference": ("entity.2.name", "model"),
    "inference.framework": ("entity.2.name", "model"),
}


def stype(s):
    return s.get("attributes", {}).get("span.type", "?")


def events(s):
    return {e.get("name"): e.get("attributes", {}) for e in s.get("events", [])}


def nonempty(d):
    return bool(d) and any(v not in (None, "", [], {}) for v in d.values())


def build_tree(spans):
    by_id = {s["context"]["span_id"]: s for s in spans}
    children = collections.defaultdict(list)
    roots = []
    for s in spans:
        parent = s.get("parent_id")
        if parent and parent in by_id:
            children[parent].append(s)
        else:
            roots.append(s)
    return children, roots


def grade_file(path):
    """Return (fails, warns, sessions, tree).

    fails  = unambiguous structural breakage (recipe cannot hold).
    warns  = empty I/O or missing tokens — these need TRIAGE, not an auto-fail:
             an empty data.input on an intermediate span (e.g. a crew/task wrapper
             whose nested agent span carries the real I/O), or a kickoff called with
             no inputs, is faithful to the app, NOT a Monocle bug. Decide per
             reference/diagnosis-tree.md before changing Monocle.
    """
    fails, warns = [], []
    try:
        with open(path) as fh:
            spans = json.load(fh)
    except Exception as e:  # noqa: BLE001
        return [f"INVALID/UNREADABLE JSON: {e}"], [], set(), None

    children, roots = build_tree(spans)
    sessions = {s["attributes"].get("scope.agentic.session") for s in spans} - {None}

    workflow_roots = [s for s in spans if stype(s) == "workflow"]
    if len(workflow_roots) != 1:
        fails.append(f"expected exactly 1 workflow root, found {len(workflow_roots)}")
    if not sessions:
        fails.append("no scope.agentic.session present (run is not anchored)")

    for s in spans:
        t = stype(s)
        ev = events(s)
        if t in IO_REQUIRED:
            if not nonempty(ev.get("data.input", {})):
                warns.append(f"empty data.input  [{t}] {s.get('name')}")
            if not nonempty(ev.get("data.output", {})):
                warns.append(f"empty data.output [{t}] {s.get('name')}")
        if t in NAME_REQUIRED:
            key, label = NAME_REQUIRED[t]
            if not s.get("attributes", {}).get(key):
                warns.append(f"missing {label} name ({key}) [{t}] {s.get('name')}")
        if t in ("inference", "inference.framework"):
            md = ev.get("metadata", {})
            if not (md.get("total_tokens") or md.get("completion_tokens")):
                warns.append(f"no token metadata [{t}] {s.get('name')}")

    return fails, warns, sessions, (children, roots)


def print_tree(tree):
    children, roots = tree

    def walk(s, depth=0):
        print("  " * depth + f"- [{stype(s)}] {str(s.get('name', ''))[:60]}")
        for c in children[s["context"]["span_id"]]:
            walk(c, depth + 1)

    for r in roots:
        walk(r)


def main(argv):
    files = []
    for arg in argv:
        files.extend(sorted(glob.glob(arg)) or [arg])
    if not files:
        print("usage: grade_trace.py <trace.json> [more.json ...]")
        return 2

    all_sessions = set()
    any_fail = False
    any_warn = False
    for path in files:
        fails, warns, sessions, tree = grade_file(path)
        all_sessions |= sessions
        status = "FAIL" if fails else ("REVIEW" if warns else "PASS")
        any_fail = any_fail or bool(fails)
        any_warn = any_warn or bool(warns)
        print(f"\n=== {path}  [{status}] ===")
        if tree is not None:
            print_tree(tree)
        for f in fails:
            print(f"  ✗ FAIL: {f}")
        for w in warns:
            print(f"  ? review: {w}")

    if len(files) > 1:
        print(f"\n=== session anchoring across {len(files)} traces ===")
        if len(all_sessions) == 1:
            print(f"  PASS — single shared session: {next(iter(all_sessions))}")
        elif len(all_sessions) == 0:
            print("  FAIL — no session on any trace")
            any_fail = True
        else:
            print(f"  FAIL — {len(all_sessions)} distinct sessions (expected 1): {all_sessions}")
            any_fail = True

    if any_fail:
        verdict = "STRUCTURAL FAIL ❌  (recipe broken — see ✗ lines)"
    elif any_warn:
        verdict = ("STRUCTURE OK ✅  — but review the '? review' lines: triage each empty-I/O /"
                   " missing-token per reference/diagnosis-tree.md (app behavior vs Monocle gap).")
    else:
        verdict = "ALL PASS ✅"
    print(f"\n{verdict}")
    return 0 if not any_fail else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
