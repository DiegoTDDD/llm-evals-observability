# ADR 0001: Gate pull requests on replays of what the model really did

**Status:** accepted

## Context
A live evaluation with a local 3B model takes one to three hours on a CPU runner: too slow to run
on every pull request, and noisy. Caching model replies by prompt does not help either: any
change to a prompt or to the flow changes every later request, so the cache misses exactly when
a change needs checking.

## Decision
Two layers:
- **Offline, on every pull request (seconds):** component evals that need no model. The first one
  replays every tool call the model made in recorded runs through the current MCP servers and
  measures how many are accepted, and why the rest are not. Interfaces, validation and argument
  handling are what changed most between runs, and this checks them against real model behaviour.
- **Live, weekly:** the projects' own end-to-end evals with the real model, traced, gated against
  `baselines/live.json`.

## Consequences
- The gate would have failed on sec-mcp-agent's original code (acceptance 0.406 against a
  baseline of 0.812) and it caught R5 before any live run.
- Recorded behaviour ages: when an interface changes on purpose, old calls against the previous
  shape are reported as such and a new dataset version is recorded from the next live run.
