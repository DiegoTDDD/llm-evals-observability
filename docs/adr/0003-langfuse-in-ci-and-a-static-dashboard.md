# ADR 0003: Self-hosted Langfuse per run, plus a static dashboard that outlives it

**Status:** accepted

## Context
The plan calls for Langfuse self-hosted and a dashboard of latency, cost and errors per tool,
at no cost. A permanently running Langfuse needs a server; a GitHub runner disappears after the job.

## Decision
- Each live job starts Langfuse v4 from a pinned `ops/langfuse/docker-compose.yml` with keys
  generated for that run, exports spans to it over OTLP, and `scripts/check_langfuse.py` fails the
  job unless the expected traces arrive through Langfuse's public API.
- The same spans go to JSONL. `evalobs.report` turns them into a static page (runs, LLM calls by
  step with tokens and latency, MCP tools with p50/p95 and errors, the arguments behind tool
  errors, slowest runs) published to GitHub Pages.
- Cost is shown as its drivers: tokens and model seconds. With a local model the money cost is
  zero; `--price-per-mtok` converts tokens to a hosted-API price when needed.

## Consequences
- Locally, `docker compose up` gives the full Langfuse UI over the same spans.
- The public dashboard does not depend on any server staying up.
