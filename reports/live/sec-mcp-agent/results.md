# Agent evaluation

Model `qwen2.5:3b` served by Ollama on a CPU-only GitHub Actions runner, temperature 0. 22 questions; 17 passed; 0 did not finish (model timeout or error).

| Metric | Value |
| --- | --- |
| Filings questions passed (right company, verified citations, expected evidence) | 75% |
| Searched the right company | 100% |
| Grounded (every citation verified against a retrieved passage) | 75% |
| Cited passage contains the expected evidence | 75% |
| Citation precision (citations on the asked company) | 100% |
| Out-of-scope questions answered without citing anything | 100% |
| Fraud questions scored with exactly the stated transaction | 75% |
| Faithful answers (every number in a source, no contradicted fraud verdict) | 96% |
| Answers stating the opposite of the fraud model's verdict | 0 |
| Answers sent back once for an invented chunk_id | 4 |
| Citations still rejected after that | 23 |
| Quotes copied exactly by the model / selected from the cited passage | 23 / 22 |
| Median / p90 latency per question | 99.8 s / 189.6 s |
| Mean tool calls per question | 1 |
| Total tokens | 116,404 |

## Per question

| id | type | passed | tools | citations | seconds | notes |
| --- | --- | --- | --- | --- | --- | --- |
| f01 | filings | yes | search_filings | 1 | 60.7 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f02 | filings | yes | search_filings | 5 | 104.3 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f03 | filings | yes | search_filings | 5 | 130.4 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f04 | filings | yes | search_filings | 4 | 95.2 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f05 | filings | yes | search_filings | 4 | 118.5 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f06 | filings | no | search_filings | 0 | 200.6 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f07 | filings | yes | search_filings | 5 | 119.1 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f08 | filings | no | search_filings | 0 | 69.8 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f09 | filings | yes | search_filings | 1 | 69.1 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f10 | filings | yes | search_filings | 5 | 141.9 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f11 | filings | no | search_filings | 0 | 189.6 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f12 | filings | yes | search_filings | 4 | 173.1 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f13 | filings | no | search_filings | 0 | 194.6 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f14 | filings | yes | search_filings | 5 | 142.7 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| f15 | filings | yes | search_filings | 1 | 89.6 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=False, unsupported_numbers=['341'], verdict_mismatch=False |
| f16 | filings | yes | search_filings | 5 | 140.8 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| o01 | out_of_scope | yes | search_filings! | 0 | 29.7 | cited=False, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| o02 | out_of_scope | yes | search_filings! | 0 | 16.7 | cited=False, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| t01 | fraud | yes | score_transaction | 0 | 73.2 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=0.039804, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| t02 | fraud | yes | score_transaction | 0 | 66.4 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=3e-06, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| t03 | fraud | no | score_transaction | 0 | 77.9 | called_tool=True, exact_arguments=False, model_flagged=False, model_probability=0.169204, faithful=True, unsupported_numbers=[], verdict_mismatch=False |
| t04 | fraud | yes | score_transaction | 0 | 80.4 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=0.095215, faithful=True, unsupported_numbers=[], verdict_mismatch=False |

Full answers: [transcripts/](transcripts/).
