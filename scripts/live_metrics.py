"""End-to-end metrics of a live run, in the shape baselines/live.json gates.

python scripts/live_metrics.py reports/live reports/live/metrics.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    live, out = Path(sys.argv[1]), Path(sys.argv[2])
    metrics: dict[str, dict] = {}
    sec = live / "sec-mcp-agent" / "results.json"
    if sec.exists():
        s = json.loads(sec.read_text(encoding="utf-8"))["summary"]
        metrics["sec_mcp_agent"] = {
            "pass_rate": round(s["passed"] / s["questions"], 3),
            "filings_pass_rate": s["filings_pass_rate"],
            "grounded_rate": s["grounded_rate"],
            "out_of_scope_pass_rate": s["out_of_scope_pass_rate"],
            "fraud_exact_arguments_rate": s["fraud_exact_arguments_rate"],
            "errors": s.get("errors", 0),
        }
        if s.get("faithful_rate") is not None:  # from sec-mcp-agent 499ca2e on
            metrics["sec_mcp_agent"]["faithful_rate"] = s["faithful_rate"]
            metrics["sec_mcp_agent"]["verdict_mismatches"] = s.get("verdict_mismatches", 0)
    fraud = live / "fraud-investigation-agents" / "results.json"
    if fraud.exists():
        s = json.loads(fraud.read_text(encoding="utf-8"))["summary"]
        metrics["fraud_agents"] = {
            "graph_pattern_accuracy": s["graph"]["pattern_accuracy"],
            "graph_verdict_accuracy": s["graph"]["verdict_accuracy"],
            "single_agent_pattern_accuracy": s["single_agent"]["pattern_accuracy"],
            "rules_pattern_accuracy": s["rules_only"]["pattern_accuracy"],
            "graph_errors": s["graph"]["errors"],
        }
        for system in ("graph", "single_agent"):  # from fraud-investigation-agents d64fb86 on
            if s[system].get("summary_faithful_rate") is not None:
                metrics["fraud_agents"][f"{system}_summary_faithful_rate"] = s[system][
                    "summary_faithful_rate"
                ]
    for f in sorted(live.glob("langfuse-*.json")):
        metrics.setdefault("langfuse", {})[f.stem.removeprefix("langfuse-")] = json.loads(
            f.read_text(encoding="utf-8")
        )["traces"]
    out.write_text(json.dumps(metrics, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=1))


if __name__ == "__main__":
    main()
