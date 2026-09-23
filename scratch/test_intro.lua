local md1 = [[
# Chapitre 1
## Section 1
Texte
]]

local md2 = [[
# Chapitre 2
Texte introductif avant la section.
## Section 2
Texte
]]

local function check_intro(doc)
  local in_h1 = false
  local has_intro = false
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level == 1 then
      in_h1 = true
      has_intro = false
    elseif in_h1 and b.t == "Header" and b.level == 2 then
      print("H1 followed by H2. Has intro text? " .. tostring(has_intro))
      in_h1 = false
    elseif in_h1 and b.t ~= "Header" then
      has_intro = true
    end
  end
end

print("Test 1:")
check_intro(pandoc.read(md1, "markdown"))
print("Test 2:")
check_intro(pandoc.read(md2, "markdown"))
