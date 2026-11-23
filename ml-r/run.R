library(plumber)
source("model.R")

model_path <- Sys.getenv("MODEL_PATH", "models/ticket-classifier.rds")
ticket_model <- tryCatch(load_model(model_path), error = function(error) {
  message("Classifier artifact unavailable. Predictions will use the fallback.")
  NULL
})
api <- pr("plumber.R")
api <- pr_set_serializer(api, serializer_unboxed_json(null = "null"))
pr_run(
  api,
  host = Sys.getenv("ML_HOST", "127.0.0.1"),
  port = as.integer(Sys.getenv("ML_PORT", "8001"))
)
