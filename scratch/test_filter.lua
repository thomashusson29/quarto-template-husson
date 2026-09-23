local text = "Biologie & Santé avec $\\alpha$ et IL-6"
local doc = pandoc.read(text, "markdown")
local tex = pandoc.write(doc, "latex"):gsub("%s*$", ""):gsub("^%s*", "")
print("Rendered: " .. tex)
