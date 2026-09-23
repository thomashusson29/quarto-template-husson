local doc = pandoc.read("# H1\n\n## H2", "markdown")
local count = 0
local new_doc = doc:walk({
  Header = function(h)
    count = count + 1
    return {
      pandoc.RawBlock("latex", "\\mark{" .. count .. "}"),
      h
    }
  end
})
local tex = pandoc.write(new_doc, "latex")
print("Tex output:\n" .. tex)
