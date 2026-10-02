-- Pages liminaires rédigées directement en Markdown.
-- Les blocs concernés sont déplacés avant la table des matières et le corps
-- recommence ensuite à la page 1 en chiffres arabes.

local labels = {
  ["frontmatter-summary"] = "Résumé",
  ["frontmatter-acknowledgements"] = "Remerciements",
  ["frontmatter-scientific-valorization"] = "Valorisation scientifique",
  ["frontmatter-abbreviations"] = "Liste des abréviations"
}

local function has_class(div, class_name)
  for _, class in ipairs(div.classes) do
    if class == class_name then
      return true
    end
  end
  return false
end

local function meta_bool(value)
  return value ~= nil and pandoc.utils.stringify(value) ~= "false"
end

local function latex_blocks(blocks)
  return pandoc.write(pandoc.Pandoc(blocks), "latex")
end

local function latex_blocks_without_toc(blocks)
  local body = latex_blocks(blocks)
  -- Les titres internes des pages liminaires structurent la page, mais ne
  -- doivent pas devenir des entrées supplémentaires de la table des matières.
  body = body:gsub("\\subparagraph{", "\\subparagraph*{")
  body = body:gsub("\\paragraph{", "\\paragraph*{")
  body = body:gsub("\\subsubsection{", "\\subsubsection*{")
  body = body:gsub("\\subsection{", "\\subsection*{")
  body = body:gsub("\\section{", "\\section*{")
  return body
end

local function abbreviation_list(blocks)
  local output = {
    "\\begin{description}[style=multiline,leftmargin=3.8cm,labelwidth=3.0cm,labelsep=0.5cm]"
  }

  for _, block in ipairs(blocks) do
    if block.t == "DefinitionList" then
      for _, item in ipairs(block.content) do
        local term = pandoc.write(
          pandoc.Pandoc({pandoc.Plain(item[1])}),
          "latex"
        ):gsub("%s+$", "")
        local definition = item[2][1] or {}
        local text = latex_blocks_without_toc(definition)
        table.insert(output, string.format(
          "\\item[{\\normalfont\\rmfamily\\bfseries %s}] %s",
          term,
          text
        ))
      end
    else
      table.insert(output, latex_blocks_without_toc({block}))
    end
  end

  table.insert(output, "\\end{description}")
  return table.concat(output, "\n")
end

local function heading(label)
  return string.format(
    "\\clearpage\n\\section*{%s}\n\\addcontentsline{toc}{section}{%s}\n",
    label,
    label
  )
end

function Pandoc(doc)
  if not FORMAT:match("latex") then
    return doc
  end

  local frontmatter = doc.meta.frontmatter
  if not frontmatter or not frontmatter.markdown then
    return doc
  end

  local collected = {}
  local remaining = {}

  for _, block in ipairs(doc.blocks) do
    if block.t == "Div" then
      local matched_class = nil
      for class_name, _ in pairs(labels) do
        if has_class(block, class_name) then
          matched_class = class_name
          break
        end
      end
      if matched_class then
        table.insert(collected, {
          class = matched_class,
          content = block.content
        })
      else
        table.insert(remaining, block)
      end
    else
      table.insert(remaining, block)
    end
  end

  if #collected == 0 then
    return doc
  end

  local output = {}
  table.insert(output, pandoc.RawBlock("latex", "\\pagenumbering{Roman}\n\\setcounter{page}{1}\n"))

  for _, item in ipairs(collected) do
    local label = labels[item.class]
    local body = latex_blocks_without_toc(item.content)

    if item.class == "frontmatter-summary" then
      body = table.concat({
        "\\clearpage",
        "\\section*{Résumé}",
        "\\addcontentsline{toc}{section}{Résumé}",
        "\\vspace{0.25\\baselineskip}",
        "\\begin{center}",
        "\\setlength{\\fboxsep}{14pt}",
        "\\setlength{\\fboxrule}{0.6pt}",
        "\\fcolorbox{headingblue}{white}{%",
        "  \\begin{minipage}{0.90\\textwidth}",
        "  \\setlength{\\parindent}{0pt}",
        "  \\setlength{\\parskip}{7pt}",
        "  \\normalsize",
        body,
        "  \\vspace{0.16\\textheight}",
        "  \\end{minipage}%",
        "}",
        "\\end{center}",
        ""
      }, "\n")
    elseif item.class == "frontmatter-abbreviations" then
      body = heading(label) .. abbreviation_list(item.content)
    else
      body = heading(label) .. body
    end

    table.insert(output, pandoc.RawBlock("latex", body))
  end

  if meta_bool(frontmatter["table-of-contents"]) then
    table.insert(output, pandoc.RawBlock("latex", table.concat({
      "\\clearpage",
      "\\begingroup",
      "\\hypersetup{linkcolor=black}",
      "\\color{black}",
      "\\setkomafont{section}{\\rmfamily\\color{black}\\normalsize}",
      "\\setkomafont{subsection}{\\rmfamily\\color{black}\\normalsize}",
      "\\setkomafont{subsubsection}{\\rmfamily\\color{black}\\normalsize}",
      "\\tableofcontents",
      "\\endgroup",
      ""
    }, "\n")))
  end

  if meta_bool(frontmatter["list-of-figures"]) then
    table.insert(output, pandoc.RawBlock("latex", table.concat({
      "\\clearpage",
      "\\renewcommand{\\listfigurename}{Liste des figures}",
      "\\addcontentsline{toc}{section}{Liste des figures}",
      "\\begingroup",
      "\\hypersetup{linkcolor=black}",
      "\\color{black}",
      "\\setkomafont{section}{\\rmfamily\\color{black}\\normalsize}",
      "\\setkomafont{subsection}{\\rmfamily\\color{black}\\normalsize}",
      "\\setkomafont{subsubsection}{\\rmfamily\\color{black}\\normalsize}",
      "\\listoffigures",
      "\\endgroup",
      ""
    }, "\n")))
  end

  if meta_bool(frontmatter["list-of-tables"]) then
    table.insert(output, pandoc.RawBlock("latex", table.concat({
      "\\clearpage",
      "\\renewcommand{\\listtablename}{Liste des tableaux}",
      "\\addcontentsline{toc}{section}{Liste des tableaux}",
      "\\begingroup",
      "\\hypersetup{linkcolor=black}",
      "\\color{black}",
      "\\setkomafont{section}{\\rmfamily\\color{black}\\normalsize}",
      "\\setkomafont{subsection}{\\rmfamily\\color{black}\\normalsize}",
      "\\setkomafont{subsubsection}{\\rmfamily\\color{black}\\normalsize}",
      "\\listoftables",
      "\\endgroup",
      ""
    }, "\n")))
  end

  table.insert(output, pandoc.RawBlock("latex", "\\clearpage\n\\pagenumbering{arabic}\n\\setcounter{page}{1}\n"))

  for _, block in ipairs(remaining) do
    table.insert(output, block)
  end

  doc.blocks = pandoc.List(output)
  return doc
end
