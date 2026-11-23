# R ticket classifier

Training uses [Classification of IT Support Tickets](https://doi.org/10.5281/zenodo.7648117) by Leonardo Santiago Benitez Pereira (2022), under CC BY 4.0. The [Tasksource release](https://huggingface.co/datasets/tasksource/it-support-tickets) exposes ticket text and a seven-class label, with 1,572 training and 657 original test rows. The training script uses the author's versioned Zenodo CSVs, checks their published MD5 hashes, and joins the text and category files by ticket ID within each split. Ticket text is a single field, so the prediction API combines the title and description. The dataset has no priority labels.

The model trains against the following application label mapping. These are local routing choices.

| Source label | Application category |
| --- | --- |
| Active Directory | Account Access |
| Computer-Services | Hardware |
| Fileservice | Network |
| O365 | Software |
| Software | Software |
| EOL | Other |
| Support general | Other |

File service tickets are routed to Network Support for shared infrastructure triage. Broad or ambiguous source labels are routed to General Support. Technicians can override any assignment.

## Train and run

Work from `ml-r/` with R 4.4+ and the `Matrix` package, which is included in standard R distributions. Install the other packages once.

```powershell
Rscript -e "install.packages(c('stringi', 'plumber', 'LiblineaR'), repos='https://cloud.r-project.org')"
Rscript run.R
```

If the baseline artifact is missing, run `Rscript train.R` before starting Plumber. The training script downloads the verified CSVs when needed, creates a baseline serving artifact and rollback copy if absent, and saves the challenger separately. Run `Rscript audit.R` for dataset analysis and `Rscript test.R` for model tests. Reports go to `evaluation/`. CSV source data and model artifacts are ignored by Git. `LiblineaR` is only needed for training and model tests.

| Environment variable | Default |
| --- | --- |
| `ML_HOST` | `127.0.0.1` |
| `ML_PORT` | `8001` |
| `MODEL_PATH` | `models/ticket-classifier.rds`, relative to `ml-r/` |

`GET /health` reports `model_loaded`. `POST /predict` accepts JSON with string fields `title` and `description`. It returns the category, confidence, model version, and `classification_source: "model"`. Confidence is an uncalibrated score for the Naive Bayes baseline and a temperature-scaled score for the linear candidate. A missing or invalid artifact, or a ticket with no vocabulary terms, returns `Unclassified`, null confidence and version, and `classification_source: "fallback"`.

Open [Swagger UI](http://127.0.0.1:8001/__docs__/) and expand **POST /predict**. Click **Try it out** to edit the example JSON, then **Execute**. Both fields must be nonblank strings. Title accepts up to 160 characters and description up to 5,000. Malformed JSON and invalid fields return HTTP 400. With Plumber running and the model loaded, run `Rscript test-api.R` to check the OpenAPI contract and HTTP responses.

## Evaluation and model selection

The [dataset audit](evaluation/dataset-notes.md) and [model decision](evaluation/model-decision.md) include data quality findings, nested validation, held-out class metrics, and scenario results. The logistic candidate improved published test macro F1 from 0.6704 to 0.7401, but it matched the baseline on the synthetic suite and lowered Hardware and Software recall on the published test. The default remains `tfidf-nb-v1`.

The [licensed dataset comparison](evaluation/licensed-dataset-comparison.md) documents three further candidates, the [label crosswalk](evaluation/label-coverage.md), and the [training strategy](evaluation/recommended-training-strategy.md).

To evaluate the candidate in parallel with the running baseline, start another Plumber instance in PowerShell.

```powershell
$env:MODEL_PATH = 'models/tfidf-logreg-v2.rds'
$env:ML_PORT = '8002'
Rscript run.R
```

In a second terminal in `ml-r/`, run `Rscript test-api.R` with `TEST_ML_SERVICE_URL=http://127.0.0.1:8002` and `TEST_MODEL_VERSION=tfidf-logreg-v2`. To restart the baseline, stop its Plumber process and run `Rscript run.R` with `MODEL_PATH` and `ML_PORT` unset, or set `MODEL_PATH=models/tfidf-nb-v1.rds` explicitly to load the rollback copy.

## Replacement dataset audit

The proposed GitHub dataset was audited at a pinned revision. Its reuse permission could not be verified, so it remains audit-only. See the [audit](evaluation/new-dataset-audit.md), [comparison](evaluation/dataset-comparison.md), [label mapping](evaluation/label-mapping.md), and [experiment status](evaluation/model-comparison.md). Existing models are scored in place without fitting or writing artifacts.

From `ml-r/`, download only the audit inputs to a temporary directory and run the scripts.

```powershell
$commit = 'af5e9e7e5823b9b599df5b1f2bbb8d399fc3816d'
$source = "https://raw.githubusercontent.com/KS-Adharshini/SLM-Support-Ticket-Classifier/$commit"
$audit = Join-Path ([IO.Path]::GetTempPath()) 'helpdesk-replacement-audit'
New-Item -ItemType Directory -Force $audit | Out-Null
foreach ($file in 'data/tickets.csv','data/generate_data.py','README.md','config.yaml') {
  Invoke-WebRequest "$source/$file" -OutFile (Join-Path $audit (Split-Path $file -Leaf))
}
python -m unittest discover -s scripts -p test_audit_replacement.py
python scripts/audit_replacement.py (Join-Path $audit 'tickets.csv') (Join-Path $audit 'generate_data.py')
Rscript scripts/evaluate_existing.R
```

The Python command prints aggregate JSON. The R command prints complete metrics for the already saved `tfidf-nb-v1.rds` and `tfidf-logreg-v2.rds`. For future adjudication, copy the [blank human-review worksheet](evaluation/human-review-template.csv) into approved storage.

## Historical baseline

The original experiment normalized Unicode and case, removed bracketed placeholders, and used sparse TF-IDF with multinomial Naive Bayes. It selected smoothing on grouped validation data with seed 42, refit on the original 1,572 training rows, and evaluated on the original 657 test rows. For the current training workflow, see the model decision above.

Measured with R 4.6.2 using smoothing of 1:

| Split | Rows | Accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| Validation | 465 | 84.73% | 0.6647 |
| Original held-out test | 657 | 71.99% | 0.6704 |
| Test rows with unseen normalized text | 496 | 66.53% | 0.6357 |

The original test split includes 161 rows whose normalized text also appears in training. The 496-row subset measures performance after excluding those rows without altering the published split. The five application categories are unevenly represented. General Support cases account for most test errors.

Original test confusion matrix. Rows are actual categories and columns are predictions.

| Actual | Account Access | Hardware | Network | Other | Software | Unclassified |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Account Access | 23 | 4 | 1 | 10 | 10 | 1 |
| Hardware | 0 | 30 | 0 | 1 | 10 | 0 |
| Network | 1 | 7 | 118 | 0 | 12 | 0 |
| Other | 10 | 18 | 0 | 180 | 71 | 0 |
| Software | 11 | 12 | 0 | 5 | 122 | 0 |
