"""Confirm the spans reached Langfuse: wait for traces to arrive, then save a summary.

    python scripts/check_langfuse.py --min-traces 10 --out reports/live/langfuse-sec-mcp-agent.json

Reads LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY. Exits 1 if fewer traces
than expected arrive within the timeout, so a broken exporter fails the live workflow.

Uses the Observations API v2 (`/api/public/v2/observations`). Langfuse v4 removed the legacy
read endpoints (`/api/public/traces`, `/api/public/observations`) on 2026-11-16; the first live
run failed here with a 404 on the old path. A trace is counted once per distinct `traceId`.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

PATH = "/api/public/v2/observations"


def get(path: str, params: dict[str, Any]) -> dict:
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
    token = base64.b64encode(
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
    ).decode()
    url = f"{host}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def fetch_observations(since: datetime, fetch: Any = get) -> list[dict]:
    """Every observation that started after `since`, following the cursor."""
    rows: list[dict] = []
    params: dict[str, Any] = {
        "fromStartTime": since.isoformat().replace("+00:00", "Z"),
        "limit": 1000,
        "fields": "core,basic,metrics",
    }
    while True:
        page = fetch(PATH, params)
        rows += page.get("data", [])
        cursor = (page.get("meta") or {}).get("cursor")
        if not cursor:
            return rows
        params["cursor"] = cursor


def summarize(rows: list[dict]) -> dict[str, Any]:
    traces = {r["traceId"] for r in rows if r.get("traceId")}
    roots = [r for r in rows if not r.get("parentObservationId")]
    return {
        "traces": len(traces),
        "observations": len(rows),
        "by_type": dict(Counter(r.get("type", "?") for r in rows)),
        "top_names": dict(Counter(r.get("name", "?") for r in rows).most_common(8)),
        "sample_roots": [
            {k: r.get(k) for k in ("name", "startTime", "latency")} for r in roots[:5]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-traces", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--since-hours", type=float, default=24.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    since = datetime.now(UTC) - timedelta(hours=args.since_hours)
    deadline = time.time() + args.timeout
    summary = summarize([])
    while time.time() < deadline:
        summary = summarize(fetch_observations(since))
        if summary["traces"] >= args.min_traces:
            break
        time.sleep(15)  # Langfuse ingests asynchronously through its worker
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    if summary["traces"] < args.min_traces:
        raise SystemExit(
            f"Langfuse has {summary['traces']} traces, expected at least {args.min_traces}"
        )


if __name__ == "__main__":
    main()
