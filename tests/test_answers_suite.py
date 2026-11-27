"""The faithfulness suite rescoring recorded answers with the pinned project's own check."""

import pytest

from evalobs.datasets import load
from evalobs.suites import answers


def test_the_pinned_check_agrees_with_every_label():
    result = answers.run(load("answers/v1.jsonl"))
    assert result["rows"] == 21
    assert result["unfaithful_caught_rate"] == 1.0 and result["false_alarm_rate"] == 0.0


def test_a_check_that_stops_catching_contradictions_is_caught(monkeypatch):
    from sec_mcp_agent.agent import faithfulness

    monkeypatch.setattr(faithfulness, "stated_verdict", lambda answer: None)
    result = answers.run(load("answers/v1.jsonl"))
    assert result["unfaithful_caught_rate"] == 0.0
    assert sorted(result["missed"]) == ["run5-t04", "run6-t04"]


@pytest.mark.parametrize("name", ["answers/v1.jsonl"])
def test_dataset_rows_are_labelled(name):
    for row in load(name):
        assert isinstance(row["faithful"], bool) and row["reason"]
