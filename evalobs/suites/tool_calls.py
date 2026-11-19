"""Component metric: would the current tools accept the calls a real model actually made?

The dataset holds every tool call qwen2.5:3b made in recorded sec-mcp-agent eval runs. Each is
replayed through the current MCP servers (in memory). Index content does not matter here, only
schemas and argument handling, so the servers run over one stub passage per indexed company
and a stub fraud model with the real categories and cities.

Errors are split by cause:
  rejected_arguments  the tool refused the arguments (validation, unknown section/company...)
  not_found           the arguments were valid but named something that does not exist
                      (a made-up chunk_id, a company outside the index): the tool answered
                      correctly, so this is not an interface failure
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from mcp.client import Client

NOT_FOUND_MARKERS = ("No chunk with id", "is not in the index")


def stub_index(companies: dict[str, str]) -> Any:
    from sec_mcp_agent.filings.corpus import make_chunks
    from sec_mcp_agent.filings.search import FilingsIndex

    chunks = []
    for ticker, name in sorted(companies.items()):
        for section in ("business", "risk_factors", "mda"):
            text = (
                f"{name} discusses risks, revenue, competition, regulation, prices, supply "
                f"chains, employees, segments and technology in its {section} section."
            )
            chunks += make_chunks(ticker, name, "2026-01-30", section, text)
    return FilingsIndex(chunks)


def stub_fraud_model(directory: Path, categories: list[str]) -> Any:
    import joblib
    import pandas as pd
    from sec_mcp_agent.fraud.model import CITY_COORDS, FraudModel
    from xgboost import XGBClassifier

    cols = [
        "amount",
        "distance_km_from_home",
        "tx_count_last_5min",
        "time_since_last_tx",
        "hour_of_day",
        *[f"category_{c}" for c in categories],
    ]
    x = pd.DataFrame([[float(i % 7) for _ in cols] for i in range(40)], columns=cols)
    model = XGBClassifier(n_estimators=2, max_depth=2).fit(x, [i % 2 for i in range(40)])
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "feature_cols": cols, "threshold": 0.5}, directory / "model.joblib"
    )
    homes = {f"card_{i:04d}": list(CITY_COORDS)[i % len(CITY_COORDS)] for i in range(200)}
    (directory / "card_home_city.json").write_text(json.dumps(homes), encoding="utf-8")
    return FraudModel.load(directory)


def classify(result: Any) -> str:
    if not result.is_error:
        return "accepted"
    text = " ".join(getattr(c, "text", "") for c in result.content)
    return "not_found" if any(m in text for m in NOT_FOUND_MARKERS) else "rejected_arguments"


async def run(
    dataset: list[dict], companies: dict[str, str], categories: list[str], workdir: Path
) -> dict[str, Any]:
    from sec_mcp_agent.filings.server import build_server as filings_server
    from sec_mcp_agent.fraud.server import build_server as fraud_server

    servers = {
        "sec-filings": filings_server(stub_index(companies)),
        "fraud-scoring": fraud_server(stub_fraud_model(workdir / "fraud", categories)),
    }
    outcomes = []
    async with Client(servers["sec-filings"]) as filings, Client(servers["fraud-scoring"]) as fraud:
        clients = {"sec-filings": filings, "fraud-scoring": fraud}
        for call in dataset:
            client = clients.get(call["server"])
            if client is None:  # a tool name the model invented
                outcomes.append({**call, "outcome": "rejected_arguments"})
                continue
            result = await client.call_tool(call["tool"], call["arguments"])
            outcomes.append({**call, "outcome": classify(result)})
    by_run: dict[str, Counter] = {}
    for o in outcomes:
        by_run.setdefault(o["run"], Counter())[o["outcome"]] += 1
    total = Counter(o["outcome"] for o in outcomes)
    n = len(outcomes)
    return {
        "calls": n,
        "acceptance_rate": round(total["accepted"] / n, 3) if n else None,
        "rejected_arguments_rate": round(total["rejected_arguments"] / n, 3) if n else None,
        "not_found": total["not_found"],
        "by_run": {r: dict(c) for r, c in sorted(by_run.items())},
        "rejected_examples": [
            {k: o[k] for k in ("run", "question_id", "tool", "arguments")}
            for o in outcomes
            if o["outcome"] == "rejected_arguments"
        ][:10],
    }
