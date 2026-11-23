# Model comparison and release decision

**Keep `tfidf-nb-v1` active.** The best candidate, `tfidf-logreg-v2`, improves agreement with the published corpus and has better probability scores within that corpus. Retain the versioned artifact for further evaluation. It matches the baseline's 7/20 on the synthetic routing suite, misses all six Network scenarios, and has lower held-out recall for Hardware and Software. The VPN failure is a coverage and taxonomy problem that the tested model families did not resolve.

## Selection and splits

The comparison uses five class-balanced outer folds with seed 42, grouping identical normalized text. Four grouped inner folds per outer fold select settings and fit calibration. Vocabulary, document frequency, IDF, and model parameters are fitted on each training partition. Near duplicates with different normalized strings can still cross validation folds. The published test labels were excluded from fitting and ranking. The baseline's published test numbers and the known VPN error had already motivated this work, so the published test is a retrospective benchmark for this project. The synthetic scenarios were frozen before training, include the known VPN example, and do not provide independent operational evidence.

Naive Bayes holds the current smoothing at 1. The candidates are one-vs-rest L2-regularized logistic regression and an L2-regularized linear SVM, both fitted with LiblineaR. They use the baseline text normalization, with optional adjacent word bigrams and document frequency of 2 or 3, followed by per-ticket L2-normalized log-TF-IDF. Costs are 0.1, 1, and 10. Class weighting compares uniform and inverse-square-root class frequency. Macro F1 ranks configs and families, with accuracy breaking ties. The winning logistic configuration uses bigrams plus unigrams, minimum document frequency 2, cost 10, and uniform weight. The final calibration temperature is 1.2726. The artifact was trained on November 22, 2026 with R 4.6.2 and LiblineaR 2.50-2.

## Training-only comparison

| Family | Accuracy | Macro F1 | Fold F1 SD | Log loss raw → calibrated | Brier raw → calibrated |
| --- | ---: | ---: | ---: | ---: | ---: |
| Naive Bayes | 71.95% | 0.6185 | 0.0794 | 3.6678 → 0.9341 | 0.4990 → 0.4248 |
| Logistic | 82.63% | 0.7537 | 0.0554 | 0.4761 → 0.4571 | 0.2436 → 0.2353 |
| Linear SVM | 81.36% | 0.7433 | 0.0695 | 0.7353 → 0.4851 | 0.3495 → 0.2447 |

Accuracy and macro F1 are pooled outer-fold estimates. A lower log loss or multiclass Brier score is better. Temperature scaling fits a positive scalar to inner out-of-fold scores. It changes confidence and preserves category rank. Held-out fold confidence for all families is softmax of scores, with SVM scores treated as margins. Unclassified examples count as misses for classification and receive a uniform distribution only for probability scoring. Naive Bayes produced 311 wrong predictions at 90% confidence or higher before calibration in these folds. Calibrated logistic produced 18. Even calibrated logistic predicted the known VPN example as Other at 85.78%, above the baseline's 77.46%. A confidence cutoff cannot identify the taxonomy gap on the current evidence. No uncertainty threshold was added.

## Published test

| Split | Baseline accuracy | Baseline macro F1 | Logistic accuracy | Logistic macro F1 |
| --- | ---: | ---: | ---: | ---: |
| Original, 657 rows | 71.99% | 0.6704 | 80.06% | 0.7401 |
| No exact training overlap, 496 rows | 66.53% | 0.6357 | 73.79% | 0.7017 |

The 496-row slice is a diagnostic and can contain near duplicates. On the full test set, the logistic model's Hardware precision increased from 42.25% to 87.50%, while Hardware recall fell from 73.17% to 51.22%. Software recall fell from 81.33% to 65.33%. Other recall increased from 64.52% to 91.04%. The gains are for reproducing the published labels. See the [complete metrics and confusion matrices](model-comparison.txt).

## Scenario routing and confident misses

| Expected category | Baseline correct | Logistic correct | Scenarios |
| --- | ---: | ---: | ---: |
| Account Access | 1 | 1 | 4 |
| Hardware | 2 | 1 | 4 |
| Network | 0 | 0 | 6 |
| Other | 1 | 1 | 2 |
| Software | 3 | 4 | 4 |

The logistic model fixed the application-crash scenario and regressed on the clicking-drive scenario. Both missed the VPN, Wi-Fi, DNS, account-lockout, and MFA cases. The [scenario fixture](scenarios.csv) and [per-ticket results](scenario-results.csv) are synthetic. The [highest-confidence corpus errors](confident-errors.csv) use source IDs and labels so the raw ticket text remains local. Examples include logistic predicting Other for account ticket 2618 at 97.71% and O365 ticket 707 at 97.18%.

A stronger release decision needs newly labeled production-like tickets, particularly VPN, Wi-Fi, DNS, identity, and hardware. Review labels against the routing taxonomy, group repeated templates, and reserve an operational holdout before tuning.
