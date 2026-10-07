local DEFAULT_LIGHT = {
  h1 = "#107895",
  h2 = "#107895",
  h3 = "#107895"
}

local DEFAULT_DARK = {
  h1 = "#61afef",
  h2 = "#61afef",
  h3 = "#61afef"
}

local function as_string(value)
  if value == nil then
    return nil
  end
  local text = pandoc.utils.stringify(value)
  if text == "" then
    return nil
  end
  return text
end

local function safe_css_color(value, fallback, label)
  local color = as_string(value) or fallback
  if color:find("[{};<>]") then
    io.stderr:write(
      "[quarto-template-husson] heading-colors: valeur CSS invalide pour "
      .. label .. "; valeur par defaut utilisee.\n"
    )
    return fallback
  end
  return color
end

local function append_header_include(meta, html)
  local include = pandoc.MetaBlocks({
    pandoc.RawBlock("html", html)
  })
  local current = meta["header-includes"]

  if current == nil then
    meta["header-includes"] = pandoc.MetaList({include})
  elseif pandoc.utils.type(current) == "List" then
    table.insert(current, include)
    meta["header-includes"] = current
  else
    meta["header-includes"] = pandoc.MetaList({current, include})
  end
end

function Meta(meta)
  local option = meta["heading-colors"]

  if option == nil or option == false then
    return meta
  end

  local light = {
    h1 = DEFAULT_LIGHT.h1,
    h2 = DEFAULT_LIGHT.h2,
    h3 = DEFAULT_LIGHT.h3
  }

  local dark = {
    h1 = DEFAULT_DARK.h1,
    h2 = DEFAULT_DARK.h2,
    h3 = DEFAULT_DARK.h3
  }

  if type(option) == "table" then
    light.h1 = safe_css_color(option.h1, light.h1, "h1")
    light.h2 = safe_css_color(option.h2, light.h2, "h2")
    light.h3 = safe_css_color(option.h3, light.h3, "h3")

    local dark_map = option.dark
    if type(dark_map) == "table" then
      dark.h1 = safe_css_color(dark_map.h1, dark.h1, "dark.h1")
      dark.h2 = safe_css_color(dark_map.h2, dark.h2, "dark.h2")
      dark.h3 = safe_css_color(dark_map.h3, dark.h3, "dark.h3")
    end
  elseif option ~= true then
    io.stderr:write(
      "[quarto-template-husson] heading-colors doit etre true, false "
      .. "ou une table h1/h2/h3; option ignoree.\n"
    )
    return meta
  end

  local css = string.format([[
<style id="husson-heading-colors">
.reveal .slides h1 { color: %s !important; }
.reveal .slides h2 { color: %s !important; }
.reveal .slides h3 { color: %s !important; }

html.auto-dark-theme-dark body .reveal .slides h1,
body.auto-dark-theme-dark .reveal .slides h1,
body.quarto-dark .reveal .slides h1 { color: %s !important; }

html.auto-dark-theme-dark body .reveal .slides h2,
body.auto-dark-theme-dark .reveal .slides h2,
body.quarto-dark .reveal .slides h2 { color: %s !important; }

html.auto-dark-theme-dark body .reveal .slides h3,
body.auto-dark-theme-dark .reveal .slides h3,
body.quarto-dark .reveal .slides h3 { color: %s !important; }
</style>
]], light.h1, light.h2, light.h3, dark.h1, dark.h2, dark.h3)

  append_header_include(meta, css)
  return meta
end
