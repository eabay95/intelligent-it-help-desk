source("model.R")
source("dataset.R")
source("experiments.R")

stopifnot(identical(
  tokenize("  Acesso, CAF\u00c9 [TICKET ID]! O365  ")[[1]],
  c("acesso", "caf\u00e9", "o365")
))

fetch_dataset("data")
train <- read_split("data", "train")
test <- read_split("data", "test")
stopifnot(nrow(train) == 1572L, nrow(test) == 657L, !any(test$id %in% train$id))
stopifnot(setequal(train$category, unname(unique(LABEL_MAPPING))))
stopifnot(identical(unname(LABEL_MAPPING[train$source_label]), train$category))
tokens <- tokenize(train$text)
held_out <- validation_rows(tokens, train$category)
stopifnot(any(held_out), any(!held_out))
keys <- vapply(tokens, paste, collapse = " ", FUN.VALUE = character(1))
stopifnot(!any(keys[held_out] %in% keys[!held_out]))
folds <- grouped_folds(keys, train$category, 5L, 42L)
stopifnot(all(vapply(split(folds, keys), function(group) length(unique(group)) == 1L, logical(1))))
stopifnot(identical(
  feature_terms(tokenize("VPN Wi-Fi MFA IPv6"), TRUE)[[1]],
  c("vpn", "wi", "fi", "mfa", "ipv6", "vpn wi", "wi fi", "fi mfa", "mfa ipv6")
))

for (family in names(LINEAR_VERSIONS)) {
  inside <- folds != 1L
  config <- list(family = family, cost = 1, weighted = TRUE, bigrams = TRUE, min_df = 2L)
  fitted <- fit_candidate(tokens[inside], train$category[inside], config)
  fitted$temperature <- 1.5
  artifact <- tempfile(fileext = ".rds")
  saveRDS(fitted, artifact)
  loaded <- load_model(artifact)
  unlink(artifact)
  stopifnot(identical(fitted, loaded), identical(loaded$version, unname(LINEAR_VERSIONS[family])))
  result <- score_tokens(loaded, tokens[!inside])
  probabilities <- score_probabilities(result$scores, loaded$temperature)
  stopifnot(all(is.finite(probabilities)), all(abs(rowSums(probabilities) - 1) < 1e-10))
}

path <- Sys.getenv("MODEL_PATH", "models/ticket-classifier.rds")
model <- load_model(path)
stopifnot(inherits(try(load_model(tempfile()), silent = TRUE), "try-error"))
known_term <- model$vocabulary[[1]]
predicted <- predict_ticket(model, known_term, known_term)
stopifnot(
  setequal(names(predicted), c("category", "confidence", "model_version", "classification_source")),
  predicted$category %in% model$classes,
  is.double(predicted$confidence), predicted$confidence >= 0, predicted$confidence <= 1,
  identical(predicted$model_version, model$version),
  predicted$classification_source == "model"
)
fallback <- list(
  category = "Unclassified", confidence = NULL,
  model_version = NULL, classification_source = "fallback"
)
stopifnot(identical(predict_ticket(NULL, known_term, known_term), fallback))
stopifnot(identical(predict_ticket(model, "!", "?"), fallback))
stopifnot(identical(predict_ticket(model, "zzq9q8vunknown", "zzq7q6vunknown"), fallback))

report <- evaluate(model, tokenize(test$text), test$category)
stopifnot(
  sum(report$confusion_matrix) == nrow(test),
  is.finite(report$accuracy), report$accuracy >= 0, report$accuracy <= 1,
  is.finite(report$macro_f1), report$macro_f1 >= 0, report$macro_f1 <= 1
)
print(report)
cat("R preprocessing, artifact loading, prediction, fallback, and held-out evaluation checks passed.\n")
