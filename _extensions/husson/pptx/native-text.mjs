// Browser measurement and native PowerPoint paragraphs. No list marker is
// rendered as a separate text box, and a visual line never becomes a shape.
export function captureNativeText(slide) {
  const blocks=[];
  const metrics=document.createElement('canvas').getContext('2d');
  const spaces=new Map();
  const rectObject=r=>({x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height});
  const plain=el=>!el.querySelector('img,svg,canvas,iframe,video,table,ul,ol,pre,code,.pptx-pseudo-text') &&
    ![el,...el.querySelectorAll('*')].some(n=>/flex|grid/.test(getComputedStyle(n).display));
  const measure=(el,owner=null,skip=null)=>{
    const cs=getComputedStyle(el), lines=[];
    const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
    for(let node=walker.nextNode();node;node=walker.nextNode()){
      if(owner&&node.parentElement.closest('li')!==owner)continue;
      if(skip&&skip.contains(node))continue;
      const style=getComputedStyle(node.parentElement);
      if(style.display==='none'||style.visibility==='hidden')continue;
      const link=node.parentElement.closest('a');
      const options={fontFace:style.fontFamily.split(',')[0].trim().replace(/^['"]|['"]$/g,''),
        fontSize:parseFloat(style.fontSize),charSpacing:parseFloat(style.letterSpacing)||0,bold:Number(style.fontWeight)>=600,
        italic:style.fontStyle==='italic',underline:style.textDecorationLine.includes('underline'),
        color:style.color,...(link?{hyperlink:{url:link.getAttribute('href')}}:{})};
      const key=JSON.stringify(options);
      for(let c=0;c<node.length;c++){
        const range=document.createRange();range.setStart(node,c);range.setEnd(node,c+1);
        const r=range.getBoundingClientRect();if(r.width<.01||r.height<.01)continue;
        let line=lines.find(x=>{
          const height=Math.min(x.bottom-x.y,r.height);
          return Math.min(x.bottom,r.bottom)-Math.max(x.y,r.y)>height*.4&&Math.abs(x.bottom-r.bottom)<height*.35;
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
        line.y=Math.min(line.y,r.y);line.x=Math.min(line.x,r.x);line.right=Math.max(line.right,r.right);line.bottom=Math.max(line.bottom,r.bottom);
        let run=line.runs.at(-1);
        if(!run||run.key!==key){run={key,text:'',options};line.runs.push(run)}
        const char=node.nodeValue[c];
        run.text+=style.textTransform==='uppercase'?char.toLocaleUpperCase():style.textTransform==='lowercase'?char.toLocaleLowerCase():
          style.textTransform==='capitalize'&&(c===0||/\s/.test(node.nodeValue[c-1]))?char.toLocaleUpperCase():char;
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
      lineHeight:parseFloat(cs.lineHeight)||parseFloat(cs.fontSize)*1.2,align:cs.textAlign};
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
  for(const p of slide.querySelectorAll('p')){
    if(used.has(p)||p.closest('ul,ol,table')||!plain(p)||!p.textContent.trim())continue;
    const elements=[p],rows=[measure(p)];used.add(p);
    let next=p.nextElementSibling;
    while(next?.tagName==='P'&&plain(next)&&next.textContent.trim()&&
      next.getBoundingClientRect().top>=elements.at(-1).getBoundingClientRect().bottom-2){
      elements.push(next);rows.push(measure(next));used.add(next);next=next.nextElementSibling;
    }
    if(rows.every(row=>row.lines.length))candidates.push({elements,rows,kind:'text'});
  }
  // Measure everything first: clearing one paragraph must not change later
  // line wrapping, collapsed margins, list counters, or neighbouring blocks.
  for(const {elements,rows,kind} of candidates){
    const first=elements[0],r=first.getBoundingClientRect();
    const id=String(blocks.length);
    const aligned=row=>['center','right','end'].includes(row.align);
    const x=Math.min(...rows.map(row=>aligned(row)?row.boxLeft:row.lines[0].x-(row.bullet ? .7*row.fontSize : 0)));
    const y=rows[0].lines[0].y;
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
      const cs=getComputedStyle(el), replacement=document.createElement('div');
      replacement.className='husson-native-text-placeholder';
      replacement.style.cssText=`display:${cs.display==='list-item'?'block':cs.display};position:relative;box-sizing:border-box;width:${box.width}px;height:${box.height}px;margin:${cs.margin};vertical-align:${cs.verticalAlign};flex-shrink:${cs.flexShrink}`;
      if(el===first){replacement.dataset.hussonNativeText=JSON.stringify(block)}
      el.replaceWith(replacement);
    }
  }
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
      parts.push({text:run.text,options:{...run.options,fontSize:run.options.fontSize*px*72,
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
      w:block.width*px,h:block.height*px,margin:0,align:'left',valign:'top',wrap:true}}],stopRecursion:true};
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
      const spacing=row.lines.length>1?(row.lines.at(-1).y-row.lines[0].y)/(row.lines.length-1):
        next?Math.min(row.lineHeight,next.lines[0].y-row.lines[0].y):row.lineHeight;
      const gap=next?Math.max(0,next.lines[0].y-row.lines[0].y-spacing*row.lines.length):0;
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
    return shape.replace(/name="[^"]*"/,`name="Husson ${block.kind==='list'?'list':'text'} ${id}"`);
  });
  if(seen.size!==blocks.length)throw new Error(`Missing native text shapes: ${seen.size}/${blocks.length}`);
  return xml;
}
