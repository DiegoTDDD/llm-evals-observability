"""Static dashboard from span JSONL: latency, errors and tokens per tool, per LLM step, per run.

    python -m evalobs.report reports/spans.jsonl reports/site/index.html

Published to GitHub Pages by the live workflow, so it stays readable when no Langfuse is up.
Cost is reported as what drives it: tokens and model seconds. A price per million tokens can
be passed to also show what the same traffic would cost on a hosted API.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOTS = {"agent.ask", "graph.investigate", "single_agent.investigate"}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]


def aggregate(spans: list[dict]) -> dict[str, Any]:
    tools: dict[str, list[dict]] = defaultdict(list)
    llm: dict[tuple[str, str], list[dict]] = defaultdict(list)
    roots: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for s in spans:
        a = s["attributes"]
        if s["name"].startswith("tool "):
            tools[a.get("mcp.tool", s["name"][5:])].append(s)
        elif a.get("gen_ai.operation.name") == "chat":
            step = a.get("llm.output_schema") or (
                "tool round" if a.get("llm.tools_offered") else "chat"
            )
            llm[(s["service"], step)].append(s)
        elif s["name"] in ROOTS:
            roots[(s["service"], s["name"])].append(s)

    def stats(group: list[dict]) -> dict[str, Any]:
        secs = [s["seconds"] or 0.0 for s in group]
        return {
            "calls": len(group),
            "errors": sum(s["status"] == "ERROR" for s in group),
            "p50": round(pct(secs, 0.5), 3),
            "p95": round(pct(secs, 0.95), 3),
            "total_seconds": round(sum(secs), 1),
        }

    llm_rows = []
    for (service, step), group in sorted(llm.items()):
        row = {"service": service, "step": step, **stats(group)}
        row["input_tokens"] = sum(
            int(s["attributes"].get("gen_ai.usage.input_tokens", 0)) for s in group
        )
        row["output_tokens"] = sum(
            int(s["attributes"].get("gen_ai.usage.output_tokens", 0)) for s in group
        )
        llm_rows.append(row)
    return {
        "spans": len(spans),
        "generated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "models": sorted({s["attributes"].get("gen_ai.request.model", "") for s in spans} - {""}),
        "roots": [{"service": k[0], "run": k[1], **stats(v)} for k, v in sorted(roots.items())],
        "llm": llm_rows,
        "tools": sorted(
            ({"tool": k, **stats(v)} for k, v in tools.items()), key=lambda r: -r["total_seconds"]
        ),
        "tool_errors": [
            {
                "tool": s["attributes"].get("mcp.tool"),
                "error": (s["error"] or "")[:160],
                "arguments": s["attributes"].get("mcp.arguments", "")[:160],
            }
            for s in spans
            if s["name"].startswith("tool ") and s["status"] == "ERROR"
        ][:30],
        "slowest": sorted(
            (
                {
                    "service": s["service"],
                    "run": s["name"],
                    "seconds": round(s["seconds"] or 0, 1),
                    "what": s["attributes"].get("question")
                    or s["attributes"].get("transaction_id", ""),
                }
                for s in spans
                if s["name"] in ROOTS
            ),
            key=lambda r: -r["seconds"],
        )[:10],
    }


def table(rows: list[dict], cols: list[tuple[str, str]], bar: str | None = None) -> str:
    if not rows:
        return "<p class=muted>No data.</p>"
    top = max((r[bar] for r in rows), default=0) or 1 if bar else 1
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in cols)
    body = []
    for r in rows:
        cells = []
        for key, _ in cols:
            v = r.get(key, "")
            text = (
                f"{v:,}"
                if isinstance(v, int)
                else (f"{v:,.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))
            )
            if key == bar:
                width = 100 * (r[bar] / top)
                text = f'<div class=bar><span style="width:{width:.0f}%"></span><em>{html.escape(text)}</em></div>'
            elif key == "errors" and v:
                text = f"<b class=err>{html.escape(text)}</b>"
            else:
                text = html.escape(text)
            cells.append(f"<td>{text}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def render(agg: dict[str, Any], price_per_mtok: float | None = None) -> str:
    tokens_in = sum(r["input_tokens"] for r in agg["llm"])
    tokens_out = sum(r["output_tokens"] for r in agg["llm"])
    llm_seconds = sum(r["total_seconds"] for r in agg["llm"])
    tool_calls = sum(r["calls"] for r in agg["tools"])
    tool_errors = sum(r["errors"] for r in agg["tools"])
    cost = ""
    if price_per_mtok is not None:
        usd = (tokens_in + tokens_out) / 1e6 * price_per_mtok
        cost = f"<div class=kpi><b>${usd:,.2f}</b><span>at ${price_per_mtok}/1M tokens</span></div>"
    kpis = (
        f"<div class=kpi><b>{sum(r['calls'] for r in agg['roots']):,}</b><span>runs</span></div>"
        f"<div class=kpi><b>{sum(r['calls'] for r in agg['llm']):,}</b><span>LLM calls</span></div>"
        f"<div class=kpi><b>{tokens_in + tokens_out:,}</b><span>tokens ({tokens_in:,} in / {tokens_out:,} out)</span></div>"
        f"<div class=kpi><b>{llm_seconds / 60:,.1f} min</b><span>model time (CPU, free runner)</span></div>"
        f"<div class=kpi><b>{tool_calls:,}</b><span>tool calls, {tool_errors} errors</span></div>{cost}"
    )
    css = """
:root{--bg:#fff;--fg:#1d1f23;--muted:#667;--line:#e4e6ea;--accent:#3b6fd8;--err:#c0392b;--barbg:#eef2fb}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--fg:#e8eaed;--muted:#9aa0a6;--line:#2a2e33;--accent:#7aa2f7;--err:#ff6b6b;--barbg:#1d2533}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;margin:0 auto;max-width:1100px;padding:24px 16px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 8px}.muted{color:var(--muted)}
.kpis{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.kpi{border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:150px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted);font-size:13px}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--muted);font-weight:600}.err{color:var(--err)}
.bar{position:relative;min-width:140px;background:var(--barbg);border-radius:4px}.bar span{display:block;height:22px;background:var(--accent);opacity:.35;border-radius:4px}
.bar em{position:absolute;left:8px;top:1px;font-style:normal}
"""
    sections = [
        (
            "Runs",
            table(
                agg["roots"],
                [
                    ("service", "Project"),
                    ("run", "Run"),
                    ("calls", "Count"),
                    ("p50", "p50 s"),
                    ("p95", "p95 s"),
                    ("errors", "Errors"),
                ],
            ),
        ),
        (
            "LLM calls by step",
            table(
                agg["llm"],
                [
                    ("service", "Project"),
                    ("step", "Step"),
                    ("calls", "Calls"),
                    ("input_tokens", "Tokens in"),
                    ("output_tokens", "Tokens out"),
                    ("p50", "p50 s"),
                    ("p95", "p95 s"),
                    ("total_seconds", "Total s"),
                    ("errors", "Errors"),
                ],
                bar="total_seconds",
            ),
        ),
        (
            "MCP tools",
            table(
                agg["tools"],
                [
                    ("tool", "Tool"),
                    ("calls", "Calls"),
                    ("errors", "Errors"),
                    ("p50", "p50 s"),
                    ("p95", "p95 s"),
                    ("total_seconds", "Total s"),
                ],
                bar="calls",
            ),
        ),
        (
            "Tool errors (what the model sent)",
            table(
                agg["tool_errors"],
                [("tool", "Tool"), ("arguments", "Arguments"), ("error", "Error")],
            ),
        ),
        (
            "Slowest runs",
            table(
                agg["slowest"],
                [("service", "Project"), ("run", "Run"), ("seconds", "Seconds"), ("what", "Input")],
            ),
        ),
    ]
    body = "".join(f"<h2>{html.escape(t)}</h2><div class=wrap>{h}</div>" for t, h in sections)
    models = ", ".join(agg["models"]) or "n/a"
    return (
        f"<!doctype html><html lang=en><meta charset=utf-8>"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Agent traces</title><style>{css}</style><body>"
        f"<h1>Agent traces</h1><p class=muted>{agg['spans']:,} OpenTelemetry spans from the "
        f"latest live evaluation · model {html.escape(models)} · generated {agg['generated']}</p>"
        f"<div class=kpis>{kpis}</div>{body}</body></html>"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spans", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--price-per-mtok", type=float, default=None)
    args = parser.parse_args()
    agg = aggregate(load(args.spans))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(agg, args.price_per_mtok), encoding="utf-8")
    args.out.with_suffix(".json").write_text(json.dumps(agg, indent=1), encoding="utf-8")
    print(f"{args.out}: {agg['spans']} spans")  # noqa: T201


if __name__ == "__main__":
    main()
