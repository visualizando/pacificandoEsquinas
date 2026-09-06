(async function () {
  'use strict';
  const status=document.getElementById('inventory-status');
  function openCase(id) {
    const select=document.getElementById('tunnel-case');
    if (![...select.options].some(o=>o.value===id)) return;
    select.value=id; select.dispatchEvent(new Event('change'));
    document.getElementById('tuneles').scrollIntoView(); select.focus({preventScroll:true});
  }
  document.querySelectorAll('[data-case]').forEach(a=>a.addEventListener('click',()=>openCase(a.dataset.case)));
  try {
    const response=await fetch('../data/processed/tunnel-inventory.json');
    if(!response.ok) throw new Error('Inventario no disponible');
    const data=await response.json();
    let results=[];
    try {const r=await fetch('../data/processed/tunnels-all.json');if(r.ok)results=(await r.json()).cases;}catch(e){}
    for(const site of data.sites){const c=results.find(c=>c.tunnel_way_ids.some(id=>site.way_ids.includes(id)));if(c){site.case_id=c.id;site.complete=Object.values(c.directions).some(d=>d.valid_tunnel_crossing&&Object.values(d.routes).every(r=>r.status==='ok'));}}
    status.textContent=`${data.sites.length} ubicaciones detectadas en OSM · ${results.length} casos procesados. Consultá resultados y advertencias en el cuadro comparativo.`;
    document.getElementById('inventory-source').textContent=`Fuente: OpenStreetMap · ${data.snapshot_at}. Se buscan calles con etiqueta tunnel que cruzan geométricamente vías ferroviarias dentro de CABA. Las calzadas cercanas con el mismo nombre se agrupan. No incluye todos los puentes ferroviarios sin etiqueta de túnel en la calle.`;
    const list=document.getElementById('inventory-list');
    for(const site of data.sites) {
      const li=document.createElement('li'), a=document.createElement('a');
      a.textContent=site.name+(site.case_id?' · ver cálculo':' · pendiente');
      a.href=site.case_id?'#tuneles':`https://www.openstreetmap.org/way/${site.way_ids[0]}`;
      if(site.case_id) a.addEventListener('click',()=>openCase(site.case_id));
      li.append(a);list.append(li);
    }
    if(!window.maplibregl) {document.getElementById('inventory-map').textContent='El mapa no pudo cargarse. Consultá la lista de ubicaciones.';return;}
    const map=new maplibregl.Map({container:'inventory-map',center:[-58.46,-34.61],zoom:11,style:{version:8,sources:{basemap:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,maxzoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}},layers:[{id:'bg',type:'background',paint:{'background-color':'#f5f5f0'}},{id:'basemap',type:'raster',source:'basemap',paint:{'raster-opacity':0.65,'raster-saturation':-0.8}}]}});
    map.addControl(new maplibregl.NavigationControl(),'top-right');
    map.on('load',()=>{
      map.addSource('rails',{type:'geojson',data:data.rails,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · ODbL'});
      map.addLayer({id:'rails',source:'rails',type:'line',paint:{'line-color':'#a5a59a','line-width':2}});
      const bounds=new maplibregl.LngLatBounds();
      for(const site of data.sites){
        const dot=document.createElement('button');dot.type='button';dot.className='inventory-dot'+(site.complete?' analyzed':'');
        dot.setAttribute('aria-label',`${site.name}: ${site.case_id?'analizado':'pendiente de análisis'}`);
        const box=document.createElement('div'), title=document.createElement('strong'), p=document.createElement('p'), a=document.createElement('a');
        title.textContent=site.name;p.textContent=site.case_id?'Cálculo disponible · consultar validación':'Pendiente de análisis';
        a.textContent=site.case_id?'Ver comparación →':'Ver ubicación en OpenStreetMap →';
        a.href=site.case_id?'#tuneles':`https://www.openstreetmap.org/way/${site.way_ids[0]}`;
        if(site.case_id)a.addEventListener('click',()=>openCase(site.case_id));
        box.append(title,p,a);
        new maplibregl.Marker({element:dot}).setLngLat(site.center).setPopup(new maplibregl.Popup({offset:15}).setDOMContent(box)).addTo(map);
        dot.setAttribute('aria-label',`${site.name}: ${site.case_id?'analizado':'pendiente de análisis'}`);
        bounds.extend(site.center);
      }
      map.fitBounds(bounds,{padding:40,maxZoom:12,duration:0});
    });
  }catch(error){status.textContent='No se pudo cargar el inventario. Los tres análisis siguen disponibles abajo.';}
})();
