"""Generate a parametrized Monocle test file from public datasets.

Reads an agent profile, selects matching datasets plus the universal safety and
tool-calling sets, turns their rows into test cases, and writes a cases file and
a driver. It never runs the agent; running the emitted pytest file does.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dataset_adapters import SOURCES

UNIVERSAL = {"safety", "tools"}
NON_COMMERCIAL = ("NC",)

DRIVER = '''import importlib
import inspect
import json
import pathlib
import pytest
import pytest_asyncio
from monocle_test_tools import TraceAssertion

_DATA = json.loads(pathlib.Path(__file__).with_name("monocle_dataset_cases.json").read_text())
_META = _DATA["meta"]
CASES = _DATA["cases"]


@pytest_asyncio.fixture(scope="session")
async def agent():
    module = importlib.import_module(_META["agent_import"])
    if _META.get("agent_factory"):
        result = getattr(module, _META["agent_factory"])(*_META.get("factory_args", []))
        return await result if inspect.isawaitable(result) else result
    return getattr(module, _META["agent_object"])


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
async def test_dataset(monocle_trace_asserter: TraceAssertion, agent, case):
    await monocle_trace_asserter.run_agent_async(agent, _META["agent_type"], case["input"])
    for tool in case.get("called_tools", []):
        asserter = monocle_trace_asserter.called_tool(tool["name"])
        for value in tool.get("inputs", []):
            asserter.contains_input(value)
    for name in case.get("not_called_tools", []):
        monocle_trace_asserter.does_not_call_tool(name)
    for value in case.get("outputs", []):
        monocle_trace_asserter.contains_output(value)
'''


def selected_sources(domains):
    return [source for source in SOURCES if source.domain in domains or source.domain in UNIVERSAL]


def classify(case, source, tools, domains):
    base = {"input": case.input, "source": source.key, "license": source.license}
    tool = tools.get(case.intent)
    if tool:
        base.update(fidelity="positive", called_tools=[{"name": tool, "inputs": case.slots[:3]}])
        return base
    if case.intent in ("harmful", "offtopic"):
        if not tools:
            return None
        base.update(fidelity="negative", not_called_tools=list(tools.values()))
        return base
    if case.answer and source.domain in domains and source.domain in ("qa", "math"):
        base.update(fidelity="inputs_only", outputs=[case.answer])
        return base
    if source.domain not in domains:
        if not tools:
            return None
        base.update(fidelity="negative", not_called_tools=list(tools.values()))
        return base
    return None


def build(profile, limit_per_source, max_cases):
    domains = set(profile["domain"])
    tools = profile.get("tools", {})
    cases, counts, skipped = [], {}, {}
    for source in selected_sources(domains):
        if max_cases and len(cases) >= max_cases:
            break
        try:
            for raw in source.load(limit_per_source):
                case = classify(raw, source, tools, domains)
                if not case:
                    continue
                case["id"] = f"{source.key}-{counts.get(source.key, 0)}"
                cases.append(case)
                counts[source.key] = counts.get(source.key, 0) + 1
                if max_cases and len(cases) >= max_cases:
                    break
        except Exception as error:
            skipped[source.key] = str(error).splitlines()[0][:120]
    return cases, counts, skipped


def write_outputs(out_dir, profile, cases):
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {key: profile[key] for key in ("agent_import", "agent_type") if key in profile}
    for key in ("agent_object", "agent_factory", "factory_args"):
        if key in profile:
            meta[key] = profile[key]
    (out_dir / "monocle_dataset_cases.json").write_text(json.dumps({"meta": meta, "cases": cases}, indent=2))
    (out_dir / "test_monocle_dataset.py").write_text(DRIVER)


def summarize(cases, counts, skipped, out_dir):
    fidelity = {}
    licenses = set()
    for case in cases:
        fidelity[case["fidelity"]] = fidelity.get(case["fidelity"], 0) + 1
        licenses.add(case["license"])
    print(f"\nGenerated {len(cases)} cases into {out_dir}/")
    print("\nBy source:")
    for key, count in sorted(counts.items(), key=lambda item: -item[1]):
        print(f"  {key:16} {count}")
    print("\nBy fidelity:")
    for key, count in sorted(fidelity.items()):
        print(f"  {key:12} {count}")
    if skipped:
        print("\nSkipped (install `datasets`, or source gated/moved):")
        for key, reason in skipped.items():
            print(f"  {key:16} {reason}")
    flagged = [name for name in licenses if any(tag in name for tag in NON_COMMERCIAL)]
    if flagged:
        print(f"\nNon-commercial sources used: {', '.join(flagged)} — do not ship a commercial suite on these.")
    print("\nNothing was run. Each case is a live agent call when you run:")
    print(f"  pytest {out_dir}/test_monocle_dataset.py -v")


def main():
    parser = argparse.ArgumentParser(description="Generate Monocle tests from public datasets.")
    parser.add_argument("profile", help="Path to the agent profile JSON.")
    parser.add_argument("--out", help="Output directory (default: alongside the profile).")
    parser.add_argument("--limit-per-source", type=int, default=100, help="Max rows pulled per dataset.")
    parser.add_argument("--max-cases", type=int, default=None, help="Cap total generated cases.")
    parser.add_argument("--list", action="store_true", help="List selected datasets and exit.")
    args = parser.parse_args()

    profile = json.loads(pathlib.Path(args.profile).read_text())
    if args.list:
        for source in selected_sources(set(profile["domain"])):
            print(f"{source.key:16} {source.domain:8} {source.license}")
        return

    out_dir = pathlib.Path(args.out) if args.out else pathlib.Path(args.profile).resolve().parent
    cases, counts, skipped = build(profile, args.limit_per_source, args.max_cases)
    write_outputs(out_dir, profile, cases)
    summarize(cases, counts, skipped, out_dir)


if __name__ == "__main__":
    main()
