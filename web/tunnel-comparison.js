(async function(){
  const $=id=>document.getElementById(id), fmt=n=>Number.isFinite(n)?Math.round(n).toLocaleString('es-AR'):'—';
  const reasons={no_path:'Red desconectada',snap_too_far:'Extremo lejos de la red',no_network:'Sin red',no_corridor:'Corredor no identificado',coincident_anchors:'Extremos coincidentes'};
  function markSelection(){document.querySelectorAll('#comparison-body tr[data-case-id]').forEach(row=>{const active=row.dataset.caseId===$('tunnel-case').value;row.classList.toggle('selected-crossing',active);row.querySelector('button').setAttribute('aria-pressed',String(active));});}
  function selectCase(id){
    const select=$('tunnel-case');
    if(![...select.options].some(option=>option.value===id)){$('comparison-status').textContent='El detalle todavía está cargando. Volvé a seleccionar el cruce en unos segundos.';return;}
    $('tunnel-direction').value=$('comparison-direction').value;
    select.value=id;select.dispatchEvent(new Event('change'));markSelection();
    $('tuneles').scrollIntoView();$('tunnels-heading').focus({preventScroll:true});
  }
  try{
    const response=await fetch('../data/processed/tunnels-all.json');if(!response.ok)throw Error();const data=await response.json();
    function render(){
      const body=$('comparison-body');body.replaceChildren();
      const direction=$('comparison-direction').value,query=$('comparison-search').value.toLocaleLowerCase('es');
      let shown=0,complete=0;
      for(const c of [...data.cases].sort((a,b)=>a.name.localeCompare(b.name,'es'))){
        const d=c.directions[direction],r=d.routes;
        const ok=d.valid_tunnel_crossing&&Object.values(r).every(v=>v.status==='ok');if(ok)complete++;
        if(!c.name.toLocaleLowerCase('es').includes(query))continue;shown++;
        const row=document.createElement('tr'),name=document.createElement('th');name.scope='row';row.dataset.caseId=c.id;
        const a=document.createElement('a');a.href='#tuneles';a.textContent=c.name;a.addEventListener('click',event=>{event.preventDefault();selectCase(c.id);});name.append(a);
        const button=document.createElement('button');button.type='button';button.className='view-crossing';button.textContent='Ver mapa y análisis ↓';button.setAttribute('aria-label',`Ver mapa y análisis de ${c.name}`);button.setAttribute('aria-controls','tuneles');button.addEventListener('click',()=>selectCase(c.id));name.append(button);row.append(name);
        const warning=!d.valid_tunnel_crossing?'Auto: no cruza este túnel':c.portal_extensions_m?.some(n=>n<60)?'Revisar extremos de acceso':null;
        if(warning){const note=document.createElement('small');note.textContent=warning;note.style.display='block';note.style.fontWeight='400';name.append(note);}
        function cell(value){const td=document.createElement('td');td.textContent=value;row.append(td);}
        for(const mode of ['car','walk','step_free']){
          const v=r[mode];cell(v.status==='ok'?`${fmt(v.distance_m)} m · ${v.model_minutes.toLocaleString('es-AR')} min`:reasons[v.status]||'Sin cálculo');
        }
        const p=d.step_free_penalty;cell(p?`${p.extra_m>=0?'+':''}${fmt(p.extra_m)} m · ${fmt(p.extra_percent)}%`:'—');
        for(const mode of ['walk','step_free']){const v=r[mode];cell(v.status==='ok'?`${v.mapped_crossings} / ${v.turns_approx}`:'—');}
        cell(!d.valid_tunnel_crossing?'Auto no validado por el túnel':!ok?'Cálculo parcial':d.pedestrian_endpoints_comparable===false?'Extremos peatonales diferentes':c.portal_extensions_m?.some(n=>n<60)?'Acceso demasiado corto · revisar extremos':c.endpoint_method==='pilot_manual'?'Piloto · revisión de campo pendiente':'Estimación automática · revisar extremos');
        body.append(row);
      }
      $('comparison-status').textContent=`${shown} de ${data.cases.length} pasos visibles · ${complete} con los tres recorridos y cruce vehicular comprobado en este sentido.`;
      markSelection();
    }
    $('comparison-direction').addEventListener('change',render);$('comparison-search').addEventListener('input',render);$('tunnel-case').addEventListener('change',markSelection);render();
  }catch(e){$('comparison-status').textContent='No se pudo cargar la corrida ampliada. Recargá la página cuando termine el cálculo.';}
})();
