-- table-column-widths.lua
-- Mise en page et calibrage automatiques de tous les tableaux (Markdown, kable, gt, gtsummary, tibble)
-- Fonctionne nativement sans nécessiter de charger gt-page-fit.R dans le document .qmd :
-- 1. Largeur 100% de \linewidth avec répartition optimale minimisant la hauteur totale
-- 2. Équilibrage des en-têtes multi-mots sur 2 lignes maximum sans unité orpheline
-- 3. Insertion automatique d'un espace avant les parenthèses d'unités (ex: CellSaver(mL) -> CellSaver (mL))
-- 4. Inférence automatique des alignements (nombres/pourcentages à droite, codes courts au centre, texte à gauche)
-- 5. Taille de police adaptative selon la densité (10pt < 6 col, 9pt pour 6-9 col, 8pt >= 10 col)

local function unicode_length(text)
  if not text then return 0 end
  local ok, length = pcall(utf8.len, text)
  if ok and length then
    return length
  end
  return #text
end

local function trim(s)
  if not s then return "" end
  local res = s:gsub("^%s+", ""):gsub("%s+$", "")
  return res
end

local function normalise_text(value)
  local res = pandoc.utils.stringify(value):gsub("%s+", " ")
  return trim(res)
end

local function space_unit_parentheses(str)
  if not str then return "" end
  local res = str:gsub("([%a%d])%(", "%1 (")
  return res
end

-- Nettoyage d'une chaîne LaTeX ou Markdown pour mesurer sa longueur réelle affichée
local function clean_cell_text(s)
  if not s then return "" end
  local res = s
  res = res:gsub("\\textbf%s*{([^{}]*)}", "%1")
  res = res:gsub("\\textit%s*{([^{}]*)}", "%1")
  res = res:gsub("\\emph%s*{([^{}]*)}", "%1")
  res = res:gsub("\\textrm%s*{([^{}]*)}", "%1")
  res = res:gsub("\\texttt%s*{([^{}]*)}", "%1")
  res = res:gsub("\\textsuperscript%s*{([^{}]*)}", "%1")
  res = res:gsub("\\textsubscript%s*{([^{}]*)}", "%1")
  res = res:gsub("\\mbox%s*{([^{}]*)}", "%1")
  res = res:gsub("\\([%%&_#$])", "%1")
  res = res:gsub("\\[a-zA-Z]+%s*%b[]%s*%b{}", "")
  res = res:gsub("\\[a-zA-Z]+%s*%b{}", "")
  res = res:gsub("\\[a-zA-Z]+", " ")
  res = res:gsub("[{}$*_`#]", "")
  res = res:gsub("<[^>]+>", "")
  res = res:gsub("%s+", " ")
  return trim(res)
end

local function split_words(s)
  local words = {}
  for w in s:gmatch("%S+") do
    table.insert(words, w)
  end
  return words
end

-- Inférence automatique de l'alignement d'une colonne selon ses valeurs nettoyées
local function detect_col_alignment(vals)
  local clean_vals = {}
  for _, v in ipairs(vals or {}) do
    local tv = trim(v)
    if tv ~= "" and tv ~= "NA" and tv ~= "—" and tv ~= "-" and tv ~= "–" then
      table.insert(clean_vals, tv)
    end
  end
  if #clean_vals == 0 then
    return "left"
  end

  local num_count = 0
  local all_short = true
  local has_code_pattern = false
  local short_keywords = {
    ["Absente"] = true, ["Absent"] = true, ["Non atteint"] = true,
    ["Oui"] = true, ["Non"] = true, ["F0"] = true, ["F1"] = true,
    ["F2"] = true, ["F3"] = true, ["F4"] = true,
    ["Favorable"] = true, ["Défavorable"] = true
  }

  for _, v in ipairs(clean_vals) do
    -- Valeurs numériques, pourcentages, moyennes ± SD, médianes [IQR] ou p-values
    local v_ascii = v:gsub("−", "-"):gsub("±", "+/-")
    if v_ascii:match("^[<>]?[+-]?%d[%d%s,%.%/%%+%-–%(%)%[%];:]*$") then
      num_count = num_count + 1
    end
    if unicode_length(v) > 14 then
      all_short = false
    end
    if v:match("^%d+[–-]%d+$") or v:match("^H%d") or short_keywords[v] then
      has_code_pattern = true
    end
  end

  if (num_count / #clean_vals) >= 0.60 then
    return "right"
  end
  if all_short and has_code_pattern then
    return "center"
  end
  return "left"
end

-- Algorithme de répartition optimale des largeurs (en %) identique à gt-page-fit.R
local function calculate_optimal_widths(headers, cols_values)
  local n_cols = #headers
  if n_cols <= 1 then
    return { 100 }
  end

  local col_info = {}
  for col_idx = 1, n_cols do
    local raw_hdr = headers[col_idx] or ""
    local lbl_clean = clean_cell_text(raw_hdr)
    local lbl_spaced = space_unit_parentheses(lbl_clean)
    local words = split_words(lbl_spaced)

    local max_word_len = 1
    for _, w in ipairs(words) do
      local wl = unicode_length(w)
      if wl > max_word_len then max_word_len = wl end
    end
    local total_hdr_len = math.max(1, unicode_length(lbl_spaced))

    local best_2line_len = total_hdr_len
    local has_multiword_line = false
    if #words > 1 then
      for i = 1, (#words - 1) do
        local l1 = table.concat(words, " ", 1, i)
        local l2 = table.concat(words, " ", i + 1, #words)
        local max_l = math.max(unicode_length(l1), unicode_length(l2))
        if max_l < best_2line_len then
          best_2line_len = max_l
        end
      end
      for i = 1, (#words - 1) do
        local l1 = table.concat(words, " ", 1, i)
        local l2 = table.concat(words, " ", i + 1, #words)
        if (unicode_length(l1) == best_2line_len and i > 1) or
           (unicode_length(l2) == best_2line_len and (#words - i) > 1) then
          has_multiword_line = true
        end
      end
    end

    local vals = cols_values[col_idx] or {}
    local vals_clean = {}
    local max_val_len = 1
    local sum_val_len = 0
    local all_le_14 = true
    local any_digit = false
    local any_alpha = false

    for _, v in ipairs(vals) do
      local vc = clean_cell_text(v)
      if vc ~= "" then
        table.insert(vals_clean, vc)
        local vl = unicode_length(vc)
        if vl > max_val_len then max_val_len = vl end
        sum_val_len = sum_val_len + vl
        if vl > 14 then all_le_14 = false end
        if vc:match("%d") then any_digit = true end
        if vc:match("%a") then any_alpha = true end
      end
    end

    local mean_val_len = (#vals_clean > 0) and (sum_val_len / #vals_clean) or 1
    local has_short_id = (#vals_clean > 0) and all_le_14 and any_digit and any_alpha
    local is_narrative = (mean_val_len > 12 or max_val_len > 16) and (not has_short_id)
    local is_compact = (max_val_len <= 8) and (not has_short_id)

    col_info[col_idx] = {
      raw_hdr = lbl_spaced,
      max_word_len = max_word_len,
      total_hdr_len = total_hdr_len,
      best_2line_len = best_2line_len,
      has_multiword_line = has_multiword_line,
      max_val_len = max_val_len,
      mean_val_len = mean_val_len,
      has_short_id = has_short_id,
      is_narrative = is_narrative,
      is_compact = is_compact,
      vals_clean = vals_clean
    }
  end

  local demands = {}
  local scores = {}
  local min_pcts = {}
  local sum_min = 0

  for i = 1, n_cols do
    local info = col_info[i]
    local d = 1
    if info.is_narrative then
      d = math.max(info.max_val_len + 4, info.total_hdr_len, 1)
    elseif info.has_short_id then
      d = math.max(info.max_val_len + 1, info.total_hdr_len, info.max_word_len + 1)
    else
      local hdr_demand
      if n_cols <= 4 and info.total_hdr_len <= 14 then
        hdr_demand = info.total_hdr_len
      else
        local extra = (info.raw_hdr:match("[%(%)/%-]") or info.raw_hdr:find("–", 1, true)) and 3 or 2
        hdr_demand = math.max(info.max_word_len + 2, info.best_2line_len + extra)
      end
      d = math.max(hdr_demand, info.max_val_len, 1)
    end
    demands[i] = d
    scores[i] = d ^ 0.90

    local base_min = math.max(5, math.floor(25 / n_cols))
    local mp = base_min
    if info.is_narrative and info.max_val_len >= 20 then
      mp = math.max(base_min, 23)
    elseif info.has_short_id then
      mp = math.max(base_min, 8)
    elseif info.best_2line_len >= 15 then
      mp = math.max(base_min, 15)
    elseif info.has_multiword_line and info.best_2line_len >= 9 then
      mp = math.max(base_min, 11)
    elseif info.max_word_len >= 9 then
      mp = math.max(base_min, 10)
    elseif info.max_word_len >= 7 then
      mp = math.max(base_min, 8)
    elseif info.is_compact then
      mp = math.max(base_min, 6)
    end
    min_pcts[i] = mp
    sum_min = sum_min + mp
  end

  local pcts = {}
  for i = 1, n_cols do pcts[i] = min_pcts[i] end
  local rem_budget = 100 - sum_min

  local function distribute_remainders(targets, floors, diff)
    local order = {}
    for i = 1, n_cols do
      order[i] = { idx = i, rem = targets[i] - floors[i] }
    end
    table.sort(order, function(a, b)
      if a.rem == b.rem then return a.idx < b.idx end
      return a.rem > b.rem
    end)
    for k = 1, math.min(diff, n_cols) do
      local idx = order[k].idx
      pcts[idx] = pcts[idx] + 1
    end
  end

  if rem_budget > 0 then
    local sum_scores = 0
    for i = 1, n_cols do sum_scores = sum_scores + scores[i] end
    local add_targets = {}
    local add_floors = {}
    local current_sum = 0
    for i = 1, n_cols do
      add_targets[i] = rem_budget * scores[i] / math.max(sum_scores, 1e-6)
      add_floors[i] = math.floor(add_targets[i])
      pcts[i] = pcts[i] + add_floors[i]
      current_sum = current_sum + pcts[i]
    end
    local diff = 100 - current_sum
    if diff > 0 then
      distribute_remainders(add_targets, add_floors, diff)
    end
  elseif rem_budget < 0 then
    local targets = {}
    local floors = {}
    local current_sum = 0
    for i = 1, n_cols do
      targets[i] = (min_pcts[i] / math.max(sum_min, 1)) * 100.0
      floors[i] = math.floor(targets[i])
      pcts[i] = floors[i]
      current_sum = current_sum + pcts[i]
    end
    local diff = 100 - current_sum
    if diff > 0 then
      distribute_remainders(targets, floors, diff)
    end
  end

  return pcts, col_info
end

function Table(tbl)
  -- Si des largeurs de colonnes ont été explicitement définies par l'auteur, ne pas les écraser
  if tbl.attr and tbl.attr.attributes and (tbl.attr.attributes["tbl-colwidths"] or tbl.attr.attributes["colwidths"]) then
    return nil
  end

  local column_count = #tbl.colspecs
  if column_count < 2 then
    return nil
  end

  local headers = {}
  local cols_values = {}
  for c = 1, column_count do
    headers[c] = ""
    cols_values[c] = {}
  end

  -- 1. Lecture et espacement des parenthèses d'unités dans l'en-tête
  if tbl.head and tbl.head.rows and #tbl.head.rows > 0 then
    local last_hdr_row = tbl.head.rows[#tbl.head.rows]
    for c, cell in ipairs(last_hdr_row.cells or {}) do
      if c <= column_count then
        headers[c] = normalise_text(cell.contents)
        cell.contents = pandoc.Blocks(cell.contents):walk({
          Str = function(el)
            local spaced = space_unit_parentheses(el.text)
            if spaced ~= el.text then
              return pandoc.Str(spaced)
            end
            return nil
          end
        })
      end
    end
  end

  -- 2. Lecture des valeurs du corps
  for _, body in ipairs(tbl.bodies or {}) do
    for _, row in ipairs(body.body or {}) do
      for c, cell in ipairs(row.cells or {}) do
        if c <= column_count then
          table.insert(cols_values[c], normalise_text(cell.contents))
        end
      end
    end
  end

  local pcts, col_info = calculate_optimal_widths(headers, cols_values)

  -- 3. Alignement automatique (si AlignDefault) et largeurs (en LaTeX)
  for c, colspec in ipairs(tbl.colspecs) do
    local align = colspec[1]
    if align == pandoc.AlignDefault and col_info[c] then
      local detected = detect_col_alignment(col_info[c].vals_clean)
      if detected == "right" then
        align = pandoc.AlignRight
      elseif detected == "center" then
        align = pandoc.AlignCenter
      else
        align = pandoc.AlignLeft
      end
    end
    local width = colspec[2]
    if FORMAT:match("latex") then
      width = pcts[c] / 100.0
    end
    tbl.colspecs[c] = { align, width }
  end

  return tbl
end

-- Extraction d'un bloc entre accolades équilibrées { ... } à partir de start_pos
local function extract_braced(str, start_pos)
  local open_pos = str:find("{", start_pos, true)
  if not open_pos then return nil end
  local depth = 0
  local i = open_pos
  local len = #str
  while i <= len do
    local ch = str:sub(i, i)
    if ch == "\\" then
      i = i + 2
    else
      if ch == "{" then
        depth = depth + 1
      elseif ch == "}" then
        depth = depth - 1
        if depth == 0 then
          return str:sub(open_pos + 1, i - 1), open_pos, i
        end
      end
      i = i + 1
    end
  end
  return nil
end

-- Analyse de la spécification de colonnes LaTeX (ex: "@{\extracolsep{\fill}}lccc")
local function parse_latex_colspec(spec)
  local has_linewidth = spec:find("\\linewidth", 1, true) or spec:find("\\textwidth", 1, true)
  local pt_widths = {}
  for w in spec:gmatch("dimexpr%s*([%d%.]+)pt") do
    table.insert(pt_widths, tonumber(w))
  end

  local alignments = {}
  local i = 1
  local len = #spec
  local pending_align = nil

  while i <= len do
    local ch = spec:sub(i, i)
    if ch == "@" or ch == "!" or ch == "<" then
      local _, _, end_b = extract_braced(spec, i + 1)
      i = end_b and (end_b + 1) or (i + 1)
    elseif ch == ">" then
      local mod_content, _, end_b = extract_braced(spec, i + 1)
      if mod_content then
        if mod_content:find("raggedleft", 1, true) then
          pending_align = "right"
        elseif mod_content:find("centering", 1, true) then
          pending_align = "center"
        elseif mod_content:find("raggedright", 1, true) then
          pending_align = "left"
        end
        i = end_b + 1
      else
        i = i + 1
      end
    elseif ch == "p" or ch == "m" or ch == "b" then
      local _, _, end_b = extract_braced(spec, i + 1)
      table.insert(alignments, pending_align or "left")
      pending_align = nil
      i = end_b and (end_b + 1) or (i + 1)
    elseif ch == "l" then
      table.insert(alignments, pending_align or "left")
      pending_align = nil
      i = i + 1
    elseif ch == "c" then
      table.insert(alignments, pending_align or "center")
      pending_align = nil
      i = i + 1
    elseif ch == "r" then
      table.insert(alignments, pending_align or "right")
      pending_align = nil
      i = i + 1
    else
      i = i + 1
    end
  end

  return alignments, has_linewidth, pt_widths
end

-- Découpage d'une ligne LaTeX en cellules séparées par & (hors \& et hors accolades)
local function split_latex_row_cells(row_str)
  local cells = {}
  local current = {}
  local depth = 0
  local i = 1
  local len = #row_str
  while i <= len do
    local ch = row_str:sub(i, i)
    if ch == "\\" then
      local next_ch = row_str:sub(i + 1, i + 1)
      table.insert(current, ch .. next_ch)
      i = i + 2
    elseif ch == "{" then
      depth = depth + 1
      table.insert(current, ch)
      i = i + 1
    elseif ch == "}" then
      if depth > 0 then depth = depth - 1 end
      table.insert(current, ch)
      i = i + 1
    elseif ch == "&" and depth == 0 then
      table.insert(cells, trim(table.concat(current)))
      current = {}
      i = i + 1
    else
      table.insert(current, ch)
      i = i + 1
    end
  end
  table.insert(cells, trim(table.concat(current)))
  return cells
end

-- Extraction des en-têtes et lignes de données d'un environnement tabular / tabular* / longtable
local function extract_latex_table_data(body_tex, n_cols)
  local headers = {}
  local cols_values = {}
  for c = 1, n_cols do
    headers[c] = ""
    cols_values[c] = {}
  end

  local cleaned_body = body_tex
    :gsub("\\toprule", "")
    :gsub("\\bottomrule", "")
    :gsub("\\hline", "")
    :gsub("\\addlinespace%s*%b[]", "")
    :gsub("\\addlinespace", "")
    :gsub("\\cmidrule%b()%s*%b{}", "")
    :gsub("\\cmidrule%s*%b{}", "")
    :gsub("\\endfirsthead", "")
    :gsub("\\endhead", "")
    :gsub("\\endfoot", "")
    :gsub("\\endlastfoot", "")

  local mid_pos = cleaned_body:find("\\midrule", 1, true)
  local header_part = nil
  local data_part = cleaned_body

  if mid_pos then
    header_part = cleaned_body:sub(1, mid_pos - 1)
    data_part = cleaned_body:sub(mid_pos + #("\\midrule"))
  end

  local function collect_rows(segment)
    local rows = {}
    if not segment then return rows end
    local pos = 1
    while pos <= #segment do
      local s, e = segment:find("\\\\", pos, true)
      local row_txt
      if s then
        row_txt = segment:sub(pos, s - 1)
        pos = e + 1
        -- Sauter un éventuel argument optionnel \\[2pt]
        if segment:sub(pos, pos) == "[" then
          local close_br = segment:find("]", pos, true)
          if close_br then pos = close_br + 1 end
        end
      else
        row_txt = segment:sub(pos)
        pos = #segment + 1
      end
      row_txt = trim(row_txt:gsub("\\midrule", ""))
      if row_txt ~= "" and not row_txt:match("^\\caption") and not row_txt:match("^\\label") then
        local cells = split_latex_row_cells(row_txt)
        if #cells == n_cols and not row_txt:find("\\multicolumn", 1, true) then
          table.insert(rows, cells)
        end
      end
    end
    return rows
  end

  local hdr_rows = collect_rows(header_part)
  local data_rows = collect_rows(data_part)

  if #hdr_rows > 0 then
    headers = hdr_rows[#hdr_rows]
  elseif #data_rows > 0 then
    headers = table.remove(data_rows, 1)
  end

  for _, r in ipairs(data_rows) do
    for c = 1, n_cols do
      table.insert(cols_values[c], r[c] or "")
    end
  end

  return headers, cols_values
end

-- Intercepte et ajuste automatiquement les tableaux générés en LaTeX brut (gt, gtsummary, kable)
function RawBlock(raw)
  if not FORMAT:match("latex") then
    return nil
  end

  local text = raw.text
  if not (text:match("\\begin%{tabular") or text:match("\\begin%{longtable")) then
    return nil
  end

  local env_start, env_end, env_name = text:find("\\begin{(tabular%*?)}")
  local spec_content, spec_open, spec_close
  if env_start then
    local search_pos = env_end + 1
    if env_name == "tabular*" then
      local _, _, width_close = extract_braced(text, search_pos)
      if width_close then search_pos = width_close + 1 end
    end
    -- Sauter un éventuel argument optionnel [t] / [c] / [b]
    local opt_s, opt_e = text:find("^%s*%b[]", search_pos)
    if opt_e then search_pos = opt_e + 1 end
    spec_content, spec_open, spec_close = extract_braced(text, search_pos)
  end

  local num_cols = 0

  if spec_content then
    local alignments, has_linewidth, pt_widths = parse_latex_colspec(spec_content)
    num_cols = #alignments

    if not has_linewidth and num_cols >= 2 then
      local close_tag = "\\end{" .. env_name .. "}"
      local close_pos = text:find(close_tag, spec_close + 1, true)
      local body_tex = close_pos and text:sub(spec_close + 1, close_pos - 1) or text:sub(spec_close + 1)

      -- Espacement automatique des parenthèses d'unités dans l'en-tête (avant \midrule)
      local mid_p = body_tex:find("\\midrule", 1, true)
      if mid_p then
        local hdr_tex = body_tex:sub(1, mid_p - 1):gsub("([%a%d])%(", "%1 (")
        body_tex = hdr_tex .. body_tex:sub(mid_p)
      end

      local headers, cols_values = extract_latex_table_data(body_tex, num_cols)
      local pcts, col_info = calculate_optimal_widths(headers, cols_values)

      -- Si des largeurs fixes en pt étaient présentes ET que le tableau n'avait pas de données extractibles,
      -- repli sur la proportionnalité des pt
      if #pt_widths == num_cols and #headers == 0 then
        local total_pt = 0
        for _, w in ipairs(pt_widths) do total_pt = total_pt + w end
        if total_pt > 0 then
          for c = 1, num_cols do
            pcts[c] = math.floor((pt_widths[c] / total_pt) * 100 + 0.5)
          end
        end
      end

      local new_specs = { "@{\\extracolsep{\\fill}}" }
      for c = 1, num_cols do
        local align = alignments[c] or "left"
        if align == "left" and col_info and col_info[c] then
          local detected = detect_col_alignment(col_info[c].vals_clean)
          if detected ~= "left" then align = detected end
        end
        local align_cmd = "\\raggedright"
        if align == "right" then
          align_cmd = "\\raggedleft"
        elseif align == "center" then
          align_cmd = "\\centering"
        end
        local prop_str = string.format("%.2f", pcts[c] / 100.0):gsub("0+$", ""):gsub("%.$", ".0")
        table.insert(
          new_specs,
          string.format(
            ">{\\%s\\arraybackslash}p{\\dimexpr %s\\linewidth -2\\tabcolsep-1.5\\arrayrulewidth}",
            align_cmd:sub(2),
            prop_str
          )
        )
      end

      local new_begin = "\\begin{tabular*}{\\linewidth}{" .. table.concat(new_specs) .. "}"
      if close_pos then
        text = text:sub(1, env_start - 1)
          .. new_begin
          .. body_tex
          .. "\\end{tabular*}"
          .. text:sub(close_pos + #close_tag)
      else
        text = text:sub(1, env_start - 1)
          .. new_begin
          .. body_tex
      end
    end
  end

  if num_cols == 0 then
    local header_row = text:match("\\toprule%s*(.-)%s*\\\\")
      or text:match("\\midrule%s*(.-)%s*\\\\")
      or text:match("\\hline%s*(.-)%s*\\\\")
    if header_row then
      local _, count = header_row:gsub("[^\\]&", "")
      num_cols = count + 1
    end
  end

  -- Ajustement de la taille de police selon la densité de colonnes (10pt / 9pt / 8pt)
  local target_size = (num_cols >= 10) and 8.0 or ((num_cols >= 6) and 9.0 or 10.0)
  local target_skip = (num_cols >= 10) and 9.6 or ((num_cols >= 6) and 10.8 or 12.0)

  if text:match("\\fontsize") then
    text = text:gsub("\\fontsize%{%s*([%d%.]+)%s*p?t?%s*%}%{%s*([%d%.]+)%s*p?t?%s*%}", function(cur_sz)
      local n_sz = tonumber(cur_sz)
      -- Si gt a émis sa taille par défaut (12pt) ou une taille > target_size, on applique target_size
      if not n_sz or n_sz > target_size then
        return string.format("\\fontsize{%.1fpt}{%.1fpt}", target_size, target_skip)
      end
      return nil
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
