"""Offline component evals: no language model, seconds to run, run on every pull request.

python scripts/run_offline.py --out reports/offline.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import anyio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalobs.datasets import load  # noqa: E402
from evalobs.suites import tool_calls  # noqa: E402

COMPANIES = json.loads((ROOT / "datasets" / "companies.json").read_text(encoding="utf-8"))
CATEGORIES = [
    "electronics",
    "entertainment",
    "fashion",
    "fuel",
    "groceries",
    "pharmacy",
    "restaurant",
    "travel",
]


async def run_all() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        return {
            "tool_calls": await tool_calls.run(
                load("tool_calls/v1.jsonl"), COMPANIES, CATEGORIES, Path(tmp)
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "offline.json")
    args = parser.parse_args()
    results = anyio.run(run_all)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
