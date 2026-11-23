# Training-only model comparison and calibration.
grouped_folds <- function(keys, labels, k, seed) {
  groups <- split(seq_along(keys), match(keys, unique(keys)))
  classes <- sort(unique(labels))
  set.seed(seed)
  order <- order(-lengths(groups), runif(length(groups)))
  load <- matrix(0, k, length(classes))
  folds <- integer(length(keys))
  for (index in order) {
    rows <- groups[[index]]
    counts <- tabulate(match(labels[rows], classes), nbins = length(classes))
    # Favor the fold with the lowest current load for the labels in this group.
    candidates <- which.min(as.vector(load %*% counts) + rowSums(load) * 1e-4)
    folds[rows] <- candidates
    load[candidates, ] <- load[candidates, ] + counts
  }
  stopifnot(all(seq_len(k) %in% folds), all(load > 0))
  folds
}

fit_candidate <- function(tokens, labels, config) {
  if (config$family == "naive_bayes") return(fit_model(tokens, labels, 1))
  terms <- feature_terms(tokens, config$bigrams)
  frequency <- table(unlist(lapply(terms, unique), use.names = FALSE))
  vocabulary <- names(frequency[frequency >= config$min_df])
  counts <- document_matrix(terms, vocabulary)
  idf <- log((1 + length(tokens)) / (1 + Matrix::colSums(counts > 0))) + 1
  features <- as(linear_features(counts, idf), "RsparseMatrix")
  classes <- sort(unique(labels))
  frequency <- table(factor(labels, levels = classes))
  weights <- if (config$weighted) setNames(sqrt(mean(frequency) / as.numeric(frequency)), classes)
  fit <- LiblineaR::LiblineaR(
    features, factor(labels, levels = classes), type = if (config$family == "logistic") 7 else 1,
    cost = config$cost, wi = weights, bias = 1
  )
  coefficients <- fit$W[classes, , drop = FALSE]
  list(
    version = unname(LINEAR_VERSIONS[config$family]), vocabulary = vocabulary, idf = idf,
    classes = classes, bigrams = config$bigrams, coefficients = coefficients[, seq_along(vocabulary),
      drop = FALSE], intercept = unname(coefficients[, ncol(coefficients)] * fit$Bias),
    temperature = 1
  )
}

candidate_grid <- function() {
  grid <- expand.grid(
    family = c("logistic", "svm"), cost = c(0.1, 1, 10), weighted = c(FALSE, TRUE),
    features = c("unigrams-df2", "bigrams-df2", "bigrams-df3"),
    stringsAsFactors = FALSE
  )
  grid$bigrams <- startsWith(grid$features, "bigrams")
  grid$min_df <- ifelse(grid$features == "bigrams-df3", 3L, 2L)
  rbind(data.frame(family = "naive_bayes", cost = NA_real_, weighted = FALSE,
                   features = "unigrams-df2", bigrams = FALSE, min_df = 2L), grid)
}

summarize_scores <- function(result, labels, temperature = 1) {
  classes <- colnames(result$scores)
  probabilities <- score_probabilities(result$scores, temperature)
  prediction <- classes[max.col(result$scores, ties.method = "first")]
  prediction[!result$known] <- "Unclassified"
  report <- classification_metrics(prediction, labels, classes)
  # Score abstentions as a uniform distribution for probability metrics.
  probabilities[!result$known, ] <- 1 / length(classes)
  truth <- match(labels, classes)
  selected <- cbind(seq_along(labels), truth)
  report$log_loss <- -mean(log(pmax(probabilities[selected], 1e-15)))
  report$brier <- mean(rowSums(probabilities ^ 2) - 2 * probabilities[selected] + 1)
  confidence <- apply(probabilities, 1L, max)
  report$confident_errors <- sum(prediction != labels & result$known & confidence >= 0.9)
  report
}

fit_temperature <- function(result, labels) {
  known <- result$known
  if (!any(known)) return(1)
  scores <- result$scores[known, , drop = FALSE]
  truth <- cbind(seq_len(nrow(scores)), match(labels[known], colnames(scores)))
  loss <- function(log_temperature) {
    probabilities <- score_probabilities(scores, exp(log_temperature))
    -mean(log(pmax(probabilities[truth], 1e-15)))
  }
  exp(optimize(loss, log(c(0.05, 20)))$minimum)
}

crossfit <- function(tokens, labels, folds, config) {
  classes <- sort(unique(labels))
  result <- list(scores = matrix(NA_real_, length(labels), length(classes),
                                 dimnames = list(NULL, classes)), known = logical(length(labels)))
  for (fold in sort(unique(folds))) {
    held <- folds == fold
    model <- fit_candidate(tokens[!held], labels[!held], config)
    scores <- score_tokens(model, tokens[held])
    result$scores[held, ] <- scores$scores
    result$known[held] <- scores$known
  }
  result
}

tune <- function(tokens, labels, folds, grid) {
  scores <- lapply(seq_len(nrow(grid)), function(i) crossfit(tokens, labels, folds, grid[i, ]))
  summaries <- lapply(scores, summarize_scores, labels = labels)
  metrics <- data.frame(
    macro_f1 = vapply(summaries, function(x) x$macro_f1, numeric(1)),
    accuracy = vapply(summaries, function(x) x$accuracy, numeric(1))
  )
  best <- order(-metrics$macro_f1, -metrics$accuracy)[[1]]
  list(config = grid[best, ], scores = scores[[best]], grid = cbind(grid, metrics))
}

nested_comparison <- function(tokens, labels, keys, folds, grid) {
  classes <- sort(unique(labels))
  families <- unique(grid$family)
  results <- setNames(lapply(families, function(family) {
    list(scores = matrix(NA_real_, length(labels), length(classes), dimnames = list(NULL, classes)),
         calibrated = matrix(NA_real_, length(labels), length(classes), dimnames = list(NULL, classes)),
         known = logical(length(labels)), fold_metrics = list())
  }), families)
  for (fold in sort(unique(folds))) {
    outer <- folds == fold
    inner <- grouped_folds(keys[!outer], labels[!outer], 4L, 4200L + fold)
    for (family in families) {
      tuning <- tune(tokens[!outer], labels[!outer], inner, grid[grid$family == family, ])
      temperature <- fit_temperature(tuning$scores, labels[!outer])
      fit <- fit_candidate(tokens[!outer], labels[!outer], tuning$config)
      result <- score_tokens(fit, tokens[outer])
      stored <- results[[family]]
      stored$scores[outer, ] <- result$scores
      stored$calibrated[outer, ] <- result$scores / temperature
      stored$known[outer] <- result$known
      summary <- summarize_scores(result, labels[outer], temperature)
      stored$fold_metrics[[fold]] <- cbind(fold = fold, tuning$config, temperature,
        macro_f1 = summary$macro_f1, accuracy = summary$accuracy)
      results[[family]] <- stored
    }
    message("Completed outer fold ", fold)
  }
  results
}
