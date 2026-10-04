-- Page-breaking rules for the six Markdown heading levels.
-- Level one starts a new page. Lower levels reserve enough room for the
-- heading and the beginning of the following content.

local function need_space(lines)
  return pandoc.RawBlock(
    "latex",
    "\\Needspace{" .. tostring(lines) .. "\\baselineskip}"
  )
end

function Header(header)
  if not FORMAT:match("latex") then
    return nil
  end

  if header.level == 1 then
    return {
      pandoc.RawBlock("latex", "\\clearpage"),
      header
    }
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
