# Replacement-data experiment status

| Arm | Status | Reason |
| --- | --- | --- |
| A. Existing data only | Reproduced by scoring both saved artifacts | Uses the existing licensed corpus and untouched artifact files |
| B. Replacement data only | Blocked | No explicit training permission. Four shared labels leave Other unrepresented. |
| C. Combined data | Blocked | No reuse permission and incompatible Other/Security boundaries |
| D. Curated replacement subset | Blocked | No reuse permission and no independently reviewed subset |

## Arm A results

| Metric | Naive Bayes v1 | Logistic v2 |
| --- | ---: | ---: |
| Published test accuracy / macro F1 | 71.99% / 0.6704 | 80.06% / 0.7401 |
| Published Network recall | 85.51% | 94.93% |
| Published Hardware recall | 73.17% | 51.22% |
| Published default-team routing accuracy | 71.99% | 80.06% |
| Published wrong predictions at confidence ≥ 90% | 161 | 12 |
| No exact overlap accuracy / macro F1 | 66.53% / 0.6357 | 73.79% / 0.7017 |
| Synthetic scenario accuracy / macro F1 | 35.00% / 0.3233 | 35.00% / 0.3231 |
| Synthetic Network / Hardware recall | 0/6 / 2/4 | 0/6 / 1/4 |
| Synthetic default-team routing accuracy | 35.00% | 35.00% |
| Synthetic wrong predictions at confidence ≥ 90% | 11 | 1 |

The VPN example is still Other at 77.46% confidence for v1 and 85.78% for v2. Both miss Wi-Fi, DNS and the other Network scenarios. The default-team metric maps category to the application's default team, including General Support for unclassified predictions. It does not measure configured overrides or real technician assignments. The published test set has known duplicate leakage and has been evaluated before. The 496-row slice removes exact normalized training matches, but near duplicates can remain. The synthetic suite is a diagnostic. [Full metrics, confusion matrices, and scenario predictions](replacement-baseline-metrics.txt)

## Controlled experiment design once permission and reviewed data exist

1. Freeze a new rights-cleared operational holdout with all five current categories, enough Network and Hardware cases, and separate Security escalation review. Assign template, near-duplicate, and repeated-incident groups before splitting. Keep each connected group in one partition across sources. Preserve the published holdout as a read-only historical benchmark and exclude any replacement training group that matches it.
2. For all eligible arms, use the same grouped training-only cross-validation protocol. Fit normalization-dependent vocabulary, TF-IDF, regularization, and confidence calibration inside the training folds. Reuse the project's R Naive Bayes and logistic estimators. Compare the same four shared classes in a diagnostic slice and report all five classes on the operational holdout, including B's inability to learn Other. Keep Security separate. Compare reviewed subset D only once there are enough independent groups.
3. Rank by macro F1 in validation, with special attention to Network and Hardware recall and default-team routing. On the frozen holdout, report accuracy, per-class precision and recall, confusion matrices, team routing, and high-confidence errors. Use the existing scenario suite only as a separately reported diagnostic. Keep any resulting RDS files in an explicit experiment directory outside `models/`. The evaluation script in this change reads only the saved Arm A artifacts and has no artifact-writing path.

No evidence supports blending the candidate CSV into training. The active baseline and saved challenger remain available.
