# Agent evaluation

Model `qwen2.5:3b` served by Ollama on a CPU-only GitHub Actions runner, temperature 0. 22 questions; 14 passed; 0 did not finish (model timeout or error).

| Metric | Value |
| --- | --- |
| Filings questions passed (right company, verified citations, expected evidence) | 56% |
| Searched the right company | 88% |
| Grounded (every citation verified against a retrieved passage) | 56% |
| Cited passage contains the expected evidence | 56% |
| Citation precision (citations on the asked company) | 100% |
| Out-of-scope questions answered without citing anything | 100% |
| Fraud questions scored with exactly the stated transaction | 75% |
| Answers sent back once for an invented chunk_id | 5 |
| Citations still rejected after that | 14 |
| Quotes copied exactly by the model / selected from the cited passage | 20 / 10 |
| Median / p90 latency per question | 144.4 s / 196.4 s |
| Mean tool calls per question | 1.09 |
| Total tokens | 96,857 |

## Per question

| id | type | passed | tools | citations | seconds | notes |
| --- | --- | --- | --- | --- | --- | --- |
| f01 | filings | yes | search_filings | 1 | 91.4 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f02 | filings | yes | search_filings | 5 | 169.8 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f03 | filings | yes | search_filings | 5 | 182.7 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f04 | filings | yes | search_filings | 4 | 165.8 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f05 | filings | yes | search_filings | 3 | 168.9 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f06 | filings | yes | search_filings | 5 | 196.4 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f07 | filings | no | search_filings! | 0 | 26.5 | searched_company=False, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f08 | filings | no | search_filings search_filings | 0 | 211.3 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f09 | filings | no | search_filings | 0 | 178.6 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f10 | filings | no | search_filings | 0 | 158.4 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f11 | filings | yes | search_filings | 1 | 142.8 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f12 | filings | no | search_filings | 0 | 149.6 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f13 | filings | no | search_filings! | 0 | 43.4 | searched_company=False, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| f14 | filings | yes | search_filings | 5 | 210.9 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f15 | filings | yes | search_filings | 1 | 146.1 | searched_company=True, grounded=True, cited=True, citations_on_target=1.0, evidence_found=True |
| f16 | filings | no | search_filings | 0 | 122.0 | searched_company=True, grounded=False, cited=False, citations_on_target=None, evidence_found=False |
| o01 | out_of_scope | yes | search_filings! | 0 | 29.6 | cited=False |
| o02 | out_of_scope | yes | search_filings! | 0 | 27.6 | cited=False |
| t01 | fraud | yes | score_transaction | 0 | 112.5 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=0.039804 |
| t02 | fraud | yes | score_transaction | 0 | 87.2 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=3e-06 |
| t03 | fraud | no | score_transaction! score_transaction | 0 | 108.5 | called_tool=True, exact_arguments=False, model_flagged=False, model_probability=0.169204 |
| t04 | fraud | yes | score_transaction | 0 | 115.5 | called_tool=True, exact_arguments=True, model_flagged=False, model_probability=0.095215 |

Full answers: [transcripts/](transcripts/).
