const finishtunnel_inventory = SiteUI.begin('Cargando análisis…');
(async function () {
  'use strict';
  const status=document.getElementById('inventory-status');
  // Fixed metre bands remain comparable when results are recalculated.
  const bands=[
    {color:'#32965b',label:'Menos de 5 m'},
    {color:'#edc949',label:'5 a 50 m'},
    {color:'#d64b40',label:'Más de 50 m'}
  ];
  const pending={color:'#92928c',label:'A revisar / sin datos'};
  function penalty(site){
    const audit=site.audit;
    if(!audit?.comparison_usable||!Number.isFinite(audit.extra_m))return {...pending,description:'Comparación pendiente de revisión'};
    const n=audit.extra_m,band=bands[n<5?0:n<=50?1:2];
    return {...band,description:n<0?`${Math.round(-n).toLocaleString('es-AR')} m menos a pie sin escaleras que en auto`:`${Math.round(n).toLocaleString('es-AR')} m extra a pie sin escaleras frente al auto`};
  }
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
    for(const site of data.sites){const c=results.find(c=>c.tunnel_way_ids.some(id=>site.way_ids.includes(id)));if(c){site.case_id=c.id;site.audit=c.directions.outbound?.endpoint_audit;}}
    const legend=document.createElement('div');legend.className='inventory-legend';
    const scale=document.createElement('div');scale.className='inventory-scale';
    for(const band of bands){
      const item=document.createElement('span');item.textContent=band.label;
      item.style.borderTopColor=band.color;scale.append(item);
    }
    legend.append(scale);
    for(const band of [pending]){
      const item=document.createElement('span'),swatch=document.createElement('i');
      swatch.style.background=band.color;swatch.setAttribute('aria-hidden','true');
      item.append(swatch,document.createTextNode(band.label));legend.append(item);
    }
    document.getElementById('inventory-map').before(legend);
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
        const level=penalty(site);
        const dot=document.createElement('button');dot.type='button';dot.className='inventory-dot';dot.style.background=window.TunnelChart.penaltyColor(site.audit);
        dot.setAttribute('aria-label',`${site.name}: ${site.case_id?'analizado':'pendiente de análisis'}`);
        const box=document.createElement('div'), title=document.createElement('strong'), p=document.createElement('p'), a=document.createElement('a');
        title.textContent=site.name;p.textContent=level.description;
        a.textContent=site.case_id?'Ver comparación →':'Ver ubicación en OpenStreetMap →';
        a.href=site.case_id?'#tuneles':`https://www.openstreetmap.org/way/${site.way_ids[0]}`;
        if(site.case_id)a.addEventListener('click',()=>openCase(site.case_id));
        box.append(title,p,a);
        new maplibregl.Marker({element:dot}).setLngLat(site.center).setPopup(new maplibregl.Popup({offset:15}).setDOMContent(box)).addTo(map);
        dot.setAttribute('aria-label',`${site.name}: ${level.description}`);dot.title=`${site.name}: ${level.description}`;
        bounds.extend(site.center);
      }
      map.fitBounds(bounds,{padding:40,maxZoom:12,duration:0});
    });
  }catch(error){status.textContent='No se pudo cargar el inventario. Los tres análisis siguen disponibles abajo.';}
})().finally(() => finishtunnel_inventory());
