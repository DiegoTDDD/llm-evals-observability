"""Write the README's live-run section from the files a live run committed.

    python scripts/readme_live.py RUN_ID [--date YYYY-MM-DD] [--sec-ref SHA] [--fraud-ref SHA]

Reads reports/live/metrics.json, reports/live/langfuse-*.json and the projects' results.json,
records the run in reports/live/history.jsonl (a rerun replaces its earlier entry), and
replaces the block between <!-- LIVE:START --> and <!-- LIVE:END --> in README.md. Each
project's numbers come from its latest finished run, so a project whose job failed keeps its
last measured results, labelled with their run. Nothing outside the markers changes.
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
VARIANCE_NOTE = (
    "docs/regressions.md#note--run-to-run-variance-is-real-so-the-live-gate-has-tolerances"
)


def pct(x: float) -> str:
    return f"{x:.0%}"


def load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def project_results(live: Path, metrics: dict, baseline: dict) -> dict[str, dict]:
    """Each project that finished in this run: headline numbers, Langfuse counts, gate, version."""
    out: dict[str, dict] = {}
    sec = load(live / SEC / "results.json")
    if sec is not None and "sec_mcp_agent" in metrics:
        out[SEC] = {
            "passed": sec["summary"]["passed"],
            "questions": sec["summary"]["questions"],
        }
    fraud = metrics.get("fraud_agents")
    if fraud:
        out[FRAUD] = {
            "graph": fraud["graph_pattern_accuracy"],
            "single": fraud["single_agent_pattern_accuracy"],
            "rules": fraud["rules_pattern_accuracy"],
        }
    for project, prefix in [(SEC, "sec_mcp_agent."), (FRAUD, "fraud_agents.")]:
        if project not in out:
            continue
        lf = load(live / f"langfuse-{project}.json") or {}
        out[project] |= {
            "traces": lf.get("traces"),
            "observations": lf.get("observations"),
            "by_type": lf.get("by_type", {}),
            "gate": passed(
                evaluate(metrics, {k: v for k, v in baseline.items() if k.startswith(prefix)})
            ),
        }
    return out


def append_history(history: Path, entry: dict) -> list[dict]:
    """Add the run, replacing an earlier entry for the same run id (a rerun); return all runs."""
    text = history.read_text(encoding="utf-8") if history.exists() else ""
    runs = [json.loads(line) for line in text.splitlines() if line]
    runs = [r for r in runs if r["run"] != entry["run"]] + [entry]
    history.write_text("".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    return runs


def ref_link(project: str, ref: str | None) -> str:
    return f"[{ref}](https://github.com/DiegoTDDD/{project}/commit/{ref})" if ref else "n/a"


def run_link(run: dict) -> str:
    return f"[{run['run']}]({REPO}/actions/runs/{run['run']}) ({run['date']})"


def latest_with(runs: list[dict], project: str) -> dict | None:
    """The most recent run in which the project finished."""
    return next((r for r in reversed(runs) if project in r.get("projects", {})), None)


def headline(project: str, res: dict) -> str:
    if project == SEC:
        return f"{res['passed']} of {res['questions']} questions passed"
    return (
        f"graph {pct(res['graph'])} pattern accuracy "
        f"(single agent {pct(res['single'])}, rules {pct(res['rules'])})"
    )


def langfuse_text(res: dict) -> tuple[str, str]:
    t = res.get("by_type", {})
    if res.get("traces") is None:
        return "not checked in this run", "not checked in this run"
    return (
        f"{res['traces']} traces, {res['observations']} observations",
        f"{t.get('GENERATION', 0)} generations, {t.get('TOOL', 0)} tool calls, "
        f"{t.get('SPAN', 0)} spans",
    )


def render(runs: list[dict], model: str) -> str:
    """The section: each project's latest finished run, then every run."""
    latest = {p: latest_with(runs, p) for p in (SEC, FRAUD)}
    if not all(latest.values()):
        raise SystemExit("no finished run for one of the projects yet: nothing to publish")
    res = {p: latest[p]["projects"][p] for p in (SEC, FRAUD)}
    lf = {p: langfuse_text(res[p]) for p in (SEC, FRAUD)}
    lines = [
        "**Dashboard: [diegotddd.github.io/llm-evals-observability]"
        "(https://diegotddd.github.io/llm-evals-observability/)**",
        "(latency, tokens and errors per run, per LLM step and per MCP tool, and the exact "
        "arguments of",
        "every failed tool call), rebuilt by every live run. This section is written by the same "
        "run ([`scripts/readme_live.py`](scripts/readme_live.py)).",
        "",
        f"Latest live results, {model} on CPU-only runners, both projects' own eval scripts run "
        "unchanged under the tracer:",
        "",
        f"| | {SEC} | {FRAUD} |",
        "| --- | --- | --- |",
        f"| Run | {run_link(latest[SEC])} | {run_link(latest[FRAUD])} |",
        f"| Project version | {ref_link(SEC, res[SEC].get('ref'))} | "
        f"{ref_link(FRAUD, res[FRAUD].get('ref'))} |",
        f"| End-to-end | {headline(SEC, res[SEC])} | {headline(FRAUD, res[FRAUD])} |",
        f"| Traces in Langfuse (read back through its API) | {lf[SEC][0]} | {lf[FRAUD][0]} |",
        f"| Observation types | {lf[SEC][1]} | {lf[FRAUD][1]} |",
        "| Live gate ([`baselines/live.json`](baselines/live.json)) | "
        f"{'✅' if res[SEC]['gate'] else '❌'} | {'✅' if res[FRAUD]['gate'] else '❌'} |",
        "",
        "Every live run, model at temperature 0. Rows with the same project version differ only "
        "by the model's run-to-run variance, which sets the live gate's tolerances "
        f"([docs/regressions.md]({VARIANCE_NOTE})). "
        "A job that fails is rerun automatically once "
        "([`rerun-live.yml`](.github/workflows/rerun-live.yml)); one that fails twice turns "
        "the run red and is listed as failed here.",
        "",
        f"| Run | Date | {SEC} version | Questions passed | {FRAUD} version | "
        "Graph: pattern accuracy | Single agent | Rules |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in runs:
        ps = r.get("projects", {})
        sec, fraud = ps.get(SEC), ps.get(FRAUD)
        failed = f"[job failed]({REPO}/actions/runs/{r['run']})"
        sec_cells = (
            f"{ref_link(SEC, sec.get('ref'))} | {sec['passed']}/{sec['questions']}"
            if sec
            else f"{ref_link(SEC, r.get('refs', {}).get(SEC))} | {failed}"
        )
        fraud_cells = (
            f"{ref_link(FRAUD, fraud.get('ref'))} | {pct(fraud['graph'])} | "
            f"{pct(fraud['single'])} | {pct(fraud['rules'])}"
            if fraud
            else f"{ref_link(FRAUD, r.get('refs', {}).get(FRAUD))} | {failed} | | "
        )
        lines.append(
            f"| [{r['run']}]({REPO}/actions/runs/{r['run']}) | {r['date']} | "
            f"{sec_cells} | {fraud_cells} |"
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
    refs = {SEC: args.sec_ref[:7], FRAUD: args.fraud_ref[:7]}
    baseline = load(root / "baselines" / "live.json") or {}
    metrics = load(live / "metrics.json") or {}
    projects = project_results(live, metrics, baseline)
    for project, res in projects.items():
        res["ref"] = refs[project] or None
    entry = {"run": args.run_id, "date": args.date, "refs": refs, "projects": projects}
    runs = append_history(live / "history.jsonl", entry)
    readme = root / "README.md"
    readme.write_text(
        replace_block(readme.read_text(encoding="utf-8"), render(runs, args.model)),
        encoding="utf-8",
    )
    print(f"README live section: run {args.run_id}, {len(runs)} runs in the history")


if __name__ == "__main__":
    main()
