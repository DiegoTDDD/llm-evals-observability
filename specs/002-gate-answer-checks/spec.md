# Spec 002: Gate the answer checks and record faithfulness in the live runs

## Problem
The projects check their answers' text against tool results, but nothing here verifies those
checks, and the live runs do not report them.

## Requirements
- R1 A versioned dataset of real answers, labelled faithful or not with a reason.
- R2 An offline suite that rescores it with the pinned project's own check: share of wrong
  answers caught, share of correct answers flagged, and the ids of each miss.
- R3 Baselines with no tolerance; the gate fails if either rate moves the wrong way.
- R4 Pins move to the project versions that ship the checks (sec-mcp-agent 499ca2e,
  fraud-investigation-agents d64fb86) in requirements.txt and live.yml.
- R5 live_metrics records sec `faithful_rate`, `verdict_mismatches` and the fraud summary
  faithfulness rates when present; the README block shows them or "not measured at this version".

## Acceptance
- The offline report has `answers.unfaithful_caught_rate` 1.0 and `answers.false_alarm_rate` 0.0
  at 499ca2e, and the gate passes.
- A test that disables verdict detection gets catch rate 0.0 with both wrong ids listed.
