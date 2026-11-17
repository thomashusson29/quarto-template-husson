#!/usr/bin/env node
// Fidelity regression: a coloured deck with cards, tabs, superscript, links
// and a character missing from the main font, exported with the shared
// adapter. Each assertion names one cause of a PPTX that did not look like
// its RevealJS source; the XML is inspected, no screenshots.
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
const dir=mkdtempSync(join(tmpdir(),'husson-fidelity-'));
try{
  mkdirSync(join(dir,'_extensions'));
  symlinkSync(resolve(repo,'_extensions/husson'),join(dir,'_extensions/husson'));
  writeFileSync(join(dir,'_quarto.yml'),'project:\n  type: default\n  post-render: node _extensions/husson/pptx/post-render.mjs\n');
  writeFileSync(join(dir,'fidelity.qmd'),`---
title: Fidelity regression
lang: fr
format:
  husson-revealjs:
    width: 1600
    height: 900
    margin: 0.06
    center: false
    transition: none
execute:
  enabled: false
---

## Fidélité {#fidelite}

\`\`\`{=html}
<style>
html,body,.reveal-viewport,.reveal .slides section,.reveal .slide-background{background:#FFF8F1!important}
.tabs{display:flex;gap:4px;padding:4px;border:2px solid #1F2430;border-radius:12px;width:max-content}
.tabs a{padding:3px 18px;border-radius:8px;font-size:17px;color:#1F2430;text-decoration:none}
.tabs a.on{background:#FFEAC2}
.card{background:#fff;border:2px solid #1F2430;border-radius:14px;box-shadow:0 5px 0 #1F2430;padding:10px 18px;width:300px}
.card p{margin:0}.card p:first-child{font-size:51px;line-height:1.1;color:#5E81AC}
.bar{display:flex;justify-content:space-between;width:900px;font-size:16px}
.bar span{color:#5E81AC}
.wrap p{margin:0}.big{display:block;font-size:78px;line-height:1.1}.l1{display:block;margin:0 0 18px}
.pause{height:4px}.trait{width:150px;height:9px;background:#F59E0B}
</style>
<nav class="tabs"><a class="on" href="#/fidelite">Onglet actif</a><a href="#/fidelite">Autre onglet</a></nav>
<p class="sous">Depuis le 1<sup>er</sup> novembre</p>
<div class="card"><p>64</p><p>interventions</p></div>
<a class="bar" href="https://example.org/planning">example.org <span>ouvrir ↗ ⇗</span></a>
<div class="wrap"><p><span class="big">GRAND</span></p><div class="pause"></div><p><span class="l1">Ligne avec marge</span></p><div class="trait"></div></div>
\`\`\`
`);
  const run=spawnSync(process.env.QUARTO_PATH||'quarto',['render','fidelity.qmd','--to','husson-pptx'],
    {cwd:dir,encoding:'utf8',timeout:240000,maxBuffer:4*1024*1024});
  assert.equal(run.status,0,run.stdout+'\n'+run.stderr);
  const zip=await JSZip.loadAsync(readFileSync(join(dir,'fidelity.pptx')));
  const slides=await Promise.all(Object.keys(zip.files).filter(n=>/^ppt\/slides\/slide\d+\.xml$/.test(n)).sort()
    .map(n=>zip.file(n).async('string')));
  const xml=slides.at(-1);
  const shapes=[...xml.matchAll(/<p:sp\b[\s\S]*?<\/p:sp>/g)].map(m=>m[0]);
  const withText=text=>shapes.find(shape=>shape.replace(/<[^>]+>/g,'').includes(text));
  const runs=shape=>[...shape.matchAll(/<a:r>[\s\S]*?<\/a:r>/g)].map(m=>m[0]);

  // 1. The page colour fills the whole slide, not a white frame around it.
  assert.ok(shapes.some(s=>/<a:off x="0" y="0"\/><a:ext cx="12192000" cy="6858000"\/>/.test(s)&&s.includes('FFF8F1')),
    'The slide background takes the colour Chrome paints behind the slide');
  assert.ok(!shapes.some(s=>/<a:off x="0" y="0"\/><a:ext cx="12192000" cy="6858000"\/>/.test(s)&&s.includes('FFFFFF')),
    'No white full-slide frame');

  // 2. A hard CSS shadow (0 5px 0) stays hard.
  const card=shapes.find(s=>s.includes('<a:outerShdw'));
  assert.ok(card&&/blurRad="0"/.test(card),'Zero shadow blur must not become the 8 pt default');

  // 3. Borders are drawn inside the box, at the RevealJS scale.
  const outline=Number(card.match(/<a:ln w="(\d+)"/)[1]);
  assert.ok(outline<15240,'A 2 px border is scaled with the slide (RevealJS factor < 1)');

  // 4. Superscript stays on its line, at the size Chrome drew (PowerPoint
  //    draws superscript at 2/3 of sz).
  const subtitle=withText('novembre');
  const sup=runs(subtitle).find(r=>/<a:t>er<\/a:t>/.test(r));
  const base=runs(subtitle).find(r=>/<a:t>[^<]*Depuis/.test(r));
  assert.ok(sup&&/baseline="30000"/.test(sup),'Superscript is PowerPoint superscript text');
  assert.ok(Number(sup.match(/sz="(\d+)"/)[1])>Number(base.match(/sz="(\d+)"/)[1]),'Superscript sz compensates PowerPoint reduction');
  assert.equal((subtitle.match(/<a:p>/g)||[]).length,1,'Superscript does not start a new line');

  // 5. Tabs: native text, no line wrapping, no hyperlink to a page anchor,
  //    active tab keeps its background.
  const tab=withText('Onglet actif');
  assert.ok(/name="Husson text/.test(tab),'Text items of a flex box are native text');
  assert.ok(/wrap="none"/.test(tab),'Chrome line breaks are explicit; PowerPoint adds none');
  assert.ok(!tab.includes('hlinkClick'),'A link to #/slide has no target in PowerPoint');
  assert.ok(shapes.some(s=>s.includes('FFEAC2')&&/prst="roundRect"/.test(s)),'The active tab keeps its own box');

  // 6. A text box that is entirely one link without CSS underline carries
  //    the link on the box: clickable, not underlined.
  const link=withText('example.org');
  assert.ok(/<p:cNvPr\b[^>]*><a:hlinkClick\b/.test(link),'Whole-text link moved to the shape');
  assert.ok(!runs(link).some(r=>r.includes('hlinkClick')),'No underlined run link');

  // 7. A character missing from the main font keeps the font Chrome used,
  //    in text presentation.
  //    (Carlito has ↗ but not ⇗; ↗ also has an emoji form.)
  const opener=runs(withText('ouvrir'));
  const face=run=>run.match(/<a:latin typeface="([^"]+)"/)[1];
  const main=opener.find(r=>r.includes('ouvrir')),missing=opener.find(r=>r.includes('⇗'));
  assert.ok(opener.some(r=>r.includes('↗︎')),'Text presentation selector after ↗');
  assert.notEqual(face(missing),face(main),'⇗ keeps the fallback font Chrome drew it with');

  // 8. Kerning on, as in Chrome.
  assert.ok(runs(withText('interventions')).every(r=>/kern="0"/.test(r)),'Native runs are kerned');

  // 9. A margin that collapses through a paragraph (the 18 px bottom margin
  //    of its inner block) is kept by the placeholder: the bar after the
  //    paragraph stays 18 px below the text instead of touching it.
  const frame=shape=>shape.match(/<a:off x="(-?\d+)" y="(-?\d+)"\/><a:ext cx="(\d+)" cy="(\d+)"\/>/).slice(1).map(Number);
  const [,textY,,textH]=frame(withText('Ligne avec marge'));
  const [,barY]=frame(shapes.find(s=>s.includes('F59E0B')));
  const px=12192000/1600;
  assert.ok(barY-(textY+textH)>10*px,`Collapsed margin kept (gap ${((barY-textY-textH)/px).toFixed(1)} px)`);
  console.log('PASS: page background, hard shadow, scaled inner borders, superscript, tabs, whole-text links, fallback glyphs, kerning, collapsed margins.');
}finally{if(process.env.HUSSON_KEEP_TEST)console.log('Test directory:',dir);else rmSync(dir,{recursive:true,force:true})}
