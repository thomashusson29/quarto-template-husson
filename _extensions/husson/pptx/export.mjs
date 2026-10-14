#!/usr/bin/env node
import { createServer } from 'node:http';
import { existsSync } from 'node:fs';
import { readFile, writeFile, realpath } from 'node:fs/promises';
import { dirname, resolve, relative, extname, sep } from 'node:path';
import puppeteer from 'puppeteer';
import JSZip from 'jszip';

const [htmlArg, pptxArg, selection = 'all'] = process.argv.slice(2);
if (!htmlArg || !pptxArg) throw new Error('Usage: node export.mjs input.html output.pptx [all|1,2,3]');
const html = resolve(htmlArg), output = resolve(pptxArg), root = dirname(html);
const cwdRelative = relative(process.cwd(), html);
let projectRoot = cwdRelative !== '..' && !cwdRelative.startsWith('..' + sep) ? process.cwd() : root;
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
    const path = resolve(projectRoot, '.' + decoded);
    if (relative(projectRoot, path).startsWith('..')) throw new Error('outside project');
    let actual;
    try { actual = await realpath(path); }
    catch (e) {
      // Auto Dark's optional dark companion files are absent in a light-only export.
      if (!/-auto-dark\.(png|jpe?g|svg)$/.test(decoded)) throw e;
      actual = await realpath(resolve(projectRoot, '.' + decoded.replace(/-auto-dark(\.(?:png|jpe?g|svg))$/, '$1')));
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
  const htmlUrl=relative(projectRoot,html).split(sep).map(encodeURIComponent).join('/');
  await page.goto(`http://127.0.0.1:${port}/${htmlUrl}`, {waitUntil:'networkidle2', timeout:120000});
  await page.waitForFunction(() => window.Reveal && Reveal.isReady(), {timeout:30000});
  await page.evaluate(() => Reveal.configure({hash:false,history:false}));
  await page.evaluate(async () => {
    document.documentElement.classList.remove('auto-dark-theme-dark');
    document.documentElement.classList.add('auto-dark-theme-light');
    document.documentElement.setAttribute('data-auto-dark-theme','light');
    document.body.classList.remove('quarto-dark'); document.body.classList.add('quarto-light');
    // The HTML theme toggle has no action in a fixed, light PowerPoint deck.
    // Hide it before taking browser pixels for fixed non-text elements.
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
      await page.waitForFunction(({id,h,v})=>{
        const current=Reveal.getIndices();
        return Reveal.getCurrentSlide()?.id===id&&current.h===h&&current.v===v;
      },{timeout:10000},view);
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
    const screen = demo ? (await page.evaluateHandle(() => Reveal.getCurrentSlide().querySelector('.screen'))).asElement() : null;
    const framePng = screen ? Buffer.from(await screen.screenshot({type:'png'})).toString('base64') : null;
    // Puppeteer screenshots may fire Reveal's pending hash navigation. Restore
    // the selected view before reading its DOM for conversion.
    await page.evaluate(({h,v})=>Reveal.slide(h,v),view);
    await page.waitForFunction(id=>Reveal.getCurrentSlide()?.id===id,{timeout:10000},view.id);
    await page.evaluate(({i, framePng}) => {
      const source=Reveal.getCurrentSlide();
      // The Husson Reveal navbar lives outside the slide. Copy its actual DOM
      // into each PowerPoint page as ordinary text and a background shape.
      const navbar=document.getElementById('husson-reveal-navbar');
      const navbarStyle=navbar&&getComputedStyle(navbar);
      const navbarRect=navbar?.getBoundingClientRect();
      const hasNavbar=navbar&&navbarRect.width>1&&navbarRect.height>1&&navbarStyle.display!=='none'&&navbarStyle.visibility!=='hidden'&&Number(navbarStyle.opacity)>0&&!navbar.classList.contains('husson-nav-hidden');
      // Quarto tabsets expose their panels in DOM order. Export each state as a
      // separate, ordinary slide. Multiple tabsets form a Cartesian product.
      const tabsets=Array.from(source.querySelectorAll('.panel-tabset'));
      const variants=tabsets.reduce((states,set)=>{
        const count=set.querySelectorAll(':scope > .tab-content > [role="tabpanel"]').length;
        if(!count)throw new Error('Tabset without panels');
        return states.flatMap(state=>Array.from({length:count},(_,index)=>[...state,index]));
      },[[]]);
      if(variants.length>100)throw new Error(`Too many tab combinations: ${variants.length}`);
      for (const variant of variants) {
        const root=document.createElement('div'); root.className='husson-pptx-slide'; root.dataset.sourceIndex=String(i+1); root.dataset.sourceId=source.id;
        const reveal=document.createElement('div'); reveal.className='reveal';
        const stage=document.createElement('div'); stage.className='slides';
        const slide=source.cloneNode(true); slide.classList.add('present'); slide.classList.remove('past','future');
        const factor=source.getBoundingClientRect().width/source.offsetWidth;
        root.dataset.revealScale=String(factor);
        const originalNodes=[source,...source.querySelectorAll('*')], clonedNodes=[slide,...slide.querySelectorAll('*')];
        // Run this after selecting the tab and attaching the clone: inactive
        // source panels have no measurable text rectangles.
        const protectOneLineFlexItems=()=>slide.querySelectorAll('*').forEach(el=>{
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
          if(room>20)el.style.setProperty('flex-grow','1','important');
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
        Array.from(slide.querySelectorAll('.panel-tabset')).forEach((set,setIndex)=>{
          const panels=Array.from(set.querySelectorAll(':scope > .tab-content > [role="tabpanel"]'));
          const chosen=variant[setIndex];
          panels.forEach((panel,panelIndex)=>{
            if(panelIndex!==chosen){panel.remove();return;}
            panel.hidden=false;
            panel.removeAttribute('hidden');
            panel.style.setProperty('display','block','important');
          });
          set.querySelectorAll(':scope > [role="tablist"] [role="tab"]').forEach((tab,tabIndex)=>{
            tab.setAttribute('aria-selected',String(tabIndex===chosen));
            tab.setAttribute('tabindex',tabIndex===chosen?'0':'-1');
          });
        });
        if(framePng){const f=slide.querySelector('iframe'); if(f){const box=source.querySelector('.screen');const img=document.createElement('img');img.src='data:image/png;base64,'+framePng;img.alt=f.title;img.style.cssText=`width:${box.offsetWidth}px!important;height:${box.offsetHeight}px!important;max-width:none!important;max-height:none!important;object-fit:fill;display:block`;f.replaceWith(img);}}
        stage.appendChild(slide);reveal.appendChild(stage);root.appendChild(reveal);
        document.getElementById('husson-pptx-stage').appendChild(root);
        if(hasNavbar){
          const editableNavbar=navbar.cloneNode(true);
          editableNavbar.removeAttribute('id');
          editableNavbar.classList.add('husson-pptx-navbar');
          editableNavbar.style.setProperty('position','absolute','important');
          editableNavbar.style.setProperty('left',`${navbarRect.x}px`,'important');
          editableNavbar.style.setProperty('top',`${navbarRect.y}px`,'important');
          editableNavbar.style.setProperty('right','auto','important');
          editableNavbar.style.setProperty('width',`${navbarRect.width}px`,'important');
          editableNavbar.style.setProperty('height',`${navbarRect.height}px`,'important');
          editableNavbar.style.setProperty('backdrop-filter','none','important');
          editableNavbar.style.setProperty('-webkit-backdrop-filter','none','important');
          editableNavbar.style.setProperty('border-bottom','none','important');
          editableNavbar.style.setProperty('transition','none','important');
          root.appendChild(editableNavbar);
          const borderWidth=parseFloat(navbarStyle.borderBottomWidth)||0;
          if(borderWidth){
            const divider=document.createElement('div');
            divider.style.cssText=`position:absolute;left:${navbarRect.x}px;top:${navbarRect.bottom-borderWidth}px;width:${navbarRect.width}px;height:${borderWidth}px;background:${navbarStyle.borderBottomColor};z-index:21`;
            root.appendChild(divider);
          }
        }
        stage.style.setProperty('transform',`scale(${factor})`,'important');
        const target=source.getBoundingClientRect();
        for(let attempt=0;attempt<8;attempt++){
          const current=slide.getBoundingClientRect();
          if(Math.abs(target.x-current.x)<.5 && Math.abs(target.y-current.y)<.5)break;
          stage.style.setProperty('left',`${parseFloat(getComputedStyle(stage).left)+target.x-current.x}px`,'important');
          stage.style.setProperty('top',`${parseFloat(getComputedStyle(stage).top)+target.y-current.y}px`,'important');
        }
        // Preserve browser one-line text in editable PowerPoint shapes, also
        // for tab panels that were hidden in the original RevealJS view.
        protectOneLineFlexItems();
        const pageSlides=[slide];
        if(slide.classList.contains('scrollable')){
          const heading=Array.from(slide.children).find(el=>/^H[12]$/.test(el.tagName));
          const headingBottom=heading?.getBoundingClientRect().bottom??slide.getBoundingClientRect().top;
          const available=875-Math.max(headingBottom+16,slide.getBoundingClientRect().top+60);
          if(available<100)throw new Error(`No room for scrollable slide ${source.id}`);
          let nextUnit=0;
          const visible=el=>{
            const cs=getComputedStyle(el),r=el.getBoundingClientRect();
            return cs.display!=='none'&&cs.visibility!=='hidden'&&r.height>1;
          };
          const measure=el=>{
            const r=el.getBoundingClientRect(),cs=getComputedStyle(el);
            return r.height+Math.max(0,parseFloat(cs.marginTop)||0)*factor+Math.max(0,parseFloat(cs.marginBottom)||0)*factor;
          };
          const units=[];
          const collect=el=>{
            const height=measure(el);
            if(height>available){
              const children=el.tagName==='TABLE'
                ?Array.from(el.querySelectorAll('tbody > tr'))
                :Array.from(el.children).filter(visible);
              const sequential=children.length>1&&children.every((child,index)=>
                index===0||child.getBoundingClientRect().top>=children[index-1].getBoundingClientRect().bottom-3);
              if(sequential&&!el.matches('.columns,.callout,.panel-tabset')){
                el.dataset.pptxUnitContainer='1';
                children.forEach(collect);
                return;
              }
              throw new Error(`Scrollable block exceeds a PowerPoint page on ${source.id}: ${el.tagName}.${el.className}`);
            }
            const id=String(nextUnit++);
            el.dataset.pptxUnit=id;
            units.push({id,height});
          };
          Array.from(slide.children).filter(el=>el!==heading&&visible(el)).forEach(collect);
          const groups=[];let group=[],used=0;
          for(const unit of units){
            if(group.length&&used+unit.height>available){groups.push(group);group=[];used=0;}
            group.push(unit.id);used+=unit.height;
          }
          if(group.length)groups.push(group);
          if(groups.length>1){
            const template=root.cloneNode(true);
            const parent=root.parentElement;
            for(let index=1;index<groups.length;index++){
              const copy=template.cloneNode(true);
              parent.appendChild(copy);
              pageSlides.push(copy.querySelector('.slides > section'));
            }
            pageSlides.forEach((part,index)=>{
              const allowed=new Set(groups[index]);
              part.querySelectorAll('[data-pptx-unit]').forEach(el=>{if(!allowed.has(el.dataset.pptxUnit))el.remove();});
              part.querySelectorAll('[data-pptx-unit-container]').forEach(el=>{
                if(!el.querySelector('[data-pptx-unit]'))el.remove();
              });
            });
          }
          for(const part of pageSlides){
            const remaining=Array.from(part.querySelectorAll('[data-pptx-unit]'));
            if(remaining.some(el=>el.getBoundingClientRect().bottom>890))
              throw new Error(`Pagination still overflows on ${source.id}`);
          }
        }
        for(const slide of pageSlides){
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
      }
    },{i,framePng});
    // CSS generated text is already materialized above as a DOM span. Keeping
    // it as text avoids compositing unrelated Reveal views into tiny bitmaps.
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
  // Keep every CSS-generated character editable. Use one of the portable
  // preferred faces and confirm that Chromium actually draws every glyph
  // with it; the declared CSS face can silently fall back for arrows.
  const pseudoFonts = await page.createCDPSession();
  await pseudoFonts.send('DOM.enable');
  await pseudoFonts.send('CSS.enable');
  const {root: documentNode} = await pseudoFonts.send('DOM.getDocument');
  const {nodeIds: pseudoNodes} = await pseudoFonts.send('DOM.querySelectorAll', {
    nodeId: documentNode.nodeId, selector: '#husson-pptx-stage .pptx-pseudo-text'
  });
  const fontCandidates = ['Carlito', 'Open Sans', 'Arial'];
  const normalizeFont = value => value.toLowerCase().replace(/[\s"']/g, '');
  for (let index = 0; index < pseudoNodes.length; index++) {
    const nodeId = pseudoNodes[index];
    const {text: generatedText, declared} = await page.evaluate(i => {
      const el = document.querySelectorAll('#husson-pptx-stage .pptx-pseudo-text')[i];
      return {text: el.textContent, declared: getComputedStyle(el).fontFamily.split(',')[0].trim().replace(/^['"]|['"]$/g, '')};
    }, index);
    if (!generatedText.trim()) continue;
    let selected = null;
    const attempted = [];
    for (const candidate of fontCandidates) {
      await page.evaluate(({i, family}) => {
        document.querySelectorAll('#husson-pptx-stage .pptx-pseudo-text')[i]
          .style.setProperty('font-family', `"${family}"`, 'important');
      }, {i:index, family:candidate});
      const computedFamily = await page.evaluate(async i => {
        const el = document.querySelectorAll('#husson-pptx-stage .pptx-pseudo-text')[i];
        const style = getComputedStyle(el);
        await document.fonts.load(`${style.fontWeight} ${style.fontSize} ${style.fontFamily}`, el.textContent);
        await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
        await new Promise(resolve=>setTimeout(resolve,50));
        return getComputedStyle(el).fontFamily;
      }, index);
      const fonts = (await pseudoFonts.send('CSS.getPlatformFontsForNode', {nodeId})).fonts;
      attempted.push(`${candidate} [${computedFamily}]: ${fonts.map(font=>font.familyName).join('+')||'none'}`);
      if (fonts.length === 1 && normalizeFont(fonts[0].familyName) === normalizeFont(candidate)) {
        selected = candidate; break;
      }
    }
    if (!selected) throw new Error(`No editable font covers generated text ${JSON.stringify(generatedText)} (tried ${attempted.join(', ')})`);
    process.stdout.write(`Generated text ${JSON.stringify(generatedText)}: ${declared} → ${selected}\n`);
  }
  await pseudoFonts.detach();
  const bundlePath=resolve(dirname(new URL(import.meta.url).pathname),'node_modules/dom-to-pptx/dist/dom-to-pptx.bundle.js');
  const bundle=await readFile(bundlePath,'utf8');
  const from="const isBlockDisplay = display === 'block' || display === 'flex' || display === 'grid' || display === 'table';";
  if(!bundle.includes(from))throw new Error('Unsupported dom-to-pptx bundle version');
  await page.addScriptTag({content:bundle.replace(from,"const isBlockDisplay = display === 'block' || display === 'flex' || display === 'grid' || display === 'table' || display === 'inline-block';")});
  const encoded=await page.evaluate(async()=>{
    const roots=Array.from(document.querySelectorAll('#husson-pptx-stage > .husson-pptx-slide'));
    const blob=await window.domToPptx.exportToPptx(roots,{width:13.333333,height:7.5,skipDownload:true,autoEmbedFonts:true,svgAsVector:false});
    const bytes=new Uint8Array(await blob.arrayBuffer()); let binary=''; for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768)); return btoa(binary);
  });
  const archive=await JSZip.loadAsync(Buffer.from(encoded,'base64'));
  const presentation=await archive.file('ppt/presentation.xml')?.async('string');
  const embeddedCarlito=[...(presentation||'').matchAll(/<p:embeddedFont\b[^>]*>[\s\S]*?<\/p:embeddedFont>/g)]
    .map(match=>match[0]).find(xml=>/<p:font\b[^>]*\btypeface="Carlito"/.test(xml));
  const variants=['regular','bold','italic','boldItalic'];
  if(!embeddedCarlito||variants.some(variant=>!new RegExp(`<p:${variant}\\b`).test(embeddedCarlito))) {
    throw new Error('Carlito was not embedded in the PPTX with all four variants');
  }
  if(Object.keys(archive.files).filter(path=>/^ppt\/fonts\/[^/]+\.fntdata$/.test(path)).length<4) {
    throw new Error('PPTX is missing embedded Carlito font data');
  }
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
    // A paragraph can contain an inline run larger than its own CSS line
    // height. PowerPoint otherwise lifts that run above the browser baseline.
    // Apply the same minimum leading to every such paragraph, regardless of
    // slide content; ordinary paragraphs retain their measured spacing.
    xml=xml.replace(/<a:p>[\s\S]*?<\/a:p>/g,paragraph=>{
      const spacing=paragraph.match(/<a:spcPts\s+val="(\d+)"\s*\/>/);
      if(!spacing)return paragraph;
      const sizes=Array.from(paragraph.matchAll(/<a:rPr\b[^>]*\bsz="(\d+)"/g),match=>Number(match[1]));
      if(!sizes.length)return paragraph;
      const largest=Math.max(...sizes),current=Number(spacing[1]);
      if(current>=largest)return paragraph;
      return paragraph.replace(spacing[0],spacing[0].replace(spacing[1],String(Math.round(largest*1.15))));
    });
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
