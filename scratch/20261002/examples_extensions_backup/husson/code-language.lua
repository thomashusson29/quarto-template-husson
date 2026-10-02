-- Ajoute un repere visuel aux blocs de code dans la sortie PDF.
-- La classe de langage existe encore dans l'AST Pandoc, mais elle est sinon
-- perdue visuellement lorsque Pandoc produit le LaTeX.

local function has_class(classes, expected)
  for _, class_name in ipairs(classes) do
    if class_name == expected then
      return true
    end
  end
  return false
end

function CodeBlock(block)
  if not FORMAT:match("latex") then
    return nil
  end

  local environment
  if has_class(block.classes, "python") then
    environment = "pythoncode"
  elseif has_class(block.classes, "r") then
    environment = "rcode"
  else
    return nil
  end

  return {
    pandoc.RawBlock("latex", "\\begin{" .. environment .. "}"),
    block,
    pandoc.RawBlock("latex", "\\end{" .. environment .. "}"),
  }
end
