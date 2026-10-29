#!/usr/bin/env node
// End-to-end regression: export real Quarto/RevealJS with the shared adapter,
// then inspect PPTX XML. No screenshots or image-based validation.
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,mkdirSync,symlinkSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';

const repo=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(resolve(repo,'_extensions/husson/pptx/package.json'));
const JSZip=require('jszip');
const {powerPointLanguage}=await import(resolve(repo,'_extensions/husson/pptx/language.mjs'));
assert.equal(powerPointLanguage('fr'),'fr-FR');
assert.equal(powerPointLanguage('fr-CA'),'fr-CA');
assert.equal(powerPointLanguage('en-GB'),'en-GB');
assert.equal(powerPointLanguage('de'),'de-DE');
const dir=mkdtempSync(join(tmpdir(),'husson-native-text-'));
try{
  mkdirSync(join(dir,'_extensions'));
  symlinkSync(resolve(repo,'_extensions/husson'),join(dir,'_extensions/husson'));
  writeFileSync(join(dir,'_quarto.yml'),'project:\n  type: default\n  post-render: node _extensions/husson/pptx/post-render.mjs\n');
  writeFileSync(join(dir,'native.qmd'),`---
title: Native text regression
lang: fr
format:
  husson-revealjs:
    width: 1600
    height: 900
    center: false
    transition: none
execute:
  enabled: false
---

## Native lists

\`\`\`{=html}
<div style="width:1100px;font-family:Carlito;font-size:32px;line-height:1.3">
<ul>
  <li>Premier élément avec <strong>gras</strong> et <a href="https://example.org/native">lien</a><br>Suite du même élément</li>
  <li>Deuxième élément<ul><li>Élément imbriqué</li></ul></li>
</ul>
<ol start="3"><li>Trois</li><li value="7">Sept</li></ol>
<ul style="list-style-type:square"><li>Puces carrées</li><li>Autre carré</li></ul>
</div>
\`\`\`

## Native paragraphs

\`\`\`{=html}
<div style="width:650px;font-family:Carlito;font-size:32px;line-height:1.3">
<p>Première ligne<br>Deuxième ligne avec <strong>gras</strong> et <span style="text-transform:uppercase;letter-spacing:1px">capitales</span>.</p>
<p>Paragraphe suivant, dans la même zone de texte.</p>
<p><strong style="font-size:1.55em">Complications biliaires</strong> <span style="margin-left:.35em;font-size:1.05em;white-space:nowrap">(6 vs 18 %)</span></p>
<p><strong>Albumine</strong><span style="margin-left:14px">20 %</span></p>
<p>inter<strong>national</strong> sans coupure</p>
</div>
<div style="width:650px;display:flex;flex-direction:column;justify-content:center;text-align:center;font-family:Carlito;font-size:32px">
<p><strong style="display:block;font-size:1.3em">Titre carte centré</strong></p>
<p>Sous-texte de la carte<br>Suite centrée</p>
</div>
<div style="width:650px;text-align:right;font-family:Carlito;font-size:32px">
<p>Bloc à droite</p><p>Suite à droite</p>
</div>
\`\`\`

## Native tables

\`\`\`{=html}
<table style="width:1000px;table-layout:fixed;border-collapse:collapse;font-size:24px">
<colgroup><col style="width:40%"><col style="width:20%"><col style="width:20%"><col style="width:20%"></colgroup>
<thead><tr style="height:54px"><th>Critère simple</th><th style="text-align:center">Vert</th><th style="text-align:center">Orange</th><th style="text-align:center">Rouge</th></tr></thead>
<tbody>
<tr style="height:54px"><td>Cellule simple</td><td style="text-align:center"><span style="color:#4f8a1c;font-weight:700">≥ 10</span></td><td style="text-align:center;color:#b87400">5 à 10</td><td style="text-align:center;color:#c8232a">&lt; 5</td></tr>
<tr style="height:54px"><td>Autre critère</td><td style="text-align:center">7,35–7,45</td><td style="text-align:center">7,25 à 7,35</td><td style="text-align:center">&lt; 7,25</td></tr>
</tbody></table>
<table style="width:1000px;table-layout:fixed;border-collapse:collapse;font-size:24px;margin-top:30px">
<colgroup><col style="width:40%"><col style="width:20%"><col style="width:20%"><col style="width:20%"></colgroup>
<thead><tr style="height:54px"><th rowspan="2">Critère fusionné</th><th colspan="3">Zones fusionnées</th></tr>
<tr style="height:54px"><th>Vert</th><th>Orange</th><th>Rouge</th></tr></thead>
<tbody><tr style="height:70px"><td rowspan="2"><p>Paragraphe en cellule<br>Suite dans la même cellule</p></td><td>Valeur A</td><td>Valeur B</td><td>Valeur C</td></tr>
<tr style="height:54px"><td>Valeur D</td><td>Valeur E</td><td>Valeur F</td></tr></tbody></table>
\`\`\`
`);
  const run=spawnSync(process.env.QUARTO_PATH||'quarto',['render','native.qmd','--to','husson-pptx'],
    {cwd:dir,encoding:'utf8',timeout:180000,maxBuffer:4*1024*1024});
  assert.equal(run.status,0,run.stdout+'\n'+run.stderr);
  const zip=await JSZip.loadAsync(readFileSync(join(dir,'native.pptx')));
  const slidePaths=Object.keys(zip.files).filter(n=>/^ppt\/slides\/slide\d+\.xml$/.test(n));
  assert.equal(slidePaths.length,4);
  const slides=await Promise.all(slidePaths.map(n=>zip.file(n).async('string')));
  const shapes=slides.flatMap(xml=>[...xml.matchAll(/<p:sp\b[\s\S]*?<\/p:sp>/g)].map(m=>m[0]));
  const lists=shapes.filter(xml=>/name="Husson list /.test(xml));
  assert.equal(lists.length,3,'Each HTML list must remain one native text box');
  const paragraphs=xml=>[...xml.matchAll(/<a:p>[\s\S]*?<\/a:p>/g)].map(m=>m[0]);
  const listParagraphs=lists.flatMap(paragraphs);
  assert.equal(listParagraphs.length,7,'One paragraph per list item, including nested items');
  assert.equal(listParagraphs.filter(p=>p.includes('<a:buChar ')).length,5);
  assert.equal(listParagraphs.filter(p=>p.includes('<a:buAutoNum ')).length,2);
  assert.ok(listParagraphs.some(p=>p.includes('lvl="1"')&&p.includes('Élément imbriqué')));
  assert.ok(listParagraphs.some(p=>p.includes('startAt="3"')&&p.includes('Trois')));
  assert.ok(listParagraphs.some(p=>p.includes('startAt="7"')&&p.includes('Sept')));
  assert.equal(listParagraphs.filter(p=>p.includes('char="▪"')).length,2);
  const first=listParagraphs.find(p=>p.includes('Premier élément'));
  assert.ok(first.includes('<a:br/>')&&first.includes('Suite du même élément'));
  assert.ok(first.includes('b="1"')&&first.includes('hlinkClick'));
  assert.ok(!shapes.some(xml=>/<a:t>[•◦▪]<\/a:t>/.test(xml)),'No fake bullet text boxes');
  const text=shapes.find(xml=>/name="Husson text /.test(xml)&&xml.includes('Première ligne'));
  assert.ok(text,'Consecutive paragraphs must remain one native text box');
  assert.equal(paragraphs(text).length,5);
  assert.ok(paragraphs(text)[0].includes('<a:br/>')&&paragraphs(text)[0].includes('Deuxième ligne'));
  assert.ok(text.includes('Paragraphe suivant'));
  const textOf=xml=>[...xml.matchAll(/<a:t(?:\s[^>]*)?>([\s\S]*?)<\/a:t>/g)].map(m=>m[1]).join('');
  const stats=paragraphs(text).find(p=>p.includes('Complications biliaires'));
  assert.match(textOf(stats),/Complications biliaires\s+\(6 vs 18 %\)/,'Inline whitespace and margins must separate labels and percentages');
  assert.ok(!stats.includes('<a:br/>'),'Different inline font sizes must stay on the same visual line');
  assert.match(textOf(paragraphs(text).find(p=>p.includes('Albumine'))),/Albumine\s+20 %/,'CSS inline margin must remain an editable space');
  assert.ok(textOf(paragraphs(text).find(p=>p.includes('national'))).includes('international sans coupure'),'No space may be invented inside a styled word');
  assert.ok(text.includes('xml:space="preserve"'));
  const centered=shapes.find(xml=>/name="Husson text /.test(xml)&&xml.includes('Titre carte centré'));
  assert.ok(centered&&centered.includes('Sous-texte de la carte')&&centered.includes('Suite centrée'),'Centered flex cards must remain one text box');
  assert.equal(paragraphs(centered).length,2);
  assert.ok(paragraphs(centered).every(p=>p.includes('algn="ctr"')));
  assert.ok(centered.includes('<a:br/>'));
  const right=shapes.find(xml=>/name="Husson text /.test(xml)&&xml.includes('Bloc à droite'));
  assert.ok(right&&right.includes('Suite à droite'));
  assert.ok(paragraphs(right).every(p=>p.includes('algn="r"')));
  assert.ok(text.includes('CAPITALES')&&!text.includes('capitales'));
  assert.ok(/\bspc="[1-9]\d*"/.test(text));
  const tables=slides.flatMap(xml=>[...xml.matchAll(/<a:tbl>[\s\S]*?<\/a:tbl>/g)].map(m=>m[0]));
  assert.equal(tables.length,2,'Every HTML table must remain a native DrawingML table');
  const simple=tables.find(xml=>xml.includes('Critère simple'));
  assert.ok(simple&&simple.includes('Cellule simple')&&simple.includes('≥ 10'));
  assert.equal((simple.match(/<a:tr\b/g)||[]).length,3);
  const grid=[...simple.matchAll(/<a:gridCol w="(\d+)"/g)].map(m=>Number(m[1]));
  assert.equal(grid.length,4);
  assert.ok(Math.abs(grid[0]/grid.reduce((a,b)=>a+b,0)-.4)<.01,'Measured column proportions must be preserved');
  const colors=[...simple.matchAll(/<a:srgbClr val="([^"]+)"/g)].map(m=>m[1].toUpperCase());
  assert.ok(['4F8A1C','B87400','C8232A'].every(c=>colors.includes(c)),JSON.stringify([...new Set(colors)]));
  assert.ok(simple.includes('algn="ctr"')&&simple.includes('b="1"'));
  const merged=tables.find(xml=>xml.includes('Critère fusionné'));
  assert.ok(merged&&merged.includes('gridSpan="3"')&&merged.includes('rowSpan="2"'),'Native merged cells must be preserved');
  assert.equal((merged.match(/<a:tr\b/g)||[]).length,4);
  assert.ok(merged.includes('Paragraphe en cellule')&&merged.includes('Suite dans la même cellule'));
  assert.ok(!shapes.some(xml=>xml.includes('Cellule simple')||xml.includes('Critère fusionné')),'No fake table cell text boxes');
  for(const xml of slides){
    const ids=[...xml.matchAll(/<p:cNvPr\b[^>]*\bid="(\d+)"/g)].map(m=>m[1]);
    assert.equal(new Set(ids).size,ids.length,'PowerPoint object IDs must be unique');
    for(const match of xml.matchAll(/<p:graphicFrame\b[\s\S]*?<\/p:graphicFrame>/g)){
      if(!match[0].includes('<a:tbl>'))continue;
      const height=[...match[0].matchAll(/<a:tr\b[^>]*\bh="(\d+)"/g)].reduce((s,m)=>s+Number(m[1]),0);
      const width=[...match[0].matchAll(/<a:gridCol w="(\d+)"/g)].reduce((s,m)=>s+Number(m[1]),0);
      const frame=match[0].match(/<p:xfrm>[\s\S]*?<a:ext cx="(\d+)" cy="(\d+)"/);
      assert.ok(frame);
      assert.equal(Number(frame[1]),width);assert.equal(Number(frame[2]),height);
    }
  }
  const assertLanguage=async(archive,expected)=>{
    let count=0;
    for(const [path,file] of Object.entries(archive.files)){
      if(!path.startsWith('ppt/')||!path.endsWith('.xml')||file.dir)continue;
      const xml=await file.async('string');
      for(const m of xml.matchAll(/<a:(?:rPr|endParaRPr|defRPr)\b([^>]*?)(?:\/)?>/g)){
        assert.ok(m[1].includes('lang="'+expected+'"'),path+': '+m[0]);count++;
      }
    }
    assert.ok(count>0);
    assert.ok((await archive.file('docProps/core.xml').async('string')).includes('<dc:language>'+expected+'</dc:language>'));
  };
  await assertLanguage(zip,'fr-FR');
  writeFileSync(join(dir,'english.qmd'),'---\ntitle: Language regression\nlang: en-GB\nformat:\n  husson-revealjs: default\nexecute:\n  enabled: false\n---\n\n## Proofing language\n\nEnglish text.\n');
  const english=spawnSync(process.env.QUARTO_PATH||'quarto',['render','english.qmd','--to','husson-pptx'],
    {cwd:dir,encoding:'utf8',timeout:180000,maxBuffer:4*1024*1024});
  assert.equal(english.status,0,english.stdout+'\n'+english.stderr);
  await assertLanguage(await JSZip.loadAsync(readFileSync(join(dir,'english.pptx'))),'en-GB');
  console.log('PASS: native lists/text/tables, inline spacing, mixed font sizes, merged cells, French/English document languages.');
}finally{if(process.env.HUSSON_KEEP_TEST)console.log('Test directory:',dir);else rmSync(dir,{recursive:true,force:true})}
