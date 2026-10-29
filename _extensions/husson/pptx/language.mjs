// Office expects a regional BCP 47 proofing tag; Quarto commonly emits just
// "fr" or "en" on <html>. Preserve an explicit region (fr-CA, en-GB, ...).
export function powerPointLanguage(value='en') {
  try {
    const locale=new Intl.Locale(value.trim().replaceAll('_','-'));
    return new Intl.Locale(locale,{region:locale.region||locale.maximize().region}).baseName;
  } catch {
    throw new Error(`Invalid presentation language: ${JSON.stringify(value)}`);
  }
}

export async function setPresentationLanguage(archive,value) {
  const language=powerPointLanguage(value);
  for(const [path,file] of Object.entries(archive.files)) {
    if(!path.startsWith('ppt/')||!path.endsWith('.xml')||file.dir)continue;
    const source=await file.async('string');
    const xml=source.replace(/<a:(rPr|endParaRPr|defRPr)\b([^>]*?)(\/?)>/g,(_,tag,attrs,close)=> {
      attrs=attrs.replace(/\s+(?:lang|altLang)=["'][^"']*["']/g,'');
      return `<a:${tag}${attrs} lang="${language}"${close}>`;
    }).replace(/<a:t(\s[^>]*)?>([\s\S]*?)<\/a:t>/g,(match,attrs='',text)=>
      /^\s|\s$/.test(text)&&!attrs.includes('xml:space=')?`<a:t${attrs} xml:space="preserve">${text}</a:t>`:match);
    if(xml!==source)archive.file(path,xml);
  }
  const core=archive.file('docProps/core.xml');
  if(core) {
    let xml=await core.async('string');
    xml=/<dc:language\b/.test(xml)
      ?xml.replace(/<dc:language\b[^>]*>[\s\S]*?<\/dc:language>/,`<dc:language>${language}</dc:language>`)
      :xml.replace('</cp:coreProperties>',`<dc:language>${language}</dc:language></cp:coreProperties>`);
    archive.file('docProps/core.xml',xml);
  }
}
