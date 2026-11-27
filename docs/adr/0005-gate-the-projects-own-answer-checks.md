# ADR 0005: Gate the projects' own answer checks on hand-labelled answers

**Status:** accepted

## Context
sec-mcp-agent and fraud-investigation-agents now check their own answers: numbers must come
from the tool results, and the text must not contradict the model's verdict. A check like that
can silently weaken (a refactor that stops detecting "flags") or turn noisy (a stricter number
match that rejects correct answers). Neither shows up in an end-to-end pass rate.

## Decision
- Dataset `answers/v1`: every answer qwen2.5:3b gave to the fraud questions in sec-mcp-agent's
  eval runs 1 to 7 (21), each labelled faithful or not, with the reason. Immutable like every
  dataset (ADR 0004).
- The offline suite rescores them with the pinned project's own check, imported, not copied, so
  the gate tests the code that ships.
- Baselines: 100% of wrong answers caught and 0% false alarms, with no tolerance; the check is
  deterministic, so any change is a real change.
- The live runs record the projects' faithfulness metrics when the pinned version reports them,
  and the README marks older versions "not measured".

## Consequences
- Only 2 of the 21 answers are wrong, so the catch rate rests on two cases; new labelled wrong
  answers go into `answers/v2`.
- Bumping the sec-mcp-agent pin now also runs the answer check against the labels.
