function Meta(meta)
  meta.mainfont = pandoc.MetaInlines{pandoc.Str("EBGaramond-Regular.otf")}
  meta.mainfontoptions = pandoc.MetaList{
    pandoc.MetaInlines{pandoc.Str("BoldFont=EBGaramond-Bold.otf")},
    pandoc.MetaInlines{pandoc.Str("ItalicFont=EBGaramond-Italic.otf")},
    pandoc.MetaInlines{pandoc.Str("BoldItalicFont=EBGaramond-BoldItalic.otf")}
  }
  return meta
end
