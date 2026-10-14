#!/usr/bin/env node
import { createServer } from 'node:http';
import { existsSync } from 'node:fs';
import { readFile, writeFile, realpath } from 'node:fs/promises';
import { dirname, resolve, relative, extname } from 'node:path';
import puppeteer from 'puppeteer';
import JSZip from 'jszip';

const [htmlArg, pptxArg, selection = 'all'] = process.argv.slice(2);
if (!htmlArg || !pptxArg) throw new Error('Usage: node export.mjs input.html output.pptx [all|1,2,3]');
const html = resolve(htmlArg), output = resolve(pptxArg), root = dirname(html);
let projectRoot = root;
for (let dir = root; ; dir = dirname(dir)) {
  if (existsSync(resolve(dir, '.git'))) { projectRoot = dir; break; }
  if (dirname(dir) === dir) break;
}
const mime = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.svg':'image/svg+xml', '.woff2':'font/woff2', '.woff':'font/woff', '.ttf':'font/ttf', '.json':'application/json' };
const warnings = [];
const server = createServer(async (req,res) => {
  try {
    const decoded = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (decoded === '/favicon.ico') { res.writeHead(204); res.end(); return; }
    const path = resolve(root, '.' + decoded);
    if (relative(projectRoot, path).startsWith('..')) throw new Error('outside project');
    let actual;
    try { actual = await realpath(path); }
    catch (e) {
      // Auto Dark's optional dark companion files are absent in a light-only export.
      if (!decoded.endsWith('-auto-dark.png')) throw e;
      actual = await realpath(resolve(root, '.' + decoded.replace(/-auto-dark\.png$/, '.png')));
    }
    const data = await readFile(actual);
    res.setHeader('Content-Type', mime[extname(path)] || 'application/octet-stream');
    res.end(data);
  } catch (e) { warnings.push(`404 ${req.url}: ${e.message}`); res.writeHead(404); res.end(String(e)); }
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const port = server.address().port;
const browser = await puppeteer.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH || '/Applications/Chromium.app/Contents/MacOS/Chromium', args: ['--no-sandbox'] });
try {
  const page = await browser.newPage();
  await page.setViewport({width:1600,height:900,deviceScaleFactor:1});
  page.on('console', msg => { if (['error','warning'].includes(msg.type())) warnings.push('browser: ' + msg.text()); });
  page.on('pageerror', e => warnings.push('page: ' + e.message));
  await page.goto(`http://127.0.0.1:${port}/${encodeURIComponent(html.split('/').pop())}`, {waitUntil:'networkidle2', timeout:120000});
  await page.waitForFunction(() => window.Reveal && Reveal.isReady(), {timeout:30000});
  await page.evaluate(() => Reveal.configure({hash:false,history:false}));
  await page.evaluate(async () => {
    document.documentElement.classList.remove('auto-dark-theme-dark');
    document.documentElement.classList.add('auto-dark-theme-light');
    document.documentElement.setAttribute('data-auto-dark-theme','light');
    document.body.classList.remove('quarto-dark'); document.body.classList.add('quarto-light');
    // The HTML theme toggle has no action in a fixed, light PowerPoint deck.
    // Hide it before taking any browser pixels, including the navbar capture.
    const exportStyle = document.createElement('style');
    exportStyle.textContent = '.auto-dark-switch{visibility:hidden!important}';
    document.head.appendChild(exportStyle);
    await document.fonts.ready;
  });
  const views = await page.evaluate(() => Array.from(document.querySelectorAll('.reveal .slides > section')).flatMap((s,h) => {
    const children = Array.from(s.children).filter(e=>e.tagName==='SECTION');
    return children.length ? children.map((e,v)=>({h,v,id:e.id,title:e.querySelector('h1,h2')?.textContent?.trim()||''})) : [{h,v:0,id:s.id,title:s.querySelector('h1,h2')?.textContent?.trim()||''}];
  }));
  const picks = selection === 'all' ? views.map((_,i)=>i) : selection.split(',').map(s=>Number(s)-1);
  if (picks.some(i=>!Number.isInteger(i)||i<0||i>=views.length)) throw new Error('Invalid slide selection');
  await page.evaluate(() => {
    const style = document.createElement('style');
    style.textContent = `#husson-pptx-stage{position:absolute;left:0;top:0;z-index:-1;pointer-events:none;width:1600px;height:900px} #husson-pptx-stage .husson-pptx-slide{position:absolute;left:0;top:0;width:1600px;height:900px;overflow:hidden;background:#fff} #husson-pptx-stage .reveal{position:absolute;left:0;top:0;width:1600px;height:900px;overflow:visible} #husson-pptx-stage .reveal .slides{position:absolute!important;left:0px!important;top:0px!important;width:1600px!important;height:900px!important;transform:scale(1)!important;transform-origin:0 0!important;perspective:none!important} #husson-pptx-stage .reveal .slides > section{position:relative!important;left:0!important;top:0!important;display:block!important;opacity:1!important;visibility:visible!important;transform:none!important;width:1600px!important;height:900px!important;overflow:visible!important} #husson-pptx-stage .fragment{opacity:1!important;visibility:visible!important;transform:none!important} #husson-pptx-stage .scrollable{overflow:visible!important} #husson-pptx-stage .pptx-before::before,#husson-pptx-stage .pptx-after::after{content:none!important;display:none!important}`;
    document.head.appendChild(style);
    const stage = document.createElement('div'); stage.id='husson-pptx-stage'; document.body.appendChild(stage);
  });
  for (const i of picks) {
    const view = views[i];
    await page.evaluate(({h,v})=>Reveal.slide(h,v),view);
    const ensureView=async()=>{
      await page.evaluate(({h,v})=>Reveal.slide(h,v),view);
      await page.waitForFunction(({id,index})=>{
        if(Reveal.getCurrentSlide()?.id!==id)return false;
        const number=document.querySelector('.reveal .slide-number');
        return !number||number.textContent.trim().startsWith(String(index));
      },{timeout:10000},{id:view.id,index:i+1});
      await new Promise(ok=>setTimeout(ok,120));
    };
    await ensureView();
    const demo = await page.evaluate(() => {
      const s=Reveal.getCurrentSlide();
      const frame=s.querySelector('iframe');
      if (!frame) return false;
      frame.src=frame.getAttribute('data-src') || frame.src;
      return true;
    });
    if (demo) {
      await page.waitForFunction(() => { const f=Reveal.getCurrentSlide().querySelector('iframe'); return f?.contentDocument?.readyState==='complete'; },{timeout:30000});
      await new Promise(ok=>setTimeout(ok,700));
    }
    const fixedBoxes=await page.evaluate(()=>{
      const selectors=['#husson-reveal-navbar','.slide-menu-button','.reveal .slide-number'];
      return selectors.map(selector=>{const el=document.querySelector(selector);if(!el)return null;const cs=getComputedStyle(el),r=el.getBoundingClientRect();return cs.visibility==='hidden'||cs.opacity==='0'||el.classList.contains('husson-nav-hidden')||r.width<1||r.height<1?null:{selector,x:r.x,y:r.y,w:r.width,h:r.height}}).filter(Boolean);
    });
    const fixedImages=[];
    for(const box of fixedBoxes){
      let data;
      for(let attempt=0;attempt<4;attempt++){
        await ensureView();
        data=Buffer.from(await page.screenshot({clip:{x:box.x,y:box.y,width:box.w,height:box.h},type:'png'})).toString('base64');
        const stillCurrent=await page.evaluate(id=>Reveal.getCurrentSlide()?.id===id,view.id);
        const hasNavbarInk=box.selector!=='#husson-reveal-navbar'||await page.evaluate(async encoded=>{
          const image=new Image();image.src='data:image/png;base64,'+encoded;await image.decode();
          const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
          const context=canvas.getContext('2d');context.drawImage(image,0,0);
          const width=Math.min(600,image.width),height=Math.min(36,image.height);
          const pixels=context.getImageData(15,2,width-15,height-2).data;
          let ink=0;for(let k=0;k<pixels.length;k+=4)if(Math.min(pixels[k],pixels[k+1],pixels[k+2])<180)ink++;
          return ink>40;
        },data);
        if(stillCurrent&&hasNavbarInk)break;
        if(attempt===3)throw new Error(`Could not capture fixed ${box.selector} on slide ${i+1}`);
      }
      fixedImages.push({...box,data});
    }
    const screen = demo ? (await page.evaluateHandle(() => Reveal.getCurrentSlide().querySelector('.screen'))).asElement() : null;
    const framePng = screen ? Buffer.from(await screen.screenshot({type:'png'})).toString('base64') : null;
    // Puppeteer screenshots may fire Reveal's pending hash navigation. Restore
    // the selected view before reading its DOM for conversion.
    await page.evaluate(({h,v})=>Reveal.slide(h,v),view);
    await page.waitForFunction(id=>Reveal.getCurrentSlide()?.id===id,{timeout:10000},view.id);
    await page.evaluate(({i, framePng, fixedImages}) => {
      const source=Reveal.getCurrentSlide();
      const slides=source.classList.contains('scrollable') ? Array.from(source.querySelectorAll('#refs .csl-entry')) : [];
      const chunks=slides.length ? slides.map(x=>[x.id]) : [null];
      for (const ids of chunks) {
        const root=document.createElement('div'); root.className='husson-pptx-slide'; root.dataset.sourceIndex=String(i+1); root.dataset.sourceId=source.id;
        const reveal=document.createElement('div'); reveal.className='reveal';
        const stage=document.createElement('div'); stage.className='slides';
        const slide=source.cloneNode(true); slide.classList.add('present'); slide.classList.remove('past','future');
        const factor=source.getBoundingClientRect().width/source.offsetWidth;
        root.dataset.revealScale=String(factor);
        const originalNodes=[source,...source.querySelectorAll('*')], clonedNodes=[slide,...slide.querySelectorAll('*')];
        // Preserve source line breaks. A text block that occupies one browser line
        // must not acquire a new line in PowerPoint because font metrics differ.
        originalNodes.forEach((el,k)=>{
          if(!el.textContent?.trim()||getComputedStyle(el).whiteSpace==='nowrap')return;
          const rects=[],walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
          for(let node=walker.nextNode();node;node=walker.nextNode()){
            if(!node.nodeValue.trim())continue;
            const range=document.createRange();range.selectNodeContents(node);
            for(const r of range.getClientRects())if(r.width>=1&&r.height>=1)rects.push(r);
          }
          const bands=[];
          for(const r of rects){
            let band=bands.find(b=>Math.min(b.bottom,r.bottom)-Math.max(b.top,r.top)>Math.min(b.bottom-b.top,r.height)*.4);
            if(band){band.top=Math.min(band.top,r.top);band.bottom=Math.max(band.bottom,r.bottom)}
            else bands.push({top:r.top,bottom:r.bottom});
          }
          if(bands.length!==1)return;
          const parent=el.parentElement;if(!parent)return;
          const parentStyle=getComputedStyle(parent),elementStyle=getComputedStyle(el);
          if(parentStyle.display!=='flex'||parentStyle.flexDirection!=='row'||
             !['normal','flex-start','start'].includes(parentStyle.justifyContent)||
             !['left','start'].includes(elementStyle.textAlign)||parent.lastElementChild!==el)return;
          const room=parent.getBoundingClientRect().right-el.getBoundingClientRect().right;
          if(room>20)clonedNodes[k].style.setProperty('flex-grow','1','important');
        });
        // Resolve CSS counters before replacing generated content. Resets are
        // scoped to descendants; increments remain visible to siblings.
        const counterValues=new Map(), counters=new Map();
        const counterTerms=(value,defaultAmount)=>{
          if(!value||value==='none')return [];
          const tokens=value.trim().split(/\s+/), result=[];
          for(let t=0;t<tokens.length;t++){
            const name=tokens[t];if(!/^[-_a-zA-Z][-_a-zA-Z0-9]*$/.test(name))continue;
            let amount=defaultAmount;if(/^[-+]?\d+$/.test(tokens[t+1]||''))amount=Number(tokens[++t]);
            result.push([name,amount]);
          }
          return result;
        };
        const visitCounters=node=>{
          const cs=getComputedStyle(node), restored=[];
          for(const [name,value] of counterTerms(cs.counterReset,0)){
            restored.push([name,counters.has(name),counters.get(name)]);counters.set(name,value);
          }
          for(const [name,amount] of counterTerms(cs.counterIncrement,1))counters.set(name,(counters.get(name)||0)+amount);
          counterValues.set(node,new Map(counters));
          for(const child of node.children)visitCounters(child);
          for(const [name,had,value] of restored.reverse()){
            if(had)counters.set(name,value);else counters.delete(name);
          }
        };
        visitCounters(source);
        const unresolvedPseudo=[];
        for(let k=0;k<originalNodes.length;k++)for(const kind of ['before','after']){
          const computed=getComputedStyle(originalNodes[k],`::${kind}`);
          const raw=computed.content;
          if(!raw||raw==='none'||raw==='normal'||raw==='""'||computed.display==='none')continue;
          const values=counterValues.get(originalNodes[k]);
          const token=/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|counter\([^)]*\)|attr\([^)]*\)/g;
          let resolved='', consumed=0, match;
          while((match=token.exec(raw))){
            if(raw.slice(consumed,match.index).trim())break;
            const part=match[0];
            if(part.startsWith('counter(')){
              const name=part.slice(8,-1).split(',')[0].trim();resolved+=String(values.get(name)||0);
            }else if(part.startsWith('attr(')){
              const name=part.slice(5,-1).trim();resolved+=originalNodes[k].getAttribute(name)||'';
            }else{
              resolved+=part.slice(1,-1).replace(/\\a\s?/gi,'\n').replace(/\\([0-9a-f]{1,6})\s?/gi,(_,hex)=>String.fromCodePoint(parseInt(hex,16))).replace(/\\(.)/g,'$1');
            }
            consumed=token.lastIndex;
          }
          if(raw.slice(consumed).trim()){
            unresolvedPseudo.push(`${originalNodes[k].tagName.toLowerCase()}${originalNodes[k].className?'.'+String(originalNodes[k].className).trim().replace(/\s+/g,'.'):''}::${kind}: ${raw}`);
            continue;
          }
          const marker=document.createElement('span');marker.textContent=resolved;
          marker.className='pptx-pseudo-text';
          for(const prop of ['display','position','left','top','right','bottom','transform','font-family','font-size','font-weight','font-style','line-height','color','width','height','flex','flex-basis','flex-grow','flex-shrink','margin','padding','text-align','white-space','opacity','z-index']){
            const value=computed.getPropertyValue(prop);if(value&&value!=='auto')marker.style.setProperty(prop,value,'important');
          }
          clonedNodes[k].classList.add(`pptx-${kind}`);
          if(kind==='before')clonedNodes[k].prepend(marker);else clonedNodes[k].append(marker);
        }
        if(unresolvedPseudo.length)root.dataset.unresolvedPseudo=JSON.stringify(unresolvedPseudo);
        slide.querySelectorAll('.fragment').forEach(el=>el.classList.add('visible'));
        if(ids){
          slide.querySelectorAll('#refs .csl-entry').forEach(el=>{if(!ids.includes(el.id))el.remove()});
          const refs=slide.querySelector('#refs');
          refs.style.setProperty('font-size','28px','important');
          refs.style.setProperty('line-height','1.28','important');
          refs.querySelectorAll('*').forEach(el=>el.style.setProperty('font-size','28px','important'));
          const h=slide.querySelector('h2'); if(h){h.textContent=ids[0]===slides[0].id?'Références':'Références (suite)';h.style.cssText='display:block!important;position:relative!important;visibility:visible!important;opacity:1!important';}
        }
        if(framePng){const f=slide.querySelector('iframe'); if(f){const box=source.querySelector('.screen');const img=document.createElement('img');img.src='data:image/png;base64,'+framePng;img.alt=f.title;img.style.cssText=`width:${box.offsetWidth}px!important;height:${box.offsetHeight}px!important;max-width:none!important;max-height:none!important;object-fit:fill;display:block`;f.replaceWith(img);}}
        stage.appendChild(slide);reveal.appendChild(stage);root.appendChild(reveal);
        for(const fixed of fixedImages){const img=document.createElement('img');img.src='data:image/png;base64,'+fixed.data;img.alt=fixed.selector;img.style.cssText=`position:absolute;left:${fixed.x}px;top:${fixed.y}px;width:${fixed.w}px;height:${fixed.h}px;max-width:none;max-height:none;object-fit:fill;z-index:20`;root.appendChild(img);}
        document.getElementById('husson-pptx-stage').appendChild(root);
        stage.style.setProperty('transform',`scale(${factor})`,'important');
        const target=source.getBoundingClientRect();
        for(let attempt=0;attempt<8;attempt++){
          const current=slide.getBoundingClientRect();
          if(Math.abs(target.x-current.x)<.5 && Math.abs(target.y-current.y)<.5)break;
          stage.style.setProperty('left',`${parseFloat(getComputedStyle(stage).left)+target.x-current.x}px`,'important');
          stage.style.setProperty('top',`${parseFloat(getComputedStyle(stage).top)+target.y-current.y}px`,'important');
        }
        // Keep each list item at its browser-measured position. The library's
        // combined list text box changes indentation and vertical spacing.
        slide.querySelectorAll('ul,ol').forEach(list=>{
          const listRect=list.getBoundingClientRect(), style=getComputedStyle(list);
          const rows=document.createElement('div');rows.className='pptx-measured-list';
          rows.style.cssText=`display:${style.display};position:relative;width:${list.offsetWidth}px;height:${list.offsetHeight}px;margin:${style.margin};vertical-align:${style.verticalAlign};box-sizing:border-box`;
          Array.from(list.children).filter(el=>el.tagName==='LI').forEach((li,index)=>{
            const r=li.getBoundingClientRect(), cs=getComputedStyle(li);
            let visualContainer=li.parentElement;
            while(visualContainer&&visualContainer!==slide){
              const s=getComputedStyle(visualContainer);
              if((s.backgroundColor!=='rgba(0, 0, 0, 0)'&&s.backgroundColor!=='transparent')||parseFloat(s.borderLeftWidth)>0)break;
              visualContainer=visualContainer.parentElement;
            }
            const contentRight=visualContainer&&visualContainer!==slide
              ?visualContainer.getBoundingClientRect().right-parseFloat(getComputedStyle(visualContainer).paddingRight)*factor
              :r.right;
            const lines=[];
            const walker=document.createTreeWalker(li,NodeFilter.SHOW_TEXT);
            for(let node=walker.nextNode();node;node=walker.nextNode()){
              const computed=getComputedStyle(node.parentElement);
              for(let c=0;c<node.length;c++){
                const range=document.createRange();range.setStart(node,c);range.setEnd(node,c+1);
                const rect=range.getBoundingClientRect();
                if(rect.width<.01)continue;
                let line=lines.find(x=>Math.abs(x.y-rect.y)<parseFloat(cs.fontSize)*.35);
                if(!line){line={x:rect.x,y:rect.y,right:rect.right,bottom:rect.bottom,runs:[]};lines.push(line)}
                line.x=Math.min(line.x,rect.x);line.right=Math.max(line.right,rect.right);line.bottom=Math.max(line.bottom,rect.bottom);
                const key=[computed.fontFamily,computed.fontSize,computed.fontWeight,computed.fontStyle,computed.color].join('|');
                let run=line.runs.at(-1);
                if(!run||run.key!==key){run={key,text:'',style:computed};line.runs.push(run)}
                run.text+=node.nodeValue[c];
              }
            }
            lines.sort((a,b)=>a.y-b.y);
            for(const visual of lines){
              const line=document.createElement('div');
              line.style.cssText=`position:absolute;left:${(visual.x-listRect.x)/factor}px;top:${(visual.y-listRect.y)/factor}px;width:${(Math.max(r.right,contentRight)-visual.x)/factor}px;height:${(visual.bottom-visual.y)/factor+4}px;font-family:${cs.fontFamily};font-size:${cs.fontSize};font-weight:${cs.fontWeight};line-height:${cs.lineHeight};color:${cs.color};white-space:nowrap`;
              for(const run of visual.runs){const span=document.createElement('span');span.textContent=run.text;span.style.cssText=`font-family:${run.style.fontFamily};font-size:${run.style.fontSize};font-weight:${run.style.fontWeight};font-style:${run.style.fontStyle};color:${run.style.color}`;line.appendChild(span)}
              rows.appendChild(line);
            }
            if(cs.listStyleType!=='none'){
              const mark=document.createElement('span');
              mark.textContent=list.tagName==='OL'?String(index+1)+'.':cs.listStyleType==='square'?'▪':cs.listStyleType==='circle'?'◦':'•';
              const markerStyle=getComputedStyle(li,'::marker');
              const first=lines[0];const x=((first?.x??r.x)-listRect.x)/factor,y=((first?.y??r.y)-listRect.y)/factor;
              mark.style.cssText=`position:absolute;left:${x-0.7*parseFloat(cs.fontSize)}px;top:${y}px;width:${0.5*parseFloat(cs.fontSize)}px;height:${parseFloat(cs.lineHeight)}px;font-family:${cs.fontFamily};font-size:${cs.fontSize};line-height:${cs.lineHeight};color:${markerStyle.color};text-align:center`;
              rows.appendChild(mark);
            }
          });
          list.replaceWith(rows);
        });
        // dom-to-pptx rasterizes native HTML tables. Rebuild their measured cells
        // as positioned HTML boxes so the labels and values remain editable.
        slide.querySelectorAll('table').forEach(table=>{
          const tableRect=table.getBoundingClientRect();
          const tableStyle=getComputedStyle(table);
          const grid=document.createElement('div');grid.className='husson-pptx-table';
          grid.style.cssText=`position:relative;width:${table.offsetWidth}px;height:${table.offsetHeight}px;margin:${tableStyle.margin};box-sizing:border-box`;
          table.querySelectorAll('th,td').forEach(cell=>{
            const r=cell.getBoundingClientRect(), cs=getComputedStyle(cell);
            const box=document.createElement('div');box.innerHTML=cell.innerHTML;
            box.style.cssText=`position:absolute;left:${(r.x-tableRect.x)/factor}px;top:${(r.y-tableRect.y)/factor}px;width:${r.width/factor}px;height:${r.height/factor}px;box-sizing:border-box;padding:${cs.padding};font-family:${cs.fontFamily};font-size:${cs.fontSize};font-weight:${cs.fontWeight};line-height:${cs.lineHeight};color:${cs.color};text-align:${cs.textAlign};background:${cs.backgroundColor};border-bottom:${cs.borderBottomWidth} ${cs.borderBottomStyle} ${cs.borderBottomColor};white-space:nowrap`;
            grid.appendChild(box);
          });
          table.replaceWith(grid);
        });
      }
    },{i,framePng,fixedImages});
    // Pseudo-elements are visual decorations. Capture their browser pixels at
    // their measured positions so PowerPoint font baselines cannot move them.
    const pseudoRects=await page.evaluate(i=>Array.from(document.querySelectorAll(`#husson-pptx-stage > .husson-pptx-slide[data-source-index=\"${i+1}\"] .pptx-pseudo-text`)).map(el=>{const r=el.getBoundingClientRect();return [r.x,r.y,r.width,r.height]}),i);
    if(pseudoRects.some(([x,y,w,h])=>w>0&&h>0&&x>=0&&y>=0&&x+w<=1600&&y+h<=900)){
      await page.evaluate(()=>{
        document.getElementById('husson-pptx-stage').style.display='none';
        Reveal.getCurrentSlide().querySelectorAll('.fragment').forEach(el=>el.classList.add('visible'));
      });
      const sourcePng=Buffer.from(await page.screenshot({type:'png'})).toString('base64');
      await page.evaluate(()=>{document.getElementById('husson-pptx-stage').style.display='';});
      await page.evaluate(async({i,sourcePng})=>{
        const screenshot=new Image();screenshot.src='data:image/png;base64,'+sourcePng;await screenshot.decode();
        const sx=screenshot.naturalWidth/window.innerWidth,sy=screenshot.naturalHeight/window.innerHeight;
        const markers=Array.from(document.querySelectorAll(`#husson-pptx-stage > .husson-pptx-slide[data-source-index=\"${i+1}\"] .pptx-pseudo-text`));
        for(const marker of markers){
          const r=marker.getBoundingClientRect();if(r.width<1||r.height<1||r.x<0||r.y<0||r.right>window.innerWidth||r.bottom>window.innerHeight)continue;
          const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.ceil(r.width*sx));canvas.height=Math.max(1,Math.ceil(r.height*sy));
          const context=canvas.getContext('2d');
          context.drawImage(screenshot,r.x*sx,r.y*sy,r.width*sx,r.height*sy,0,0,canvas.width,canvas.height);
          const picture=document.createElement('img');picture.src=canvas.toDataURL('image/png');picture.alt=marker.textContent;
          picture.style.cssText=marker.style.cssText;
          const factor=Number(marker.closest('.husson-pptx-slide').dataset.revealScale);
          picture.style.setProperty('width',`${r.width/factor}px`,'important');picture.style.setProperty('height',`${r.height/factor}px`,'important');
          marker.replaceWith(picture);
        }
      },{i,sourcePng});
    }
    process.stdout.write(`Prepared ${i+1}/${views.length}: ${view.title}${demo?' [demo still]':''}\n`);
  }
  const prep=await page.evaluate(async()=>{
    const roots=Array.from(document.querySelectorAll('#husson-pptx-stage > .husson-pptx-slide'));
    await Promise.all(Array.from(document.querySelectorAll('#husson-pptx-stage img')).map(img=>img.decode().catch(()=>{})));
    const broken=[];
    for(const root of roots)for(const img of root.querySelectorAll('img')){if(!img.complete||img.naturalWidth===0)broken.push(img.src)}
    return {count:roots.length,broken,scales:roots.map(root=>Number(root.dataset.revealScale)),
      unresolved:roots.flatMap((root,i)=>(JSON.parse(root.dataset.unresolvedPseudo||'[]')).map(value=>`slide ${i+1}: ${value}`))};
  });
  if(prep.broken.length) throw new Error('Images missing: '+prep.broken.map(x=>x.slice(0,120)).join(', '));
  if(prep.unresolved.length) throw new Error('Unsupported CSS generated content: '+prep.unresolved.slice(0,10).join('; '));
  const bundlePath=resolve(dirname(new URL(import.meta.url).pathname),'node_modules/dom-to-pptx/dist/dom-to-pptx.bundle.js');
  const bundle=await readFile(bundlePath,'utf8');
  const from="const isBlockDisplay = display === 'block' || display === 'flex' || display === 'grid' || display === 'table';";
  if(!bundle.includes(from))throw new Error('Unsupported dom-to-pptx bundle version');
  await page.addScriptTag({content:bundle.replace(from,"const isBlockDisplay = display === 'block' || display === 'flex' || display === 'grid' || display === 'table' || display === 'inline-block';")});
  const encoded=await page.evaluate(async()=>{
    const roots=Array.from(document.querySelectorAll('#husson-pptx-stage > .husson-pptx-slide'));
    const blob=await window.domToPptx.exportToPptx(roots,{width:13.333333,height:7.5,skipDownload:true,autoEmbedFonts:false,svgAsVector:false});
    const bytes=new Uint8Array(await blob.arrayBuffer()); let binary=''; for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768)); return btoa(binary);
  });
  const archive=await JSZip.loadAsync(Buffer.from(encoded,'base64'));
  for(let slide=1;slide<=prep.count;slide++){
    const path=`ppt/slides/slide${slide}.xml`,part=archive.file(path);
    if(!part)throw new Error(`Missing PowerPoint slide: ${path}`);
    let xml=await part.async('string');const scale=prep.scales[slide-1];
    if(!Number.isFinite(scale)||scale<=0)throw new Error(`Invalid RevealJS scale for slide ${slide}`);
    // dom-to-pptx adds a nearly full-slide browser snapshot after the editable
    // shapes. It captures the live Reveal deck behind our staging layer, so it
    // can show a stale slide in other PPTX readers and needlessly bloats files.
    // Remove only this known canvas-sized artifact, never ordinary images.
    const overlayIds=[];
    xml=xml.replace(/<p:pic\b[\s\S]*?<\/p:pic>/g,picture=>{
      if(!/<a:off x="60960" y="45720"\s*\/>/.test(picture)||
         !/<a:ext cx="12131040" cy="6751320"\s*\/>/.test(picture))return picture;
      const id=picture.match(/<a:blip\b[^>]*\br:embed="(rId\d+)"/);
      if(!id)throw new Error(`Unidentified full-slide raster on slide ${slide}`);
      overlayIds.push(id[1]);return '';
    });
    if(overlayIds.length>1)throw new Error(`Multiple full-slide rasters on slide ${slide}`);
    if(overlayIds.length){
      const relPath=`ppt/slides/_rels/slide${slide}.xml.rels`,relPart=archive.file(relPath);
      if(!relPart)throw new Error(`Missing slide relationships: ${relPath}`);
      let rels=await relPart.async('string');
      for(const id of overlayIds){
        const relation=new RegExp(`<Relationship\\b(?=[^>]*\\bId="${id}")[^>]*/>`);
        const found=rels.match(relation);
        const target=found?.[0].match(/\bTarget="\.\.\/media\/([^"]+)"/);
        if(!target)throw new Error(`Missing full-slide raster relationship ${id}`);
        rels=rels.replace(relation,'');
        archive.remove(`ppt/media/${target[1]}`);
      }
      archive.file(relPath,rels);
    }
    xml=xml.replace(/(<a:(?:rPr|endParaRPr|defRPr)\b[^>]*\bsz=")(\d+)(")/g,(_,a,size,b)=>a+Math.max(100,Math.round(Number(size)*scale))+b);
    xml=xml.replace(/(<a:spcPts\s+val=")(\d+)(")/g,(_,a,size,b)=>a+Math.max(100,Math.round(Number(size)*scale))+b);
    archive.file(path,xml);
  }
  // The converter's image resampling can prepend a black pixel row to small
  // browser captures. Detect that exact edge pattern in generated PNGs and
  // copy the neighboring background row; ordinary pictures are untouched.
  const smallPngs=[];
  for(const [name,file] of Object.entries(archive.files)){
    if(!/^ppt\/media\/.*\.png$/.test(name))continue;
    const bytes=await file.async('nodebuffer');
    if(bytes.length<24||bytes.readUInt32BE(16)>300||bytes.readUInt32BE(20)>300)continue;
    smallPngs.push({name,data:bytes.toString('base64')});
  }
  const repaired=await page.evaluate(async images=>{
    const output=[];
    for(const {name,data} of images){
      const image=new Image();image.src='data:image/png;base64,'+data;await image.decode();
      if(image.height<2)continue;
      const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
      const context=canvas.getContext('2d');context.drawImage(image,0,0);
      const top=context.getImageData(0,0,image.width,1).data;
      const next=context.getImageData(0,1,image.width,1).data;
      let dark=0,light=0;
      for(let x=0;x<image.width;x++){
        const k=x*4;
        if(top[k+3]<16||(top[k]<16&&top[k+1]<16&&top[k+2]<16&&top[k+3]>200))dark++;
        if(next[k]>220&&next[k+1]>220&&next[k+2]>220)light++;
      }
      if(dark/image.width<.98||light/image.width<.9)continue;
      context.putImageData(context.getImageData(0,1,image.width,1),0,0);
      output.push({name,data:canvas.toDataURL('image/png').split(',')[1]});
    }
    return output;
  },smallPngs);
  for(const {name,data} of repaired)archive.file(name,Buffer.from(data,'base64'));
  await writeFile(output,await archive.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));
  process.stdout.write(`Wrote ${output} (${prep.count} slides)\n`);
  if(warnings.length) process.stderr.write(warnings.slice(0,30).join('\n')+'\n');
} finally { await browser.close(); server.close(); }
