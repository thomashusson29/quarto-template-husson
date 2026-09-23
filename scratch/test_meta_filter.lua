function Meta(meta)
  if meta.thesis then
    if not meta.mainfont then
      meta.mainfont = pandoc.MetaInlines{pandoc.Str("Times New Roman")}
    end
    if not meta.linestretch then
      meta.linestretch = pandoc.MetaInlines{pandoc.Str("1.15")}
    end
    if not meta.fontsize then
      meta.fontsize = pandoc.MetaInlines{pandoc.Str("11pt")}
    end
  end
  return meta
end
