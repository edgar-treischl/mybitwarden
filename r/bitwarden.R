#' Fetch a Bitwarden item by name or ID and return its login info and custom fields as a tibble.
#'
#' @param item_name_or_id A string representing the name or ID of the Bitwarden item to fetch. 
#'  This can be the item's name or its unique identifier.
#'
#' @returns A tibble containing the login information (username and password) 
#'  and any custom fields associated with the specified Bitwarden item.
#' @export
#'
fetch_bitwarden <- function(item_name_or_id) {
  
  # Null-coalescing helper
  `%||%` <- function(x, y) if (is.null(x)) y else x
  
  # Get session
  bw_session <- Sys.getenv("BW_SESSION")
  if (bw_session == "") cli_abort(c(
    "BW_SESSION not set.",
    "i" = "Run `bw unlock --raw` and export it as:",
    "*" = "export BW_SESSION=$(bw unlock --raw)"
  ))
  
  cli_output <- suppressWarnings(
    tryCatch(
      system2(
        "bw",
        args = c("get", "item", item_name_or_id, "--session", bw_session),
        stdout = TRUE,
        stderr = TRUE
      ),
      error = function(e) {
        cli_abort(c(
          "x" = "Error running Bitwarden CLI.",
          "i" = "Make sure 'bw' is installed and available in PATH."
        ))
      }
    )
  )
  
  cli_status <- attr(cli_output, "status") %||% 0
  raw_text <- paste(cli_output, collapse = "\n")
  
  # Check for CLI errors / "Not found" before parsing JSON
  if (!is.null(cli_status) && cli_status != 0 || grepl("not found", raw_text, ignore.case = TRUE)) {
    cli::cli_abort(c(
      "x" = glue::glue("Bitwarden item '{item_name_or_id}' not found."),
      "i" = "Check the item name or ID.",
      "*" = "Run `bw list items --session $BW_SESSION` to see available items."
    ))
  }
  
  # Parse JSON safely
  item <- tryCatch(
    jsonlite::fromJSON(raw_text, simplifyVector = FALSE),
    error = function(e) {
      cli_abort(c(
        "x" = glue::glue("Failed to parse Bitwarden item JSON for '{item_name_or_id}'"),
        "i" = "Raw CLI output:",
        "*" = raw_text
      ))
    }
  )
  
  # Login info
  login_cols <- list(
    username = item$login$username %||% NA_character_,
    password = item$login$password %||% NA_character_
  )
  
  login_info <- tibble::as_tibble(login_cols)
  
  # Custom fields
  custom_fields <- purrr::map(item$fields, ~ .x$value %||% NA_character_) |> 
    purrr::set_names(purrr::map_chr(item$fields, "name")) |> 
    tibble::as_tibble()
  
  # Combine
  secret <- tibble::as_tibble(dplyr::bind_cols(login_info, custom_fields))
  cli::cli_alert_success(glue::glue("Fetched '{item_name_or_id}' from Bitwarden successfully."))
  return(secret)
}

fetch_bitwarden("MYAPI")
