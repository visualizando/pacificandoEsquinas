const finishtunnel_comparison = SiteUI.begin('Cargando análisis…');
/* Cards use exactly the saved route/context geometries from the detail view. */
(async function(){
  const $=id=>document.getElementById(id),fmt=n=>Math.round(n).toLocaleString('es-AR');
  const colors={car:'#8db6ce',walk:'#ab4b08',step_free:'#8036ad'};
  function el(tag,text,cls){const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;}
  function markSelection(){document.querySelectorAll('#comparison-body [data-case-id]').forEach(card=>{const active=card.dataset.caseId===$('tunnel-case').value;card.classList.toggle('selected-crossing',active);card.querySelector('button').setAttribute('aria-pressed',String(active));});}
  function selectCase(id){
    const select=$('tunnel-case');
    if(![...select.options].some(o=>o.value===id)){$('comparison-status').textContent='El detalle está cargando. Volvé a seleccionar el cruce en unos segundos.';return;}
    select.value=id;select.dispatchEvent(new Event('change'));markSelection();
    $('tuneles').scrollIntoView();$('tunnels-heading').focus({preventScroll:true});
  }
  function thumbnail(c,d){
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
    svg.setAttribute('viewBox','0 0 440 230');svg.setAttribute('role','img');
    svg.setAttribute('aria-label','Recorridos en auto y a pie sin escaleras de '+c.name);
    const paths=['car','step_free'].filter(m=>d.routes[m].status==='ok');
    const points=paths.flatMap(m=>d.routes[m].geometry.coordinates).concat([c.origin,c.destination]);
    const xs=points.map(p=>p[0]*.82),ys=points.map(p=>-p[1]);
    const xmin=Math.min(...xs),ymin=Math.min(...ys),dx=Math.max(...xs)-xmin,dy=Math.max(...ys)-ymin;
    const scale=Math.min(392/Math.max(dx,.0001),182/Math.max(dy,.0001));
    const project=p=>[24+(392-dx*scale)/2+(p[0]*.82-xmin)*scale,24+(182-dy*scale)/2+(-p[1]-ymin)*scale];
    function line(ps,color,width,dash){if(ps.length<2)return;const path=document.createElementNS(ns,'path');path.setAttribute('d',ps.map((p,i)=>{const q=project(p);return (i?'L':'M')+q[0].toFixed(1)+','+q[1].toFixed(1);}).join(' '));path.setAttribute('fill','none');path.setAttribute('stroke',color);path.setAttribute('stroke-width',width);path.setAttribute('stroke-linejoin','round');if(dash)path.setAttribute('stroke-dasharray',dash);svg.append(path);}
    for(const f of c.context.features)line(f.geometry.coordinates,f.properties.kind==='rail'?'#999990':'#e0e0d8',f.properties.kind==='rail'?2:1,f.properties.kind==='rail'?'4 10':null);
    for(const f of c.context.features)if(f.properties.kind==='street'&&f.properties.name===c.corridor)line(f.geometry.coordinates,'#a7a79e',2);
    for(const mode of paths)line(d.routes[mode].geometry.coordinates,colors[mode],mode==='car'?6:3,null);
    for(const [label,p] of [['A',c.origin],['B',c.destination]]){const q=project(p);const circle=document.createElementNS(ns,'circle');circle.setAttribute('cx',q[0]);circle.setAttribute('cy',q[1]);circle.setAttribute('r','10');circle.setAttribute('fill','#171717');svg.append(circle);const t=document.createElementNS(ns,'text');t.setAttribute('x',q[0]);t.setAttribute('y',q[1]+4);t.setAttribute('text-anchor','middle');t.setAttribute('fill','white');t.setAttribute('font-size','12');t.textContent=label;svg.append(t);}
    return svg;
  }
  try{
    const response=await fetch('../data/processed/tunnels-all.json');if(!response.ok)throw Error();const data=await response.json();
    function render(){
      const body=$('comparison-body');body.replaceChildren();
      const direction='outbound',query=$('comparison-search').value.toLocaleLowerCase('es');let shown=0;
      // One zero-based distance scale across all cards, independent of filtering.
      const maximum=Math.max(1,...data.cases.flatMap(c=>['car','walk','step_free'].map(m=>c.directions[direction].routes[m].distance_m||0)));
      for(const c of [...data.cases].sort((a,b)=>a.name.localeCompare(b.name,'es'))){
        if(!c.name.toLocaleLowerCase('es').includes(query))continue;shown++;
        const d=c.directions[direction],card=el('article',null,'crossing-card');card.dataset.caseId=c.id;
        const h=el('h3',c.name);card.append(h);
        const figure=el('figure');figure.append(thumbnail(c,d));card.append(figure);
        const audit=d.endpoint_audit,usable=audit?.comparison_usable===true;
        const dot=el('span',null,'crossing-status-dot');dot.style.background=window.TunnelChart.penaltyColor(audit);dot.setAttribute('aria-hidden','true');h.prepend(dot);
        const summary=el('div',null,'crossing-summary');
        summary.append(el('p',usable?(audit.extra_m<0?'−':'+')+fmt(Math.abs(audit.extra_m))+' m':'A revisar','crossing-penalty'));
        summary.append(el('p',usable?'a pie sin escaleras vs. auto':'Extremos o recorrido','crossing-label'));card.append(summary);
        card.append(window.TunnelChart.bars(d,maximum));
        const button=el('button','Ver más: mapa y análisis →','view-crossing');button.type='button';button.setAttribute('aria-label','Ver más: mapa y análisis de '+c.name);button.setAttribute('aria-controls','tuneles');button.addEventListener('click',()=>selectCase(c.id));card.append(button);body.append(card);
      }
      $('comparison-status').textContent=shown+' de '+data.cases.length+' cruces'+(shown?'':' · No hay coincidencias. Probá otro nombre.');markSelection();
    }
    $('comparison-search').addEventListener('input',render);$('tunnel-case').addEventListener('change',markSelection);render();
  }catch(e){$('comparison-status').textContent='No se pudieron cargar los cruces. Recargá la página para volver a intentar.';}
})().finally(() => finishtunnel_comparison());
