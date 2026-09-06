/* Cards use exactly the saved route/context geometries from the detail view. */
(async function(){
  const $=id=>document.getElementById(id),fmt=n=>Math.round(n).toLocaleString('es-AR');
  const colors={car:'#1466a3',walk:'#ab4b08',step_free:'#8036ad'};
  function el(tag,text,cls){const n=document.createElement(tag);if(text)n.textContent=text;if(cls)n.className=cls;return n;}
  function markSelection(){document.querySelectorAll('#comparison-body [data-case-id]').forEach(card=>{const active=card.dataset.caseId===$('tunnel-case').value;card.classList.toggle('selected-crossing',active);card.querySelector('button').setAttribute('aria-pressed',String(active));});}
  function selectCase(id){
    const select=$('tunnel-case');
    if(![...select.options].some(o=>o.value===id)){$('comparison-status').textContent='El detalle está cargando. Volvé a seleccionar el cruce en unos segundos.';return;}
    $('tunnel-direction').value=$('comparison-direction').value;
    select.value=id;select.dispatchEvent(new Event('change'));markSelection();
    $('tuneles').scrollIntoView();$('tunnels-heading').focus({preventScroll:true});
  }
  function thumbnail(c,d){
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
    svg.setAttribute('viewBox','0 0 440 230');svg.setAttribute('role','img');
    svg.setAttribute('aria-label','Vista de los recorridos peatonales de '+c.name);
    const paths=['walk','step_free'].filter(m=>d.routes[m].status==='ok');
    const points=paths.flatMap(m=>d.routes[m].geometry.coordinates).concat([c.origin,c.destination]);
    const xs=points.map(p=>p[0]*.82),ys=points.map(p=>-p[1]);
    const xmin=Math.min(...xs),ymin=Math.min(...ys),dx=Math.max(...xs)-xmin,dy=Math.max(...ys)-ymin;
    const scale=Math.min(392/Math.max(dx,.0001),182/Math.max(dy,.0001));
    const project=p=>[24+(392-dx*scale)/2+(p[0]*.82-xmin)*scale,24+(182-dy*scale)/2+(-p[1]-ymin)*scale];
    function line(ps,color,width,dash){if(ps.length<2)return;const path=document.createElementNS(ns,'path');path.setAttribute('d',ps.map((p,i)=>{const q=project(p);return (i?'L':'M')+q[0].toFixed(1)+','+q[1].toFixed(1);}).join(' '));path.setAttribute('fill','none');path.setAttribute('stroke',color);path.setAttribute('stroke-width',width);path.setAttribute('stroke-linejoin','round');if(dash)path.setAttribute('stroke-dasharray',dash);svg.append(path);}
    for(const f of c.context.features)line(f.geometry.coordinates,f.properties.kind==='rail'?'#84847b':'#d1d1c7',f.properties.kind==='rail'?2:1,f.properties.kind==='rail'?'5 4':null);
    for(const mode of paths)line(d.routes[mode].geometry.coordinates,colors[mode],mode==='walk'?6:3,mode==='step_free'?'7 4':null);
    for(const [label,p] of [['A',c.origin],['B',c.destination]]){const q=project(p);const circle=document.createElementNS(ns,'circle');circle.setAttribute('cx',q[0]);circle.setAttribute('cy',q[1]);circle.setAttribute('r','10');circle.setAttribute('fill','#171717');svg.append(circle);const t=document.createElementNS(ns,'text');t.setAttribute('x',q[0]);t.setAttribute('y',q[1]+4);t.setAttribute('text-anchor','middle');t.setAttribute('fill','white');t.setAttribute('font-size','12');t.textContent=label;svg.append(t);}
    return svg;
  }
  try{
    const response=await fetch('../data/processed/tunnels-all.json');if(!response.ok)throw Error();const data=await response.json();
    function render(){
      const body=$('comparison-body');body.replaceChildren();
      const direction=$('comparison-direction').value,query=$('comparison-search').value.toLocaleLowerCase('es');let shown=0;
      for(const c of [...data.cases].sort((a,b)=>a.name.localeCompare(b.name,'es'))){
        if(!c.name.toLocaleLowerCase('es').includes(query))continue;shown++;
        const d=c.directions[direction],card=el('article',null,'crossing-card');card.dataset.caseId=c.id;
        const h=el('h3',c.name);card.append(h);
        const figure=el('figure');figure.append(thumbnail(c,d),el('figcaption','Naranja: a pie · Violeta: sin escaleras · © OpenStreetMap'));card.append(figure);
        const p=c.id==='osm_440436964'?null:d.step_free_penalty;
        card.append(el('p','Desvío al evitar escaleras','crossing-label'));
        card.append(el('p',p?'+'+fmt(p.extra_m)+' m · '+fmt(p.extra_percent)+'%':'Pendiente de comparación','crossing-penalty'));
        const r=d.routes;
        card.append(el('p','A pie: '+(r.walk.status==='ok'?fmt(r.walk.distance_m)+' m':'sin cálculo')+' · Sin escaleras: '+(r.step_free.status==='ok'?fmt(r.step_free.distance_m)+' m':'sin cálculo'),'crossing-distances'));
        const warning=c.id==='osm_440436964'?'El rodeo azul del detalle es del auto. Accesos peatonales por revisar.':!d.valid_tunnel_crossing?'El auto no cruza este túnel en el sentido elegido.':c.portal_extensions_m?.some(n=>n<60)?'Extremos de acceso por revisar.':'Estimación OSM · revisión de accesos pendiente.';
        card.append(el('p',warning,'crossing-warning'));
        const button=el('button','Ver más: mapa y análisis →','view-crossing');button.type='button';button.setAttribute('aria-label','Ver más: mapa y análisis de '+c.name);button.setAttribute('aria-controls','tuneles');button.addEventListener('click',()=>selectCase(c.id));card.append(button);body.append(card);
      }
      $('comparison-status').textContent=shown+' de '+data.cases.length+' cruces'+(shown?'':' · No hay coincidencias. Probá otro nombre.');markSelection();
    }
    $('comparison-direction').addEventListener('change',render);$('comparison-search').addEventListener('input',render);$('tunnel-case').addEventListener('change',markSelection);render();
  }catch(e){$('comparison-status').textContent='No se pudieron cargar los cruces. Recargá la página para volver a intentar.';}
})();
