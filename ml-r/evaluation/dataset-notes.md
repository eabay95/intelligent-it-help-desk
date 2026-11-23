# Dataset audit

The source is Leonardo Santiago Benitez Pereira's [Classification of IT Support Tickets](https://doi.org/10.5281/zenodo.7648117), licensed CC BY 4.0. The versioned CSV files join CSV columns `id,text` and `id,category_truth`. There is one free-text file per split and no independent description, language, impact, or priority field in the joined data. Keep the published 1,572/657 split. [Tasksource dataset card](https://huggingface.co/datasets/tasksource/it-support-tickets)

| Original category | Application category | Train | Test |
| --- | --- | ---: | ---: |
| Active Directory | Account Access | 84 | 49 |
| Computer-Services | Hardware | 65 | 41 |
| EOL | Other | 45 | 58 |
| Fileservice | Network | 546 | 138 |
| O365 | Software | 127 | 92 |
| Software | Software | 164 | 58 |
| Support general | Other | 541 | 221 |

There are no blank source texts and one training text becomes empty after normalization. Excess normalized copies within train and test number 660 and 129. Two normalized-text groups have conflicting mapped labels. The audit also finds 116 near-only pairs within train, 65 within test, and 139 across splits. A near-only pair has different normalized text, at least three shared distinct word trigrams, and trigram Jaccard similarity of at least 0.80. The cross-split pairs involve 63 test rows. Separately, 161 test rows have an exact normalized match in training. See [full audit](dataset-audit.txt) and [term counts](term-coverage.csv).

**Why the VPN example fails.** The baseline predicts Other at 0.7746. The token `vpn` is in its fitted vocabulary. Ten training tickets mention VPN, with nine mapped to Other and one to Account Access. Zero Network training tickets mention VPN, Wi-Fi variants, or DNS under the audit patterns. In contrast, 470 of 546 Network training tickets contain `file`. So this label primarily teaches file services. Training shows the same issue for account terminology. Eleven password mentions are in Network, five in Account Access, and eight in Other. The tested MFA patterns are absent throughout. Hardware terms are better represented, especially printer-related terms in Hardware. Software terms appear across categories.

Manual inspection of the original training labels found explicit VPN connection failure and DNS troubleshooting within Support general. These would reasonably route to Network under the application taxonomy. A VPN permission request could instead belong to Account Access. Term counts are coverage proxies and cannot justify bulk relabeling. The published labels and application mapping are retained for comparable evaluation.

**Baseline.** Unicode NFC normalization and case folding remove bracketed placeholders and split on punctuation. A document-frequency floor of 2 selects word unigrams. Log-count TF-IDF feeds multinomial Naive Bayes with smoothing of 1 and empirical class priors. Confidence is a softmax of summed class log scores. Long repeated evidence can make the scores overly certain. The original fit scored 71.99% accuracy and 0.6704 macro F1 on the published test set, and 66.53% and 0.6357 on 496 rows that have no exact normalized training match. That subset can still contain near duplicates.
