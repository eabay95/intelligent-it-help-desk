LABEL_MAPPING <- c(
  "Active Directory" = "Account Access",
  "Computer-Services" = "Hardware",
  "EOL" = "Other",
  "Fileservice" = "Network",
  "O365" = "Software",
  "Software" = "Software",
  "Support general" = "Other"
)
MODEL_VERSION <- "tfidf-nb-v1"
LINEAR_VERSIONS <- c(logistic = "tfidf-logreg-v2", svm = "tfidf-svm-v2")

tokenize <- function(text) {
  text <- stringi::stri_trans_casefold(stringi::stri_trans_nfc(text))
  text <- stringi::stri_replace_all_regex(text, "\\[[^\\[\\]]+\\]", " ")
  text <- stringi::stri_replace_all_regex(text, "[^\\p{L}\\p{N}]+", " ")
  strsplit(trimws(text), " +")
}

document_matrix <- function(tokens, vocabulary) {
  indices <- match(unlist(tokens, use.names = FALSE), vocabulary)
  document <- rep.int(seq_along(tokens), lengths(tokens))
  known <- !is.na(indices)
  Matrix::sparseMatrix(
    i = document[known], j = indices[known], x = rep(1, sum(known)),
    dims = c(length(tokens), length(vocabulary))
  )
}

tfidf <- function(counts, idf) {
  log1p(counts) %*% Matrix::Diagonal(x = idf)
}

fit_model <- function(tokens, labels, alpha) {
  frequencies <- table(unlist(lapply(tokens, unique), use.names = FALSE))
  vocabulary <- names(frequencies[frequencies >= 2])
  stopifnot(length(vocabulary) > 0, all(unique(LABEL_MAPPING) %in% labels))
  counts <- document_matrix(tokens, vocabulary)
  idf <- log((1 + length(tokens)) / (1 + Matrix::colSums(counts > 0))) + 1
  features <- tfidf(counts, idf)
  classes <- sort(unique(labels))
  class_counts <- do.call(rbind, lapply(classes, function(category) {
    Matrix::colSums(features[labels == category, , drop = FALSE])
  }))
  smoothed <- class_counts + alpha
  list(
    version = MODEL_VERSION,
    vocabulary = vocabulary,
    idf = idf,
    classes = classes,
    log_terms = log(smoothed / rowSums(smoothed)),
    log_prior = log(as.numeric(table(factor(labels, levels = classes))) / length(labels))
  )
}

feature_terms <- function(tokens, bigrams) {
  lapply(tokens, function(words) {
    words <- words[nzchar(words)]
    if (!bigrams || length(words) < 2L) return(words)
    c(words, paste(head(words, -1L), tail(words, -1L)))
  })
}

linear_features <- function(counts, idf) {
  features <- tfidf(counts, idf)
  norm <- sqrt(Matrix::rowSums(features ^ 2))
  Matrix::Diagonal(x = 1 / ifelse(norm > 0, norm, 1)) %*% features
}

score_tokens <- function(model, tokens) {
  baseline <- identical(model$version, MODEL_VERSION)
  terms <- if (baseline) tokens else feature_terms(tokens, model$bigrams)
  counts <- document_matrix(terms, model$vocabulary)
  features <- if (baseline) tfidf(counts, model$idf) else linear_features(counts, model$idf)
  coefficients <- if (baseline) model$log_terms else model$coefficients
  intercept <- if (baseline) model$log_prior else model$intercept
  scores <- sweep(as.matrix(features %*% t(coefficients)), 2L, intercept, "+")
  colnames(scores) <- model$classes
  list(scores = scores, known = Matrix::rowSums(counts) > 0)
}

score_probabilities <- function(scores, temperature = 1) {
  scaled <- scores / temperature
  exponent <- exp(sweep(scaled, 1L, apply(scaled, 1L, max), "-"))
  exponent / rowSums(exponent)
}

predict_tokens <- function(model, tokens) {
  result <- score_tokens(model, tokens)
  scores <- result$scores
  best <- max.col(scores, ties.method = "first")
  probabilities <- score_probabilities(scores, if (is.null(model$temperature)) 1 else model$temperature)
  data.frame(
    category = ifelse(result$known, model$classes[best], "Unclassified"),
    confidence = ifelse(result$known, probabilities[cbind(seq_along(best), best)], NA_real_)
  )
}

load_model <- function(path) {
  if (!file.exists(path)) stop("Ticket model artifact does not exist.")
  model <- readRDS(path)
  if (!is.list(model) || length(model$version) != 1L ||
      !model$version %in% c(MODEL_VERSION, LINEAR_VERSIONS) ||
      !is.character(model$vocabulary) || length(model$vocabulary) == 0L ||
      !setequal(model$classes, unname(unique(LABEL_MAPPING))) || anyDuplicated(model$classes) ||
      !is.numeric(model$idf) || length(model$idf) != length(model$vocabulary) ||
      !all(is.finite(model$idf))) {
    stop("Invalid ticket model artifact.")
  }
  baseline <- identical(model$version, MODEL_VERSION)
  coefficients <- if (baseline) model$log_terms else model$coefficients
  intercept <- if (baseline) model$log_prior else model$intercept
  if (!is.matrix(coefficients) || !is.numeric(coefficients) ||
      !identical(dim(coefficients), c(length(model$classes), length(model$vocabulary))) ||
      !is.numeric(intercept) || length(intercept) != length(model$classes) ||
      !all(is.finite(c(coefficients, intercept))) ||
      (!baseline && (!is.logical(model$bigrams) || length(model$bigrams) != 1L ||
        is.na(model$bigrams) || !is.numeric(model$temperature) || length(model$temperature) != 1L ||
        !is.finite(model$temperature) || model$temperature <= 0))) {
    stop("Invalid ticket model artifact.")
  }
  model
}

predict_ticket <- function(model, title, description) {
  if (!is.null(model)) {
    result <- predict_tokens(model, tokenize(paste(title, description)))
    if (result$category != "Unclassified") {
      return(list(
        category = result$category, confidence = result$confidence,
        model_version = model$version, classification_source = "model"
      ))
    }
  }
  list(
    category = "Unclassified", confidence = NULL,
    model_version = NULL, classification_source = "fallback"
  )
}
