"""The README's live-run section is rendered from a run's files, and only that section changes."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import readme_live


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    live = tmp_path / "reports" / "live"
    write(live / "sec-mcp-agent" / "results.json", {"summary": {"passed": 17, "questions": 22}})
    write(
        live / "metrics.json",
        {
            "sec_mcp_agent": {"pass_rate": 0.773, "out_of_scope_pass_rate": 1.0, "errors": 0},
            "fraud_agents": {
                "graph_pattern_accuracy": 0.8,
                "graph_verdict_accuracy": 0.833,
                "single_agent_pattern_accuracy": 0.4,
                "rules_pattern_accuracy": 0.8,
                "graph_errors": 0,
            },
        },
    )
    write(
        live / "langfuse-sec-mcp-agent.json",
        {"traces": 22, "observations": 231, "by_type": {"GENERATION": 78, "TOOL": 22, "SPAN": 131}},
    )
    write(
        tmp_path / "baselines" / "live.json",
        {
            "sec_mcp_agent.pass_rate": {"value": 0.705, "tolerance": 0.15},
            "fraud_agents.graph_pattern_accuracy": {"value": 0.767, "tolerance": 0.034},
        },
    )
    (tmp_path / "README.md").write_text(
        "# Title\n\n<!-- LIVE:START -->\nold numbers\n<!-- LIVE:END -->\n\n## Run it\n",
        encoding="utf-8",
    )
    return tmp_path


def test_renders_the_run_and_keeps_the_rest_of_the_readme(repo):
    readme_live.main(
        [
            "45249221224",
            "--date",
            "2026-11-23",
            "--sec-ref",
            "e0bd06eb5040528f",
            "--fraud-ref",
            "4920573",
        ],
        root=repo,
    )
    text = (repo / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# Title\n\n<!-- LIVE:START -->\n")
    assert text.endswith("<!-- LIVE:END -->\n\n## Run it\n")
    assert "old numbers" not in text
    assert "17 of 22 questions passed" in text
    assert "graph 80% pattern accuracy (single agent 40%, rules 80%)" in text
    assert "22 traces, 231 observations" in text
    assert "78 generations, 22 tool calls, 131 spans" in text
    assert "| Live gate ([`baselines/live.json`](baselines/live.json)) | ✅ | ✅ |" in text
    assert "[e0bd06e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/e0bd06e) | 17/22 |" in text


def test_a_project_without_files_shows_no_result(repo):
    readme_live.main(["1", "--date", "2026-11-23"], root=repo)
    text = (repo / "README.md").read_text(encoding="utf-8")
    fraud_traces = [line for line in text.splitlines() if line.startswith("| Traces in Langfuse")]
    assert fraud_traces[0].endswith("| no result |")


def test_a_regression_shows_in_the_gate_row(repo):
    metrics = repo / "reports" / "live" / "metrics.json"
    data = json.loads(metrics.read_text(encoding="utf-8"))
    data["fraud_agents"]["graph_pattern_accuracy"] = 0.6
    write(metrics, data)
    readme_live.main(["2", "--date", "2026-11-30"], root=repo)
    assert "| ✅ | ❌ |" in (repo / "README.md").read_text(encoding="utf-8")


def test_history_keeps_one_line_per_run(repo):
    readme_live.main(["1", "--date", "2026-11-19"], root=repo)
    readme_live.main(["2", "--date", "2026-11-23"], root=repo)
    readme_live.main(["2", "--date", "2026-11-23"], root=repo)  # the publish job rerun
    lines = (repo / "reports" / "live" / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["run"] for line in lines] == ["1", "2"]
    assert "| [2](" in (repo / "README.md").read_text(encoding="utf-8")


def test_missing_markers_fail(repo):
    (repo / "README.md").write_text("# Title\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        readme_live.main(["1"], root=repo)
