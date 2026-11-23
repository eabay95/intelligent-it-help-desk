# Compare saved models without fitting or writing any artifacts.
source("model.R")
source("dataset.R")

fetch_dataset("data")
train <- read_split("data", "train")
test <- read_split("data", "test")
stopifnot(!any(train$id %in% test$id))
normalized <- function(tokens) vapply(tokens, paste, collapse = " ", FUN.VALUE = character(1))
test_tokens <- tokenize(test$text)
unseen <- !normalized(test_tokens) %in% normalized(tokenize(train$text))
scenarios <- read.csv("evaluation/scenarios.csv", encoding = "UTF-8")
scenario_tokens <- tokenize(paste(scenarios$title, scenarios$description))
teams <- c(
  Network = "Network Support", Hardware = "Hardware Support", Software = "Application Support",
  "Account Access" = "Identity & Access Support", Other = "General Support",
  Unclassified = "General Support"
)

report <- lapply(c("models/tfidf-nb-v1.rds", "models/tfidf-logreg-v2.rds"), function(path) {
  model <- load_model(path)
  evaluate_predictions <- function(predictions, labels) {
    list(
      classification = classification_metrics(predictions$category, labels, model$classes),
      default_team_routing_accuracy = mean(teams[predictions$category] == teams[labels]),
      high_confidence_incorrect = sum(predictions$category != labels &
                                        predictions$confidence >= 0.90, na.rm = TRUE)
    )
  }
  published <- predict_tokens(model, test_tokens)
  synthetic <- predict_tokens(model, scenario_tokens)
  list(
    version = model$version,
    published = evaluate_predictions(published, test$category),
    no_exact_training_overlap = evaluate_predictions(published[unseen, ], test$category[unseen]),
    synthetic = evaluate_predictions(synthetic, scenarios$expected),
    scenario_predictions = cbind(scenarios[c("id", "expected")], synthetic)
  )
})
print(report)
