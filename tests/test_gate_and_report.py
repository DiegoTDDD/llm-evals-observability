"""The regression gate, immutable datasets, the tool-call replay suite and the dashboard."""

import hashlib
import json

import pytest

from evalobs import datasets
from evalobs.gate import evaluate, markdown, passed
from evalobs.report import aggregate, render

BASE = {
    "suite.accuracy": {"value": 0.8, "higher_is_better": True, "tolerance": 0.02},
    "suite.errors": {"value": 0.1, "higher_is_better": False, "tolerance": 0.0},
}


@pytest.mark.parametrize(
    ("accuracy", "errors", "ok", "statuses"),
    [
        (0.8, 0.1, True, ["unchanged", "unchanged"]),
        (0.79, 0.1, True, ["unchanged", "unchanged"]),  # within tolerance
        (0.77, 0.1, False, ["regressed", "unchanged"]),
        (0.9, 0.05, True, ["improved", "improved"]),
        (0.8, 0.11, False, ["unchanged", "regressed"]),  # lower is better, no tolerance
    ],
)
def test_gate_statuses(accuracy, errors, ok, statuses):
    checks = evaluate({"suite": {"accuracy": accuracy, "errors": errors}}, BASE)
    assert [c.status for c in checks] == statuses and passed(checks) is ok


def test_missing_metric_fails_the_gate():
    checks = evaluate({"suite": {"accuracy": 0.9}}, BASE)
    assert not passed(checks) and checks[1].status == "missing"
    assert "FAILED" in markdown(checks, "offline")


def test_datasets_are_immutable(tmp_path, monkeypatch):
    path = tmp_path / "x" / "v1.jsonl"
    path.parent.mkdir()
    path.write_text('{"a": 1}\n')
    manifest = {"x/v1.jsonl": {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(datasets, "DATASETS", tmp_path)
    assert datasets.load("x/v1.jsonl") == [{"a": 1}]
    path.write_text('{"a": 2}\n')
    with pytest.raises(datasets.DatasetChanged):
        datasets.load("x/v1.jsonl")


def test_committed_datasets_match_their_manifest():
    manifest = json.loads((datasets.DATASETS / "manifest.json").read_text())
    for name in manifest:
        assert datasets.load(name)


@pytest.mark.anyio
async def test_tool_call_replay_classifies_outcomes(tmp_path):
    from evalobs.suites import tool_calls

    companies = {"AAPL": "Apple Inc.", "XOM": "Exxon Mobil Corp"}
    tx = {
        "card_id": "card_0001",
        "amount": 10,
        "category": "fuel",
        "city": "Recife",
        "timestamp": "2026-03-01T10:00:00",
    }
    data = [
        {
            "run": "r",
            "question_id": "q",
            "server": "sec-filings",
            "tool": "search_filings",
            "arguments": {"query": "tariffs", "section": "RISK FACTORS", "ticker": "Apple"},
        },
        {
            "run": "r",
            "question_id": "q",
            "server": "sec-filings",
            "tool": "search_filings",
            "arguments": {"query": "x", "k": 99},
        },
        {
            "run": "r",
            "question_id": "q",
            "server": "sec-filings",
            "tool": "search_filings",
            "arguments": {"query": "coffee", "ticker": "SBUX"},
        },
        {
            "run": "r",
            "question_id": "q",
            "server": "sec-filings",
            "tool": "get_chunk",
            "arguments": {"chunk_id": "1"},
        },
        {
            "run": "r",
            "question_id": "q",
            "server": "fraud-scoring",
            "tool": "score_transaction",
            "arguments": tx,
        },
        {
            "run": "r",
            "question_id": "q",
            "server": "fraud-scoring",
            "tool": "score_transaction",
            "arguments": {"transaction": tx},
        },
        {
            "run": "r",
            "question_id": "q",
            "server": "?",
            "tool": "delete_everything",
            "arguments": {},
        },
    ]
    out = await tool_calls.run(data, companies, ["fuel", "groceries"], tmp_path)
    assert out["by_run"]["r"] == {"accepted": 2, "rejected_arguments": 3, "not_found": 2}
    assert out["acceptance_rate"] == round(2 / 7, 3)


def test_dashboard_aggregates_spans():
    def span(name, seconds, attrs, status="UNSET", service="sec-mcp-agent"):
        return {
            "name": name,
            "seconds": seconds,
            "attributes": attrs,
            "status": status,
            "error": "bad" if status == "ERROR" else None,
            "service": service,
        }

    spans = [
        span("agent.ask", 30.0, {"question": "q1"}),
        span(
            "chat qwen",
            10.0,
            {
                "gen_ai.operation.name": "chat",
                "llm.tools_offered": 4,
                "gen_ai.usage.input_tokens": 900,
                "gen_ai.usage.output_tokens": 40,
                "gen_ai.request.model": "qwen2.5:3b",
            },
        ),
        span(
            "chat qwen",
            12.0,
            {
                "gen_ai.operation.name": "chat",
                "llm.output_schema": "AnswerDraft",
                "gen_ai.usage.input_tokens": 1500,
                "gen_ai.usage.output_tokens": 200,
                "gen_ai.request.model": "qwen2.5:3b",
            },
        ),
        span("tool search_filings", 0.02, {"mcp.tool": "search_filings"}),
        span(
            "tool search_filings",
            0.03,
            {"mcp.tool": "search_filings", "mcp.arguments": "{}"},
            "ERROR",
        ),
    ]
    agg = aggregate(spans)
    assert agg["models"] == ["qwen2.5:3b"]
    [tool] = agg["tools"]
    assert tool["calls"] == 2 and tool["errors"] == 1
    steps = {r["step"]: r for r in agg["llm"]}
    assert (
        steps["tool round"]["input_tokens"] == 900 and steps["AnswerDraft"]["output_tokens"] == 200
    )
    page = render(agg, price_per_mtok=1.0)
    assert "Agent traces" in page and "2,640" in page and "$0.00" in page
    assert agg["slowest"][0]["what"] == "q1"
