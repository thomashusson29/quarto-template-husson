local md2 = [[
# Chapitre 2
Texte introductif avant la section.
## Section 2
Texte
]]
local doc = pandoc.read(md2, "markdown")
for i, b in ipairs(doc.blocks) do
  print(i, b.t, b.level or "")
end
