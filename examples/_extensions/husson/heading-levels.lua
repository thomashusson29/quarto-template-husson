-- Page-breaking rules for the six Markdown heading levels.
-- Level one starts a new page systematically in thesis mode or when
-- pagebreak-h1 / chapter-pagebreak is enabled; otherwise it reserves
-- vertical space (\Needspace) so standard reports and articles flow naturally.
-- Lower levels reserve enough room for the heading and the beginning of the
-- following content.

local pagebreak_h1 = false

local function parse_bool(val)
  if val == nil then return nil end
  if type(val) == "boolean" then return val end
  local s = pandoc.utils.stringify(val):lower():gsub("^%s+", ""):gsub("%s+$", "")
  if s == "true" or s == "yes" or s == "1" then return true end
  if s == "false" or s == "no" or s == "0" then return false end
  return nil
end

local function need_space(lines)
  return pandoc.RawBlock(
    "latex",
    "\\Needspace{" .. tostring(lines) .. "\\baselineskip}"
  )
end

local function Meta(meta)
  local is_thesis = (meta.thesis ~= nil and meta.thesis ~= false)
  local explicit_pb = parse_bool(meta["pagebreak-h1"])
  if explicit_pb == nil then
    explicit_pb = parse_bool(meta["chapter-pagebreak"])
  end
  if explicit_pb ~= nil then
    pagebreak_h1 = explicit_pb
  else
    pagebreak_h1 = is_thesis
  end
end

local function Header(header)
  if not FORMAT:match("latex") then
    return nil
  end

  if header.level == 1 then
    local force_pb = pagebreak_h1
    if header.classes:includes("pagebreak") or (header.attributes and header.attributes["pagebreak"] == "true") then
      force_pb = true
    elseif header.classes:includes("no-pagebreak") or (header.attributes and header.attributes["pagebreak"] == "false") then
      force_pb = false
    end

    if force_pb then
      return {
        pandoc.RawBlock("latex", "\\clearpage"),
        header
      }
    else
      return {need_space(8), header}
    end
  end

  if header.level == 2 then
    return {need_space(8), header}
  end

  if header.level == 3 then
    return {need_space(5), header}
  end

  if header.level == 4 or header.level == 5 then
    return {need_space(3), header}
  end

  if header.level == 6 then
    return {
      pandoc.RawBlock("latex", "\\begin{hussonsixthheading}"),
      pandoc.Plain(header.content),
      pandoc.RawBlock("latex", "\\end{hussonsixthheading}")
    }
  end
end

return {
  { Meta = Meta },
  { Header = Header }
}
