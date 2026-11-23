# Audit of three licensed ticket datasets

**Recommendation: Human-label additional examples.** Kaggle is the closest labeled schema, and Mack is the richest starting pool for Network annotation. None of the three releases currently supports a trustworthy five-category replacement. All downloads succeeded. The models and application were untouched.

## Actual rows and text quality

| Audited unit | Rows | Nonblank normalized text | Missing text | Exact duplicate excess | Normalized duplicate excess | Near-only pairs / affected rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A. Mendeley issue metadata | 66,691 | No text field | No description column | — | — | — |
| A. All sampled conversation utterances | 30,104 | 29,883 | 23 | 21,532 | 21,799 | 123 / 2,357 |
| A. First available public reporter comment per issue | 356 | 356 | 0 | 0 | 1 | 2 / 4 |
| B. Kaggle v1 ticket documents | 47,837 | 47,837 | 0 | 0 | 0 | 6,192 / 1,940 |
| C. Mack user prompts | 103,226 | 103,226 | 0 | 29,596 | 30,367 | 3,484 / 10,156 |

Excess duplicates count eligible rows beyond one per text. Normalization uses Unicode NFC, case folding, bracket placeholder removal, and punctuation/spacing normalization. Near-only pairs have different normalized text, at least three shared distinct word trigrams, and Jaccard similarity of at least 0.8. Pair counts are distinct normalized text pairs. Affected row counts include copies. Boilerplate or templates can recur with lower similarity and are not exhaustively identified by this measure. The audit emits aggregate counts rather than ticket text. [Full aggregate audit and source hashes](licensed-audit.json)

### A. Mendeley operational workflow and conversation sample

Issue metadata types are Ticket 45,275, Service 5,300, Subtask 4,746, Story 4,538, HD Service 1,686, Task 1,540, Vacation 856, Project 842, Sub-task 544, Epic 403, Deployment 350, Retrospective 241, Sprint Summary 208, Assistance 109, and Bug 53. These are workflow types. The text sample represents 360 issues and all utterances joined to an issue. There are 5,700 reporter, 12,820 assignee, and 11,584 other-role utterances. The first available public reporter comments break down as Ticket 338, Deployment 9, and HD Service 9. They are proxies for intake text, and the sample may start later in an incident thread.

- All-utterance median length is 13 characters, with 9–55 interquartile range. The first-comment median is 155 characters, with 103–248 interquartile range. Thirty thousand utterances therefore represent far fewer independent routing events.
- Among 2,000 sampled usable utterances, the detector found 736 English, 1,261 undetermined, and three other. In the 356 reporter comments it found 339 English, six Arabic, and 11 undetermined.
- Identifier/number masking adds only 25 template matches beyond normalized equality for utterances. The largest masked group contains 4,714 rows. Eighty-five normalized utterance groups have conflicting joined workflow types, consistent with generic utterances occurring in several issue types. The first-public-reporter subset has no such conflicts and only one normalized excess copy.
- The release flags 8,707 utterances as private in the source workflow. Automated screening found two credential-format indicators among all utterances and none in the first-reporter subset. The dataset also retains masked metadata identifiers. Use redaction review and exclude private comments from any proposed training input. [Publisher provenance](https://data.mendeley.com/datasets/btm76zndnt/3)

### B. Kaggle processed labeled release

| Source label | Rows |
| --- | ---: |
| Hardware | 13,617 |
| HR Support | 10,915 |
| Access | 7,125 |
| Miscellaneous | 7,060 |
| Storage | 2,777 |
| Purchase | 2,464 |
| Internal Project | 2,119 |
| Administrative rights | 1,760 |

The downloaded CSV confirms the publisher's dimensions and exactly the columns `Document` and `Topic_group`. Hardware is 28.46% of rows and Administrative rights is 3.68%. Typical document length is 175 characters with a 110–304 interquartile range and 7–7,015 full range. Language screening of 2,000 rows found 1,907 English, 71 undetermined, and 22 other. Processing and mixed jargon can make language detection unreliable. The identifier/number template check adds no collisions on top of normalized equality. Of 6,192 near-only pairs, 397 have different source labels. Similar text can describe different requests, so this finding flags pairs for review. Zero exact normalized label conflicts is expected with zero duplicates and says little about correctness.

The processed file has zero hits for the five sensitive patterns measured. That finding cannot clear names, internal identifiers, or obfuscated data. The original publisher does not establish how upstream records were collected or classified. Topics describe queues including HR and Procurement, and there is no Network or Software routing label. [Original release](https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset/versions/1) · [Publisher API](https://www.kaggle.com/api/v1/datasets/view/adisongoh/it-service-ticket-classification-dataset)

### C. Mack generated conversations

All 103,226 records have exactly a user turn and an assistant turn under `messages`. All are unlabeled for routing. There are 8,989 assistant replies in snake-case tag form. Other replies include technical guidance and persona responses, which makes reply-as-label unreliable. User prompts have median length 50 characters, interquartile range 42–60, and full range 5–490. The card declares English. Screening 2,000 prompts found 1,682 English, 243 undetermined, and 75 other predictions. Short, stylized prompts and technical vocabulary make these estimates noisy. The near-match and exact-repetition counts support grouping before any annotation or evaluation. Masking identifiers and numbers produces 1,975 additional collisions over normalized equality. The largest resulting group has 375 rows. Repeated persona or task openings include 19,354 prompts beginning with Explain and 17,513 with Mack.

Pattern screening found eight user prompts with IPv4-format strings. Assistant replies contain 10 email-format, 14 IPv4-format, and 11 URL indicators. The checks cannot determine whether they are synthetic or sensitive. Audit reports include no values. Use the user turn only after redaction, deduplication, and human triage. [Publisher card](https://huggingface.co/datasets/benjaminmacklin/IT_Support_V2)

## Reproduced experiment A

| Metric | Saved Naive Bayes v1 | Saved logistic v2 |
| --- | ---: | ---: |
| Published accuracy / macro F1 | 71.99% / 0.6704 | 80.06% / 0.7401 |
| Published Network recall | 85.51% | 94.93% |
| Published Hardware recall | 73.17% | 51.22% |
| Published default-team routing accuracy | 71.99% | 80.06% |
| Published high-confidence misses (≥90%) | 161 | 12 |
| Synthetic scenario accuracy / macro F1 | 35.00% / 0.3233 | 35.00% / 0.3231 |
| Synthetic Network recall | 0/6 | 0/6 |
| Synthetic Hardware recall | 2/4 | 1/4 |

The source-only result was reproduced with the saved RDS files. See [complete per-category metrics, confusion matrices, diagnostic subset and routing results](licensed-baseline-metrics.txt). Neither candidate training nor blending was justified by the labels. The previous scenarios are diagnostics. See the [strategy](recommended-training-strategy.md) for a frozen operational holdout.

## Reproduce

From `ml-r/` in PowerShell with Python and the existing R environment:

```powershell
python scripts/fetch_licensed.py
$root = Join-Path ([IO.Path]::GetTempPath()) 'helpdesk-licensed-audit'
python -m pip install --target (Join-Path $root 'audit-deps') langdetect==1.0.9
$env:PYTHONPATH = Join-Path $root 'audit-deps'
python -m unittest discover -s scripts -p 'test_audit_*.py'
python scripts/audit_licensed.py $root
Rscript scripts/evaluate_existing.R
$env:TEST_MODEL_VERSION = 'tfidf-nb-v1'
Rscript test-api.R
```

`fetch_licensed.py` checks all four SHA-256 pins. The Python script prints aggregate JSON. The R script prints baseline metrics and writes no artifacts. Language estimates use deterministic samples of up to 2,000 usable texts with seed 42. Text with fewer than 25 letters or detector confidence below 0.8 is undetermined. Sensitive rows are counts of email, IPv4, phone, URL, and explicit credential-assignment patterns. Pattern hits can be false positives. No hits do not establish anonymization.
