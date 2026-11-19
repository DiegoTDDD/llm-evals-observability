"""Build the versioned datasets from the other projects' recorded eval runs.

    python scripts/collect_datasets.py --sec-mcp-agent ../sec-mcp-agent \
        --fraud-agents ../fraud-investigation-agents

Writes datasets/<name>/<version>.jsonl and refreshes datasets/manifest.json (sha256 per file).
A dataset file is never edited in place: new recordings become a new version.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "datasets"


def tool_calls(sec_repo: Path) -> list[dict]:
    rows = []
    for results in sorted((sec_repo / "eval").glob("**/results.json")):
        run = results.parent.name if results.parent.name != "eval" else "latest"
        data = json.loads(results.read_text(encoding="utf-8"))
        for row in data["rows"]:
            for t in (row.get("answer") or {}).get("tool_calls", []):
                rows.append(
                    {
                        "run": run,
                        "model": data.get("model"),
                        "question_id": row["id"],
                        "server": t["server"],
                        "tool": t["tool"],
                        "arguments": t["arguments"],
                        "accepted_then": t["ok"],
                    }
                )
    return rows


def write(name: str, version: str, rows: list[dict]) -> Path:
    path = DATASETS / name / f"{version}.jsonl"
    if path.exists():
        raise SystemExit(f"{path} exists: datasets are immutable, use a new version")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    return path


def refresh_manifest() -> dict:
    manifest = {}
    for path in sorted(DATASETS.glob("*/*.jsonl")):
        manifest[str(path.relative_to(DATASETS))] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": sum(1 for _ in path.open(encoding="utf-8")),
        }
    (DATASETS / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sec-mcp-agent", type=Path)
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()
    if args.sec_mcp_agent:
        print(write("tool_calls", args.version, tool_calls(args.sec_mcp_agent)))
    print(json.dumps(refresh_manifest(), indent=1))


if __name__ == "__main__":
    main()
