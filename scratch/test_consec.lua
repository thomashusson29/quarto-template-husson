local md = [[
# Chapitre 1
## Section 1
Texte de section 1

# Chapitre 2
## Sous-chapitre 2
### Section 2
#### Sous-section 2
##### Paragraphe 2
Texte du paragraphe 2

## Autre section
Texte autre section
]]

local doc = pandoc.read(md, "markdown")
local header_needs_mark = {}
local last_header = nil

local function check_headers(blocks)
  for _, b in ipairs(blocks) do
    if b.t == "Header" then
      if last_header then
        if b.level > last_header.level then
          header_needs_mark[last_header] = false
        else
          header_needs_mark[last_header] = true
        end
      end
      last_header = b
      header_needs_mark[b] = true
    elseif b.t ~= "RawBlock" then
      if last_header then
        header_needs_mark[last_header] = true
        last_header = nil
      end
    end
  end
end

check_headers(doc.blocks)

for _, b in ipairs(doc.blocks) do
  if b.t == "Header" then
    print(b.level, pandoc.utils.stringify(b.content), "needs_mark: " .. tostring(header_needs_mark[b]))
  end
end
