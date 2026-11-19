# llm-evals-observability

[![gate](https://github.com/DiegoTDDD/llm-evals-observability/actions/workflows/gate.yml/badge.svg)](https://github.com/DiegoTDDD/llm-evals-observability/actions/workflows/gate.yml)
[![live](https://github.com/DiegoTDDD/llm-evals-observability/actions/workflows/live.yml/badge.svg)](https://github.com/DiegoTDDD/llm-evals-observability/actions/workflows/live.yml)

Evaluation and observability for two agent projects,
[sec-mcp-agent](https://github.com/DiegoTDDD/sec-mcp-agent) (MCP tools + citations) and
[fraud-investigation-agents](https://github.com/DiegoTDDD/fraud-investigation-agents) (LangGraph
team): versioned datasets, a regression gate on every pull request, weekly live runs traced with
OpenTelemetry into a self-hosted Langfuse, and a public dashboard. Free to run: local model,
GitHub Actions, GitHub Pages.

## Problem

Agents built on small local models fail in ways unit tests do not see: the model sends
arguments the tools reject, a reply never ends, a fix in one place breaks another. Live evals
catch this but take hours on a CPU, so they cannot guard every pull request, and without
tracing nobody can see where the time and the errors go.

## Solution

```
every pull request (seconds)                        every week (hours, real model)
────────────────────────────                        ──────────────────────────────
datasets/ (immutable, sha256 manifest)              each project's own eval script, unchanged,
   └─ tool_calls/v1: 69 calls the model really         run under evalobs.instrument_run
      made in recorded runs                                │ OpenTelemetry spans: LLM calls (GenAI
          │                                                │ attributes, tokens), MCP tool calls,
          ▼                                                │ one root span per question/case
offline suites ──► reports/offline.json                    ├──► Langfuse v4, self-hosted in the job
          │                                                │      (check: traces arrive via its API)
          ▼                                                └──► JSONL ──► dashboard on GitHub Pages
gate vs baselines/offline.json ──► fail the PR                        │
                                                          end-to-end metrics ──► gate vs baselines/live.json
```

- **Offline gate**: replays every tool call the model made in recorded runs through the current
  MCP servers. A change that makes the tools reject what the model actually sends fails the pull
  request, without running a model (ADR 0001).
- **Tracing without touching the projects**: a launcher patches the LLM call, the MCP client and
  the run entry points, like `opentelemetry-instrument`. The MCP SDK propagates trace context, so
  each tool server's span nests under the agent's tool call (ADR 0002).
- **Langfuse + static dashboard**: Langfuse runs inside the job with per-run keys; the same spans
  build a static page of latency, tokens and errors per tool and per LLM step (ADR 0003).

## Results

### The gate catches R1

The same 69 recorded calls of qwen2.5:3b, replayed through three versions of sec-mcp-agent:

| sec-mcp-agent | Accepted | Rejected for their arguments | Gate |
| --- | --- | --- | --- |
| [1049d4b](https://github.com/DiegoTDDD/sec-mcp-agent/commit/1049d4b) (original) | 40.6% | 56.5% | ❌ fails |
| [7b7cbc4](https://github.com/DiegoTDDD/sec-mcp-agent/commit/7b7cbc469e62bd6cec53094bf9c71acd1a86d402) (after eval-run fixes) | 75.4% | 14.5% | ❌ fails |
| [abd66dc](https://github.com/DiegoTDDD/sec-mcp-agent/commit/abd66dc7b0ba6ecaae583c1f15df533ecf03b110) (current, R5 fixed) | **81.2%** | **8.7%** | ✅ baseline |

The replay also found R5: once R1 was fixed, most calls still rejected named sections the index
does not have. Every regression found so far, with cause, fix and evidence:
[docs/regressions.md](docs/regressions.md).

### Live runs

<!-- LIVE:START -->
The first live run fills this section and publishes the dashboard.
<!-- LIVE:END -->

## Run it

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q -p anyio                                     # 16 tests
python scripts/run_offline.py                          # reports/offline.json
python scripts/gate.py reports/offline.json baselines/offline.json

# Langfuse locally, then trace a project's eval
docker compose -f ops/langfuse/docker-compose.yml up -d   # http://localhost:3000
python -m evalobs.instrument_run --service sec-mcp-agent --jsonl reports/spans.jsonl --otlp \
    ../sec-mcp-agent/scripts/run_eval.py -- --model qwen2.5:3b
python -m evalobs.report reports/spans.jsonl reports/site/index.html
```

## Design decisions

- [ADR 0001](docs/adr/0001-offline-gate-replays-real-model-behaviour.md): gate pull requests on replays of what the model really did.
- [ADR 0002](docs/adr/0002-tracing-without-touching-the-projects.md): trace the projects without changing them.
- [ADR 0003](docs/adr/0003-langfuse-in-ci-and-a-static-dashboard.md): self-hosted Langfuse per run, plus a static dashboard that outlives it.
- [ADR 0004](docs/adr/0004-immutable-versioned-datasets.md): datasets are immutable and versioned.

## Limits

- The offline gate checks interfaces against recorded behaviour, not reasoning; reasoning is
  measured weekly by the live runs.
- Langfuse lives only for the duration of a live job; the persistent view is the static dashboard
  (or a local `docker compose up`).

## Stack

Python 3.11, OpenTelemetry SDK (OTLP/HTTP), Langfuse v4 (self-hosted), MCP Python SDK 2.x,
Ollama (qwen2.5:3b), pytest, ruff, GitHub Actions, GitHub Pages.

## License

MIT
