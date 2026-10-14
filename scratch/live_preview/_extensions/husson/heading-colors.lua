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

local function resolve_colors(option)
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

  if option == true then
    return light, dark
  end

  if type(option) ~= "table" then
    io.stderr:write(
      "[quarto-template-husson] heading-colors doit etre true, false "
      .. "ou une table h1/h2/h3; option ignoree.\n"
    )
    return nil, nil
  end

  light.h1 = safe_css_color(option.h1, light.h1, "h1")
  light.h2 = safe_css_color(option.h2, light.h2, "h2")
  light.h3 = safe_css_color(option.h3, light.h3, "h3")

  local dark_map = option.dark
  if type(dark_map) == "table" then
    dark.h1 = safe_css_color(dark_map.h1, dark.h1, "dark.h1")
    dark.h2 = safe_css_color(dark_map.h2, dark.h2, "dark.h2")
    dark.h3 = safe_css_color(dark_map.h3, dark.h3, "dark.h3")
  end

  return light, dark
end

local function append_style(existing, extra)
  if existing == nil or existing == "" then
    return extra
  end
  if existing:sub(-1) ~= ";" then
    existing = existing .. ";"
  end
  return existing .. " " .. extra
end

function Pandoc(doc)
  local option = doc.meta["heading-colors"]

  if option == nil or option == false then
    return doc
  end

  local light, dark = resolve_colors(option)
  if light == nil then
    return doc
  end

  return doc:walk({
    Header = function(h)
      if h.level < 1 or h.level > 3 then
        return h
      end

      local key = "h" .. tostring(h.level)
      h.classes:insert("husson-heading-colored")

      local vars = string.format(
        "--husson-heading-light:%s; --husson-heading-dark:%s;",
        light[key],
        dark[key]
      )

      h.attributes["style"] = append_style(h.attributes["style"], vars)
      return h
    end
  })
end
