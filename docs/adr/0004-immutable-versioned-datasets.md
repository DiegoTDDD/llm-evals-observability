# ADR 0004: Datasets are immutable and versioned

**Status:** accepted

## Context
A score is only comparable to a baseline if the data under it did not change.

## Decision
Datasets live in `datasets/<name>/<version>.jsonl`, with a sha256 per file in
`datasets/manifest.json`. Loading a file whose hash does not match fails. New recordings become a
new version (`collect_datasets.py` refuses to overwrite); baselines name the version they used.

## Consequences
Changing a dataset is visible in review as a new file, never a silent edit.
