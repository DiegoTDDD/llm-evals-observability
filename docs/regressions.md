# Regression log

Real regressions found in the projects this repository evaluates, how each was detected, the
fix, and the evidence. Newest first.

## R5 — Unknown sections rejected (sec-mcp-agent, found here)

- **Detected by:** the offline tool-call replay (`tool_calls` suite). After R1's fix, the calls
  the model really made that were still rejected were mostly invented sections: `"R&D"`,
  `"CONTRACTORS"`, `"INDUSTRIES_AND_OPERATIONS"`, `"competition"`.
- **Fix:** [sec-mcp-agent@abd66dc](https://github.com/DiegoTDDD/sec-mcp-agent/commit/abd66dc7b0ba6ecaae583c1f15df533ecf03b110):
  a section the index does not have means "search every section".
- **Evidence:** acceptance of the model's 69 recorded calls 75.4% → 81.2%; arguments rejected
  14.5% → 8.7%. The remaining 6: five calls made against an older interface (nested
  `transaction` object) and one real model error (missing timestamp).

## R4 — Evaluation cases not reproducible (fraud-investigation-agents)

- **Detected by:** the eval workflow's case check failed on its first run.
- **Cause:** realtime-fraud-detection-ml's generator seeds `random` but draws transaction ids
  with `uuid4()`; each rebuild repeats every transaction with a new id.
- **Fix:** cases keyed by card + timestamp ([923fe03](https://github.com/DiegoTDDD/fraud-investigation-agents/commit/923fe0376bda6a5279b5703fec7a006338bdf372)).
  Verified by regenerating the data: 0% of ids equal, every other column identical, cases identical.

## R3 — One model reply never ended (sec-mcp-agent)

- **Detected by:** eval run 2 stopped answering after question 14 and held the runner until the
  3-hour job limit.
- **Cause:** JSON-constrained generation with no token limit and no HTTP timeout.
- **Fix:** [bc4b0b4](https://github.com/DiegoTDDD/sec-mcp-agent/commit/bc4b0b4): 768-token cap,
  240 s timeout per request, a failed question is scored as failed and the run continues.

## R2 — Tesla missing from the index (sec-mcp-agent)

- **Detected by:** run 1 transcripts: `Unknown ticker 'TSLA'`.
- **Cause:** Tesla's latest 10-K filing was an amendment (10-K/A) with no Business, Risk Factors
  or MD&A, so all three sections were skipped.
- **Fix:** the index skips amendments and falls back to an older filing when sections are missing.

## R1 — Tool schemas a 3B model could not satisfy (sec-mcp-agent)

- **Detected by:** eval run 1: 7 of 22 questions passed; most tool calls failed validation.
- **Cause:** a strict `section` enum (the model writes "RISK FACTORS", "MD&A", "Management's
  Discussion…") and a nested `transaction` object whose JSON schema the model copied into the
  call instead of filling it in.
- **Fix:** [cacf91e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/cacf91e) and
  [7b7cbc4](https://github.com/DiegoTDDD/sec-mcp-agent/commit/7b7cbc469e62bd6cec53094bf9c71acd1a86d402):
  lenient section and company resolution, flat parameters, a reminder when the model answers
  without tools, citations anchored on the retrieved passage.
- **Evidence:** run 1 → run 3: 7/22 → 11/22 questions; replaying the same 69 recorded calls,
  acceptance 40.6% (original code) → 75.4%. The offline gate fails on the original code:
  see [the gate on 1049d4b](../README.md#the-gate-catches-r1).
