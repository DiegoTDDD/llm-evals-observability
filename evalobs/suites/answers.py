"""Component metric: does sec-mcp-agent's faithfulness check judge real answers correctly?

The dataset holds every answer qwen2.5:3b gave to the fraud questions in sec-mcp-agent's eval
runs 1 to 7, each labelled by hand: faithful, or not (runs 5 and 6, t04, say the model "flags"
a purchase it did not flag). Each is rescored with the pinned project's own check
(sec_mcp_agent.agent.faithfulness), so a change to that check that stops catching a
contradiction, or starts flagging a faithful answer, fails the offline gate.
"""

from __future__ import annotations

from typing import Any


def run(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from sec_mcp_agent.agent.faithfulness import check

    missed, false_alarms = [], []
    for r in rows:
        got = check(r["answer"], r["question"], r["cited_passages"], r["fraud_scores"]).faithful
        if r["faithful"] and not got:
            false_alarms.append(r["id"])
        elif not r["faithful"] and got:
            missed.append(r["id"])
    unfaithful = sum(not r["faithful"] for r in rows)
    faithful = len(rows) - unfaithful
    return {
        "rows": len(rows),
        "unfaithful_caught_rate": round(1 - len(missed) / unfaithful, 3) if unfaithful else 1.0,
        "false_alarm_rate": round(len(false_alarms) / faithful, 3) if faithful else 0.0,
        "missed": missed,
        "false_alarms": false_alarms,
    }
