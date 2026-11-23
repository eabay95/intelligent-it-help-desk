# Handle malformed JSON without exposing parser details or returning HTTP 500.
plumber::register_parser(
  "helpdesk_json",
  function() {
    function(value, ...) {
      tryCatch(
        jsonlite::parse_json(rawToChar(value), simplifyVector = FALSE),
        error = function(error) NULL
      )
    }
  },
  fixed = "application/json",
  verbose = FALSE
)

#* @plumber
function(pr) {
  plumber::pr_set_api_spec(pr, function(spec) {
    operation <- spec$paths[["/predict"]]$post
    operation$requestBody <- list(
      required = TRUE,
      content = list("application/json" = list(
        schema = list(
          type = "object",
          required = list("title", "description"),
          properties = list(
            title = list(type = "string", minLength = 1L, maxLength = 160L,
                         description = "Nonblank ticket title."),
            description = list(type = "string", minLength = 1L, maxLength = 5000L,
                               description = "Nonblank description of the issue.")
          )
        ),
        example = list(
          title = "VPN keeps disconnecting",
          description = paste("My company VPN disconnects every five minutes,",
                              "even after restarting my laptop.")
        )
      ))
    )
    operation$responses[["400"]] <- list(description = "Malformed JSON or invalid ticket fields.")
    spec$paths[["/predict"]]$post <- operation
    spec
  })
}

#* @get /health
function() {
  list(status = "ok", model_loaded = !is.null(ticket_model))
}

#* Classify a support ticket
#* @post /predict
#* @parser helpdesk_json
function(req, res) {
  valid_text <- function(value, max_length) {
    is.character(value) && length(value) == 1L && !is.na(value) &&
      nzchar(trimws(value, whitespace = "[\\h\\v]")) && nchar(value) <= max_length
  }
  bad_request <- function(message) {
    res$status <- 400L
    list(error = message)
  }
  body <- req$body
  if (!is.list(body) || is.null(names(body))) {
    return(bad_request("Send a JSON object containing title and description."))
  }
  if (!valid_text(body[["title"]], 160L)) {
    return(bad_request("Provide a title as a nonblank string of 1-160 characters."))
  }
  if (!valid_text(body[["description"]], 5000L)) {
    return(bad_request("Provide a description as a nonblank string of 1-5000 characters."))
  }
  predict_ticket(ticket_model, body[["title"]], body[["description"]])
}
