# Mise en page automatique des tableaux gt dans les sorties PDF Quarto.
#
# Le module est volontairement charge une seule fois dans le chunk de setup :
#   source("_extensions/husson/gt-page-fit.R")
#   husson_tables_on()
#
# gtsummary imprime ses tableaux via gt. Le hook knit_print ci-dessous couvre
# donc les objets gt crees directement et les tableaux gtsummary, sans imposer
# un appel de mise en forme apres chaque tableau.

husson_latex_output <- function() {
  requireNamespace("knitr", quietly = TRUE) &&
    isTRUE(knitr::is_latex_output())
}

husson_fit_gt_to_page <- function(tbl,
                                  label_pct = 44,
                                  p_pct = 8,
                                  min_other_pct = 8,
                                  force = FALSE) {
  if (!inherits(tbl, "gt_tbl") ||
      (!isTRUE(force) && !husson_latex_output())) {
    return(tbl)
  }

  if (!requireNamespace("gt", quietly = TRUE)) {
    return(tbl)
  }

  # GT ne fournit pas encore de selecteur public pour repartir automatiquement
  # la largeur entre toutes les colonnes visibles. Si sa structure interne
  # evolue, on conserve au minimum la largeur totale du tableau.
  boxhead <- tbl[["_boxhead"]]
  if (!is.data.frame(boxhead) ||
      !all(c("var", "type", "column_width") %in% names(boxhead))) {
    return(gt::tab_options(tbl, table.width = gt::pct(100)))
  }

  visible <- boxhead$var[boxhead$type != "hidden"]
  if (length(visible) < 2L) {
    return(gt::tab_options(tbl, table.width = gt::pct(100)))
  }

  # Une largeur explicitement definie par l'auteur reste prioritaire.
  existing <- boxhead$column_width[match(visible, boxhead$var)]
  has_explicit_width <- vapply(
    existing,
    function(x) {
      length(x) > 0L &&
        !all(is.na(x)) &&
        any(nzchar(as.character(x)))
    },
    logical(1)
  )
  if (any(has_explicit_width)) {
    return(gt::tab_options(tbl, table.width = gt::pct(100)))
  }

  lower <- tolower(visible)
  p_cols <- visible[grepl(
    "^(p|q)([._-]?(value|valeur))?[0-9]*$",
    lower
  )]

  preferred_labels <- c(
    "label", "variable", "characteristic", "caractéristique",
    "caracteristique", "méthode", "methode", "stratégie", "strategie",
    "description", "exposition", "critère", "critere"
  )
  label_candidates <- visible[lower %in% preferred_labels]
  non_p_cols <- setdiff(visible, p_cols)
  label_col <- if (length(label_candidates)) {
    label_candidates[[1L]]
  } else if (length(non_p_cols)) {
    non_p_cols[[1L]]
  } else {
    visible[[1L]]
  }

  p_cols <- setdiff(p_cols, label_col)
  other_cols <- setdiff(visible, c(label_col, p_cols))

  # Les p/q-values sont compactes, la colonne descriptive absorbe les retours
  # a la ligne, et le solde est reparti uniformement entre les estimations.
  p_total <- if (length(p_cols)) {
    min(p_pct * length(p_cols), 20)
  } else {
    0
  }
  label_width <- min(
    label_pct,
    100 - p_total - min_other_pct * length(other_cols)
  )
  label_width <- max(label_width, 24)
  other_total <- 100 - label_width - p_total

  width_map <- stats::setNames(label_width, label_col)
  if (length(other_cols)) {
    width_map <- c(
      width_map,
      stats::setNames(
        rep(other_total / length(other_cols), length(other_cols)),
        other_cols
      )
    )
  }
  if (length(p_cols)) {
    width_map <- c(
      width_map,
      stats::setNames(
        rep(p_total / length(p_cols), length(p_cols)),
        p_cols
      )
    )
  }

  if (!requireNamespace("rlang", quietly = TRUE)) {
    return(gt::tab_options(tbl, table.width = gt::pct(100)))
  }

  width_specs <- lapply(
    names(width_map),
    function(column) {
      rlang::new_formula(
        rlang::sym(column),
        gt::pct(unname(width_map[[column]]))
      )
    }
  )

  gt::cols_width(tbl, .list = width_specs) |>
    gt::tab_options(table.width = gt::pct(100))
}

husson_tables_on <- function(label_pct = 44,
                             p_pct = 8,
                             min_other_pct = 8) {
  if (!requireNamespace("knitr", quietly = TRUE) ||
      !requireNamespace("gt", quietly = TRUE)) {
    warning(
      "Les packages 'knitr' et 'gt' sont necessaires pour husson_tables_on().",
      call. = FALSE
    )
    return(invisible(FALSE))
  }

  if (isTRUE(getOption("husson.tables.hook_installed", FALSE))) {
    return(invisible(TRUE))
  }

  original <- getS3method(
    "knit_print",
    "gt_tbl",
    envir = asNamespace("knitr"),
    optional = TRUE
  )
  if (is.null(original)) {
    warning("La methode d'impression de 'gt' est introuvable.", call. = FALSE)
    return(invisible(FALSE))
  }

  wrapper <- function(x, ..., inline = FALSE) {
    x <- husson_fit_gt_to_page(
      x,
      label_pct = label_pct,
      p_pct = p_pct,
      min_other_pct = min_other_pct
    )
    original(x, ..., inline = inline)
  }

  options(
    husson.tables.knit_print_original = original,
    husson.tables.hook_installed = TRUE
  )
  registerS3method(
    "knit_print",
    "gt_tbl",
    wrapper,
    envir = asNamespace("knitr")
  )

  invisible(TRUE)
}

husson_tables_off <- function() {
  original <- getOption("husson.tables.knit_print_original")
  if (is.function(original) && requireNamespace("knitr", quietly = TRUE)) {
    registerS3method(
      "knit_print",
      "gt_tbl",
      original,
      envir = asNamespace("knitr")
    )
  }
  options(
    husson.tables.knit_print_original = NULL,
    husson.tables.hook_installed = FALSE
  )
  invisible(TRUE)
}
