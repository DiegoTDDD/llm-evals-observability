"""Write the README's live-run section from the files a live run committed.

    python scripts/readme_live.py RUN_ID [--date YYYY-MM-DD] [--sec-ref SHA] [--fraud-ref SHA]

Reads reports/live/metrics.json, reports/live/langfuse-*.json and the projects' results.json,
appends the run to reports/live/history.jsonl (once per run id), and replaces the block between
<!-- LIVE:START --> and <!-- LIVE:END --> in README.md. Nothing outside the markers changes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalobs.gate import evaluate, passed  # noqa: E402

START, END = "<!-- LIVE:START -->", "<!-- LIVE:END -->"
REPO = "https://github.com/DiegoTDDD/llm-evals-observability"
SEC, FRAUD = "sec-mcp-agent", "fraud-investigation-agents"


def pct(x: float | None) -> str:
    return "no result" if x is None else f"{x:.0%}"


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def run_entry(live: Path, run_id: str, date: str, refs: dict[str, str]) -> dict:
    """The headline numbers of one run and the project versions it ran, for history.jsonl."""
    sec = load(live / SEC / "results.json")
    metrics = load(live / "metrics.json") or {}
    fraud = metrics.get("fraud_agents", {})
    entry: dict = {"run": run_id, "date": date, **{k: v[:7] for k, v in refs.items() if v}}
    if sec is not None:
        entry["sec_passed"] = sec["summary"]["passed"]
        entry["sec_questions"] = sec["summary"]["questions"]
    for key, name in [
        ("graph_pattern", "graph_pattern_accuracy"),
        ("single_pattern", "single_agent_pattern_accuracy"),
        ("rules_pattern", "rules_pattern_accuracy"),
    ]:
        if name in fraud:
            entry[key] = fraud[name]
    return entry


def append_history(history: Path, entry: dict) -> list[dict]:
    """Add the run unless it is already there (a rerun of the publish job); return all runs."""
    text = history.read_text(encoding="utf-8") if history.exists() else ""
    runs = [json.loads(line) for line in text.splitlines() if line]
    runs = [r for r in runs if r["run"] != entry["run"]] + [entry]
    history.write_text("".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    return runs


def ref_link(project: str, ref: str | None) -> str:
    return f"[{ref}](https://github.com/DiegoTDDD/{project}/commit/{ref})" if ref else "n/a"


def gate_cell(metrics: dict, baseline: dict, prefix: str) -> str:
    checks = evaluate(metrics, {k: v for k, v in baseline.items() if k.startswith(prefix)})
    return "✅" if passed(checks) else "❌"


def langfuse_cells(live: Path, service: str) -> tuple[str, str]:
    lf = load(live / f"langfuse-{service}.json")
    if lf is None:
        return "no result", "no result"
    t = lf.get("by_type", {})
    return (
        f"{lf['traces']} traces, {lf['observations']} observations",
        f"{t.get('GENERATION', 0)} generations, {t.get('TOOL', 0)} tool calls, "
        f"{t.get('SPAN', 0)} spans",
    )


def render(live: Path, baseline: dict, runs: list[dict], model: str) -> str:
    metrics = load(live / "metrics.json") or {}
    now = runs[-1]
    fraud = metrics.get("fraud_agents")
    sec_cell = (
        f"{now['sec_passed']} of {now['sec_questions']} questions passed"
        if "sec_passed" in now
        else "no result"
    )
    fraud_cell = (
        f"graph {pct(fraud['graph_pattern_accuracy'])} pattern accuracy "
        f"(single agent {pct(fraud['single_agent_pattern_accuracy'])}, "
        f"rules {pct(fraud['rules_pattern_accuracy'])})"
        if fraud
        else "no result"
    )
    sec_lf, fraud_lf = langfuse_cells(live, SEC), langfuse_cells(live, FRAUD)
    lines = [
        "**Dashboard: [diegotddd.github.io/llm-evals-observability]"
        "(https://diegotddd.github.io/llm-evals-observability/)**",
        "(latency, tokens and errors per run, per LLM step and per MCP tool, and the exact "
        "arguments of",
        "every failed tool call), rebuilt by every live run. This section is written by the same "
        "run ([`scripts/readme_live.py`](scripts/readme_live.py)).",
        "",
        f"Latest live run [{now['run']}]({REPO}/actions/runs/{now['run']}) ({now['date']}), "
        f"{model} on CPU-only runners, both projects' own eval scripts run unchanged under the "
        "tracer:",
        "",
        f"| | {SEC} | {FRAUD} |",
        "| --- | --- | --- |",
        f"| End-to-end | {sec_cell} | {fraud_cell} |",
        f"| Traces in Langfuse (read back through its API) | {sec_lf[0]} | {fraud_lf[0]} |",
        f"| Observation types | {sec_lf[1]} | {fraud_lf[1]} |",
        "| Live gate ([`baselines/live.json`](baselines/live.json)) | "
        f"{gate_cell(metrics, baseline, 'sec_mcp_agent.')} | "
        f"{gate_cell(metrics, baseline, 'fraud_agents.')} |",
        "",
        "Every live run, model at temperature 0. Rows with the same project version differ only "
        "by the model's run-to-run variance, which sets the live gate's tolerances "
        "([docs/regressions.md](docs/regressions.md#note--run-to-run-variance-is-real-so-the-live-gate-has-tolerances)):",
        "",
        f"| Run | Date | {SEC} version | Questions passed | {FRAUD} version | "
        "Graph: pattern accuracy | Single agent | Rules |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in runs:
        sec = f"{r['sec_passed']}/{r['sec_questions']}" if "sec_passed" in r else "no result"
        lines.append(
            f"| [{r['run']}]({REPO}/actions/runs/{r['run']}) | {r['date']} | "
            f"{ref_link(SEC, r.get('sec_ref'))} | {sec} | {ref_link(FRAUD, r.get('fraud_ref'))} | "
            f"{pct(r.get('graph_pattern'))} | {pct(r.get('single_pattern'))} | "
            f"{pct(r.get('rules_pattern'))} |"
        )
    return "\n".join(lines)


def replace_block(readme: str, block: str) -> str:
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise SystemExit(f"README.md must contain {START} and {END} exactly once")
    head, rest = readme.split(START)
    _, tail = rest.split(END)
    return f"{head}{START}\n{block}\n{END}{tail}"


def main(argv: list[str] | None = None, root: Path = ROOT) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--date", default=datetime.now(UTC).strftime("%Y-%m-%d"))
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--sec-ref", default="", help="sec-mcp-agent commit the run used")
    parser.add_argument("--fraud-ref", default="", help="fraud-investigation-agents commit")
    args = parser.parse_args(argv)
    live = root / "reports" / "live"
    refs = {"sec_ref": args.sec_ref, "fraud_ref": args.fraud_ref}
    entry = run_entry(live, args.run_id, args.date, refs)
    runs = append_history(live / "history.jsonl", entry)
    baseline = load(root / "baselines" / "live.json") or {}
    readme = root / "README.md"
    readme.write_text(
        replace_block(readme.read_text(encoding="utf-8"), render(live, baseline, runs, args.model)),
        encoding="utf-8",
    )
    print(f"README live section: run {args.run_id}, {len(runs)} runs in the history")


if __name__ == "__main__":
    main()
