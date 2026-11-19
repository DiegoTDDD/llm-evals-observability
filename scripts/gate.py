"""Fail (exit 1) if any gated metric regressed against its baseline.

    python scripts/gate.py reports/offline.json baselines/offline.json
In GitHub Actions the table is also written to the job summary.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evalobs.gate import run_gate

summary = os.environ.get("GITHUB_STEP_SUMMARY")
ok = run_gate(Path(sys.argv[1]), Path(sys.argv[2]), Path(summary) if summary else None)
sys.exit(0 if ok else 1)
