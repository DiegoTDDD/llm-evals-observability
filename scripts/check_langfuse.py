"""Confirm the spans reached Langfuse: wait for traces from a service, then save a summary.

    python scripts/check_langfuse.py --service sec-mcp-agent --min-traces 10 \
        --out reports/live/langfuse-sec-mcp-agent.json

Reads LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY. Exits 1 if fewer traces
than expected arrive within the timeout, so a broken exporter fails the live workflow.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.request
from pathlib import Path


def get(path: str) -> dict:
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
    token = base64.b64encode(
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
    ).decode()
    req = urllib.request.Request(f"{host}{path}", headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-traces", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    deadline = time.time() + args.timeout
    total = 0
    while time.time() < deadline:
        data = get("/api/public/traces?limit=50")
        total = data.get("meta", {}).get("totalItems", len(data.get("data", [])))
        if total >= args.min_traces:
            break
        time.sleep(15)  # Langfuse ingests asynchronously through its worker
    observations = get("/api/public/observations?limit=1").get("meta", {}).get("totalItems")
    sample = [{k: t.get(k) for k in ("name", "timestamp", "latency", "totalCost")}
              for t in get("/api/public/traces?limit=5").get("data", [])]
    summary = {"traces": total, "observations": observations, "sample": sample}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    if total < args.min_traces:
        raise SystemExit(f"Langfuse has {total} traces, expected at least {args.min_traces}")


if __name__ == "__main__":
    main()
