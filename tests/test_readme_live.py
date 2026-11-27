"""The README's live-run section is rendered from a run's files, and only that section changes."""

import json
import shutil
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


def run(repo, run_id, date, sec="e0bd06eb5040528f", fraud="4920573"):
    readme_live.main([run_id, "--date", date, "--sec-ref", sec, "--fraud-ref", fraud], root=repo)
    return (repo / "README.md").read_text(encoding="utf-8")


def add_fraud(repo):
    write(
        repo / "reports" / "live" / "langfuse-fraud-investigation-agents.json",
        {
            "traces": 62,
            "observations": 1013,
            "by_type": {"GENERATION": 115, "TOOL": 357, "SPAN": 541},
        },
    )


def test_renders_the_run_and_keeps_the_rest_of_the_readme(repo):
    add_fraud(repo)
    text = run(repo, "45249221224", "2026-11-23")
    assert text.startswith("# Title\n\n<!-- LIVE:START -->\n")
    assert text.endswith("<!-- LIVE:END -->\n\n## Run it\n")
    assert "old numbers" not in text and "no result" not in text
    assert "17 of 22 questions passed" in text
    assert "graph 80% pattern accuracy (single agent 40%, rules 80%)" in text
    assert "22 traces, 231 observations" in text
    assert "78 generations, 22 tool calls, 131 spans" in text
    assert "| Live gate ([`baselines/live.json`](baselines/live.json)) | ✅ | ✅ |" in text
    assert "[e0bd06e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/e0bd06e) | 17/22 |" in text


def test_a_failed_project_keeps_its_last_finished_run(repo):
    add_fraud(repo)
    run(repo, "1", "2026-11-23")
    live = repo / "reports" / "live"
    shutil.rmtree(live / "fraud-investigation-agents", ignore_errors=True)
    (live / "langfuse-fraud-investigation-agents.json").unlink()
    metrics = json.loads((live / "metrics.json").read_text(encoding="utf-8"))
    del metrics["fraud_agents"]
    write(live / "metrics.json", metrics)
    text = run(repo, "2", "2026-11-30")
    run_row = next(line for line in text.splitlines() if line.startswith("| Run |"))
    assert "actions/runs/2) (2026-11-30)" in run_row.split("|")[2]
    assert "actions/runs/1) (2026-11-23)" in run_row.split("|")[3]
    assert "graph 80% pattern accuracy" in text and "no result" not in text
    row = next(line for line in text.splitlines() if line.startswith("| [2]("))
    assert "| 17/22 |" in row and "[job failed](" in row


def test_a_regression_shows_in_the_gate_row(repo):
    add_fraud(repo)
    metrics = repo / "reports" / "live" / "metrics.json"
    data = json.loads(metrics.read_text(encoding="utf-8"))
    data["fraud_agents"]["graph_pattern_accuracy"] = 0.6
    write(metrics, data)
    assert "| ✅ | ❌ |" in run(repo, "2", "2026-11-30")


def test_a_rerun_replaces_its_run_in_the_history(repo):
    add_fraud(repo)
    run(repo, "1", "2026-11-19")
    run(repo, "2", "2026-11-23")
    run(repo, "2", "2026-11-23")
    lines = (repo / "reports" / "live" / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["run"] for line in lines] == ["1", "2"]


def test_nothing_to_publish_before_both_projects_have_finished_once():
    with pytest.raises(SystemExit):
        readme_live.render([{"run": "1", "date": "d", "projects": {}}], "m")


def test_missing_markers_fail(repo):
    add_fraud(repo)
    (repo / "README.md").write_text("# Title\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        readme_live.main(["1"], root=repo)
