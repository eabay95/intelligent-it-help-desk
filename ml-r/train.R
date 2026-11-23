source("model.R")
source("dataset.R")
source("experiments.R")

fetch_dataset("data")
train <- read_split("data", "train")
stopifnot(nrow(train) == 1572L)
tokens <- tokenize(train$text)
keys <- vapply(tokens, paste, collapse = " ", FUN.VALUE = character(1))
labels <- train$category
grid <- candidate_grid()
folds <- grouped_folds(keys, labels, 5L, 42L)
nested <- nested_comparison(tokens, labels, keys, folds, grid)

summaries <- lapply(nested, function(x) {
  raw <- summarize_scores(x, labels)
  calibrated <- summarize_scores(list(scores = x$calibrated, known = x$known), labels)
  fold_metrics <- do.call(rbind, x$fold_metrics)
  list(raw = raw, calibrated = calibrated, folds = fold_metrics,
       fold_f1_sd = sd(fold_metrics$macro_f1))
})
comparison <- do.call(rbind, lapply(names(summaries), function(family) {
  result <- summaries[[family]]
  data.frame(
    family, accuracy = result$raw$accuracy, macro_f1 = result$raw$macro_f1,
    fold_f1_sd = result$fold_f1_sd, raw_log_loss = result$raw$log_loss,
    calibrated_log_loss = result$calibrated$log_loss, raw_brier = result$raw$brier,
    calibrated_brier = result$calibrated$brier,
    raw_confident_errors = result$raw$confident_errors,
    calibrated_confident_errors = result$calibrated$confident_errors,
    calibrated_account_recall = result$calibrated$per_category["Account Access", "recall"],
    calibrated_hardware_recall = result$calibrated$per_category["Hardware", "recall"]
  )
}))
# Rank families without seeing the held-out test set or synthetic scenarios.
ranking <- order(-comparison$macro_f1, -comparison$accuracy)
winner <- comparison$family[ranking[[1]]]
linear <- setdiff(comparison$family[ranking], "naive_bayes")[[1]]
tuning <- tune(tokens, labels, folds, grid[grid$family == linear, ])
challenger <- fit_candidate(tokens, labels, tuning$config)
challenger$temperature <- fit_temperature(tuning$scores, labels)
challenger$training <- list(
  date = format(Sys.time(), "%Y-%m-%d", tz = "America/Los_Angeles"), dataset = "10.5281/zenodo.7648117",
  rows = nrow(train), seed = 42L, preprocessing = "NFC casefold, placeholders removed, log-TF-IDF L2",
  config = tuning$config, nested_validation = summaries[[linear]]$calibrated,
  liblinear_version = as.character(utils::packageVersion("LiblineaR"))
)
baseline <- fit_model(tokens, labels, 1)

# Only the fixed baseline and training-selected challenger enter the final evaluation.
test <- read_split("data", "test")
stopifnot(nrow(test) == 657L, !any(test$id %in% train$id))
test_tokens <- tokenize(test$text)
test_keys <- vapply(test_tokens, paste, collapse = " ", FUN.VALUE = character(1))
new_text <- !test_keys %in% keys
scenarios <- read.csv("evaluation/scenarios.csv", encoding = "UTF-8")
scenario_tokens <- tokenize(paste(scenarios$title, scenarios$description))
stopifnot(!any(vapply(scenario_tokens, paste, collapse = " ", FUN.VALUE = character(1)) %in% keys))
models <- list(baseline = baseline, challenger = challenger)
held_out <- lapply(models, function(model) list(
  original = evaluate(model, test_tokens, test$category),
  no_exact_overlap = evaluate(model, test_tokens[new_text], test$category[new_text])
))
challenger$training$test <- held_out$challenger
challenger$training$limitations <- paste(
  "Published labels group connectivity into Other and Network is primarily file services.",
  "Published test data has exact and near duplicates; no independent operational set."
)
scenario_results <- do.call(rbind, lapply(models, function(model) {
  cbind(scenarios[, c("id", "expected")], version = model$version,
        predict_tokens(model, scenario_tokens))
}))
wrong_examples <- function(model) {
  predicted <- predict_tokens(model, test_tokens)
  incorrect <- which(predicted$category != test$category & !is.na(predicted$confidence))
  top <- head(incorrect[order(-predicted$confidence[incorrect])], 5)
  data.frame(id = test$id[top], source_label = test$source_label[top], expected = test$category[top],
             predicted[top, ], version = model$version)
}

dir.create("models", showWarnings = FALSE)
baseline_path <- "models/tfidf-nb-v1.rds"
if (!file.exists(baseline_path)) saveRDS(baseline, baseline_path)
serving_path <- "models/ticket-classifier.rds"
if (!file.exists(serving_path)) saveRDS(baseline, serving_path)
artifact <- file.path("models", paste0(challenger$version, ".rds"))
saveRDS(challenger, artifact)
write.csv(comparison, "evaluation/candidate-comparison.csv", row.names = FALSE)
write.csv(tuning$grid, "evaluation/selected-family-tuning.csv", row.names = FALSE)
write.csv(scenario_results, "evaluation/scenario-results.csv", row.names = FALSE)
write.csv(do.call(rbind, lapply(models, wrong_examples)), "evaluation/confident-errors.csv", row.names = FALSE)
report <- list(
  training_selected_family = winner, challenger_artifact = artifact,
  challenger_metadata = challenger$training[c("date", "config", "preprocessing", "liblinear_version")],
  classes = challenger$classes, challenger_temperature = challenger$temperature,
  validation = summaries, original_test_rows_seen_in_training = sum(!new_text),
  held_out = held_out, scenarios_correct = with(scenario_results, table(version, expected == category))
)
capture.output(print(report), file = "evaluation/model-comparison.txt")
print(comparison)
print(lapply(held_out, function(x) lapply(x, function(y) c(accuracy = y$accuracy, macro_f1 = y$macro_f1))))
print(report$scenarios_correct)
message("Saved ", artifact, ". The active artifact was preserved.")
