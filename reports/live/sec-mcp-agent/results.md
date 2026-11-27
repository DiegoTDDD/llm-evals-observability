# Agent evaluation

Model `qwen2.5:3b` served by Ollama on a CPU-only GitHub Actions runner, temperature 0. 22 questions; 14 passed; 0 did not finish (model timeout or error).

| Metric | Value |
| --- | --- |
| Filings questions passed (right company, verified citations, expected evidence) | 56% |
| Searched the right company | 94% |
| Grounded (every citation verified against a retrieved passage) | 56% |
| Cited passage contains the expected evidence | 56% |
| Citation precision (citations on the asked company) | 100% |
| Out-of-scope questions answered without citing anything | 100% |
| Fraud questions scored with exactly the stated transaction | 75% |
| Answers sent back once for an invented chunk_id | 4 |
| Citations still rejected after that | 17 |
| Quotes copied exactly by the model / selected from the cited passage | 17 / 12 |
| Median / p90 latency per question | 100.6 s / 155.0 s |
| Mean tool calls per question | 1.05 |
| Total tokens | 109,328 |

## Per question

| id | type | passed | tools | citations | seconds | notes |
| --- | --- | --- | --- | --- | --- | --- |
| f01 | filings | yes | search_filings | 1 | 59.2 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f02 | filings | no | search_filings | 0 | 99.2 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f03 | filings | no | search_filings | 0 | 69.6 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f04 | filings | yes | search_filings | 4 | 104.4 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f05 | filings | yes | search_filings | 4 | 117.7 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f06 | filings | yes | search_filings | 4 | 129.9 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f07 | filings | no | search_filings! | 0 | 16.0 | searched_company=False, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f08 | filings | no | search_filings search_filings | 0 | 115.4 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f09 | filings | yes | search_filings | 1 | 94.4 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f10 | filings | no | search_filings | 0 | 221.0 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f11 | filings | yes | search_filings | 5 | 129.3 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f12 | filings | no | search_filings | 0 | 109.3 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f13 | filings | yes | search_filings | 4 | 117.5 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f14 | filings | no | search_filings | 0 | 275.4 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f15 | filings | yes | search_filings | 1 | 101.9 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f16 | filings | yes | search_filings | 5 | 155.0 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| o01 | out_of_scope | yes | search_filings! | 0 | 29.5 | cited=False |
| o02 | out_of_scope | yes | search_filings! | 0 | 17.1 | cited=False |
| t01 | fraud | yes | score_transaction | 0 | 78.3 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=0.039804 |
| t02 | fraud | yes | score_transaction | 0 | 72.8 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=3e-06 |
| t03 | fraud | no | score_transaction | 0 | 69.5 | called_tool=True, exact_arguments=False, model_flagged=False, model_probability=0.169204 |
| t04 | fraud | yes | score_transaction | 0 | 73.2 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=0.095215 |

Full answers: [transcripts/](transcripts/).
