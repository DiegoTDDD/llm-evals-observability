"""The Langfuse check pages through the Observations API v2 and counts distinct traces."""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_langfuse


def test_follows_the_cursor_and_counts_distinct_traces():
    pages = [
        {"data": [{"traceId": "t1", "type": "SPAN", "name": "case"},
                  {"traceId": "t1", "type": "GENERATION", "name": "llm.chat",
                   "parentObservationId": "x"}],
         "meta": {"cursor": "next"}},
        {"data": [{"traceId": "t2", "type": "SPAN", "name": "case"}], "meta": {"cursor": None}},
    ]  # fmt: skip
    calls = []

    def fake(path, params):
        calls.append((path, dict(params)))
        return pages[len(calls) - 1]

    rows = check_langfuse.fetch_observations(datetime(2026, 11, 19, tzinfo=UTC), fetch=fake)
    assert [c[0] for c in calls] == ["/api/public/v2/observations"] * 2
    assert calls[0][1]["fromStartTime"] == "2026-11-19T00:00:00Z"
    assert "cursor" not in calls[0][1] and calls[1][1]["cursor"] == "next"
    s = check_langfuse.summarize(rows)
    assert s["traces"] == 2 and s["observations"] == 3
    assert s["by_type"] == {"SPAN": 2, "GENERATION": 1}
    assert [r["name"] for r in s["sample_roots"]] == ["case", "case"]


def test_empty_langfuse_counts_zero():
    assert check_langfuse.summarize([])["traces"] == 0
