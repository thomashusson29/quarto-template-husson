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
    purple      = "#c678dd",
    orange      = "#d19a66",
    cyan        = "#56b6c2",
    yellow      = "#e5c07b",
    cycle       = c("#61afef", "#98c379", "#e06c75", "#c678dd", "#d19a66", "#56b6c2", "#e5c07b")
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
auto_dark_state$ggplot2_installed         <- FALSE
auto_dark_state$plotly_installed          <- FALSE
auto_dark_state$python_hook_installed     <- FALSE


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
  dark_image <- magick::image_modulate(dark_image, brightness = 115, saturation = 115, hue = 200)

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


# ── 9b. ggplot2 adapter (transparent background + One Dark Pro palette) ──────
#
# Automatically sets the default ggplot2 discrete colour/fill palettes to the
# One Dark Pro cycle, and intercepts knitr printing of ggplot objects so that
# plot, panel, and legend backgrounds remain transparent even when the user
# adds a complete theme such as `+ theme_minimal()` or `+ theme_bw()`.

auto_dark_install_ggplot2_adapter <- function(pal = auto_dark_palette()) {
  if (!auto_dark_html_output()) {
    return(invisible(FALSE))
  }

  # 1. Default One Dark Pro discrete colour and fill scales
  options(
    ggplot2.discrete.colour = pal$cycle,
    ggplot2.discrete.fill   = pal$cycle
  )

  if (isTRUE(auto_dark_state$ggplot2_installed) ||
      !requireNamespace("knitr", quietly = TRUE)) {
    return(invisible(FALSE))
  }

  wrapper <- function(x, ..., options = NULL) {
    if (isTRUE(getOption("auto_dark.active", FALSE)) &&
        isTRUE(getOption("auto_dark.transparent_figures", TRUE)) &&
        auto_dark_html_output() &&
        requireNamespace("ggplot2", quietly = TRUE)) {
      x <- x + ggplot2::theme(
        plot.background       = ggplot2::element_rect(fill = "transparent", colour = NA),
        panel.background      = ggplot2::element_rect(fill = "transparent", colour = NA),
        legend.background     = ggplot2::element_rect(fill = "transparent", colour = NA),
        legend.box.background = ggplot2::element_rect(fill = "transparent", colour = NA),
        legend.key            = ggplot2::element_rect(fill = "transparent", colour = NA),
        panel.grid.major      = ggplot2::element_line(colour = "#80808040"),
        panel.grid.minor      = ggplot2::element_line(colour = "#80808020")
      )
    }
    knitr::normal_print(x)
  }

  registerS3method("knit_print", "ggplot", wrapper, envir = asNamespace("knitr"))
  registerS3method("knit_print", "ggplot2::ggplot", wrapper, envir = asNamespace("knitr"))

  auto_dark_state$ggplot2_installed <- TRUE
  invisible(TRUE)
}


# ── 9c. Plotly adapter (R & Python 2D/3D interactive figures) ─────────────────
#
# Automatically styles R `plotly` htmlwidgets and Python `plotly` figures with
# transparent paper/plot/3D-scene backgrounds and the One Dark Pro discrete
# colour cycle. Browser-side `auto-dark-renderings.js` then synchronizes text,
# legend, and 2D/3D axis colours whenever the page switches between light and
# One Dark Pro dark mode.

auto_dark_normalize_plotly_title <- function(obj) {
  if (is.character(obj)) {
    return(list(text = obj))
  }
  if (is.list(obj)) {
    return(obj)
  }
  list()
}

auto_dark_style_plotly_widget <- function(x, pal = auto_dark_palette(), force_recolor = FALSE) {
  if (!requireNamespace("plotly", quietly = TRUE)) {
    return(x)
  }

  had_user_colors <- FALSE
  if (!is.null(x$x$attrs) && is.list(x$x$attrs)) {
    for (i in seq_along(x$x$attrs)) {
      if (!is.null(x$x$attrs[[i]]$colors)) {
        had_user_colors <- TRUE
      }
    }
    x <- tryCatch(
      suppressWarnings(suppressMessages(plotly::plotly_build(x))),
      error = function(e) x
    )
  }

  if ((!had_user_colors || isTRUE(force_recolor)) &&
      !is.null(x$x$data) && is.list(x$x$data)) {
    n_cycle <- length(pal$cycle)
    for (i in seq_along(x$x$data)) {
      col_i <- pal$cycle[((i - 1) %% n_cycle) + 1]
      tr_mode <- x$x$data[[i]]$mode
      if (is.character(tr_mode) && length(tr_mode) == 1 && !grepl("lines", tr_mode, fixed = TRUE)) {
        x$x$data[[i]]$line <- NULL
      }
      mc <- x$x$data[[i]]$marker$color
      if (is.character(mc) && length(mc) == 1) {
        x$x$data[[i]]$marker$color <- col_i
      }
      lc <- x$x$data[[i]]$line$color
      if (is.character(lc) && length(lc) == 1) {
        x$x$data[[i]]$line$color <- col_i
      }
    }
  }

  # Prevent htmlwidgets from running plotly_build a second time (which would
  # turn scatter3d mode = "markers" into "markers+lines").
  x$preRenderHook <- NULL

  layout <- x$x$layout %||% list()
  layout$template      <- NULL
  layout$paper_bgcolor <- "rgba(0,0,0,0)"
  layout$plot_bgcolor  <- "rgba(0,0,0,0)"
  layout$colorway      <- pal$cycle
  layout$font          <- utils::modifyList(layout$font %||% list(), list(color = pal$text))

  layout$title <- utils::modifyList(
    auto_dark_normalize_plotly_title(layout$title),
    list(font = list(color = pal$text_strong))
  )

  legend <- layout$legend %||% list()
  legend$title <- auto_dark_normalize_plotly_title(legend$title)
  layout$legend <- utils::modifyList(
    legend,
    list(
      bgcolor     = "rgba(0,0,0,0)",
      bordercolor = "rgba(0,0,0,0)",
      font        = list(color = pal$text),
      title       = list(font = list(color = pal$text_strong))
    )
  )

  axis_2d <- list(
    gridcolor     = "rgba(128,128,128,0.25)",
    zerolinecolor = "rgba(128,128,128,0.40)",
    linecolor     = "rgba(128,128,128,0.40)",
    tickfont      = list(color = pal$text),
    title         = list(font = list(color = pal$text_strong))
  )
  for (ax_name in c("xaxis", "yaxis")) {
    ax <- layout[[ax_name]] %||% list()
    ax$title <- auto_dark_normalize_plotly_title(ax$title)
    layout[[ax_name]] <- utils::modifyList(ax, axis_2d)
  }

  # Use opaque hex colours for 3D WebGL axes/grids so browser premultiplied-alpha
  # canvas compositing never washes out the grid on a white light-mode page.
  axis_3d <- list(
    backgroundcolor = "rgba(0,0,0,0)",
    showbackground  = FALSE,
    showgrid        = TRUE,
    showline        = TRUE,
    gridcolor       = "#7b8794",
    gridwidth       = 1,
    zerolinecolor   = "#636d83",
    linecolor       = "#636d83",
    tickcolor       = "#636d83",
    tickfont        = list(color = pal$text),
    title           = list(font = list(color = pal$text_strong))
  )
  scene <- layout$scene %||% list()
  scene$bgcolor <- "rgba(0,0,0,0)"
  if (is.null(scene$camera)) {
    scene$camera <- list(eye = list(x = 1.45, y = 1.45, z = 1.25))
  }
  for (ax_name in c("xaxis", "yaxis", "zaxis")) {
    ax <- scene[[ax_name]] %||% list()
    ax$title <- auto_dark_normalize_plotly_title(ax$title)
    scene[[ax_name]] <- utils::modifyList(ax, axis_3d)
  }
  layout$scene <- scene
  layout$margin <- utils::modifyList(
    list(l = 10, r = 10, b = 20, t = 50),
    layout$margin %||% list()
  )

  x$x$layout <- layout
  x
}

auto_dark_install_plotly_adapter <- function(pal = auto_dark_palette()) {
  if (!auto_dark_html_output() ||
      !requireNamespace("knitr", quietly = TRUE) ||
      isTRUE(auto_dark_state$plotly_installed)) {
    return(invisible(FALSE))
  }

  # 1. R plotly htmlwidget adapter
  r_wrapper <- function(x, ..., options = NULL) {
    if (isTRUE(getOption("auto_dark.active", FALSE)) &&
        isTRUE(getOption("auto_dark.transparent_figures", TRUE)) &&
        auto_dark_html_output()) {
      pal_cur <- getOption("auto_dark.palette", auto_dark_palette())
      x <- auto_dark_style_plotly_widget(x, pal = pal_cur)
    }
    if (requireNamespace("htmlwidgets", quietly = TRUE)) {
      orig_hw <- getFromNamespace("knit_print.htmlwidget", "htmlwidgets")
      return(orig_hw(x, ..., options = options))
    }
    knitr::normal_print(x)
  }

  registerS3method("knit_print", "plotly", r_wrapper, envir = asNamespace("knitr"))

  # 2. Python plotly Figure adapter (fallback if not handled via _repr_html_)
  py_wrapper <- function(x, ..., options = NULL) {
    if (!auto_dark_html_output() || !requireNamespace("reticulate", quietly = TRUE)) {
      return(knitr::normal_print(x))
    }
    html_str <- reticulate::py_to_r(x$`_repr_html_`())
    knitr::asis_output(html_str)
  }

  registerS3method("knit_print", "plotly.basedatatypes.BaseFigure", py_wrapper, envir = asNamespace("knitr"))
  registerS3method("knit_print", "plotly.graph_objs._figure.Figure", py_wrapper, envir = asNamespace("knitr"))

  auto_dark_state$plotly_installed <- TRUE
  invisible(TRUE)
}


# ── 9d. Python / matplotlib & plotly adapter via reticulate ──────────────────
#
# Automatically configures matplotlib and plotly in Python chunks with
# transparent backgrounds and the One Dark Pro colour cycle. Rendered static
# Python figures pass through knitr's standard `plot` hook (section 7), where
# `magick` (`auto_dark_make_dark_image`) creates the `*-auto-dark.png`
# companion image. Interactive Python `plotly` figures emit clean transparent
# HTML widgets synchronized with `auto-dark-renderings.js`.

auto_dark_configure_python <- function(pal = auto_dark_palette()) {
  if (!auto_dark_html_output()) {
    return(invisible(FALSE))
  }

  if (!nzchar(Sys.getenv("RETICULATE_PYTHON")) && nzchar(Sys.which("python3"))) {
    Sys.setenv(RETICULATE_PYTHON = Sys.which("python3"))
  }

  colors_py <- paste(sprintf("'%s'", pal$cycle), collapse = ", ")
  py_code <- sprintf(
    paste(
      "try:",
      "    import matplotlib as mpl",
      "    mpl.rcParams.update({",
      "        'figure.facecolor': 'none',",
      "        'axes.facecolor': 'none',",
      "        'savefig.transparent': True,",
      "        'savefig.facecolor': 'none',",
      "        'axes.prop_cycle': mpl.cycler(color=[%s])",
      "    })",
      "except Exception:",
      "    pass",
      "",
      "try:",
      "    import json, base64, uuid, numpy as np",
      "    import plotly.io as pio",
      "    import plotly.graph_objects as go",
      "    import plotly.express as px",
      "    from plotly.basedatatypes import BaseFigure",
      "    _ad_cycle = [%s]",
      "    px.defaults.color_discrete_sequence = _ad_cycle",
      "    pio.templates['onedark_auto'] = go.layout.Template(",
      "        layout=dict(",
      "            paper_bgcolor='rgba(0,0,0,0)',",
      "            plot_bgcolor='rgba(0,0,0,0)',",
      "            colorway=_ad_cycle,",
      "            font=dict(color='#abb2bf'),",
      "            title=dict(font=dict(color='#e6edf3')),",
      "            legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='rgba(0,0,0,0)', font=dict(color='#abb2bf')),",
      "            scene=dict(",
      "                bgcolor='rgba(0,0,0,0)',",
      "                xaxis=dict(backgroundcolor='rgba(0,0,0,0)', showbackground=False, showgrid=True, showline=True, gridcolor='#7b8794', zerolinecolor='#636d83', linecolor='#636d83', tickcolor='#636d83'),",
      "                yaxis=dict(backgroundcolor='rgba(0,0,0,0)', showbackground=False, showgrid=True, showline=True, gridcolor='#7b8794', zerolinecolor='#636d83', linecolor='#636d83', tickcolor='#636d83'),",
      "                zaxis=dict(backgroundcolor='rgba(0,0,0,0)', showbackground=False, showgrid=True, showline=True, gridcolor='#7b8794', zerolinecolor='#636d83', linecolor='#636d83', tickcolor='#636d83')",
      "            )",
      "        )",
      "    )",
      "    pio.templates.default = 'plotly_white+onedark_auto'",
      "    go.Figure.show = lambda self, *args, **kwargs: self",
      "    def _auto_dark_decode_bdata(obj):",
      "        if isinstance(obj, dict):",
      "            if 'bdata' in obj and 'dtype' in obj:",
      "                arr = np.frombuffer(base64.b64decode(obj['bdata']), dtype=obj['dtype'])",
      "                if 'shape' in obj:",
      "                    dims = [int(s.strip()) for s in str(obj['shape']).split(',') if s.strip()]",
      "                    arr = arr.reshape(dims)",
      "                return arr.tolist()",
      "            return {k: _auto_dark_decode_bdata(v) for k, v in obj.items()}",
      "        if isinstance(obj, (list, tuple)):",
      "            return [_auto_dark_decode_bdata(v) for v in obj]",
      "        if hasattr(obj, 'tolist'):",
      "            return obj.tolist()",
      "        return obj",
      "    def _auto_dark_repr_html(self):",
      "        d = _auto_dark_decode_bdata(self.to_plotly_json())",
      "        lay = d.setdefault('layout', {})",
      "        lay.pop('template', None)",
      "        lay['paper_bgcolor'] = 'rgba(0,0,0,0)'",
      "        lay['plot_bgcolor'] = 'rgba(0,0,0,0)'",
      "        lay['colorway'] = _ad_cycle",
      "        lay.setdefault('font', {})['color'] = '#abb2bf'",
      "        if isinstance(lay.get('title'), str):",
      "            lay['title'] = {'text': lay['title']}",
      "        lay.setdefault('title', {}).setdefault('font', {})['color'] = '#e6edf3'",
      "        leg = lay.setdefault('legend', {})",
      "        leg['bgcolor'] = 'rgba(0,0,0,0)'",
      "        leg['bordercolor'] = 'rgba(0,0,0,0)'",
      "        leg.setdefault('font', {})['color'] = '#abb2bf'",
      "        if isinstance(leg.get('title'), str):",
      "            leg['title'] = {'text': leg['title']}",
      "        leg.setdefault('title', {}).setdefault('font', {})['color'] = '#e6edf3'",
      "        sc = lay.setdefault('scene', {})",
      "        sc['bgcolor'] = 'rgba(0,0,0,0)'",
      "        sc.setdefault('camera', {'eye': {'x': 1.45, 'y': 1.45, 'z': 1.25}})",
      "        mrg = lay.setdefault('margin', {})",
      "        for mk, mv in (('l', 10), ('r', 10), ('b', 20), ('t', 50)):",
      "            mrg.setdefault(mk, mv)",
      "        for ax_nm in ('xaxis', 'yaxis', 'zaxis'):",
      "            ax = sc.setdefault(ax_nm, {})",
      "            ax['backgroundcolor'] = 'rgba(0,0,0,0)'",
      "            ax['showbackground'] = False",
      "            ax['showgrid'] = True",
      "            ax['showline'] = True",
      "            ax['gridcolor'] = '#7b8794'",
      "            ax['gridwidth'] = 1",
      "            ax['zerolinecolor'] = '#636d83'",
      "            ax['linecolor'] = '#636d83'",
      "            ax['tickcolor'] = '#636d83'",
      "            ax.setdefault('tickfont', {})['color'] = '#abb2bf'",
      "            if isinstance(ax.get('title'), str):",
      "                ax['title'] = {'text': ax['title']}",
      "            ax.setdefault('title', {}).setdefault('font', {})['color'] = '#e6edf3'",
      "        h = lay.get('height', 480)",
      "        div_id = 'plotly-py-' + uuid.uuid4().hex[:12]",
      "        payload = json.dumps({'data': d.get('data', []), 'layout': lay})",
      "        return (",
      "            f'<div id=\"{div_id}\" class=\"plotly-graph-div js-plotly-plot auto-dark-no-filter\" '",
      "            f'style=\"height:{h}px; width:100%%;\"></div>'",
      "            f'<script>(function(){{var spec={payload};'",
      "            f'function render(){{var el=document.getElementById(\"{div_id}\");if(!el||!window.Plotly)return;'",
      "            f'window.Plotly.newPlot(el,spec.data,spec.layout,{{responsive:true}}).then(function(){{'",
      "            f'window.dispatchEvent(new CustomEvent(\"auto-dark-change\"));}});}}'",
      "            f'if(window.Plotly){{render();}}else{{'",
      "            f'var s=document.querySelector(\"script[data-auto-dark-plotly-cdn]\");'",
      "            f'if(!s){{s=document.createElement(\"script\");s.src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\";'",
      "            f's.setAttribute(\"data-auto-dark-plotly-cdn\",\"true\");document.head.appendChild(s);}}'",
      "            f's.addEventListener(\"load\",render);'",
      "            f'window.addEventListener(\"DOMContentLoaded\",render);'",
      "            f'window.addEventListener(\"load\",render);}}}})'",
      "            f'();</script>'",
      "        )",
      "    BaseFigure._repr_html_ = _auto_dark_repr_html",
      "except Exception:",
      "    pass",
      sep = "\n"
    ),
    colors_py,
    colors_py
  )

  activate_py <- function(init = FALSE) {
    if (requireNamespace("reticulate", quietly = TRUE) &&
        tryCatch(reticulate::py_available(initialize = init), error = function(e) FALSE)) {
      tryCatch(reticulate::py_run_string(py_code), error = function(e) NULL)
    }
  }

  activate_py(init = FALSE)

  if (requireNamespace("knitr", quietly = TRUE) && !isTRUE(auto_dark_state$python_hook_installed)) {
    knitr::knit_hooks$set(auto_dark_py = function(before, options, envir) {
      if (before && identical(options$engine, "python")) {
        activate_py(init = TRUE)
      }
    })
    knitr::opts_chunk$set(auto_dark_py = TRUE)
    auto_dark_state$python_hook_installed <- TRUE
  }

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
    auto_dark_install_ggplot2_adapter(pal)
    auto_dark_install_plotly_adapter(pal)
    auto_dark_configure_python(pal)
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
