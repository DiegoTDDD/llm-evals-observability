"""Regression gate: compare a run's metrics with the committed baseline and fail on a drop.

baselines/<suite>.json lists each gated metric with its baseline value, direction and
tolerance:

    {"tool_calls.acceptance_rate": {"value": 0.812, "higher_is_better": true, "tolerance": 0.0}}

A metric that got worse by more than its tolerance fails the gate. A metric that improved is
reported so the baseline can be raised in the same pull request.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Check:
    metric: str
    baseline: float
    current: float | None
    higher_is_better: bool
    tolerance: float

    @property
    def delta(self) -> float | None:
        return None if self.current is None else round(self.current - self.baseline, 4)

    @property
    def status(self) -> str:
        if self.current is None:
            return "missing"
        worse = (
            self.baseline - self.current if self.higher_is_better else self.current - self.baseline
        )
        if worse > self.tolerance + 1e-9:
            return "regressed"
        better = -worse
        return "improved" if better > 1e-9 else "unchanged"


def lookup(results: dict[str, Any], dotted: str) -> float | None:
    node: Any = results
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return float(node) if isinstance(node, int | float) else None


def evaluate(results: dict[str, Any], baseline: dict[str, Any]) -> list[Check]:
    return [
        Check(
            metric=name,
            baseline=float(spec["value"]),
            current=lookup(results, name),
            higher_is_better=bool(spec.get("higher_is_better", True)),
            tolerance=float(spec.get("tolerance", 0.0)),
        )
        for name, spec in sorted(baseline.items())
    ]


def passed(checks: list[Check]) -> bool:
    return all(c.status in {"improved", "unchanged"} for c in checks)


def markdown(checks: list[Check], title: str) -> str:
    icon = {"regressed": "❌", "missing": "❌", "improved": "⬆️", "unchanged": "✅"}
    lines = [
        f"### {title}: {'passed' if passed(checks) else 'FAILED'}",
        "",
        "| Metric | Baseline | Now | Change | |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in checks:
        now = "n/a" if c.current is None else f"{c.current:g}"
        delta = "n/a" if c.delta is None else f"{c.delta:+g}"
        lines.append(f"| `{c.metric}` | {c.baseline:g} | {now} | {delta} | {icon[c.status]} |")
    return "\n".join(lines) + "\n"


def run_gate(results_path: Path, baseline_path: Path, summary_path: Path | None = None) -> bool:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    checks = evaluate(results, baseline)
    text = markdown(checks, baseline_path.stem)
    print(text)  # noqa: T201
    if summary_path:
        with summary_path.open("a", encoding="utf-8") as f:
            f.write(text)
    return passed(checks)
