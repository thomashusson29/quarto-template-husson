function Div(div)
  if FORMAT:match("latex") and div.classes:includes("landscape") then
    table.insert(div.content, 1, pandoc.RawBlock("latex", "\\begin{landscape}\n"))
    table.insert(div.content, pandoc.RawBlock("latex", "\n\\end{landscape}"))
    return div.content
  end
  return nil
end
