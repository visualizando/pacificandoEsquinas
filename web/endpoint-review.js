/* Local drafts only. Exported reviews feed src/tunnel_review.py, never OSM. */
window.createEndpointReviewer = function({map, current, markers, restoreLayers}) {
  const $=id=>document.getElementById(id), key='pacificando.endpoint-reviews.v1';
  const keys=['origin','destination'], fields=['review-a-lon','review-a-lat','review-b-lon','review-b-lat'];
  let drafts={}, storageError=false;
  try { drafts=JSON.parse(localStorage.getItem(key)||'{}'); } catch { storageError=true; }
  if(!drafts || Array.isArray(drafts) || typeof drafts!=='object')drafts={};
  const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const fresh=d=>d && keys.every(k=>same(d.baseline?.[k],current()[k]));
  function draft(){const c=current(),d=drafts[c.id];return fresh(d)?d:{id:c.id,origin:[...c.origin],destination:[...c.destination],baseline:{origin:c.origin,destination:c.destination},notes:'',reviewed:false};}
  function persist(d){drafts[current().id]=d;try{localStorage.setItem(key,JSON.stringify(drafts));storageError=false;}catch{storageError=true;}}
  function status(message){$('review-status').textContent=message+(storageError?' No se pudo guardar en el navegador: exportá antes de salir.':'');}
  function valid(){return $('endpoint-form').reportValidity();}
  function changed(d){return keys.some(k=>!same(d[k],current()[k]));}
  function paint(){
    const editing=$('endpoint-review').open,d=draft();
    markers().forEach((m,i)=>{m.setDraggable(editing);m.setLngLat(editing?d[keys[i]]:current()[keys[i]]);});
    restoreLayers();
    if(editing && changed(d)) for(const mode of ['car','walk','step_free'])map.setLayoutProperty('tunnel-'+mode,'visibility','none');
    $('review-stale').hidden=!(editing && changed(d));
  }
  function fill(){
    const d=draft(),c=current(),box=c.bbox;
    fields.forEach((id,i)=>{$(id).value=d[keys[Math.floor(i/2)]][i%2];$(id).min=box[i%2===0?1:0];$(id).max=box[i%2===0?3:2];});
    $('review-notes').value=d.notes;
    status(drafts[c.id]&&!fresh(drafts[c.id])?'Hay un borrador de una corrida anterior. Revisá los puntos actuales antes de guardarlo.':d.reviewed?'Extremos revisados en este navegador; exportación y recálculo pendientes.':'Abrí el editor para mover A y B. Podés ingresar coordenadas con el teclado.');
    paint();
  }
  function saveInputs(){
    if(!valid())return false;
    const d=draft();d.origin=fields.slice(0,2).map(id=>Number($(id).value));d.destination=fields.slice(2).map(id=>Number($(id).value));d.notes=$('review-notes').value;d.reviewed=false;
    persist(d);paint();status('Borrador guardado. Comprobá que A quede antes de la entrada y B después de la salida, en la mano permitida.');return true;
  }
  fields.forEach(id=>$(id).addEventListener('change',saveInputs));
  $('review-notes').addEventListener('change',saveInputs);
  $('endpoint-review').addEventListener('toggle',paint);
  $('endpoint-form').addEventListener('submit',event=>{
    event.preventDefault();if(!saveInputs())return;
    const d=draft();d.reviewed=true;persist(d);
    const select=$('tunnel-case'),options=[...select.options];
    const next=options.slice(select.selectedIndex+1).concat(options.slice(0,select.selectedIndex)).find(o=>!drafts[o.value]?.reviewed);
    if(next){select.value=next.value;select.dispatchEvent(new Event('change'));$('endpoint-review').scrollIntoView({block:'start'});$('review-a-lon').focus({preventScroll:true});}
    else status('Todos los cruces tienen una revisión guardada. Exportá el archivo para recalcular.');
  });
  $('review-reset').addEventListener('click',()=>{delete drafts[current().id];try{localStorage.setItem(key,JSON.stringify(drafts));}catch{storageError=true;}fill();});
  $('review-export').addEventListener('click',()=>{
    const cases=Object.values(drafts).filter(d=>d.reviewed).map(({reviewed,...d})=>d);
    if(!cases.length){status('Primero marcá al menos un cruce como revisado.');return;}
    const url=URL.createObjectURL(new Blob([JSON.stringify({schema_version:1,cases},null,2)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='endpoint-reviews.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    status(`${cases.length} revisiones exportadas. Importá el archivo y recalculá para actualizar rutas y distancias.`);
  });
  function refresh(){
    markers().forEach((m,i)=>m.on('dragend',()=>{const p=m.getLngLat();$(fields[i*2]).value=p.lng.toFixed(7);$(fields[i*2+1]).value=p.lat.toFixed(7);if(!saveInputs())paint();}));
    fill();
  }
  return {refresh,paint};
};
