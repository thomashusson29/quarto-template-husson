-- Calcule automatiquement les largeurs des colonnes des tableaux Markdown.
--
-- Pandoc attribue la même largeur à toutes les colonnes lorsqu'aucune largeur
-- n'est précisée. Ce comportement gaspille de l'espace pour les colonnes de
-- libellés courts et augmente le nombre de retours à la ligne dans les colonnes
-- narratives. Le filtre estime donc le besoin de chaque colonne à partir de la
-- longueur moyenne de son contenu et de son mot le plus long.

-- Valeur volontairement prudente : elle réserve assez de largeur pour le mot
-- le plus long, y compris lorsqu'il est composé en gras ou en chasse fixe.
local FULL_LINE_CHARACTERS = 92
local ABSOLUTE_MINIMUM = 0.065
local ABSOLUTE_MAXIMUM = 0.60

local function unicode_length(text)
  local length = utf8.len(text)
  return length or #text
end

local function normalise_text(value)
  return pandoc.utils.stringify(value)
    :gsub("%s+", " ")
    :gsub("^%s+", "")
    :gsub("%s+$", "")
end

local function append_rows(destination, source)
  for _, row in ipairs(source or {}) do
    table.insert(destination, row)
  end
end

local function table_rows(tbl)
  local rows = {}

  if tbl.head then
    append_rows(rows, tbl.head.rows)
  end

  for _, body in ipairs(tbl.bodies or {}) do
    append_rows(rows, body.head)
    append_rows(rows, body.body)
  end

  if tbl.foot then
    append_rows(rows, tbl.foot.rows)
  end

  return rows
end

local function content_metrics(tbl, column_count)
  local totals = {}
  local counts = {}
  local longest_words = {}

  for column = 1, column_count do
    totals[column] = 0
    counts[column] = 0
    longest_words[column] = 0
  end

  for _, row in ipairs(table_rows(tbl)) do
    for column, cell in ipairs(row.cells or {}) do
      if column <= column_count then
        local text = normalise_text(cell.contents)
        local length = unicode_length(text)

        if length > 0 then
          totals[column] = totals[column] + length
          counts[column] = counts[column] + 1
        end

        for word in text:gmatch("%S+") do
          -- Découpage sur les tirets, barres obliques ou césures explicites
          for segment in word:gmatch("[^%-%s\u{00ad}\\%/]+") do
            local seg_len = unicode_length(segment)
            -- Les mots techniques/composés longs (> 12 caractères) sont sécables par césure LaTeX
            if seg_len > 12 then
              seg_len = math.ceil(seg_len / 2)
            end
            longest_words[column] = math.max(
              longest_words[column],
              seg_len
            )
          end
        end
      end
    end
  end

  return totals, counts, longest_words
end

local function bounded_proportions(scores, minimums)
  local widths = {}
  local active = {}
  local remaining_width = 1
  local remaining_score = 0

  for column, score in ipairs(scores) do
    active[column] = true
    remaining_score = remaining_score + score
  end

  local changed = true
  while changed do
    changed = false

    for column, score in ipairs(scores) do
      if active[column] then
        local proposed = remaining_width * score / remaining_score

        if proposed < minimums[column] then
          widths[column] = minimums[column]
          active[column] = false
          remaining_width = remaining_width - minimums[column]
          remaining_score = remaining_score - score
          changed = true
        end
      end
    end
  end

  for column, score in ipairs(scores) do
    if active[column] then
      widths[column] = remaining_width * score / remaining_score
    end
  end

  -- Une colonne narrative unique ne doit pas absorber presque toute la page.
  -- L'excédent éventuel est redistribué entre les autres colonnes.
  local excess = 0
  local recipients = 0
  for column, width in ipairs(widths) do
    if width > ABSOLUTE_MAXIMUM then
      excess = excess + width - ABSOLUTE_MAXIMUM
      widths[column] = ABSOLUTE_MAXIMUM
    else
      recipients = recipients + 1
    end
  end

  if excess > 0 and recipients > 0 then
    for column, width in ipairs(widths) do
      if width < ABSOLUTE_MAXIMUM then
        widths[column] = width + excess / recipients
      end
    end
  end

  return widths
end

function Table(tbl)
  if not FORMAT:match("latex") then
    return nil
  end

  -- Si des largeurs de colonnes ont été explicitement définies par l'auteur, ne pas les écraser
  if tbl.attr and tbl.attr.attributes and (tbl.attr.attributes["tbl-colwidths"] or tbl.attr.attributes["colwidths"]) then
    return nil
  end

  local column_count = #tbl.colspecs

  if column_count < 2 then
    return nil
  end

  local totals, counts, longest_words = content_metrics(tbl, column_count)
  local scores = {}
  local minimums = {}

  for column = 1, column_count do
    local average = totals[column] / math.max(counts[column], 1)

    -- La racine carrée empêche une cellule exceptionnellement longue de
    -- monopoliser la largeur tout en favorisant les colonnes narratives.
    scores[column] = math.sqrt(math.max(average, 1))
    minimums[column] = math.max(
      ABSOLUTE_MINIMUM,
      math.min(0.24, (longest_words[column] + 1) / FULL_LINE_CHARACTERS)
    )
  end

  local widths = bounded_proportions(scores, minimums)

  for column, colspec in ipairs(tbl.colspecs) do
    tbl.colspecs[column] = {colspec[1], widths[column]}
  end

  return tbl
end

-- Intercepte et ajuste automatiquement les tableaux générés en LaTeX brut (ex: gt, kable)
function RawBlock(raw)
  if not FORMAT:match("latex") then
    return nil
  end

  local text = raw.text
  if not (text:match("\\begin%{tabular") or text:match("\\begin%{longtable")) then
    return nil
  end

  -- 1. Détection des largeurs fixes en pt dans dimexpr (ex: générées par gt à partir de px)
  local pt_widths = {}
  for w in text:gmatch("dimexpr%s*([%d%.]+)pt") do
    table.insert(pt_widths, tonumber(w))
  end

  if #pt_widths > 0 then
    local total_pt = 0
    for _, w in ipairs(pt_widths) do
      total_pt = total_pt + w
    end

    -- Normalisation automatique à 100% de \linewidth
    if total_pt > 0 then
      text = text:gsub("(dimexpr%s*)([%d%.]+)pt", function(pre, w)
        local num = tonumber(w)
        local proportion = num / total_pt
        return string.format("%s%.3f\\linewidth", pre, proportion)
      end)
    end
  end

  -- Détection du nombre de colonnes pour ajuster la police
  local num_cols = #pt_widths
  if num_cols == 0 then
    local header_row = text:match("\\toprule%s*(.-)%s*\\\\")
      or text:match("\\midrule%s*(.-)%s*\\\\")
      or text:match("\\hline%s*(.-)%s*\\\\")
    if header_row then
      local _, count = header_row:gsub("[^\\]&", "")
      num_cols = count + 1
    end
  end

  -- 2. Ajustement de la taille de police (réduction maximale autorisée : 25% de 11pt)
  -- \small (~10pt, -9%) par défaut, ou \footnotesize (~9pt, -18%) si >= 6 colonnes
  local target_size = (num_cols >= 6) and 9 or 10
  local target_skip = (num_cols >= 6) and 11 or 12

  if text:match("\\fontsize") then
    text = text:gsub("\\fontsize%{%s*[%d%.]+%s*p?t?%s*%}%{%s*[%d%.]+%s*p?t?%s*%}", function()
      return string.format("\\fontsize{%.1fpt}{%.1fpt}", target_size, target_skip)
    end)
  end

  if text ~= raw.text then
    return pandoc.RawBlock(raw.format, text)
  end

  return nil
end

function RawInline(el)
  if FORMAT:match("latex") and el.format == "html" and (el.text == "<br>" or el.text == "<br/>" or el.text == "<br />") then
    return pandoc.RawInline("latex", "\\newline ")
  end
  return nil
end

