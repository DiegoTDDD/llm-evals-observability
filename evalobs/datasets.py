"""Versioned datasets: immutable JSONL files checked against datasets/manifest.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DATASETS = Path(__file__).resolve().parents[1] / "datasets"


class DatasetChanged(Exception):
    pass


def load(name: str) -> list[dict]:
    path = DATASETS / name
    manifest = json.loads((DATASETS / "manifest.json").read_text(encoding="utf-8"))
    expected = manifest[name]["sha256"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise DatasetChanged(
            f"{name} does not match its manifest hash; datasets are immutable, "
            "add a new version instead"
        )
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
