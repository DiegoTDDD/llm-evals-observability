# Regression log

Real regressions found in the projects this repository evaluates, how each was detected, the
fix, and the evidence. Newest first.

## R9 — Answers that contradicted the fraud model (sec-mcp-agent, found by labelling answers)

- **Detected by:** labelling every fraud answer of eval runs 1 to 7 for `answers/v1`. In runs 5
  and 6, question t04, the answer says the model "flags this transaction with a probability of
  9.52%"; the score it cites is below the 0.5625 threshold and `flagged` is false. Both runs
  scored the question as passed, because the eval only checked which tools were called.
- **Cause:** nothing compared the answer's text with the tool results.
- **Fix:** [499ca2e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/499ca2e65ab976ba389ee3c88f51adde0508f7e6):
  a deterministic check (numbers must appear in the sources, the stated verdict must match the
  model's); failing answers are marked `[unverified]` and counted in the eval.
- **Evidence:** the check catches both answers and flags none of the 19 correct ones; the
  offline gate holds it there (ADR 0005).

## R8 — Each project's results overwritten by a stale copy (this repository, found in an audit)

- **Detected by:** an audit of run 45249221224: the committed sec-mcp-agent results were
  byte-for-byte those of the run before, although the run used a newer sec-mcp-agent commit.
  The run's artifacts said otherwise: 14 of 22 questions, 232 Langfuse observations.
- **Cause:** each project job uploaded all of `reports/live/`, which in the checkout also holds
  the *other* project's results from the previous commit. The publish job merges both
  artifacts, so whichever was extracted last replaced one project's fresh results with last
  week's. Run 44567898582 published a stale fraud graph (76.7% instead of 80.0%) and run
  45249221224 a stale sec-mcp-agent score (17/22 instead of 14/22). The span files were named
  per project and were never affected, so the dashboard and dataset `tool_calls/v2` are right.
- **Fix:** each job uploads only its own project's files; the publish job drops last run's
  per-project files before merging. The three runs' results were rebuilt from each project's
  own artifact, and the README section is now written from them.
- **Evidence:** true results per run: sec-mcp-agent 14, 17, 14 of 22; fraud graph 76.7%, 80.0%,
  80.0%; single agent 46.7%, 43.3%, 40.0%. All three runs pass the live gate.

## R7 — A wrong ticker lost a question the query answered (sec-mcp-agent, found in the traces)

- **Detected by:** the trace dashboard of live run 44557681399, table "Tool errors (what the model
  sent)": `search_filings {"query": "UnitedHealth Group medical cost trends", "ticker": "UHG"}`
  failed with "not in the index". The ticker is UNH; the query named the company.
- **Fix:** [sec-mcp-agent@e0bd06e](https://github.com/DiegoTDDD/sec-mcp-agent/commit/e0bd06eb5040528f328dd61e42ac655439ac73fb):
  a wrong ticker falls back to the company the query names unambiguously; a ticker for a company
  that is not indexed (TM, SBUX in the same traces) still fails.
- **Evidence:** dataset `tool_calls/v2` (162 recorded calls, including the live run's) replayed
  through both versions: acceptance 83.3% → 85.2%, "not in the index" 20 → 17. The offline
  baseline moved to the new value, so a change that loses these calls again fails the gate.

## R6 — Langfuse removed the API the trace check read (this repository, found by the live run)

- **Detected by:** the first live run ([44557681399](https://github.com/DiegoTDDD/llm-evals-observability/actions/runs/44557681399)).
  Both projects' evals finished (sec-mcp-agent 22 questions, fraud-investigation-agents 30
  cases, 0 errors), then `check_langfuse.py` failed with HTTP 404 on `/api/public/traces`.
- **Cause:** Langfuse v4 removed the legacy read endpoints on 2026-11-16, three days before the
  run. OTLP ingestion was unaffected; only the check could not read the traces back.
- **Fix:** [20823cc](https://github.com/DiegoTDDD/llm-evals-observability/commit/20823cc): page
  through the Observations API v2 (`/api/public/v2/observations`) and count distinct trace ids,
  with a unit test for the cursor and the counting.

## Note — run-to-run variance is real, so the live gate has tolerances

Same code (sec-mcp-agent 80086e0), same model, temperature 0, same questions: 17/22 in the
project's own eval run and 14/22 in this repository's first live run. Ollama on a CPU is not
bit-for-bit repeatable, and one different token early in a reply changes the tool call. The
fraud-investigation-agents graph scored 76.7% in both: its tool arguments are written by code,
not by the model (that project's ADR 0001), so it varies less. `baselines/live.json` therefore
gates sec-mcp-agent's pass rate with a tolerance of 0.15 (about three questions) around the mean
of the two runs, and the fraud graph with one case (0.034).

Update after three live runs (results corrected in R8): sec-mcp-agent 14, 17 and 14 of 22,
and the fraud graph 76.7%, 80.0% and 80.0% with the same commit, so the graph is not
bit-for-bit repeatable either; the one-case tolerance covers that. Every run's numbers and
project versions are in the README table, written by the live run itself.

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
