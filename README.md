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

With dataset `tool_calls/v2` (162 calls: the project's six eval runs plus this repository's
first live run), the trace dashboard led to R7, a wrong ticker for a company the query named:

| sec-mcp-agent | Accepted | "Not in the index" | Gate |
| --- | --- | --- | --- |
| [80086e0](https://github.com/DiegoTDDD/sec-mcp-agent/commit/80086e07f50c1e9f4309dca9a864c6f94bab3f84) | 83.3% | 20 | ❌ fails the new baseline |
| [e0bd06e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/e0bd06eb5040528f328dd61e42ac655439ac73fb) (R7 fixed) | **85.2%** | **17** | ✅ baseline |
| [499ca2e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/499ca2e65ab976ba389ee3c88f51adde0508f7e6) (current, answer checks added) | 85.2% | 17 | ✅ |

**Proof that the gate blocks it:** [pull request #1](https://github.com/DiegoTDDD/llm-evals-observability/pull/1)
pins sec-mcp-agent back to 80086e0; the gate failed it
([run 44568525181](https://github.com/DiegoTDDD/llm-evals-observability/actions/runs/44568525181):
acceptance 0.833 against a baseline of 0.852) and it was closed without merging.

### The gate also checks the answer check

From [499ca2e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/499ca2e65ab976ba389ee3c88f51adde0508f7e6)
sec-mcp-agent checks each answer's text against what its tools returned: every number must appear
in a cited passage or a fraud score, and the answer must not contradict the model's verdict.
Dataset `answers/v1` holds all 21 answers qwen2.5:3b gave to the fraud questions in the project's
eval runs 1 to 7, labelled by hand. Two are wrong (R9): they say the model "flags" a purchase it
scored 9.5% against a 56% threshold. The offline gate rescores all 21 with the pinned check:

| Metric | Value | Baseline |
| --- | --- | --- |
| Wrong answers the check catches | 2 of 2 (100%) | 100%, no tolerance |
| Correct answers it flags (false alarms) | 0 of 19 (0%) | 0%, no tolerance |

A change that makes the check miss a contradiction fails the pull request
([`tests/test_answers_suite.py`](tests/test_answers_suite.py) disables verdict detection and
shows both answers slip through). The live runs record the same checks on fresh answers: the
share of faithful sec-mcp-agent answers, and of fraud reports whose summary states only what the
evidence shows.

The replay also found R5: once R1 was fixed, most calls still rejected named sections the index
does not have. Every regression found so far, with cause, fix and evidence:
[docs/regressions.md](docs/regressions.md).

### Live runs

<!-- LIVE:START -->
**Dashboard: [diegotddd.github.io/llm-evals-observability](https://diegotddd.github.io/llm-evals-observability/)**
(latency, tokens and errors per run, per LLM step and per MCP tool, and the exact arguments of
every failed tool call), rebuilt by every live run. This section is written by the same run ([`scripts/readme_live.py`](scripts/readme_live.py)).

Latest live results, qwen2.5:3b on CPU-only runners, both projects' own eval scripts run unchanged under the tracer:

| | sec-mcp-agent | fraud-investigation-agents |
| --- | --- | --- |
| Run | [46096097419](https://github.com/DiegoTDDD/llm-evals-observability/actions/runs/46096097419) (2026-11-28) | [46096097419](https://github.com/DiegoTDDD/llm-evals-observability/actions/runs/46096097419) (2026-11-28) |
| Project version | [499ca2e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/499ca2e) | [d64fb86](https://github.com/DiegoTDDD/fraud-investigation-agents/commit/d64fb86) |
| End-to-end | 17 of 22 questions passed | graph 83% pattern accuracy (single agent 40%, rules 80%) |
| Text that states only what the tools returned (the projects' own checks) | 21 of 22 answers | graph 90% of summaries (single agent 50%) |
| Traces in Langfuse (read back through its API) | 22 traces, 235 observations | 62 traces, 972 observations |
| Observation types | 81 generations, 22 tool calls, 132 spans | 110 generations, 339 tool calls, 523 spans |
| Live gate ([`baselines/live.json`](baselines/live.json)) | ✅ | ✅ |

Every live run, model at temperature 0. Rows with the same project version differ only by the model's run-to-run variance, which sets the live gate's tolerances ([docs/regressions.md](docs/regressions.md#note--run-to-run-variance-is-real-so-the-live-gate-has-tolerances)). A job that fails is rerun automatically once ([`rerun-live.yml`](.github/workflows/rerun-live.yml)); one that fails twice turns the run red and is listed as failed here.

| Run | Date | sec-mcp-agent version | Questions passed | fraud-investigation-agents version | Graph: pattern accuracy | Single agent | Rules |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [44557681399](https://github.com/DiegoTDDD/llm-evals-observability/actions/runs/44557681399) | 2026-11-19 | [80086e0](https://github.com/DiegoTDDD/sec-mcp-agent/commit/80086e0) | 14/22 | [4920573](https://github.com/DiegoTDDD/fraud-investigation-agents/commit/4920573) | 77% | 47% | 80% |
| [44567898582](https://github.com/DiegoTDDD/llm-evals-observability/actions/runs/44567898582) | 2026-11-19 | [80086e0](https://github.com/DiegoTDDD/sec-mcp-agent/commit/80086e0) | 17/22 | [4920573](https://github.com/DiegoTDDD/fraud-investigation-agents/commit/4920573) | 80% | 43% | 80% |
| [45249221224](https://github.com/DiegoTDDD/llm-evals-observability/actions/runs/45249221224) | 2026-11-23 | [e0bd06e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/e0bd06e) | 14/22 | [4920573](https://github.com/DiegoTDDD/fraud-investigation-agents/commit/4920573) | 80% | 40% | 80% |
| [46096097419](https://github.com/DiegoTDDD/llm-evals-observability/actions/runs/46096097419) | 2026-11-28 | [499ca2e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/499ca2e) | 17/22 | [d64fb86](https://github.com/DiegoTDDD/fraud-investigation-agents/commit/d64fb86) | 83% | 40% | 80% |
<!-- LIVE:END -->

## Run it

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q -p anyio                                     # 23 tests
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
- [ADR 0005](docs/adr/0005-gate-the-projects-own-answer-checks.md): gate the projects' own answer checks on hand-labelled answers.

## Limits

- The offline gate checks interfaces against recorded behaviour, and the answer check against 21
  labelled answers with only 2 wrong ones; reasoning is measured weekly by the live runs.
- The answer checks are deterministic: they catch unsupported numbers and contradicted verdicts,
  not every misleading sentence.
- Langfuse lives only for the duration of a live job; the persistent view is the static dashboard
  (or a local `docker compose up`).

## Stack

Python 3.11, OpenTelemetry SDK (OTLP/HTTP), Langfuse v4 (self-hosted), MCP Python SDK 2.x,
Ollama (qwen2.5:3b), pytest, ruff, GitHub Actions, GitHub Pages.

## License

MIT
