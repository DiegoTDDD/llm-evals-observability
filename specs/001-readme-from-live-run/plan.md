# Plan 001

- `scripts/readme_live.py RUN_ID`: reads `reports/live/metrics.json` and
  `reports/live/langfuse-*.json`, appends to `reports/live/history.jsonl` (idempotent per run
  id), renders the block and replaces it in `README.md`.
- `live.yml` publish job: run it after `live_metrics.py`, and stage `README.md` with `reports/`.
- Failed project job: the publish job deletes stale per-project files before merging the
  artifacts, so a missing artifact leaves no result instead of last week's.
- Tests: rendering, idempotent history, missing markers, a missing project.
