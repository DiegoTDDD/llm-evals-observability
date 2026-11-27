# Spec 001: the README's live-run section is written by the live run

## Problem
The weekly live run commits its reports, but the README's "Live runs" section was written by
hand after the second run. Run 45249221224 changed the fraud graph's pattern accuracy (0.767 to
0.8) and the README still showed run 44567898582: the page a reader sees first was out of date.

## Requirements
- R1. The live workflow rewrites the block between `<!-- LIVE:START -->` and `<!-- LIVE:END -->`
  from the run's files: run id, end-to-end results, Langfuse trace and observation counts by
  type, and the live gate's result against `baselines/live.json`.
- R2. Each run appends one line to `reports/live/history.jsonl`; the block lists every run's
  headline numbers, so the variance behind the gate's tolerances is visible.
- R3. Text outside the markers is never changed; missing markers fail loudly.
- R4. A project whose job failed shows "no result" instead of a stale number.

## Clarifications
- The gate result in the block is computed with `evalobs.gate`, the same code the gate step runs.
- History is seeded with the three runs so far (44557681399, 44567898582, 45249221224) from
  their committed `metrics.json`.
