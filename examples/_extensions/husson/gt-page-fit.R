# Mise en page automatique des tableaux (gt, kable, tibble, markdown) dans les sorties PDF Quarto.
#
# Le module est charge dans le chunk de setup :
#   source("_extensions/husson/gt-page-fit.R")
#   husson_tables_on()
#
# Objectifs :
# - 100% de la largeur de la page (\linewidth)
# - Hauteur minimale (largeurs de colonnes automatiques et proportionnelles au contenu)
# - Police controlee (reduction maximale de 25% : \small ~10pt ou \footnotesize ~9pt pour >= 6 colonnes)
# - Remplacement automatique des largeurs px() excessives qui debordent de la page

husson_latex_output <- function() {
  requireNamespace("knitr", quietly = TRUE) &&
    isTRUE(knitr::is_latex_output())
}

# Calcul heuristique de repartition optimale de largeur (en %) minimisant les retours a la ligne
husson_calculate_optimal_widths <- function(df, visible_cols) {
  n_cols <- length(visible_cols)
  if (n_cols <= 1L) {
    return(stats::setNames(100, visible_cols))
  }

  demands <- vapply(visible_cols, function(col) {
    vals <- df[[col]]
    lens <- nchar(as.character(vals))
    lens <- lens[!is.na(lens)]
    if (length(lens) == 0L) lens <- 1
    hdr_len <- nchar(as.character(col))
    p90 <- if (length(lens) > 1L) stats::quantile(lens, 0.90, names = FALSE) else max(lens)
    max(hdr_len, p90, 1)
  }, numeric(1))

  # Transformation puissance pour equilibrer les colonnes narratives et les colonnes courtes
  scores <- demands^0.65

  # Plancher minimal par colonne pour eviter l'etouffement des en-tetes courts
  min_pct <- max(6, 35 / n_cols)
  raw_pcts <- scores / sum(scores) * 100
  adjusted <- pmax(raw_pcts, min_pct)
  pcts <- round(adjusted / sum(adjusted) * 100, 1)

  # Ajustement du dernier arrondi pour atteindre exactement 100.0%
  diff <- 100 - sum(pcts)
  pcts[which.max(pcts)] <- pcts[which.max(pcts)] + diff

  stats::setNames(pcts, visible_cols)
}

husson_fit_gt_to_page <- function(tbl, force = FALSE) {
  if (!inherits(tbl, "gt_tbl") ||
      (!isTRUE(force) && !husson_latex_output())) {
    return(tbl)
  }

  if (!requireNamespace("gt", quietly = TRUE) ||
      !requireNamespace("rlang", quietly = TRUE)) {
    return(tbl)
  }

  boxhead <- tbl[["_boxhead"]]
  if (!is.data.frame(boxhead) ||
      !all(c("var", "type") %in% names(boxhead))) {
    return(gt::tab_options(tbl, table.width = gt::pct(100)))
  }

  visible <- boxhead$var[boxhead$type != "hidden"]
  n_cols <- length(visible)
  if (n_cols < 1L) {
    return(gt::tab_options(tbl, table.width = gt::pct(100)))
  }

  # Verification des largeurs existantes
  existing <- boxhead$column_width[match(visible, boxhead$var)]
  has_pixels <- FALSE
  has_valid_pct <- FALSE

  all_strs <- unlist(lapply(existing, as.character))
  all_strs <- all_strs[!is.na(all_strs) & nzchar(all_strs)]

  if (length(all_strs) > 0L) {
    if (any(grepl("px$", all_strs, ignore.case = TRUE))) {
      has_pixels <- TRUE
    } else if (all(grepl("%$", all_strs))) {
      nums <- as.numeric(sub("%$", "", all_strs))
      if (all(!is.na(nums)) && abs(sum(nums) - 100) < 5) {
        has_valid_pct <- TRUE
      }
    }
  }

  # Si l'auteur a deja fourni une repartition valide en %, on la conserve.
  # En revanche, si des px() sont presents (ex: table 1 avec 905px qui deborde),
  # ou si aucune largeur n'est specifiee, on calcule la repartition optimale.
  if (!has_valid_pct || has_pixels) {
    df <- tbl[["_data"]]
    if (is.data.frame(df)) {
      col_names <- intersect(visible, names(df))
      if (length(col_names) == n_cols) {
        width_map <- husson_calculate_optimal_widths(df, visible)
        width_specs <- lapply(
          names(width_map),
          function(column) {
            rlang::new_formula(
              rlang::sym(column),
              gt::pct(unname(width_map[[column]]))
            )
          }
        )
        tbl <- gt::cols_width(tbl, .list = width_specs)
      }
    }
  }

  # Police proportionnee : \small (10pt, -9%) par defaut, ou \footnotesize (9pt, -18%) si >= 6 colonnes
  font_size <- if (n_cols >= 6L) "9pt" else "10pt"

  tbl |>
    gt::tab_options(
      table.width = gt::pct(100),
      table.font.size = font_size,
      data_row.padding = gt::px(3),
      column_labels.padding = gt::px(4)
    )
}

husson_tables_on <- function() {
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

  # 1. Hook d'impression pour les tableaux gt
  original_gt <- getS3method(
    "knit_print",
    "gt_tbl",
    envir = asNamespace("knitr"),
    optional = TRUE
  )

  wrapper_gt <- function(x, ..., inline = FALSE) {
    x <- husson_fit_gt_to_page(x)
    if (is.function(original_gt)) {
      original_gt(x, ..., inline = inline)
    } else {
      knitr::normal_print(x)
    }
  }

  # 2. Hook d'impression pour les data.frame et tibble (redirection vers gt automatique)
  original_df <- getS3method(
    "knit_print",
    "data.frame",
    envir = asNamespace("knitr"),
    optional = TRUE
  )

  wrapper_df <- function(x, ..., inline = FALSE) {
    if (husson_latex_output()) {
      gt_x <- gt::gt(x) |> husson_fit_gt_to_page()
      knitr::knit_print(gt_x, ..., inline = inline)
    } else if (is.function(original_df)) {
      original_df(x, ..., inline = inline)
    } else {
      knitr::normal_print(x)
    }
  }

  options(
    husson.tables.knit_print_original_gt = original_gt,
    husson.tables.knit_print_original_df = original_df,
    husson.tables.hook_installed = TRUE
  )

  registerS3method("knit_print", "gt_tbl", wrapper_gt, envir = asNamespace("knitr"))
  registerS3method("knit_print", "data.frame", wrapper_df, envir = asNamespace("knitr"))
  if (requireNamespace("tibble", quietly = TRUE)) {
    registerS3method("knit_print", "tbl_df", wrapper_df, envir = asNamespace("knitr"))
  }

  invisible(TRUE)
}

husson_tables_off <- function() {
  orig_gt <- getOption("husson.tables.knit_print_original_gt")
  orig_df <- getOption("husson.tables.knit_print_original_df")

  if (requireNamespace("knitr", quietly = TRUE)) {
    if (is.function(orig_gt)) {
      registerS3method("knit_print", "gt_tbl", orig_gt, envir = asNamespace("knitr"))
    }
    if (is.function(orig_df)) {
      registerS3method("knit_print", "data.frame", orig_df, envir = asNamespace("knitr"))
      if (requireNamespace("tibble", quietly = TRUE)) {
        registerS3method("knit_print", "tbl_df", orig_df, envir = asNamespace("knitr"))
      }
    }
  }

  options(
    husson.tables.knit_print_original_gt = NULL,
    husson.tables.knit_print_original_df = NULL,
    husson.tables.hook_installed = FALSE
  )
  invisible(TRUE)
}
