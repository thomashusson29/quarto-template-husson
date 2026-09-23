-- navigation-header.lua
-- Filtre Lua Pandoc pour la barre de navigation hierarchique Quarto PDF
-- Reconstruit automatiquement l'arborescence des headings (H1 a H5)
-- Affiche uniquement la section courante et sa hierarchie active
-- Prend en compte l'attribut facultatif nav-title pour les titres courts
-- Respecte la police globale du document (via \normalfont)

local function is_latex_format()
  return FORMAT:match("latex")
end

local function is_revealjs_format()
  return FORMAT:match("revealjs")
end

local function clean_inlines(inlines)
  return inlines:walk({
    Footnote = function(fn) return {} end,
    Cite = function(c) return c.content end
  })
end

local function get_heading_title(h)
  if not h then return "" end

  -- 1. Attribut nav-title prioritaire
  local nav_title = h.attributes and h.attributes["nav-title"]
  if nav_title and nav_title ~= "" then
    local doc = pandoc.read(nav_title, "markdown")
    local tex = pandoc.write(doc, "latex"):gsub("%s*$", ""):gsub("^%s*", "")
    return tex
  end

  -- 2. Titre reel issu du heading Pandoc (sans notes de bas de page)
  local cleaned = clean_inlines(h.content)
  local doc = pandoc.Pandoc({pandoc.Plain(cleaned)})
  local tex = pandoc.write(doc, "latex"):gsub("%s*$", ""):gsub("^%s*", "")
  return tex
end

local function extract_meta_text(meta_item)
  if not meta_item then return "" end
  if type(meta_item) == "table" and meta_item.t == "MetaInlines" then
    local cleaned = clean_inlines(meta_item)
    local d = pandoc.Pandoc({pandoc.Plain(cleaned)})
    return pandoc.write(d, "latex"):gsub("%s*$", ""):gsub("^%s*", "")
  elseif type(meta_item) == "table" and meta_item.t == "MetaBlocks" then
    local d = pandoc.Pandoc(meta_item)
    return pandoc.write(d, "latex"):gsub("%s*$", ""):gsub("^%s*", "")
  elseif type(meta_item) == "table" and meta_item.t == "MetaList" then
    local names = {}
    for _, item in ipairs(meta_item) do
      local s = extract_meta_text(item)
      if s ~= "" then table.insert(names, s) end
    end
    return table.concat(names, ", ")
  elseif type(meta_item) == "table" and meta_item.name then
    return extract_meta_text(meta_item.name)
  else
    return pandoc.utils.stringify(meta_item)
  end
end

local function process_latex(doc)

  -- Extraction des metadonnees pour le pied de page (auteur et titre)
  local doc_title = extract_meta_text(doc.meta["short-title"] or doc.meta["footer-title"] or doc.meta.title)
  local doc_author = extract_meta_text(doc.meta["footer-author"] or doc.meta.author)
  local footer_left = extract_meta_text(doc.meta["footer-left"])

  local footer_defs = {}
  if doc_title ~= "" then
    table.insert(footer_defs, "\\hussondoctitle{" .. doc_title .. "}")
  end
  if doc_author ~= "" then
    table.insert(footer_defs, "\\hussondocauthor{" .. doc_author .. "}")
  end
  if footer_left ~= "" then
    table.insert(footer_defs, "\\hussondocfooterleft{" .. footer_left .. "}")
  end

  -- Possibilite de desactiver la barre de navigation d'en-tete via le frontmatter YAML
  if doc.meta["navigation-bar"] == false or doc.meta["navbar"] == false then
    if #footer_defs > 0 then
      local fdefs_latex = "\n% Metadonnees du pied de page Husson\n" .. table.concat(footer_defs, "\n") .. "\n"
      table.insert(doc.blocks, 1, pandoc.RawBlock("latex", fdefs_latex))
    end
    return doc
  end

  -- 1. Collecter les evenements structurels (headers et contenu)
  local items = {}
  doc:walk({
    Header = function(h)
      if h.level >= 1 and h.level <= 5 then
        if not (h.classes:includes("unlisted") or (h.attributes and h.attributes["nav"] == "false")) then
          table.insert(items, { type = "header", h = h, level = h.level })
        end
      end
    end,
    Para = function(p)
      table.insert(items, { type = "content" })
    end,
    Table = function(t)
      table.insert(items, { type = "content" })
    end,
    CodeBlock = function(c)
      table.insert(items, { type = "content" })
    end,
    BlockQuote = function(b)
      table.insert(items, { type = "content" })
    end
  })

  -- Identifier les headers qui necessitent reellement une marque
  -- Si un header est suivi immediatement d'un sous-titre de niveau superieur sans contenu,
  -- seul le sous-titre le plus profond (ou le contenu reel commence) emet une marque.
  local header_seq = {}
  for i, it in ipairs(items) do
    if it.type == "header" then
      local next_it = items[i + 1]
      local needs_mark = true
      if next_it and next_it.type == "header" and next_it.level > it.level then
        needs_mark = false
      end
      it.needs_mark = needs_mark
      table.insert(header_seq, it)
    end
  end

  if #header_seq == 0 then
    if #footer_defs > 0 then
      local fdefs_latex = "\n% Metadonnees du pied de page Husson\n" .. table.concat(footer_defs, "\n") .. "\n"
      table.insert(doc.blocks, 1, pandoc.RawBlock("latex", fdefs_latex))
    end
    return doc
  end

  -- 2. Construire la hierarchie courante pour chaque header
  local cur_h1 = nil
  local cur_h2 = nil
  local cur_h3 = nil
  local cur_h4 = nil
  local cur_h5 = nil

  local state_counter = 0
  local defs = {}
  local header_mark_ids = {} -- index par sequence de headers (1 a #header_seq)

  for idx, it in ipairs(header_seq) do
    local h = it.h
    local title = get_heading_title(h)
    local raw_text = pandoc.utils.stringify(h.content)

    -- Avertissement preventif si un H2 est long sans nav-title
    if (not (h.attributes and h.attributes["nav-title"])) and h.level == 2 and #raw_text > 28 then
      io.stderr:write("[quarto-template-husson] Conseil: Le titre \"" .. raw_text .. "\" (niveau 2) gagnerait a recevoir un attribut nav-title court pour optimiser la barre de navigation.\n")
    end

    if h.level == 1 then
      cur_h1 = { title = title, id = state_counter + 1 }
      cur_h2 = nil
      cur_h3 = nil
      cur_h4 = nil
      cur_h5 = nil
    elseif h.level == 2 then
      if not cur_h1 then cur_h1 = { title = "", id = 1 } end
      cur_h2 = { title = title }
      cur_h3 = nil
      cur_h4 = nil
      cur_h5 = nil
    elseif h.level == 3 then
      if not cur_h1 then cur_h1 = { title = "", id = 1 } end
      if not cur_h2 then cur_h2 = { title = title } end
      cur_h3 = { title = title }
      cur_h4 = nil
      cur_h5 = nil
    elseif h.level == 4 then
      if not cur_h1 then cur_h1 = { title = "", id = 1 } end
      if not cur_h2 then cur_h2 = { title = title } end
      cur_h4 = { title = title }
      cur_h5 = nil
    elseif h.level == 5 then
      if not cur_h1 then cur_h1 = { title = "", id = 1 } end
      if not cur_h2 then cur_h2 = { title = title } end
      cur_h5 = { title = title }
    end

    if it.needs_mark then
      state_counter = state_counter + 1
      header_mark_ids[idx] = state_counter

      -- Construire le breadcrumb
      local bc = {}
      if cur_h2 then table.insert(bc, cur_h2.title) end
      if cur_h3 then table.insert(bc, cur_h3.title) end
      if cur_h4 then table.insert(bc, cur_h4.title) end
      if cur_h5 then table.insert(bc, cur_h5.title) end

      local bar_code = ""
      if #bc == 0 then
        -- H1 seul
        local h1_t = cur_h1 and cur_h1.title or ""
        bar_code = "\\hussonnavfit{\\hussonnavstandalone{" .. h1_t .. "}}"
      else
        -- H1 avec fil d'Ariane
        local bc_str = ""
        for k, seg in ipairs(bc) do
          if k == 1 then
            bc_str = "\\textcolor{headingblue}{" .. seg .. "}"
          elseif k == #bc then
            bc_str = bc_str .. "\\hussonsep \\textbf{\\textcolor{headingblue}{" .. seg .. "}}"
          else
            bc_str = bc_str .. "\\hussonsep \\textcolor{headingblue}{" .. seg .. "}"
          end
        end

        local full_bar = "\\noindent\\normalfont\\scriptsize \\textcolor{headingblue}{\\textbf{" .. cur_h1.title .. "}}\\hussonbarsep " .. bc_str
        bar_code = "\\hussonnavfit{" .. full_bar .. "}"
      end

      local h1_num = cur_h1 and cur_h1.id or 0
      table.insert(defs, "\\hussonnavstate{" .. tostring(state_counter) .. "}{" .. tostring(h1_num) .. "}{" .. bar_code .. "}")
    else
      header_mark_ids[idx] = nil
    end
  end

  -- 3. Injecter les marques dans le document
  local walk_idx = 0
  local new_doc = doc:walk({
    Header = function(h)
      if h.level >= 1 and h.level <= 5 then
        if not (h.classes:includes("unlisted") or (h.attributes and h.attributes["nav"] == "false")) then
          walk_idx = walk_idx + 1
          local st = header_mark_ids[walk_idx]
          if st then
            return {
              pandoc.RawBlock("latex", "\\hussonnavmark{" .. tostring(st) .. "}"),
              h
            }
          end
        end
      end
    end
  })

  -- 4. Inserer les definitions LaTeX au debut des blocs
  local all_defs = {}
  if #footer_defs > 0 then
    table.insert(all_defs, "% Metadonnees du pied de page Husson\n" .. table.concat(footer_defs, "\n"))
  end
  if #defs > 0 then
    table.insert(all_defs, "% Definitions des etats de la barre de navigation Husson\n" .. table.concat(defs, "\n"))
  end

  if #all_defs > 0 then
    local defs_latex = "\n" .. table.concat(all_defs, "\n\n") .. "\n"
    table.insert(new_doc.blocks, 1, pandoc.RawBlock("latex", defs_latex))
  end

  return new_doc
end

local function get_heading_title_plain(h)
  if not h then return "" end
  local nav_title = h.attributes and h.attributes["nav-title"]
  if nav_title and nav_title ~= "" then
    return pandoc.utils.stringify(pandoc.read(nav_title, "markdown"))
  end
  return pandoc.utils.stringify(clean_inlines(h.content))
end

local function escape_json(str)
  return str:gsub('\\', '\\\\'):gsub('"', '\\"')
end

local function process_revealjs(doc)
  if doc.meta["navigation-bar"] == false or doc.meta["navbar"] == false then
    return doc
  end

  local cur_h1 = nil
  local cur_h2 = nil
  local cur_h3 = nil
  local cur_h4 = nil
  local cur_h5 = nil

  return doc:walk({
    Header = function(h)
      if h.level < 1 or h.level > 5 then
        return h
      end

      local is_hidden = h.classes:includes("unlisted") or (h.attributes and h.attributes["nav"] == "false")
      if is_hidden then
        h.attributes["data-nav-hidden"] = "true"
        return h
      end

      local title = get_heading_title_plain(h)

      -- Prise en compte de nav-chapter pour definir ou changer de chapitre sans diapositive H1
      local nav_chapter = h.attributes and h.attributes["nav-chapter"]
      if nav_chapter and nav_chapter ~= "" then
        cur_h1 = nav_chapter
      end

      if h.level == 1 then
        cur_h1 = title
        cur_h2 = nil
        cur_h3 = nil
        cur_h4 = nil
        cur_h5 = nil
      elseif h.level == 2 then
        if not cur_h1 then cur_h1 = "" end
        cur_h2 = title
        cur_h3 = nil
        cur_h4 = nil
        cur_h5 = nil
      elseif h.level == 3 then
        if not cur_h1 then cur_h1 = "" end
        if not cur_h2 then cur_h2 = title end
        cur_h3 = title
        cur_h4 = nil
        cur_h5 = nil
      elseif h.level == 4 then
        if not cur_h1 then cur_h1 = "" end
        if not cur_h2 then cur_h2 = title end
        cur_h4 = title
        cur_h5 = nil
      elseif h.level == 5 then
        if not cur_h1 then cur_h1 = "" end
        if not cur_h2 then cur_h2 = title end
        cur_h5 = title
      end

      local bc = {}
      if cur_h2 and cur_h2 ~= "" then table.insert(bc, cur_h2) end
      if cur_h3 and cur_h3 ~= "" then table.insert(bc, cur_h3) end
      if cur_h4 and cur_h4 ~= "" then table.insert(bc, cur_h4) end
      if cur_h5 and cur_h5 ~= "" then table.insert(bc, cur_h5) end

      local json_segments = {}
      for _, s in ipairs(bc) do
        table.insert(json_segments, '"' .. escape_json(s) .. '"')
      end

      h.attributes["data-nav-h1"] = cur_h1 or ""
      h.attributes["data-nav-bc"] = "[" .. table.concat(json_segments, ",") .. "]"
      h.attributes["data-nav-active"] = title

      local raw_text = pandoc.utils.stringify(h.content)
      if (not (h.attributes and h.attributes["nav-title"])) and h.level == 2 and #raw_text > 28 then
        io.stderr:write("[quarto-template-husson] Conseil: Le titre \"" .. raw_text .. "\" (niveau 2) gagnerait a recevoir un attribut nav-title court pour optimiser la barre de navigation.\n")
      end

      return h
    end
  })
end

function Pandoc(doc)
  if is_latex_format() then
    return process_latex(doc)
  elseif is_revealjs_format() then
    return process_revealjs(doc)
  else
    return doc
  end
end
