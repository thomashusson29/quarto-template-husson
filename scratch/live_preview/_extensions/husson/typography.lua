-- typography.lua
-- Gestion universelle de la typographie, bibliographie et mise en page pour quarto-template-husson
--
-- Fonctionnalités :
-- 1. Choix de police : Computer Modern (LaTeX default), Times New Roman, Garamond, Roboto, Carlito, ou personnalisée
-- 2. Configuration automatique du mode thèse ou rapport :
--    - Interligne 1.15 si non défini
--    - Taille de police 11pt si non définie
--    - Marges calibrées
-- 3. Définition automatique de documentclass: scrartcl si absent pour garantir la compatibilité KOMA-Script
-- 4. Résolution automatique des clés de citation et ajout de la bibliographie partagée (_extensions/husson/biblio_shared.bib)
-- 5. Support universel des blocs ::: {.landscape}

local function stringify_val(val)
  if val == nil then
    return nil
  end
  local res = pandoc.utils.stringify(val):gsub("^%s+", ""):gsub("%s+$", "")
  return res
end

local citation_map = {
  ["austinBalanceDiagnosticsComparing2009"] = "austin2009",
  ["austinOptimalCaliperWidths2011"] = "austin2011a",
  ["austinUsePropensityScore2014"] = "austin2014a",
  ["eisetConsiderationsUsingMultiple2022a"] = "eiset2022",
  ["garridoMethodsConstructingAssessing2014"] = "garrido2014",
  ["grangerAvoidingPitfallsWhen2019"] = "granger2019",
  ["imaiMisunderstandingsExperimentalistsObservationalists2008"] = "imai2008",
  ["iwagamiIntroductionMatchingCaseControl2022"] = "iwagami2022",
  ["lingHowApplyMultiple2020"] = "ling2020",
  ["nguyenMultipleImputationPropensity2024"] = "nguyen2024",
  ["pikeBiasEfficiencyLogistic1980a"] = "pike1980",
  ["pishgarMatchThemMatchingWeighting2021"] = "pishgar2021",
  ["reiterModelDiagnosticsRemote2003"] = "reiter2003",
  ["rosenbaumCentralRolePropensity"] = "rosenbaum",
  ["schomakerBootstrapInferenceWhen2018"] = "schomaker2018",
  ["segalasPropensityScoreMatching2023"] = "segalas2023",
  ["stuartPrognosticScoreBased2013"] = "stuart2013",
  ["vanBuuren2011mice"] = "vanbuuren2011",
  ["wanMatchedUnmatchedAnalysis2021"] = "wan2021",
  ["zhangBalanceDiagnosticsPropensity2019"] = "zhang2019"
}

function Cite(cite)
  for _, item in ipairs(cite.citations) do
    if citation_map[item.id] then
      item.id = citation_map[item.id]
    end
  end
  return cite
end

local ext_dir = pandoc.path.directory(PANDOC_SCRIPT_FILE):gsub("\\", "/")

local function file_exists(path)
  local f = io.open(path, "rb")
  if f then
    f:close()
    return true
  end
  return false
end

local function append_header_include(meta, latex_code)
  local block = pandoc.MetaBlocks{pandoc.RawBlock("latex", latex_code)}
  if not meta["header-includes"] then
    meta["header-includes"] = pandoc.MetaList{block}
  elseif meta["header-includes"].t == "MetaList" then
    meta["header-includes"]:insert(block)
  else
    meta["header-includes"] = pandoc.MetaList{meta["header-includes"], block}
  end
end

function Meta(meta)
  -- 0. Enrichissement automatique de la bibliographie avec biblio_shared.bib (tous formats)
  if meta.bibliography then
    local shared_path = ext_dir .. "/biblio_shared.bib"
    if file_exists(shared_path) then
      local bib_list = pandoc.List()
      local already_present = false
      if meta.bibliography.t == "MetaList" then
        for _, b in ipairs(meta.bibliography) do
          local b_str = stringify_val(b) or ""
          if b_str:match("biblio_shared%.bib$") then
            already_present = true
          end
          table.insert(bib_list, b)
        end
      else
        local b_str = stringify_val(meta.bibliography) or ""
        if b_str:match("biblio_shared%.bib$") then
          already_present = true
        end
        table.insert(bib_list, meta.bibliography)
      end
      if not already_present then
        table.insert(bib_list, pandoc.MetaInlines{pandoc.Str(shared_path)})
      end
      meta.bibliography = bib_list
    end
  end

  if not FORMAT:match("latex") then
    return meta
  end

  -- 1. Classe de document par défaut : scrartcl (KOMA-Script) si non précisée
  if not meta.documentclass then
    meta.documentclass = pandoc.MetaInlines{pandoc.Str("scrartcl")}
  end

  -- 2. Chemins de recherche LaTeX pour les logos et ressources embarqués dans l'extension
  append_header_include(
    meta,
    "\\makeatletter\\def\\input@path{{" .. ext_dir .. "/}}\\makeatother\n" ..
    "\\graphicspath{{" .. ext_dir .. "/}{images/}{./}}"
  )

  -- 3. Détection du mode thèse / page de garde
  local is_thesis = false
  if meta.thesis ~= nil and meta.thesis ~= false then
    is_thesis = true
    if type(meta.thesis) == "table" and meta.thesis.logo then
      local logo_str = stringify_val(meta.thesis.logo)
      if logo_str and logo_str ~= "" and not file_exists(logo_str) then
        local base_logo = pandoc.path.filename(logo_str)
        if file_exists(ext_dir .. "/" .. base_logo) then
          meta.thesis.logo = pandoc.MetaInlines{pandoc.Str(base_logo)}
        end
      end
    end
  end

  -- Éviter un double sommaire si frontmatter.table-of-contents est activé
  if meta.frontmatter and type(meta.frontmatter) == "table" then
    local fm_toc = meta.frontmatter["table-of-contents"]
    if fm_toc ~= nil and stringify_val(fm_toc) ~= "false" then
      meta.toc = false
    end
  end

  -- 4. Détection du choix de police (Times New Roman par défaut)
  local chosen_font = stringify_val(meta.font)
  if not chosen_font and is_thesis and type(meta.thesis) == "table" and meta.thesis.font then
    chosen_font = stringify_val(meta.thesis.font)
  end
  if not chosen_font and meta.mainfont then
    chosen_font = stringify_val(meta.mainfont)
  end

  local font_family = "times"
  if chosen_font then
    local lower = chosen_font:lower()
    if lower:match("computer") or lower:match("latin modern") or lower:match("default") or lower == "cm" then
      font_family = "default"
    elseif lower:match("carlito") or lower:match("calibri") then
      font_family = "carlito"
    elseif lower:match("garamond") then
      font_family = "garamond"
    elseif lower:match("roboto") then
      font_family = "roboto"
    elseif lower:match("times") or lower:match("termes") then
      font_family = "times"
    else
      font_family = "custom"
    end
  end

  -- 5. Application de la police
  if font_family == "times" then
    meta.mainfont = pandoc.MetaInlines{pandoc.Str("Times New Roman")}
  elseif font_family == "carlito" then
    meta.mainfont = pandoc.MetaInlines{pandoc.Str("Carlito-Regular.ttf")}
    meta.mainfontoptions = pandoc.MetaList{
      pandoc.MetaInlines{pandoc.RawInline("latex", "Path=" .. ext_dir .. "/fonts/")},
      pandoc.MetaInlines{pandoc.Str("BoldFont=Carlito-Bold.ttf")},
      pandoc.MetaInlines{pandoc.Str("ItalicFont=Carlito-Italic.ttf")},
      pandoc.MetaInlines{pandoc.Str("BoldItalicFont=Carlito-BoldItalic.ttf")}
    }
  elseif font_family == "garamond" then
    meta.mainfont = pandoc.MetaInlines{pandoc.Str("EBGaramond-Regular.otf")}
    meta.mainfontoptions = pandoc.MetaList{
      pandoc.MetaInlines{pandoc.Str("BoldFont=EBGaramond-Bold.otf")},
      pandoc.MetaInlines{pandoc.Str("ItalicFont=EBGaramond-Italic.otf")},
      pandoc.MetaInlines{pandoc.Str("BoldItalicFont=EBGaramond-BoldItalic.otf")}
    }
  elseif font_family == "roboto" then
    meta.mainfont = pandoc.MetaInlines{pandoc.Str("Roboto")}
  elseif font_family == "custom" then
    meta.mainfont = pandoc.MetaInlines{pandoc.Str(chosen_font)}
  elseif font_family == "default" then
    -- Computer Modern (LaTeX default) : on ne force aucun \setmainfont
    meta.mainfont = nil
  end

  -- 6. Paramètres spécifiques au mode thèse
  if is_thesis then
    if not meta.linestretch then
      meta.linestretch = pandoc.MetaInlines{pandoc.Str("1.15")}
    end

    local fs = stringify_val(meta.fontsize)
    if not fs or fs == "10pt" then
      meta.fontsize = pandoc.MetaInlines{pandoc.Str("11pt")}
    end

    if not meta.geometry then
      meta.geometry = pandoc.MetaInlines{pandoc.Str("top=3cm,bottom=2.5cm,left=3cm,right=2.5cm")}
    end
  end

  -- 7. Couleurs des titres (activées par défaut en PDF ; désactivées si heading-colors: false)
  local hc = meta["heading-colors"]
  if hc == false or (hc ~= nil and (stringify_val(hc) or ""):lower() == "false") then
    append_header_include(
      meta,
      "\\AtBeginDocument{%\n" ..
      "  \\definecolor{headingblue}{HTML}{000000}%\n" ..
      "  \\definecolor{headingred}{HTML}{000000}%\n" ..
      "  \\definecolor{headinggreen}{HTML}{000000}%\n" ..
      "  \\definecolor{headingcharcoal}{HTML}{000000}%\n" ..
      "}"
    )
  end

  return meta
end

-- 7. Support universel de ::: {.landscape} pour insérer une section en paysage
function Div(div)
  if FORMAT:match("latex") and div.classes:includes("landscape") then
    table.insert(div.content, 1, pandoc.RawBlock("latex", "\\begin{landscape}\n"))
    table.insert(div.content, pandoc.RawBlock("latex", "\n\\end{landscape}"))
    return div.content
  end
  return nil
end
