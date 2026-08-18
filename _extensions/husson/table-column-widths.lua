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
          longest_words[column] = math.max(
            longest_words[column],
            unicode_length(word)
          )
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
