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
  return pandoc.utils.stringify(val):gsub("^%s+", ""):gsub("%s+$", "")
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

function Meta(meta)
  if not FORMAT:match("latex") then
    return meta
  end

  -- 1. Classe de document par défaut : scrartcl (KOMA-Script) si non précisée
  if not meta.documentclass then
    meta.documentclass = pandoc.MetaInlines{pandoc.Str("scrartcl")}
  end

  -- 2. Détection du mode thèse / page de garde
  local is_thesis = false
  if meta.thesis ~= nil and meta.thesis ~= false then
    is_thesis = true
  end

  -- 3. Détection du choix de police
  local chosen_font = stringify_val(meta.font)
  if not chosen_font and is_thesis and type(meta.thesis) == "table" and meta.thesis.font then
    chosen_font = stringify_val(meta.thesis.font)
  end
  if not chosen_font and meta.mainfont then
    chosen_font = stringify_val(meta.mainfont)
  end

  local font_family = "default"
  if chosen_font then
    local lower = chosen_font:lower()
    if lower:match("computer") or lower:match("latin modern") or lower:match("default") then
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
  elseif is_thesis then
    font_family = "times"
  else
    font_family = "default"
  end

  -- 4. Application de la police
  if font_family == "times" then
    meta.mainfont = pandoc.MetaInlines{pandoc.Str("Times New Roman")}
  elseif font_family == "carlito" then
    meta.mainfont = pandoc.MetaInlines{pandoc.Str("Carlito-Regular.ttf")}
    meta.mainfontoptions = pandoc.MetaList{
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

  -- 5. Paramètres spécifiques au mode thèse
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

  -- 6. Enrichissement automatique de la bibliographie avec biblio_shared.bib si présente
  if meta.bibliography then
    local shared_path = "_extensions/husson/biblio_shared.bib"
    local bib_list = pandoc.List()
    if meta.bibliography.t == "MetaList" then
      for _, b in ipairs(meta.bibliography) do
        table.insert(bib_list, b)
      end
    else
      table.insert(bib_list, meta.bibliography)
    end
    table.insert(bib_list, pandoc.MetaInlines{pandoc.Str(shared_path)})
    meta.bibliography = bib_list
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
