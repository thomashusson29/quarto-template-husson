local md = [[
# Introduction
Texte intro

# Chapitre 1
## Section 1
Texte section 1

# Chapitre 2
## Sous-chapitre 2
### Section 2
#### Sous-section 2
##### Paragraphe 2
Texte paragraphe 2

## Autre section
Texte autre section

# Conclusion
Texte conclusion
]]

local doc = pandoc.read(md, "markdown")

local items = {}
doc:walk({
  Header = function(h)
    table.insert(items, { type = "header", h = h, level = h.level })
  end,
  Para = function(p)
    table.insert(items, { type = "content" })
  end
})

for i, it in ipairs(items) do
  if it.type == "header" then
    local next_it = items[i+1]
    local needs_mark = true
    if next_it and next_it.type == "header" and next_it.level > it.level then
      needs_mark = false
    end
    print(it.level, pandoc.utils.stringify(it.h.content), "needs_mark: " .. tostring(needs_mark))
  end
end
