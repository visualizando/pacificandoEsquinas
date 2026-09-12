const $=id=>document.getElementById(id), fmt=(n,d=0)=>n.toLocaleString('es-AR',{maximumFractionDigits:d});
let data, selected=[], map, loaded=false, popup;
const fc=features=>({type:'FeatureCollection',features});
function filters(){return {level:$('level').value,sector:$('sector').value,commune:$('commune').value,noAvenues:$('no-avenues').checked,oneWay:$('one-way').checked,minimum:Number($('minimum').value),review:$('review').checked};}
function showBlock(f){
  const p=f.properties, content=document.createElement('div');
  const heading=document.createElement('h3');heading.textContent=p.street;content.append(heading);
  const info=document.createElement('p');info.textContent=`${fmt(p.length_m)} m · ${p.direction==='DOBLE'?'Doble mano':'Mano única'} · ${p.avenue?'Avenida / bulevar':'Calle / pasaje'}`;content.append(info);
  const area=document.createElement('p');area.textContent=Number.isFinite(p.area_m2)?`${fmt(p.area_m2)} m² calculados · ${fmt(p.measured_length_m/p.length_m*100,1)}% de la longitud`:'Superficie sin datos';content.append(area);
  const list=document.createElement('ul');
  for(const link of p.matches){const s=data.schools[link.id],li=document.createElement('li');li.textContent=`${s.name} — ${s.address} · ${s.levels.join(', ')}${link.quality==='revisar'?' · Ubicación aproximada':''}`;list.append(li);}
  content.append(list);
  if(map&&loaded){const coords=f.geometry.type==='LineString'?f.geometry.coordinates:f.geometry.coordinates.flat();map.flyTo({center:coords[Math.floor(coords.length/2)],zoom:16});if(popup)popup.remove();popup=new maplibregl.Popup().setLngLat(coords[Math.floor(coords.length/2)]).setDOMContent(content).addTo(map);}
}
function update(){
  if(!data)return;
  if(popup)popup.remove();
  selected=SchoolFilters.select(data,filters());
  const stats=SchoolFilters.summarize(selected,data.schools),m=data.metadata;
  const total=SchoolFilters.summarize(data.features.map(f=>({...f,properties:{...f.properties,matches:f.properties.schools}})),data.schools);
  const validArea=stats.measuredBlocks>0||stats.blocks===0;
  const coverage=stats.length?stats.measuredLength/stats.length*100:0;
  const metrics=[
    [stats.establishments,total.establishments,fmt(stats.establishments),'Escuelas alcanzadas ↑',`${fmt(stats.establishments/total.establishments*100,1)}% del total · más es mejor`],
    [stats.blocks,m.eligible_city_blocks,fmt(stats.blocks/m.eligible_city_blocks*100,1)+'%','Cuadras afectadas ↓',`${fmt(stats.blocks)} cuadras · menos es mejor`],
    [stats.area,total.area,validArea?fmt(stats.area)+' m²':'Sin datos','Espacio recreativo disponible', 'Estimado · no incluye tramos sin datos'],
    [stats.area/10000,total.area/10000,validArea?fmt(stats.area/10000,1):'Sin datos','Manzanas equivalentes','1 manzana ≈ 10.000 m²']
  ];
  $('surface-detail').textContent=`Superficie calculada sobre el ${fmt(coverage,1)}% de la longitud seleccionada.`;
  $('metrics').replaceChildren(...metrics.map(([n,max,value,label,note])=>{
    const div=document.createElement('div');div.className='metric'+(label.includes('↑')||label.includes('↓')?' primary-metric':'');
    const head=document.createElement('div');head.className='metric-head';
    const name=document.createElement('span');name.textContent=label;const val=document.createElement('strong');val.textContent=value;head.append(name);
    const track=document.createElement('div');track.className='bar-track';
    const bar=document.createElement('div');bar.className='bar-fill';bar.style.width=`${max?Math.min(100,n/max*100):0}%`;track.append(bar,val);
    const foot=document.createElement('small');foot.className='bar-scale';const end=document.createElement('span');end.textContent=note;foot.append(end);div.append(head,track,foot);return div;
  }));
  document.querySelectorAll('[data-level]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.level ? $('level').value.split(',').includes(b.dataset.level) : !$('level').value)));
  $('multiple').setAttribute('aria-pressed',String(Number($('minimum').value)>=2));
  const extra=Number(Boolean($('sector').value))+Number(Boolean($('commune').value))+Number(!$('review').checked)+Number($('minimum').value==='3');
  $('extra-count').textContent=extra?`· ${extra} activos`:'';
  $('avenue-label').textContent=$('no-avenues').checked?'Avenidas: excluidas':'Avenidas: incluidas';
  $('direction-label').textContent=$('one-way').checked?'Sentido: solo mano única':'Sentido: cualquiera';
  $('multiple').textContent=`Escuelas: ${$('minimum').value} o más`;
  $('status').textContent=selected.length?`${fmt(selected.length)} cuadras con escuelas para evaluar cierres en horario escolar`:'Sin resultados.';
  if(map&&loaded){map.getSource('selection').setData(fc(selected.map(f=>({...f,properties:{id:f.properties.id,count:f.properties.matches.length}}))));}
  if(addressQuery)renderAddress();
}
async function start(){
  try{const response=await fetch('../data/processed/school-streets.json?v=surface-2019-1',{cache:'no-store'});if(!response.ok)throw Error('No se pudo descargar el archivo de cuadras.');data=await response.json();
    if(!data.metadata.surface)throw Error('Faltan los datos de superficie. Recargá la página.');
    for(let i=1;i<=15;i++)$('commune').add(new Option(`Comuna ${i}`,String(i)));
    restoreSchoolLink();
    const m=data.metadata;$('coverage').textContent=`${fmt(m.source_records)} registros · ${fmt(m.school_blocks)} cuadras candidatas · ${m.unresolved.length} sin asignar.`;
    update();
    if(typeof maplibregl==='undefined'){throw Error('No se pudo cargar el mapa. Los filtros y el buscador siguen disponibles.');}
    map=new maplibregl.Map({container:'map',preserveDrawingBuffer:true,attributionControl:false,center:[-58.44,-34.615],zoom:11.5,style:{version:8,sources:{blocks:{type:'geojson',data:'../data/processed/school-blocks-base.json',attribution:'Manzanas esquemáticas · Buenos Aires Data · CC-BY-2.5-AR'}},layers:[{id:'paper',type:'background',paint:{'background-color':'#fafbf8'}},{id:'blocks',type:'fill',source:'blocks',paint:{'fill-color':'#e3e6de'}},{id:'block-edges',type:'line',source:'blocks',paint:{'line-color':'#fafbf8','line-width':['interpolate',['linear'],['zoom'],10,.6,14,2,18,5]}}]}});
    map.addControl(new maplibregl.NavigationControl());
    map.addControl(new maplibregl.AttributionControl({compact:true}));
    map.on('load',()=>{map.addSource('selection',{type:'geojson',data:fc([])});map.addLayer({id:'selection',type:'line',source:'selection',layout:{'line-cap':'round','line-join':'round'},paint:{'line-color':['step',['get','count'],'#79ae8c',2,'#3d8a61',3,'#176044'],'line-width':['interpolate',['linear'],['zoom'],10,2,14,4,18,8]}});loaded=true;update();});
    map.on('click','selection',e=>{const f=selected.find(f=>f.properties.id===e.features[0].properties.id);if(f)showBlock(f);});
    map.on('mouseenter','selection',()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave','selection',()=>map.getCanvas().style.cursor='');
  }catch(e){$('status').textContent=`${e.message} Recargá la página para reintentar.`;}
}
$('filters').addEventListener('submit',e=>e.preventDefault());
$('filters').addEventListener('input',update);$('filters').addEventListener('reset',()=>setTimeout(()=>{$('level').value='';update();},0));

$('level-chips').addEventListener('click',e=>{const b=e.target.closest('[data-level]');if(!b)return;const levels=new Set($('level').value.split(',').filter(Boolean));if(!b.dataset.level)levels.clear();else if(levels.has(b.dataset.level))levels.delete(b.dataset.level);else levels.add(b.dataset.level);$('level').value=[...levels].join(',');update();});
$('multiple').addEventListener('click',()=>{$('minimum').value=Number($('minimum').value)>=2?'1':'2';update();});
let addressRows, addressQuery='';
function renderAddress(){
  if(!addressRows||!data)return;
  const box=$('address-result');box.replaceChildren();
  const result=SchoolAddressSearch.find(addressRows,addressQuery);
  if(result.error){box.textContent=result.error;return;}
  const ids=new Set(result.matches.map(r=>r.block).filter(Boolean));
  const affected=selected.filter(f=>ids.has(f.properties.id));
  const note=document.createElement('p');
  note.textContent=affected.length?'Sí, está incluida en esta selección.':ids.size?'No está incluida con estos filtros.':'No figura como cuadra escolar en estos datos.';
  box.append(note);
  if(result.matches.some(r=>r.block===null)&&ids.size) {const warning=document.createElement('p');warning.textContent='La altura coincide con más de un tramo; revisá la ubicación.';box.append(warning);}
  const relevant=affected.length?affected:data.features.filter(f=>ids.has(f.properties.id)).map(f=>({...f,properties:{...f.properties,matches:f.properties.schools}}));
  const schools=new Set(relevant.flatMap(f=>f.properties.matches.map(l=>l.id)));
  const list=document.createElement('ul');for(const id of schools){const li=document.createElement('li');li.textContent=data.schools[id].name;list.append(li);}box.append(list);
  for(const f of relevant){const button=document.createElement('button');button.type='button';button.textContent=`Ver ${f.properties.street} en el mapa`;button.onclick=()=>showBlock(f);box.append(button);}
  if(map&&loaded&&!relevant.length)map.flyTo({center:result.matches[0].point,zoom:16});
}
$('address-search').addEventListener('submit',async e=>{
  e.preventDefault();addressQuery=$('address').value;
  if(!data){$('address-result').textContent='Los datos todavía están cargando.';return;}
  try{if(!addressRows){$('address-result').textContent='Buscando…';const response=await fetch('../data/processed/school-addresses.json?v=1');if(!response.ok)throw Error();addressRows=await response.json();}renderAddress();}
  catch{$('address-result').textContent='No se pudo cargar el callejero. Intentá de nuevo.';}
});
start();
