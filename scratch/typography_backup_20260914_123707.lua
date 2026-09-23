-- typography.lua
-- Gestion universelle de la typographie pour quarto-template-husson
--
-- Fonctionnalités :
-- 1. Choix de police parmi : Times New Roman (défaut), Garamond (EB Garamond), Roboto, ou police personnalisée
-- 2. Configuration automatique du mode thèse (thesis: true ou thesis: {...}) :
--    - Police Times New Roman (sauf indication explicite)
--    - Interligne 1.15 (linestretch: 1.15)
--    - Taille de police 11pt (fontsize: 11pt)
--    - Marges de thèse calibrées (top=3cm, bottom=2.5cm, left=3cm, right=2.5cm)
-- 3. Élimination du repli vers Computer Modern pour tous les documents Husson PDF.

local function stringify_val(val)
  if val == nil then
    return nil
  end
  return pandoc.utils.stringify(val):gsub("^%s+", ""):gsub("%s+$", "")
end

function Meta(meta)
  if not FORMAT:match("latex") then
    return meta
  end

  -- 1. Détection du mode thèse
  local is_thesis = false
  if meta.thesis ~= nil and meta.thesis ~= false then
    is_thesis = true
  end

  -- 2. Détection du choix de police
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
    if lower:match("carlito") or lower:match("calibri") then
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
    font_family = "times"
  end

  -- 3. Application de la police
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
  end

  -- 4. Paramètres spécifiques au mode thèse
  if is_thesis then
    -- Interligne 1,15
    if not meta.linestretch then
      meta.linestretch = pandoc.MetaInlines{pandoc.Str("1.15")}
    end

    -- Taille de police 11pt
    local fs = stringify_val(meta.fontsize)
    if not fs or fs == "10pt" then
      meta.fontsize = pandoc.MetaInlines{pandoc.Str("11pt")}
    end

    -- Géométrie de page de thèse calibrée
    if not meta.geometry then
      meta.geometry = pandoc.MetaInlines{pandoc.Str("top=3cm,bottom=2.5cm,left=3cm,right=2.5cm")}
    end
  end

  return meta
end

-- 5. Support universel de ::: {.landscape} pour insérer une section en paysage
function Div(div)
  if FORMAT:match("latex") and div.classes:includes("landscape") then
    table.insert(div.content, 1, pandoc.RawBlock("latex", "\\begin{landscape}\n"))
    table.insert(div.content, pandoc.RawBlock("latex", "\n\\end{landscape}"))
    return div.content
  end
  return nil
end

