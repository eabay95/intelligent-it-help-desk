DATASET_URL <- "https://zenodo.org/records/7648117/files/"
DATASET_MD5 <- c(
  "X_train.csv" = "0a79f0c2f95fcdb407f24b2c0ad7f7d1",
  "y_train.csv" = "90876921486a26a67bc1976da87305d9",
  "X_test.csv" = "02328c4e09a78a41acb22ce17e6e0312",
  "y_test.csv" = "2f054c0e3d8cbbbd76adf30d13a7710a"
)

fetch_dataset <- function(data_dir) {
  dir.create(data_dir, showWarnings = FALSE, recursive = TRUE)
  for (filename in names(DATASET_MD5)) {
    path <- file.path(data_dir, filename)
    expected <- DATASET_MD5[[filename]]
    if (!file.exists(path)) {
      downloaded <- paste0(path, ".download")
      status <- download.file(paste0(DATASET_URL, filename), downloaded, mode = "wb")
      if (status != 0L || tools::md5sum(downloaded)[[1]] != expected ||
          !file.rename(downloaded, path)) stop("Could not download verified dataset file ", filename)
    }
    if (tools::md5sum(path)[[1]] != expected) {
      stop("Checksum mismatch for ", path, ". Replace it with the published file.")
    }
  }
}

read_split <- function(data_dir, split) {
  read_file <- function(prefix) {
    read.csv(
      file.path(data_dir, paste0(prefix, "_", split, ".csv")),
      encoding = "UTF-8", colClasses = "character", na.strings = NULL
    )
  }
  texts <- read_file("X")
  labels <- read_file("y")
  stopifnot(
    all(c("id", "text") %in% names(texts)),
    all(c("id", "category_truth") %in% names(labels)),
    !anyNA(texts$id), !anyNA(labels$id), all(nzchar(texts$id)),
    !anyDuplicated(texts$id), !anyDuplicated(labels$id), setequal(texts$id, labels$id)
  )
  source_label <- labels$category_truth[match(texts$id, labels$id)]
  category <- unname(LABEL_MAPPING[source_label])
  stopifnot(!anyNA(category), !anyNA(texts$text))
  data.frame(id = texts$id, text = texts$text, category = category, source_label = source_label)
}

validation_rows <- function(tokens, labels) {
  keys <- vapply(tokens, paste, collapse = " ", FUN.VALUE = character(1))
  groups <- split(keys, labels)
  set.seed(42)
  held_out <- unlist(lapply(groups, function(values) {
    unique_keys <- unique(values)
    sample(unique_keys, max(1L, floor(length(unique_keys) * 0.2)))
  }), use.names = FALSE)
  keys %in% held_out
}

evaluate <- function(model, tokens, expected) {
  predicted <- predict_tokens(model, tokens)$category
  classification_metrics(predicted, expected, model$classes)
}

classification_metrics <- function(predicted, expected, classes) {
  confusion <- table(
    actual = factor(expected, levels = classes),
    predicted = factor(predicted, levels = c(classes, "Unclassified"))
  )
  correct <- diag(confusion[, classes, drop = FALSE])
  actual <- rowSums(confusion)
  predictions <- colSums(confusion)[classes]
  f1 <- ifelse(actual + predictions > 0, 2 * correct / (actual + predictions), 0)
  list(
    rows = length(expected),
    accuracy = mean(expected == predicted),
    macro_f1 = mean(f1),
    per_category = data.frame(
      support = actual, precision = ifelse(predictions > 0, correct / predictions, 0),
      recall = ifelse(actual > 0, correct / actual, 0), f1 = f1, row.names = classes
    ),
    confusion_matrix = confusion
  )
}
