# auto-dark-setup.R
#
# Entry point for the auto-dark Quarto extension.
# Source this file once in a hidden setup chunk, then call auto_dark_on().
#
# Usage:
#   source("_extensions/auto-dark/auto-dark-setup.R")
#   auto_dark_on()
#
# See README.md for full path variants (GitHub install vs. local checkout).


# ── 1. Utility helpers ────────────────────────────────────────────────────────

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0 || all(is.na(x))) y else x
}


# ── 2. One Dark palette ───────────────────────────────────────────────────────

auto_dark_palette <- function(name = "onedark") {
  if (!identical(name, "onedark")) {
    stop("Only palette = 'onedark' is currently supported.", call. = FALSE)
  }

  list(
    name        = "onedark",
    bg          = "#282c34",
    bg_soft     = "#2c313a",
    panel       = "#21252b",
    border      = "#3e4451",
    text        = "#abb2bf",
    text_strong = "#e6edf3",
    text_muted  = "#8b949e",
    blue        = "#61afef",
    green       = "#98c379",
    red         = "#e06c75",
    purple      = "#c678dd"
  )
}


# ── 3. Extension state ────────────────────────────────────────────────────────
#
# A small environment used to track installation status of each hook so that
# repeated calls to auto_dark_on() do not double-install hooks.

auto_dark_state <- new.env(parent = emptyenv())
auto_dark_state$active                    <- FALSE
auto_dark_state$plot_hook_installed       <- FALSE
auto_dark_state$plot_hook_original        <- NULL
auto_dark_state$include_graphics_installed <- FALSE
auto_dark_state$include_graphics_original  <- NULL
auto_dark_state$flowchart_installed       <- FALSE
auto_dark_state$flowchart_original        <- NULL


# ── 4. Context helpers ────────────────────────────────────────────────────────

# Returns TRUE when knitr is knitting to HTML output.
auto_dark_html_output <- function() {
  requireNamespace("knitr", quietly = TRUE) && isTRUE(knitr::is_html_output())
}


# ── 5. Graphics device – transparent backgrounds ──────────────────────────────
#
# Sets dev.args$bg = "transparent" so that plot panel and device backgrounds
# are transparent PNG/JPEG/WebP, allowing the One Dark page background
# (#282c34) to show through behind rendered figures.

auto_dark_configure_transparent_figures <- function() {
  if (!auto_dark_html_output()) {
    return(invisible(FALSE))
  }

  auto_dark_dev_args <- knitr::opts_chunk$get("dev.args")
  if (is.null(auto_dark_dev_args)) {
    auto_dark_dev_args <- list()
  }
  auto_dark_dev_args$bg <- "transparent"

  knitr::opts_chunk$set(
    fig.bg  = "transparent",
    dev.args = auto_dark_dev_args
  )

  invisible(TRUE)
}


# ── 6. Companion image generation (magick) ────────────────────────────────────
#
# For each rendered figure (PNG/JPEG/WebP), the source image is first rewritten
# with exact white made transparent. A dark companion image is then produced by
# negating colours and rotating hue slightly. The companion is written to the
# same folder with the suffix "-auto-dark" before the file extension, e.g.
# "fig-1.png" → "fig-1-auto-dark.png".
#
# The browser-side script (auto-dark-renderings.js) probes for these companions
# and inserts a hidden dark copy next to each figure; CSS shows the right one.
#
# Requires the `magick` package. Falls back to CSS filtering silently when magick
# is absent (with a warning unless quiet = TRUE).

auto_dark_companion_path <- function(path) {
  sub("(\\.[^.\\/]+)$", "-auto-dark\\1", path)
}

auto_dark_can_process_image <- function(path) {
  ext <- tolower(tools::file_ext(path))
  nzchar(ext) && ext %in% c("png", "jpg", "jpeg", "webp") && file.exists(path)
}

auto_dark_make_dark_image <- function(path, palette = auto_dark_palette()) {
  if (!auto_dark_can_process_image(path) ||
      !requireNamespace("magick", quietly = TRUE)) {
    return(invisible(NULL))
  }

  image <- magick::image_read(path)

  # Exact white is typically the device/page background. Making it transparent
  # lets the One Dark page colour show through. A very small fuzz (0.5%) avoids
  # erasing near-white clinical diagram elements (boxes, labels, backgrounds).
  image <- magick::image_transparent(image, color = "white", fuzz = 0.005)
  magick::image_write(image, path = path)

  dark_path <- auto_dark_companion_path(path)
  dark_image <- magick::image_negate(image)
  dark_image <- magick::image_modulate(dark_image, hue = 200)

  dir.create(dirname(dark_path), recursive = TRUE, showWarnings = FALSE)
  magick::image_write(dark_image, path = dark_path)

  invisible(dark_path)
}

# Process a vector of image paths, skipping if the feature is disabled or if
# the chunk has opted out via class.output = "auto-dark-no-filter".
auto_dark_make_dark_images <- function(paths, options = knitr::opts_current$get()) {
  if (!isTRUE(getOption("auto_dark.generate_dark_images", TRUE)) ||
      !auto_dark_html_output()) {
    return(invisible(NULL))
  }

  class <- paste(options$class.output %||% character(), collapse = " ")
  if (grepl("auto-dark-no-filter", class, fixed = TRUE)) {
    return(invisible(NULL))
  }

  palette <- getOption("auto_dark.palette", auto_dark_palette())
  lapply(paths, auto_dark_make_dark_image, palette = palette)
  invisible(NULL)
}


# ── 7. knitr plot hook ────────────────────────────────────────────────────────
#
# Wraps the default knitr plot hook so that every rendered figure triggers
# dark companion image generation before the original hook inserts the <img>.

auto_dark_install_plot_hook <- function() {
  if (!requireNamespace("knitr", quietly = TRUE) ||
      isTRUE(auto_dark_state$plot_hook_installed)) {
    return(invisible(FALSE))
  }

  auto_dark_state$plot_hook_original <- knitr::knit_hooks$get("plot")

  knitr::knit_hooks$set(plot = function(x, options) {
    auto_dark_make_dark_images(x, options)
    auto_dark_state$plot_hook_original(x, options)
  })

  auto_dark_state$plot_hook_installed <- TRUE
  invisible(TRUE)
}


# ── 8. knitr::include_graphics() adapter ─────────────────────────────────────
#
# knitr::include_graphics() returns a "knit_image_paths" object. This adapter
# wraps its S3 knit_print method so that local image files also get a dark
# companion generated at render time — without the user needing to call any
# extra function.

auto_dark_install_include_graphics_adapter <- function() {
  if (!requireNamespace("knitr", quietly = TRUE) ||
      isTRUE(auto_dark_state$include_graphics_installed)) {
    return(invisible(FALSE))
  }

  original <- getS3method(
    "knit_print",
    "knit_image_paths",
    envir    = asNamespace("knitr"),
    optional = TRUE
  )

  auto_dark_state$include_graphics_original <- original

  wrapper <- function(x, options, ...) {
    auto_dark_make_dark_images(as.character(x), options)

    if (!is.null(original)) {
      return(original(x, options, ...))
    }

    NextMethod()
  }

  registerS3method(
    "knit_print",
    "knit_image_paths",
    wrapper,
    envir = asNamespace("knitr")
  )

  auto_dark_state$include_graphics_installed <- TRUE
  invisible(TRUE)
}


# ── 9. flowchart::fc_draw() adapter ──────────────────────────────────────────
#
# Patches flowchart::fc_draw() so that its canvas_bg argument defaults to
# "transparent", allowing the One Dark page background to show through
# flowchart diagrams without the user needing to set canvas_bg manually.

auto_dark_install_flowchart_adapter <- function() {
  if (isTRUE(auto_dark_state$flowchart_installed) ||
      !requireNamespace("flowchart", quietly = TRUE)) {
    return(invisible(FALSE))
  }

  original <- getS3method(
    "fc_draw",
    "fc",
    envir    = asNamespace("flowchart"),
    optional = TRUE
  )
  if (is.null(original)) {
    return(invisible(FALSE))
  }

  auto_dark_state$flowchart_original <- original

  wrapper <- function(object, ..., canvas_bg = "transparent") {
    original(object, ..., canvas_bg = canvas_bg)
  }

  registerS3method(
    "fc_draw",
    "fc",
    wrapper,
    envir = asNamespace("flowchart")
  )

  auto_dark_state$flowchart_installed <- TRUE
  invisible(TRUE)
}


# ── 10. Public API: auto_dark_on() / auto_dark_off() ─────────────────────────

#' Enable the One Dark theme for the current knitr session.
#'
#' Call once in a hidden setup chunk after sourcing this file.
#' See README.md for the full list of arguments and their defaults.
#'
#' @param palette           Palette name. Only "onedark" is currently supported.
#' @param mode              "robust" (companion images via magick) or "filter"
#'                          (CSS-only fallback, no magick required).
#' @param transparent_figures  Set device background to transparent so the page
#'                          background colour is visible behind plots.
#' @param generate_dark_images  Create *-auto-dark.* companion images for each
#'                          rendered figure.
#' @param include_graphics  Hook knitr::include_graphics() to also generate
#'                          companions for local image files.
#' @param flowchart         Patch flowchart::fc_draw() canvas_bg default to
#'                          "transparent".
#' @param thematic          Call thematic::thematic_on() with the One Dark palette.
#'                          Requires the `thematic` package.
#' @param quiet             Suppress warnings about missing optional packages.
#'
#' @return Invisibly returns the active palette list.
auto_dark_on <- function(palette             = "onedark",
                         mode                = "robust",
                         transparent_figures = TRUE,
                         generate_dark_images = TRUE,
                         include_graphics    = TRUE,
                         flowchart           = TRUE,
                         thematic            = FALSE,
                         quiet               = FALSE) {

  if (!mode %in% c("robust", "filter")) {
    stop("mode must be 'robust' or 'filter'.", call. = FALSE)
  }

  pal <- auto_dark_palette(palette)

  options(
    auto_dark.active               = TRUE,
    auto_dark.mode                 = mode,
    auto_dark.palette              = pal,
    auto_dark.transparent_figures  = transparent_figures,
    auto_dark.generate_dark_images = generate_dark_images
  )

  if (isTRUE(transparent_figures)) {
    auto_dark_configure_transparent_figures()
  }

  if (isTRUE(generate_dark_images)) {
    auto_dark_install_plot_hook()
  }

  if (isTRUE(generate_dark_images) && isTRUE(include_graphics)) {
    auto_dark_install_include_graphics_adapter()
  }

  if (isTRUE(flowchart)) {
    auto_dark_install_flowchart_adapter()
  }

  if (isTRUE(thematic)) {
    if (requireNamespace("thematic", quietly = TRUE)) {
      thematic::thematic_on(bg = pal$bg, fg = pal$text, accent = pal$blue)
    } else if (!isTRUE(quiet)) {
      warning(
        "Package 'thematic' is not installed; R plots will use their default theme.",
        call. = FALSE
      )
    }
  }

  if (!requireNamespace("magick", quietly = TRUE) &&
      isTRUE(generate_dark_images) &&
      !isTRUE(quiet)) {
    warning(
      "Package 'magick' is not installed; dark plot images will fall back to CSS filtering only.",
      call. = FALSE
    )
  }

  auto_dark_state$active <- TRUE
  invisible(pal)
}


#' Disable auto dark mode for the current knitr session.
#'
#' Stops companion image generation. Does not remove installed hooks.
auto_dark_off <- function() {
  options(
    auto_dark.active               = FALSE,
    auto_dark.generate_dark_images = FALSE
  )
  auto_dark_state$active <- FALSE
  invisible(TRUE)
}
