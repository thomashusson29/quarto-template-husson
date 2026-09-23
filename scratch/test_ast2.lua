local md = [[
# H1
## H2_1
### H3
## H2_2
# H1_2
]]
local doc = pandoc.read(md, "markdown")

-- Pass 1: collect
local headers = {}
doc:walk({
  Header = function(h)
    table.insert(headers, h)
  end
})
print("Collected: " .. #headers .. " headers.")

-- Pass 2: walk and replace with mark
local idx = 0
local new_doc = doc:walk({
  Header = function(h)
    idx = idx + 1
    return {
      pandoc.RawBlock("latex", "\\hussonnavmark{" .. tostring(idx) .. "}"),
      h
    }
  end
})
local tex = pandoc.write(new_doc, "latex")
print(tex)
