source("model.R")
source("dataset.R")

token_keys <- function(tokens) vapply(tokens, paste, collapse = " ", FUN.VALUE = character(1))

shingles <- function(tokens) lapply(tokens, function(words) {
  n <- length(words)
  if (n < 3L) return(character())
  unique(paste(words[seq_len(n - 2L)], words[2L:(n - 1L)], words[3L:n]))
})

# Near duplicates must differ under exact normalization and share 80% of word trigrams.
near_pairs <- function(tokens, keys) {
  grams <- shingles(tokens)
  vocabulary <- unique(unlist(grams, use.names = FALSE))
  incidence <- document_matrix(grams, vocabulary)
  overlap <- Matrix::summary(Matrix::tcrossprod(incidence))
  sizes <- lengths(grams)
  keep <- overlap$i < overlap$j & keys[overlap$i] != keys[overlap$j] &
    overlap$x >= 3L & overlap$x / (sizes[overlap$i] + sizes[overlap$j] - overlap$x) >= 0.8
  overlap[keep, c("i", "j")]
}

fetch_dataset("data")
train <- read_split("data", "train")
test <- read_split("data", "test")
all <- rbind(train, test)
split <- rep(c("Train", "Test"), c(nrow(train), nrow(test)))
tokens <- tokenize(all$text)
keys <- token_keys(tokens)
pairs <- near_pairs(tokens, keys)
near_counts <- function(keep) {
  edges <- pairs[keep, ]
  c(pairs = nrow(edges), rows = length(unique(c(edges$i, edges$j))))
}

terms <- list(
  VPN = "vpn", WiFi = "wi[ -]?fi|wlan|wireless", DNS = "dns",
  Network = "network|rede|netzwerk", Login = "login|log[ -]?in|sign[ -]?in",
  Password = "password|senha|passwort", MFA = "mfa|2fa|authenticator",
  Hardware = "hardware|laptop|printer|impressora", Software = "software|install|crash"
)
normalized <- stringi::stri_trans_casefold(all$text)
coverage <- do.call(rbind, lapply(names(terms), function(name) {
  matches <- grepl(paste0("\\b(", terms[[name]], ")\\b"), normalized, perl = TRUE)
  counts <- as.data.frame(table(split, all$category, factor(matches, levels = c(FALSE, TRUE))),
                          stringsAsFactors = FALSE)
  names(counts) <- c("split", "category", "matched", "rows")
  data.frame(term = name, counts[counts$matched == "TRUE", c("split", "category", "rows")])
}))
common_terms <- lapply(split(tokens[split == "Train"], train$category), function(rows) {
  frequency <- sort(table(unlist(lapply(rows, unique), use.names = FALSE)), decreasing = TRUE)
  head(frequency[nzchar(names(frequency))], 15)
})
report <- list(
  raw_labels = table(all$source_label, split), application_labels = table(all$category, split),
  blank_or_whitespace = tapply(!nzchar(stringi::stri_trim_both(all$text)), split, sum),
  normalized_empty = tapply(!nzchar(keys), split, sum),
  exact_duplicate_excess = tapply(keys, split, function(x) sum(duplicated(x))),
  conflicting_normalized_groups = sum(vapply(split(all$category, keys), function(x) {
    length(unique(x)) > 1L
  }, logical(1))),
  exact_test_rows_seen_in_train = sum(keys[split == "Test"] %in% keys[split == "Train"]),
  near_train = near_counts(split[pairs$i] == "Train" & split[pairs$j] == "Train"),
  near_test = near_counts(split[pairs$i] == "Test" & split[pairs$j] == "Test"),
  near_cross = near_counts(split[pairs$i] != split[pairs$j]),
  near_cross_test_rows = length(unique(pairs$j[split[pairs$i] != split[pairs$j]])),
  common_training_terms_by_document_frequency = common_terms
)
capture.output(print(report), file = "evaluation/dataset-audit.txt")
write.csv(coverage, "evaluation/term-coverage.csv", row.names = FALSE)
print(report)
