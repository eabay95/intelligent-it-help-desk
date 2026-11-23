# Recommended training strategy

**Human-label additional examples.** Keep the current artifacts and deployed version in place. The new sources supply examples for review, but none supplies sufficiently trustworthy labels for a five-category replacement or a defensible blend.

| Strategy | Decision |
| --- | --- |
| A. Existing source only | Reproduced using the saved baseline and challenger. Keep this as the control at the current taxonomy and holdout. |
| B. Best verified replacement only | No fit. Kaggle is closest to the existing routing task, but omits Network and Software labels, mixes other organizational queues, and has unverified upstream provenance. Mack is an unlabeled discovery pool. Mendeley offers operational conversational examples with coarse workflow types. |
| C. Carefully curated combination | Defer until independently reviewed, privacy-cleared labels and a sufficient frozen holdout exist. Blending coarse labels or generated prompts now would reward the wrong taxonomy. |

Reuse the [review worksheet](human-review-template.csv) with two independent reviewers and adjudication. Prioritize first-reporter or user-side text where provenance and privacy permit. Sample VPN transport failures and entitlement denials separately, Wi-Fi association and roaming, DNS resolution, and file-share reachability versus permissions. Balance these with physical laptop and printer failures, software installation/crashes, identity issues, and genuinely general requests. Don't derive labels from assistant answers or keyword matches. Retain an explicit `out_of_scope` or `needs_review` state in the research worksheet, outside the production taxonomy.

Before fitting, freeze an independently labeled operational holdout with all five categories. Group exact and near-duplicate texts, delexicalized templates, incident threads, and cross-source matches before assigning examples to folds. Keep each group together and keep the frozen holdout out of preprocessing fitting, vocabulary, tuning, and calibration. Keep the published benchmark available for historical comparison. Use the existing 20 scenarios as a diagnostic that has already informed decisions.

Compare the existing Naive Bayes and logistic pipelines and keep any experimental artifact outside the serving model directory. Rank candidates in group-aware validation by macro F1. Review Network and Hardware precision and recall explicitly before promotion. Run the frozen holdout once for accuracy, macro F1, per-category confusion, default-team routing, coverage or abstention if applicable, and wrong predictions above a predeclared confidence threshold. Analyze results by source, language, and incident type. Require a Network recall gain without a material Hardware regression and a review of high-confidence errors before considering deployment. The reported incumbent metrics remain an estimate of published-label agreement or diagnostic behavior, depending on the split.
