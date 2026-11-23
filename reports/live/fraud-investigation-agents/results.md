# Investigation evaluation

30 alerts from the fraud model's test period with known answers. Language model `qwen2.5:3b` served by Ollama on a CPU-only GitHub Actions runner, temperature 0.

**Verdict**: fraud or legitimate. **Pattern**: the verdict and the fraud type (high_amount, card_testing, impossible_travel, or none for legitimate) are both right.

| System | Verdict | Pattern | Median seconds per case | Errors |
| --- | --- | --- | --- | --- |
| model_only | 97% | n/a (no pattern) | 0.0 | 0 |
| rules_only | 83% | 80% | 0.0 | 0 |
| single_agent | 80% | 40% | 25.12 | 0 |
| graph | 83% | 80% | 44.18 | 0 |

## Pattern accuracy by case type

| Case type | Cases | rules_only | single_agent | graph |
| --- | --- | --- | --- | --- |
| card_testing | 6 | 6 | 0 | 6 |
| card_testing (hard) | 2 | 0 | 0 | 0 |
| high_amount | 8 | 7 | 8 | 7 |
| impossible_travel | 7 | 5 | 0 | 5 |
| none | 4 | 3 | 4 | 3 |
| none (hard) | 3 | 3 | 0 | 3 |

## The critic loop

- Approved on the first round: 9
- Approved after the critic sent work back: 21
- Still rejected after 3 rounds: 0
- Critic rejections in total: 25; extra checks it requested: 11
- Cases the rework turned from wrong to right: 12; from right to wrong: 3
- Mean LLM calls per case: 2.83

## Per case

| Case | Expected | Difficulty | rules | single agent | graph | Rounds |
| --- | --- | --- | --- | --- | --- | --- |
| [c01](transcripts/c01.md) | high_amount | normal | fraud/high_amount ✓ | fraud/high_amount ✓ | fraud/high_amount ✓ | 1 |
| [c02](transcripts/c02.md) | high_amount | normal | fraud/high_amount ✓ | fraud/high_amount ✓ | fraud/high_amount ✓ | 1 |
| [c03](transcripts/c03.md) | high_amount | normal | fraud/high_amount ✓ | fraud/high_amount ✓ | fraud/high_amount ✓ | 1 |
| [c04](transcripts/c04.md) | high_amount | normal | fraud/high_amount ✓ | fraud/high_amount ✓ | fraud/high_amount ✓ | 1 |
| [c05](transcripts/c05.md) | high_amount | normal | fraud/high_amount ✓ | fraud/high_amount ✓ | fraud/high_amount ✓ | 1 |
| [c06](transcripts/c06.md) | high_amount | normal | fraud/high_amount ✓ | fraud/high_amount ✓ | fraud/high_amount ✓ | 1 |
| [c07](transcripts/c07.md) | high_amount | normal | fraud/high_amount ✓ | fraud/high_amount ✓ | fraud/high_amount ✓ | 1 |
| [c08](transcripts/c08.md) | high_amount | normal | legitimate/none ✗ | fraud/high_amount ✓ | legitimate/none ✗ | 2 |
| [c09](transcripts/c09.md) | card_testing | normal | fraud/card_testing ✓ | fraud/high_amount ✗ | fraud/card_testing ✓ | 2 |
| [c10](transcripts/c10.md) | card_testing | normal | fraud/card_testing ✓ | fraud/high_amount ✗ | fraud/card_testing ✓ | 2 |
| [c11](transcripts/c11.md) | card_testing | normal | fraud/card_testing ✓ | fraud/high_amount ✗ | fraud/card_testing ✓ | 2 |
| [c12](transcripts/c12.md) | card_testing | normal | fraud/card_testing ✓ | fraud/high_amount ✗ | fraud/card_testing ✓ | 2 |
| [c13](transcripts/c13.md) | card_testing | normal | fraud/card_testing ✓ | fraud/high_amount ✗ | fraud/card_testing ✓ | 2 |
| [c14](transcripts/c14.md) | card_testing | normal | fraud/card_testing ✓ | legitimate/none ✗ | fraud/card_testing ✓ | 2 |
| [c15](transcripts/c15.md) | card_testing | hard: first charge of a burst | legitimate/none ✗ | legitimate/none ✗ | legitimate/none ✗ | 3 |
| [c16](transcripts/c16.md) | card_testing | hard: first charge of a burst | legitimate/none ✗ | legitimate/none ✗ | legitimate/none ✗ | 3 |
| [c17](transcripts/c17.md) | impossible_travel | normal | fraud/card_testing ✗ | fraud/high_amount ✗ | fraud/card_testing ✗ | 3 |
| [c18](transcripts/c18.md) | impossible_travel | normal | fraud/impossible_travel ✓ | fraud/high_amount ✗ | fraud/impossible_travel ✓ | 2 |
| [c19](transcripts/c19.md) | impossible_travel | normal | fraud/impossible_travel ✓ | fraud/high_amount ✗ | fraud/impossible_travel ✓ | 2 |
| [c20](transcripts/c20.md) | impossible_travel | normal | fraud/impossible_travel ✓ | fraud/high_amount ✗ | fraud/impossible_travel ✓ | 2 |
| [c21](transcripts/c21.md) | impossible_travel | normal | fraud/impossible_travel ✓ | fraud/high_amount ✗ | fraud/impossible_travel ✓ | 2 |
| [c22](transcripts/c22.md) | impossible_travel | normal | fraud/impossible_travel ✓ | fraud/high_amount ✗ | fraud/impossible_travel ✓ | 2 |
| [c23](transcripts/c23.md) | impossible_travel | normal | legitimate/none ✗ | fraud/high_amount ✗ | legitimate/none ✗ | 2 |
| [c24](transcripts/c24.md) | none | normal | fraud/card_testing ✗ | legitimate/none ✓ | fraud/card_testing ✗ | 2 |
| [c25](transcripts/c25.md) | none | normal | legitimate/none ✓ | legitimate/none ✓ | legitimate/none ✓ | 1 |
| [c26](transcripts/c26.md) | none | normal | legitimate/none ✓ | legitimate/none ✓ | legitimate/none ✓ | 1 |
| [c27](transcripts/c27.md) | none | normal | legitimate/none ✓ | legitimate/none ✓ | legitimate/none ✓ | 3 |
| [c28](transcripts/c28.md) | none | hard: legitimate purchase outside the home city | legitimate/none ✓ | fraud/high_amount ✗ | legitimate/none ✓ | 2 |
| [c29](transcripts/c29.md) | none | hard: legitimate purchase outside the home city | legitimate/none ✓ | fraud/high_amount ✗ | legitimate/none ✓ | 2 |
| [c30](transcripts/c30.md) | none | hard: legitimate purchase outside the home city | legitimate/none ✓ | fraud/high_amount ✗ | legitimate/none ✓ | 2 |
