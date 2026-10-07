# Mise en page automatique des tableaux (gt, kable, tibble, markdown) dans les sorties PDF Quarto.
#
# Le module est charge dans le chunk de setup :
#   source("_extensions/husson/gt-page-fit.R")
#   husson_tables_on()
#
# Objectifs :
# - 100% de la largeur de la page (\linewidth)
# - Hauteur minimale (largeurs de colonnes automatiques et proportionnelles au contenu)
# - Police controlee (\small ~10pt ou \footnotesize ~9pt pour >= 6 colonnes, \scriptsize ~8pt pour >= 10 colonnes)
# - Remplacement automatique des largeurs px() excessives qui debordent de la page

husson_latex_output <- function() {
  requireNamespace("knitr", quietly = TRUE) &&
    isTRUE(knitr::is_latex_output())
}

# Inférence automatique du type d'alignement par colonne selon son contenu
husson_detect_col_alignment <- function(vals) {
  clean_vals <- trimws(as.character(vals))
  clean_vals <- clean_vals[!is.na(clean_vals) & nzchar(clean_vals)]
  if (length(clean_vals) == 0L) return("left")

  # 1. Numerique ou pourcentages formates (ex: "9,1", "1 987", "50 %", "0,48")
  # Autorise quelques mentions qualitatives minoritaires (ex: "Absente", "<15,6")
  is_num <- grepl("^[<>]?[+-]?[0-9][0-9 ,.]*([ ]*%)?$", clean_vals)
  if (mean(is_num) >= 0.6) return("right")

  # 2. Codes courts, plages, delais, fibrose, statut qualitatif
  is_short_code <- all(nchar(clean_vals) <= 14L) &&
                   (any(grepl("^[0-9]+[–-][0-9]+$", clean_vals)) ||
                    any(grepl("^H[0-9]", clean_vals)) ||
                    any(clean_vals %in% c("Absente", "Absent", "Non atteint", "Oui", "Non",
                                          "F0", "F1", "F2", "F3", "F4", "Favorable", "Défavorable")))
  if (is_short_code) return("center")

  "left"
}

# Calcul heuristique de repartition optimale de largeur (en %) minimisant les retours a la ligne
# et garantissant la hauteur minimale absolue du tableau
husson_calculate_optimal_widths <- function(df, visible_cols, boxhead = NULL, tbl = NULL) {
  n_cols <- length(visible_cols)
  if (n_cols <= 1L) {
    return(stats::setNames(100, visible_cols))
  }

  body_df <- df
  if (inherits(tbl, "gt_tbl")) {
    tryCatch({
      built <- gt:::build_data(tbl, context = "latex")
      if (is.data.frame(built[["_body"]])) {
        body_df <- built[["_body"]]
      }
    }, error = function(e) NULL)
  }

  col_info <- lapply(visible_cols, function(col) {
    # 1. En-tete reel nettoye
    lbl_clean <- as.character(col)
    if (is.data.frame(boxhead) && "var" %in% names(boxhead) && "column_label" %in% names(boxhead)) {
      match_idx <- match(col, boxhead$var)
      if (!is.na(match_idx)) {
        lbl_str <- as.character(boxhead$column_label[[match_idx]])
        lbl_clean <- gsub("[*_`#]|<[^>]+>", "", lbl_str)
        lbl_clean <- gsub("\\\\[a-zA-Z]+(\\[[^\\]]*\\])?(\\{[^}]*\\})?", "", lbl_clean)
        lbl_clean <- gsub("[{}]", "", lbl_clean)
        lbl_clean <- gsub("[ \t\r\n]+", " ", lbl_clean)
        lbl_clean <- trimws(lbl_clean)
      }
    }

    # Espace avant parenthese d'unite si absent (ex: CellSaver(mL) -> CellSaver (mL))
    lbl_spaced <- gsub("([a-zA-Z0-9])\\(", "\\1 (", lbl_clean)
    words <- strsplit(lbl_spaced, "[ \t\r\n]+")[[1]]
    words <- words[nzchar(words)]
    max_word_len <- if (length(words) > 0L) max(nchar(words)) else 1L
    total_hdr_len <- nchar(lbl_spaced)

    # Calcul de la longueur maximale de la plus longue ligne pour une coupe optimale en 2 lignes
    best_2line_len <- total_hdr_len
    has_multiword_line <- FALSE
    if (length(words) > 1L) {
      best_2line_len <- total_hdr_len
      for (i in 1L:(length(words) - 1L)) {
        l1 <- paste(words[1L:i], collapse = " ")
        l2 <- paste(words[(i + 1L):length(words)], collapse = " ")
        max_l <- max(nchar(l1), nchar(l2))
        if (max_l < best_2line_len) best_2line_len <- max_l
      }
      for (i in 1L:(length(words) - 1L)) {
        l1 <- paste(words[1L:i], collapse = " ")
        l2 <- paste(words[(i + 1L):length(words)], collapse = " ")
        if ((nchar(l1) == best_2line_len && i > 1L) || (nchar(l2) == best_2line_len && (length(words) - i) > 1L)) {
          has_multiword_line <- TRUE
        }
      }
    }

    # 2. Cellules de donnees nettoyees
    vals <- body_df[[col]]
    vals_clean <- gsub("[*_`#]|<[^>]+>", "", as.character(vals))
    vals_clean <- gsub("\\\\[a-zA-Z]+(\\[[^\\]]*\\])?(\\{[^}]*\\})?", "", vals_clean)
    vals_clean <- gsub("[{}]", "", vals_clean)
    vals_clean <- trimws(vals_clean)
    vals_clean <- vals_clean[!is.na(vals_clean) & nzchar(vals_clean)]

    val_lens <- if (length(vals_clean) > 0L) nchar(vals_clean) else 0L
    max_val_len <- if (length(val_lens) > 0L) max(val_lens) else 1L
    mean_val_len <- if (length(val_lens) > 0L) mean(val_lens) else 1
    p90_val_len <- if (length(val_lens) > 1L) stats::quantile(val_lens, 0.90, names = FALSE) else max_val_len

    # Classification de la colonne :
    # a. Identifiants courts alphanumeriques (ex: "Foie 07/07", "Piece 1") : ne doivent jamais etre coupes
    has_short_id <- (length(vals_clean) > 0L) && all(val_lens <= 14L) && any(grepl("[0-9]", vals_clean)) && any(grepl("[a-zA-Z]", vals_clean))
    # b. Colonne narrative descriptive (phrases, resections, noms de parametres longs)
    is_narrative <- (mean_val_len > 12 || max_val_len > 16) && !has_short_id
    # c. Colonne courte/compacte (chiffres, pourcentages, codes)
    is_compact <- (max_val_len <= 8L) && !has_short_id

    list(
      col = col,
      words = words,
      max_word_len = max_word_len,
      total_hdr_len = total_hdr_len,
      best_2line_len = best_2line_len,
      has_multiword_line = has_multiword_line,
      max_val_len = max_val_len,
      mean_val_len = mean_val_len,
      p90_val_len = p90_val_len,
      has_short_id = has_short_id,
      is_narrative = is_narrative,
      is_compact = is_compact,
      vals_clean = vals_clean
    )
  })

  # Calcul des demandes
  demands <- vapply(col_info, function(info) {
    if (info$is_narrative) {
      # Juste ce qui est necessaire pour tenir le contenu descriptif sans retour a la ligne
      return(max(info$max_val_len + 4L, info$total_hdr_len, 1L))
    }

    if (info$has_short_id) {
      # Identifiant court : doit tenir sur une seule ligne
      return(max(info$max_val_len + 1L, info$total_hdr_len, info$max_word_len + 1L))
    }

    # Pour les en-tetes multi-mots :
    # Donner la place suffisante pour que l'en-tete tienne STRICTEMENT sur 2 lignes propres
    # sans jamais repousser les unites sur une 3e ligne isolee
    hdr_demand <- if (n_cols <= 4L && info$total_hdr_len <= 14L) {
      info$total_hdr_len
    } else {
      extra <- if (grepl("[()/–-]", info$col)) 3L else 2L
      max(info$max_word_len + 2L, info$best_2line_len + extra)
    }
    val_demand <- info$max_val_len
    max(hdr_demand, val_demand, 1L)
  }, numeric(1))
  names(demands) <- visible_cols

  # Transformation puissance
  scores <- demands^0.90

  # Planchers minimaux calibres sur la typographie XeLaTeX
  min_pcts <- vapply(col_info, function(info) {
    base_min <- max(5L, as.integer(floor(25 / n_cols)))
    if (info$is_narrative && info$max_val_len >= 20L) {
      max(base_min, 23L)
    } else if (info$has_short_id) {
      max(base_min, 8L)
    } else if (info$best_2line_len >= 15L) {
      max(base_min, 15L)
    } else if (info$has_multiword_line && info$best_2line_len >= 9L) {
      max(base_min, 11L)
    } else if (info$max_word_len >= 9L) {
      max(base_min, 10L)
    } else if (info$max_word_len >= 7L) {
      max(base_min, 8L)
    } else if (info$is_compact) {
      max(base_min, 6L)
    } else {
      base_min
    }
  }, integer(1))

  # Allocation contrainte garantissant que les planchers ne soient jamais erodes
  pcts <- min_pcts
  rem_budget <- 100L - sum(pcts)

  if (rem_budget > 0L) {
    weights <- scores
    add_target <- rem_budget * weights / sum(weights)
    add_floor <- as.integer(floor(add_target))
    pcts <- pcts + add_floor
    diff <- 100L - sum(pcts)
    if (diff > 0L) {
      remainders <- add_target - add_floor
      top_idx <- order(remainders, decreasing = TRUE)[seq_len(diff)]
      pcts[top_idx] <- pcts[top_idx] + 1L
    }
  } else if (rem_budget < 0L) {
    target <- pcts / sum(pcts) * 100
    pcts <- as.integer(floor(target))
    diff <- 100L - sum(pcts)
    if (diff > 0L) {
      remainders <- target - pcts
      top_idx <- order(remainders, decreasing = TRUE)[seq_len(diff)]
      pcts[top_idx] <- pcts[top_idx] + 1L
    }
  }

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

  df <- tbl[["_data"]]

  # 1. Espace automatique avant les parentheses dans les en-tetes si absent (ex: CellSaver(mL) -> CellSaver (mL))
  for (i in seq_along(boxhead$var)) {
    lbl <- as.character(boxhead$column_label[[i]])
    if (grepl("([a-zA-Z0-9])\\(", lbl)) {
      new_lbl <- gsub("([a-zA-Z0-9])\\(", "\\1 (", lbl)
      boxhead$column_label[[i]] <- new_lbl
    }
  }
  tbl[["_boxhead"]] <- boxhead

  # 2. Inférence automatique des alignements si non spécifiés explicitement
  if (is.data.frame(df)) {
    for (col in visible) {
      curr_align <- boxhead$column_align[boxhead$var == col]
      if (is.na(curr_align) || curr_align == "left") {
        vals <- trimws(as.character(df[[col]]))
        vals <- vals[!is.na(vals) & nzchar(vals)]
        if (length(vals) > 0L) {
          detected_align <- husson_detect_col_alignment(vals)
          if (detected_align != "left") {
            tbl <- gt::cols_align(tbl, align = detected_align, columns = dplyr::all_of(col))
          }
        }
      }
    }
    boxhead <- tbl[["_boxhead"]]
  }

  # 3. Verification des largeurs existantes
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
  # En revanche, si des px() sont presents (qui debordent en LaTeX) ou si aucune largeur n'est specifiee,
  # on calcule la repartition optimale.
  if (!has_valid_pct || has_pixels) {
    if (is.data.frame(df)) {
      col_names <- intersect(visible, names(df))
      if (length(col_names) == n_cols) {
        width_map <- husson_calculate_optimal_widths(df, visible, boxhead = boxhead, tbl = tbl)
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

  # 4. Police et espacements proportionnes selon la densite du tableau
  # NOTE IMPORTANTE : gt pour LaTeX n'accepte QUE des entiers en pt ("10pt", "9pt", "8pt").
  # Les chaines avec decimales ("8.5pt") ou "px" sont ignorees silencieusement par gt et font retomber le tableau a 11pt.
  font_size <- if (n_cols >= 10L) "8pt" else if (n_cols >= 6L) "9pt" else "10pt"
  row_pad <- if (n_cols >= 8L) gt::px(2.5) else if (n_cols >= 6L) gt::px(3) else gt::px(3.5)
  col_pad <- if (n_cols >= 8L) gt::px(3) else if (n_cols >= 6L) gt::px(3.5) else gt::px(4)

  tbl |>
    gt::tab_options(
      table.width = gt::pct(100),
      table.font.size = font_size,
      data_row.padding = row_pad,
      column_labels.padding = col_pad
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
