# Plan 002

- `datasets/answers/v1.jsonl` built from sec-mcp-agent `eval/history/run1..7/results.json`
  (fraud questions only), labelled by reading each answer against its fraud score; sha256 in the
  manifest.
- `evalobs/suites/answers.py` imports `sec_mcp_agent.agent.faithfulness.check`.
- `scripts/run_offline.py` adds the suite; `baselines/offline.json` adds two metrics.
- `scripts/live_metrics.py` copies the new summary fields when present (older pins have none).
- `scripts/readme_live.py` adds one row; history rows are unchanged.
- ADR 0005; regressions R9; README section.
