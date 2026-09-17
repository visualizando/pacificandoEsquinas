const finishschool_noise = SiteUI.begin('Cargando análisis…');
/* One circle per street, packed inside its median noise band. */
(async()=>{
 const summary=document.getElementById('noise-summary'),svg=document.getElementById('noise-chart'),note=document.getElementById('noise-point');
 try{
 const response=await fetch('../data/processed/school-noise.json?v=2');if(!response.ok)throw Error();
 const data=await response.json(),rows=data.rows.filter(r=>r.coverage_pct>=80&&Number.isFinite(r.noise_band));
 const lo=Math.min(...rows.map(r=>r.noise_band)),hi=Math.max(...rows.map(r=>r.noise_band)),width=((hi-lo)/5+1)*100+60,nodes=[];
 // Seeded randomness keeps the organic layout stable across reloads.
 let seed=7319;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 for(let band=lo;band<=hi;band+=5){
 const placed=[];
 for(const {row} of rows.filter(r=>r.noise_band===band).map(row=>({row,order:random()})).sort((a,b)=>a.order-b.order)){
 const radius=2*Math.sqrt(row.schools);let chosen;
 for(let level=0;!chosen;level++)for(const sign of level?[-1,1]:[1]){
 for(const offset of Array.from({length:40},()=> (random()-.5)*96)){
 if(Math.abs(offset)+radius>48)continue;
 const p={x:offset,y:sign*level*2+(random()-.5)*3,radius,row};
 if(placed.every(q=>Math.hypot(q.x-p.x,q.y-p.y)>=q.radius+radius+.35)){chosen=p;break;}
 }if(chosen)break;
 }
 placed.push(chosen);
 }placed.forEach(p=>nodes.push({...p,x:p.x+80+(band-lo)/5*100}));
 }
 const extent=Math.max(50,...nodes.map(p=>Math.abs(p.y)+p.radius)),height=extent*2+100;
 svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.style.minWidth=`${width}px`;
 function el(tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text)n.textContent=text;svg.append(n);return n;}
 const label=b=>b<=30?'≤35':b>=80?'≥80':`${b}–${b+5}`;
 for(let b=lo;b<=hi;b+=5){const x=30+(b-lo)/5*100;el('line',{x1:x,x2:x,y1:30,y2:height-50,stroke:'var(--line)'});el('text',{x:x+50,y:height-28,'text-anchor':'middle'},label(b));}
 el('text',{x:30,y:18},'Menos ruido');el('text',{x:width-30,y:18,'text-anchor':'end'},'Más ruido →');el('text',{x:width/2,y:height-7,'text-anchor':'middle'},'Ruido diurno estimado · dBA · 2018');
 nodes.forEach(p=>{p.y+=extent+35;el('circle',{cx:p.x,cy:p.y,r:p.radius,fill:`hsl(18 65% ${83-(p.row.noise_band-lo)/Math.max(5,hi-lo)*53}%)`});});
 const mark=el('circle',{r:6,fill:'none',stroke:'var(--ink)','stroke-width':2,visibility:'hidden'}),overlay=el('rect',{x:25,y:25,width:width-50,height:height-75,fill:'transparent'}),hint=note.textContent;
 overlay.addEventListener('pointermove',event=>{const q=new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());const p=nodes.reduce((a,b)=>Math.hypot(b.x-q.x,b.y-q.y)<Math.hypot(a.x-q.x,a.y-q.y)?b:a);Object.entries({cx:p.x,cy:p.y,r:p.radius+2,visibility:'visible'}).forEach(([k,v])=>mark.setAttribute(k,v));note.textContent=`${p.row.street} · ${p.row.schools} ${p.row.schools===1?'escuela':'escuelas'} · ${label(p.row.noise_band)} dBA`;});
 overlay.addEventListener('pointerleave',()=>{mark.setAttribute('visibility','hidden');note.textContent=hint;});
 summary.textContent=`${rows.length.toLocaleString('es-AR')} cuadras, ordenadas por su rango de ruido típico.`;
 document.getElementById('noise-coverage').textContent=`Se excluyen ${data.rows.length-rows.length} cuadras con datos insuficientes. Se exige cobertura del mapa en al menos el 80% de las muestras de cada cuadra.`;
 }catch(e){summary.textContent='No se pudo cargar el gráfico. Recargá la página para reintentar.';console.error(e);}
})().finally(() => finishschool_noise());
