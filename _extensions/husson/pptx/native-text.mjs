// Browser measurement and native PowerPoint paragraphs. No list marker is
// rendered as a separate text box, and a visual line never becomes a shape.
export function captureNativeText(slide) {
  const blocks=[];
  const metrics=document.createElement('canvas').getContext('2d');
  const spaces=new Map();
  const fontMetrics=new Map();
  const rectObject=r=>({x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height});
  const plain=el=>!el.querySelector('img,svg,canvas,iframe,video,table,ul,ol,pre,code,.pptx-pseudo-text') &&
    ![el,...el.querySelectorAll('*')].some(n=>/flex|grid/.test(getComputedStyle(n).display));
  const measure=(el,owner=null,skip=null)=>{
    const cs=getComputedStyle(el), lines=[];
    // A line is as tall as its tallest inline box: a larger inner element
    // (e.g. a title span set to 2.6em) brings its own line-height.
    // Line heights are CSS pixels; line positions are measured on screen,
    // after the RevealJS scale. Express both in screen pixels.
    const screenScale=el.offsetWidth?el.getBoundingClientRect().width/el.offsetWidth:1;
    const heightOf=style=>(parseFloat(style.lineHeight)||parseFloat(style.fontSize)*1.2)*screenScale;
    let lineHeight=heightOf(cs),kerning=true;
    const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
    for(let node=walker.nextNode();node;node=walker.nextNode()){
      if(owner&&node.parentElement.closest('li')!==owner)continue;
      if(skip&&skip.contains(node))continue;
      const style=getComputedStyle(node.parentElement);
      if(style.display==='none'||style.visibility==='hidden')continue;
      lineHeight=Math.max(lineHeight,heightOf(style));
      if(style.fontKerning==='none')kerning=false;
      // A link to an anchor of the HTML page (#/slide, #section) has no
      // target in PowerPoint: keep the text, drop the hyperlink.
      const link=node.parentElement.closest('a[href]:not([href^="#"])');
      // Superscript/subscript (ordinal 1er, footnote marks) stay on the line
      // of their paragraph, as PowerPoint superscript or subscript text.
      let shifted=null;
      for(let n=node.parentElement;n&&n!==el.parentElement&&!shifted;n=n.parentElement){
        const v=getComputedStyle(n).verticalAlign;if(v==='super'||v==='sub')shifted=v;
      }
      // Characters Chrome drew with a fallback font (data-husson-fallback,
      // char -> font, set by the exporter) keep that font in PowerPoint.
      const fallback=JSON.parse(node.parentElement.closest('[data-husson-fallback]')?.dataset.hussonFallback||'{}');
      const baseOptions={fontFace:style.fontFamily.split(',')[0].trim().replace(/^['"]|['"]$/g,''),
        ...(shifted==='super'?{superscript:true}:shifted==='sub'?{subscript:true}:{}),
        fontSize:parseFloat(style.fontSize),charSpacing:parseFloat(style.letterSpacing)||0,bold:Number(style.fontWeight)>=600,
        italic:style.fontStyle==='italic',
        // Explicit either way: PptxGenJS underlines every hyperlink otherwise.
        underline:{style:style.textDecorationLine.includes('underline')?'sng':'none'},
        color:style.color,...(link?{hyperlink:{url:link.getAttribute('href')}}:{})};
      for(let c=0;c<node.length;c++){
        const options=fallback[node.nodeValue[c]]?{...baseOptions,fontFace:fallback[node.nodeValue[c]]}:baseOptions;
        const key=JSON.stringify(options);
        const range=document.createRange();range.setStart(node,c);range.setEnd(node,c+1);
        const r=range.getBoundingClientRect();if(r.width<.01||r.height<.01)continue;
        // A raised or lowered character belongs to the line it overlaps most.
        const overlap=x=>Math.min(x.bottom,r.bottom)-Math.max(x.y,r.y);
        let line=shifted?lines.filter(x=>overlap(x)>0).sort((a,b)=>overlap(b)-overlap(a))[0]:lines.find(x=>{
          const height=Math.min(x.bottom-x.y,r.height);
          return overlap(x)>height*.4&&Math.abs(x.bottom-r.bottom)<height*.35;
        });
        if(!line){line={...rectObject(r),runs:[]};lines.push(line)}
        // Inline margins and spaces collapsed by layout are geometry, not
        // characters returned by a Range. Preserve them in the same text box
        // as a real space with a measured character advance.
        const previous=line.runs.at(-1);
        const gap=previous?r.x-line.right:0;
        if(previous&&gap>.5){
          const font=`${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
          if(!spaces.has(font)){metrics.font=font;spaces.set(font,metrics.measureText(' ').width)}
          line.runs.push({key:`gap:${line.runs.length}`,text:' ',options:{...options,gapWidth:gap,spaceWidth:spaces.get(font)}});
        }
        line.x=Math.min(line.x,r.x);line.right=Math.max(line.right,r.right);
        // Raised/lowered characters do not move the line's baseline.
        if(!shifted){line.y=Math.min(line.y,r.y);line.bottom=Math.max(line.bottom,r.bottom)}
        // Font ascent/descent of the largest run: Chrome puts the baseline
        // at line.y + ascent; PowerPoint needs both to place it the same way.
        const size=parseFloat(style.fontSize);
        if(!shifted&&!(line.size>=size)){
          const font=`${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
          if(!fontMetrics.has(font)){metrics.font=font;const m=metrics.measureText('x');fontMetrics.set(font,[m.fontBoundingBoxAscent,m.fontBoundingBoxDescent])}
          const [ascent,descent]=fontMetrics.get(font);
          line.size=size;line.ascent=ascent*screenScale;line.descent=descent*screenScale;
        }
        let run=line.runs.at(-1);
        if(!run||run.key!==key){run={key,text:'',options};line.runs.push(run)}
        const char=node.nodeValue[c];
        run.text+=style.textTransform==='uppercase'?char.toLocaleUpperCase():style.textTransform==='lowercase'?char.toLocaleLowerCase():
          style.textTransform==='capitalize'&&(c===0||/\s/.test(node.nodeValue[c-1]))?char.toLocaleUpperCase():char;
        // Characters with both a text and an emoji form (↗, ©, ☎…) are drawn
        // as text by Chrome unless followed by U+FE0F; PowerPoint picks the
        // emoji form. Say "text form" explicitly with U+FE0E.
        if(/\p{Emoji}/u.test(char)&&!/\p{Emoji_Presentation}/u.test(char)&&!/[0-9#*]/.test(char)&&
          !/[\uFE0E\uFE0F]/.test(node.nodeValue[c+1]||''))run.text+='\uFE0E';
      }
    }
    lines.sort((a,b)=>a.y-b.y);
    for(const line of lines){
      // Collapsed HTML whitespace at line edges must not be inserted as text.
      if(line.runs.length){line.runs[0].text=line.runs[0].text.trimStart();line.runs.at(-1).text=line.runs.at(-1).text.trimEnd();line.runs=line.runs.filter(r=>r.text)}
    }
    const box=el.getBoundingClientRect();
    return {boxLeft:box.x+(parseFloat(cs.borderLeftWidth)||0)+(parseFloat(cs.paddingLeft)||0),
      boxRight:box.right-(parseFloat(cs.borderRightWidth)||0)-(parseFloat(cs.paddingRight)||0),
      lines:lines.filter(l=>l.runs.some(r=>r.text)),fontSize:parseFloat(cs.fontSize),
      lineHeight,kerning,align:cs.textAlign};
  };
  const candidates=[];
  for(const list of slide.querySelectorAll('ul,ol')){
    if(list.parentElement.closest('ul,ol,table'))continue;
    // Preserve diagrams/media as handled by the normal converter, rather than
    // dropping non-text list contents during semantic text extraction.
    if(list.querySelector('img,svg,canvas,iframe,video,table,pre'))continue;
    const numbers=new Map(),rows=[];
    for(const li of list.querySelectorAll('li')){
      const parent=li.parentElement,cs=getComputedStyle(li);
      // Husson nested lists use a generated arrow instead of ::marker.
      // Consume that single glyph as a real PowerPoint bullet as well.
      const before=li.matches('.pptx-before')?li.querySelector(':scope > .pptx-pseudo-text'):null;
      const generated=before&&Array.from(before.textContent.trim()).length===1?before:null;
      const row=measure(li,li,generated);
      if(!row.lines.length)continue;
      const siblings=Array.from(parent.children).filter(n=>n.tagName==='LI');
      const reversed=parent.hasAttribute('reversed');
      let value=numbers.get(parent)??(parent.hasAttribute('start')?Number(parent.getAttribute('start')):reversed?siblings.length:1);
      if(li.hasAttribute('value'))value=Number(li.getAttribute('value'));
      numbers.set(parent,value+(reversed?-1:1));
      let depth=0;for(let p=parent;p&&p!==list;p=p.parentElement)if(p.matches('ul,ol'))depth++;
      const marker=generated?getComputedStyle(generated):getComputedStyle(li,'::marker');
      row.bullet=cs.listStyleType==='none'&&!generated?null:{ordered:parent.tagName==='OL',style:cs.listStyleType,
        number:value,depth:Math.min(8,depth),color:marker.color,...(generated?{character:generated.textContent.trim()}:{}),
        fontFace:cs.fontFamily.split(',')[0].trim().replace(/^['"]|['"]$/g,''),fontSize:parseFloat(marker.fontSize)||row.fontSize};
      rows.push(row);
    }
    if(rows.length)candidates.push({elements:[list],rows,kind:'list'});
  }
  const used=new Set();
  // Paragraphs and headings: headings otherwise go through the generic
  // converter, which does not place the baseline where Chrome drew it.
  for(const p of slide.querySelectorAll('p,h1,h2,h3,h4,h5,h6')){
    if(used.has(p)||p.closest('ul,ol,table')||!plain(p)||!p.textContent.trim())continue;
    const elements=[p],rows=[measure(p)];used.add(p);
    let next=p.nextElementSibling;
    while(next?.tagName==='P'&&plain(next)&&next.textContent.trim()&&
      next.getBoundingClientRect().top>=elements.at(-1).getBoundingClientRect().bottom-2){
      elements.push(next);rows.push(measure(next));used.add(next);next=next.nextElementSibling;
    }
    if(rows.every(row=>row.lines.length))candidates.push({elements,rows,kind:'text'});
  }
  // Bare text directly inside a flex or grid box is an anonymous item:
  // give it an element (same layout) so it is measured like the others.
  for(const box of slide.querySelectorAll('*')){
    if(!/flex|grid/.test(getComputedStyle(box).display)||box.closest('svg'))continue;
    for(const text of Array.from(box.childNodes).filter(n=>n.nodeType===3&&n.nodeValue.trim())){
      // A custom tag no stylesheet targets: a <span> would match rules such
      // as `.bar span` and change the text's colour or size.
      const item=document.createElement('husson-text');text.replaceWith(item);item.appendChild(text);
    }
  }
  // Text-only items of flex and grid boxes (tabs, chips, labels): measured
  // like a one-paragraph block, their own box kept on the placeholder.
  for(const item of slide.querySelectorAll('*')){
    if(used.has(item)||item.children.length||!item.textContent.trim()||item.closest('ul,ol,table,svg,pre')||
      /^(P|H[1-6]|LI|TD|TH|SCRIPT|STYLE)$/.test(item.tagName)||item.matches('.pptx-pseudo-text'))continue;
    const parent=item.parentElement;
    if(!parent||!/flex|grid/.test(getComputedStyle(parent).display)||/flex|grid/.test(getComputedStyle(item).display))continue;
    const row=measure(item);used.add(item);
    if(row.lines.length)candidates.push({elements:[item],rows:[row],kind:'text'});
  }
  // Measure everything first: clearing one paragraph must not change later
  // line wrapping, collapsed margins, list counters, or neighbouring blocks.
  const pending=[];
  // Effective margin of a block after CSS margin collapsing: a child's top or
  // bottom margin passes through a parent without border, padding or its own
  // formatting context. The placeholder has no children, so it must carry
  // the collapsed margin itself or the following content moves.
  const collapsedMargin=(el,side)=>{
    const values=[];
    for(let node=el;node;){
      const cs=getComputedStyle(node);
      values.push(parseFloat(cs[`margin${side}`])||0);
      if((parseFloat(cs[`padding${side}`])||0)||(parseFloat(cs[`border${side}Width`])||0)||
        cs.display!=='block'||cs.overflow!=='visible'||/absolute|fixed/.test(cs.position)||cs.float!=='none')break;
      const children=Array.from(node.children).filter(child=>{const c=getComputedStyle(child);return c.display!=='none'&&!/absolute|fixed/.test(c.position)});
      const next=side==='Top'?children[0]:children.at(-1);
      const textBefore=next&&Array.from(node.childNodes).slice(...(side==='Top'?[0,Array.from(node.childNodes).indexOf(next)]:[Array.from(node.childNodes).indexOf(next)+1]))
        .some(child=>child.nodeType===3&&child.nodeValue.trim());
      if(!next||textBefore)break;
      node=next;
    }
    return Math.max(0,...values)+Math.min(0,...values);
  };
  for(const {elements,rows,kind} of candidates){
    const first=elements[0],r=first.getBoundingClientRect();
    const id=String(blocks.length);
    const aligned=row=>['center','right','end'].includes(row.align);
    const x=Math.min(...rows.map(row=>aligned(row)?row.boxLeft:row.lines[0].x-(row.bullet ? .7*row.fontSize : 0)));
    // PowerPoint places a line's baseline at spacing × ascent/(ascent+descent)
    // below the top of an exact-spaced line; Chrome puts it at line.y + ascent.
    // Choose each paragraph's top, spacing and space-after so that every
    // baseline lands where Chrome drew it.
    let end=null,previous=null;
    for(const row of rows){
      const n=row.lines.length,first=row.lines[0];
      const ratio=first.ascent/(first.ascent+first.descent);
      const baseline=first.y+first.ascent;
      let spacing=n>1?(row.lines.at(-1).y-first.y)/(n-1):row.lineHeight;
      let top=baseline-ratio*spacing;
      // A single line may use a tighter exact spacing to start lower: its
      // baseline stays put and it no longer overlaps the paragraph above.
      if(end!==null&&top<end&&n===1){spacing=Math.max(.1,(baseline-end)/ratio);top=baseline-ratio*spacing}
      if(previous)previous.gap=Math.max(0,top-end);
      row.spacing=spacing;row.gap=0;row.top=top;
      end=top+n*spacing;previous=row;
    }
    const y=rows[0].top;
    const right=Math.max(...rows.flatMap(row=>row.lines.map(l=>l.right)),...rows.map(row=>row.boxRight));
    const bottom=Math.max(...rows.flatMap(row=>row.lines.map(l=>l.bottom)));
    const block={id,kind,x:x-r.x,y:y-r.y,width:right-x,height:bottom-y+4,rows};
    for(const row of rows){
      row.boxLeft-=r.x;row.boxRight-=r.x;
      for(const line of row.lines){line.x-=r.x;line.y-=r.y}
    }
    const dimensions=elements.map(el=>({el,r:el.getBoundingClientRect()}));
    blocks.push(block);
    for(const {el,r:box} of dimensions){
      // getBoundingClientRect() includes the RevealJS scale of the stage, while
      // the placeholder is sized in CSS pixels: undo the scale, or every block
      // after a paragraph moves up by (1 - scale) of the paragraph height.
      const scale=el.offsetWidth?box.width/el.offsetWidth:1;
      const cs=getComputedStyle(el), replacement=document.createElement('div');
      replacement.className='husson-native-text-placeholder';
      replacement.style.cssText=`display:${cs.display==='list-item'?'block':cs.display};position:relative;box-sizing:border-box;width:${box.width/scale}px;height:${box.height/scale}px;margin:${collapsedMargin(el,'Top')}px ${cs.marginRight} ${collapsedMargin(el,'Bottom')}px ${cs.marginLeft};vertical-align:${cs.verticalAlign};flex-shrink:${cs.flexShrink}`;
      // Keep the element's own box (heading rule, panel fill) on the placeholder.
      for(const property of ['border-top','border-right','border-bottom','border-left','border-radius','background-color','background-image','box-shadow'])
        replacement.style.setProperty(property,cs.getPropertyValue(property));
      // The placeholder keeps the element's box; the native text sits on a
      // child covering it, so the converter draws both the box and the text.
      if(el===first){
        const text=document.createElement('div');
        text.style.cssText=`position:absolute;left:${-parseFloat(cs.borderLeftWidth)||0}px;top:${-parseFloat(cs.borderTopWidth)||0}px;width:${box.width/scale}px;height:${box.height/scale}px`;
        text.dataset.hussonNativeText=JSON.stringify(block);
        replacement.appendChild(text);
      }
      pending.push({el,replacement});
    }
  }
  // Replace only once every placeholder has read its element's styles:
  // a sibling rule such as `h2 + p` must still apply while it is measured.
  for(const {el,replacement} of pending)el.replaceWith(replacement);
  return blocks;
}

// Called by the version-checked dom-to-pptx hook. Let PptxGenJS handle rich
// text, hyperlinks, font embedding, paragraphs, and soft line breaks.
export function renderNativeText(node,config,domOrder,effectiveZIndex) {
  const data=node.dataset?.hussonNativeText;if(!data)return null;
  const block=JSON.parse(data),r=node.getBoundingClientRect(),px=config.scale/96,parts=[];
  const color=value=>{
    const rgb=value.match(/[\d.]+/g);if(!rgb)return '000000';
    return rgb.slice(0,3).map(n=>Math.round(Number(n)).toString(16).padStart(2,'0')).join('').toUpperCase();
  };
  for(const row of block.rows){
    for(let l=0;l<row.lines.length;l++)for(let i=0;i<row.lines[l].runs.length;i++){
      const run=row.lines[l].runs[i];if(!run.text)continue;
      const first=l===0&&i===0;
      // PowerPoint draws superscript/subscript text at 2/3 of its size:
      // write 3/2 of the size Chrome used (measured in PowerPoint).
      const reduced=run.options.superscript||run.options.subscript?1.5:1;
      parts.push({text:run.text,options:{...run.options,fontSize:run.options.fontSize*px*72*reduced,
        color:color(run.options.color),charSpacing:(run.options.gapWidth!==undefined?run.options.gapWidth-run.options.spaceWidth:run.options.charSpacing)*px*72,align:'left',
        ...(l>0&&i===0?{softBreakBefore:true}:{}),
        ...(first&&row.bullet?{bullet:row.bullet.ordered?{type:'number',numberStartAt:row.bullet.number}:{characterCode:'2022'}}:{})}});
    }
    if(parts.length)parts.at(-1).options.breakLine=true;
  }
  if(parts.length)delete parts.at(-1).options.breakLine;
  return {items:[{type:'text',domOrder,zIndex:effectiveZIndex.concat([0,-1]),
    hussonNativeId:block.id,textParts:parts,options:{
      x:config.offX+(r.x+block.x-config.rootX)*px,y:config.offY+(r.y+block.y-config.rootY)*px,
      // Every line break Chrome made is written explicitly (softBreakBefore):
      // PowerPoint must not add its own when its advances differ slightly.
      w:block.width*px,h:block.height*px,margin:0,align:'left',valign:'top',wrap:false}}],stopRecursion:true};
}

// Apply the measured paragraph indents/spacing after the converter's font
// scaling. Geometry stays in slide units; list levels and markers stay native.
export function finalizeNativeText(xml,blocks,slideWidth=12192000,sourceWidth=1600) {
  const emu=slideWidth/sourceWidth,pt=emu/12700;
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  const color=value=>{
    const rgb=value.match(/[\d.]+/g);return rgb?rgb.slice(0,3).map(n=>Math.round(Number(n)).toString(16).padStart(2,'0')).join('').toUpperCase():'000000';
  };
  const seen=new Set();
  xml=xml.replace(/<p:sp\b[\s\S]*?<\/p:sp>/g,shape=>{
    const id=shape.match(/husson-native:(\d+)/)?.[1];if(id===undefined)return shape;
    const block=blocks.find(b=>b.id===id);if(!block)throw new Error(`Unknown native text block ${id}`);
    seen.add(id);let index=0;
    shape=shape.replace(/<a:p>[\s\S]*?<\/a:p>/g,paragraph=>{
      const row=block.rows[index++];if(!row)throw new Error(`Extra native paragraph in ${id}`);
      const aligned=['center','right','end'].includes(row.align);
      const textX=aligned?row.boxLeft:row.lines[0].x,indent=Math.round((textX-block.x)*emu);
      const rightMargin=aligned?Math.max(0,Math.round((block.x+block.width-row.boxRight)*emu)):0;
      const marker=row.bullet;
      const next=block.rows[index];
      const spacing=row.spacing,gap=next?row.gap:0;
      let ppr=`<a:pPr algn="${row.align==='center'?'ctr':['right','end'].includes(row.align)?'r':row.align==='justify'?'just':'l'}" marL="${indent}" marR="${rightMargin}" indent="${marker?-Math.round(.7*row.fontSize*emu):0}"${marker?` lvl="${marker.depth}"`:''}>`;
      ppr+=`<a:lnSpc><a:spcPts val="${Math.round(spacing*pt*100)}"/></a:lnSpc>`;
      if(gap)ppr+=`<a:spcAft><a:spcPts val="${Math.round(gap*pt*100)}"/></a:spcAft>`;
      if(marker){
        ppr+=`<a:buClr><a:srgbClr val="${color(marker.color)}"/></a:buClr><a:buSzPct val="100000"/><a:buFont typeface="${escape(marker.fontFace)}"/>`;
        const styles={'decimal':'arabicPeriod','lower-alpha':'alphaLcPeriod','upper-alpha':'alphaUcPeriod','lower-roman':'romanLcPeriod','upper-roman':'romanUcPeriod'};
        ppr+=marker.ordered?`<a:buAutoNum type="${styles[marker.style]||'arabicPeriod'}" startAt="${marker.number}"/>`:
          `<a:buChar char="${escape(marker.character||(marker.style==='square'?'▪':marker.style==='circle'?'◦':'•'))}"/>`;
      }else ppr+='<a:buNone/>';
      ppr+='</a:pPr>';
      return paragraph.replace(/<a:pPr\b[\s\S]*?<\/a:pPr>/,ppr);
    });
    if(index!==block.rows.length)throw new Error(`Missing native paragraphs in ${id}: ${index}/${block.rows.length}`);
    // Chrome kerns text unless font-kerning is none; PowerPoint kerns a run
    // only when it carries kern (0 = at every size).
    if(block.rows.every(row=>row.kerning))shape=shape.replace(/<a:rPr\b(?![^>]*\bkern=)/g,'<a:rPr kern="0"');
    return shape.replace(/name="[^"]*"/,`name="Husson ${block.kind==='list'?'list':'text'} ${id}"`);
  });
  if(seen.size!==blocks.length)throw new Error(`Missing native text shapes: ${seen.size}/${blocks.length}`);
  return xml;
}
