# Run against a running Plumber service with a trained model.
base_url <- Sys.getenv("TEST_ML_SERVICE_URL", "http://127.0.0.1:8001")

request <- function(path, body = NULL) {
  handle <- curl::new_handle()
  if (!is.null(body)) {
    curl::handle_setopt(handle, postfields = body)
    curl::handle_setheaders(handle, "Content-Type" = "application/json")
  }
  response <- curl::curl_fetch_memory(paste0(base_url, path), handle)
  list(status = response$status_code, data = jsonlite::parse_json(rawToChar(response$content)))
}

health <- request("/health")
stopifnot(health$status == 200L, identical(health$data, list(status = "ok", model_loaded = TRUE)))
spec <- request("/openapi.json")
operation <- spec$data$paths[["/predict"]]$post
json <- operation$requestBody$content[["application/json"]]
stopifnot(
  spec$status == 200L, isTRUE(operation$requestBody$required),
  identical(json$schema$required, list("title", "description")),
  json$schema$properties$title$maxLength == 160L,
  json$schema$properties$description$maxLength == 5000L,
  !is.null(operation$responses[["400"]])
)

result <- request("/predict", jsonlite::toJSON(json$example, auto_unbox = TRUE))
stopifnot(
  result$status == 200L, identical(result$data$classification_source, "model"),
  setequal(names(result$data), c("category", "confidence", "model_version", "classification_source")),
  is.numeric(result$data$confidence), result$data$confidence >= 0, result$data$confidence <= 1
)
expected_version <- Sys.getenv("TEST_MODEL_VERSION")
if (nzchar(expected_version)) stopifnot(identical(result$data$model_version, expected_version))
unknown <- request("/predict", '{"title":"zzq9q8vunknown","description":"zzq7q6vunknown"}')
stopifnot(unknown$status == 200L, identical(unknown$data, list(
  category = "Unclassified", confidence = NULL, model_version = NULL, classification_source = "fallback"
)))

invalid <- list(
  '{"title":' = "JSON object",
  '[]' = "JSON object",
  '{"description":"VPN issue"}' = "title",
  '{"title":"VPN issue"}' = "description",
  '{"title":["VPN"],"description":"No connection"}' = "title",
  '{"title":"VPN","description":42}' = "description",
  '{"title":"VPN","description":"   "}' = "description"
)
for (body in names(invalid)) {
  result <- request("/predict", body)
  stopifnot(result$status == 400L, grepl(invalid[[body]], result$data$error, fixed = TRUE))
}
cat("Plumber OpenAPI, health, model prediction, and invalid-request checks passed.\n")
