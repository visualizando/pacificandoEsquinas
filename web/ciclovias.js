'use strict';
const finishPageLoad = SiteUI.begin('Cargando datos y mapa…');
const $ = id => document.getElementById(id);
const fmt = n => n.toLocaleString('es-AR', {maximumFractionDigits:1});
let map, data, popup;
const bounds = [[-58.535,-34.705],[-58.335,-34.525]];
function visibility() {
  const proposed = $('proposed').checked;
  map.setLayoutProperty('existing', 'visibility', 'visible');
  map.setLayoutProperty('proposed', 'visibility', proposed ? 'visible' : 'none');
  if (popup) popup.remove();
  $('status').textContent = proposed ? 'Red actual + nuevas ciclovías de mi propuesta.' : 'Situación actual: las ciclovías que ya existen.';
  CycleCoverage.update?.();
}
function select(feature, lngLat) {
  const p = feature.properties;
  const content = document.createElement('div');
  const title = document.createElement('h3'); title.textContent = p.street;
  const kind = document.createElement('p'); kind.textContent = p.kind === 'existing' ? 'Red actual' : 'Mi propuesta · nuevas ciclovías';
  const length = document.createElement('p'); length.textContent = `${fmt(p.length_m)} m`;
  const link = document.createElement('a'); link.href = `https://www.openstreetmap.org/way/${p.osm_id}`; link.textContent = 'Ver calle en OpenStreetMap'; link.target = '_blank'; link.rel = 'noopener';
  content.append(title,kind,length,link);
  $('selection').replaceChildren(content);
  if(popup) popup.remove();
  popup = new maplibregl.Popup().setLngLat(lngLat).setDOMContent(content.cloneNode(true)).addTo(map);
}
async function start() {
  try {
    const response = await fetch('../data/processed/cycle-completion.json?v=union1');
    if(!response.ok) throw Error('No se pudieron cargar los datos de ciclovías.');
    data = await response.json();
    const m = data.metadata;
    for (const [value,label,cls] of [[`${fmt(m.existing_km)} km`,'Red actual','existing-value'],[`${fmt(m.proposed_km)} km`,'Mi propuesta','proposed-value']]) {
      const row=document.createElement('div'), name=document.createElement('span'), number=document.createElement('strong');
      name.textContent=label; number.textContent=value; number.className=cls; row.append(name,number); $('metrics').append(row);
    }
    $('source-date').textContent=`Red actual · OpenStreetMap: ${new Date(m.osm_date).toLocaleDateString('es-AR',{timeZone:'UTC'})}. Longitudes aproximadas.`;
    if(typeof maplibregl === 'undefined') throw Error('No se pudo cargar la biblioteca del mapa.');
    map = new maplibregl.Map({container:'map',attributionControl:false,bounds,fitBoundsOptions:{padding:22},style:{version:8,sources:{blocks:{type:'geojson',data:'../data/processed/school-blocks-base.json',attribution:'Manzanas · Buenos Aires Data · CC-BY-2.5-AR'}},layers:[{id:'paper',type:'background',paint:{'background-color':'#fafbf8'}},{id:'blocks',type:'fill',source:'blocks',paint:{'fill-color':'#e3e6de'}},{id:'block-edges',type:'line',source:'blocks',paint:{'line-color':'#fafbf8','line-width':['interpolate',['linear'],['zoom'],10,.6,14,2,18,5]}}]}});
    map.addControl(new maplibregl.NavigationControl());
    map.addControl(new maplibregl.AttributionControl({compact:true}));
    map.addControl(new maplibregl.ScaleControl({unit:'metric'}));
    map.on('error',()=>{$('status').textContent='No se pudo cargar parte del mapa. Recargá la página para reintentar.';});
    SiteUI.watchMap(map, finishPageLoad);
    map.on('load',()=>{
      for(const kind of ['proposed','existing']) {
        map.addSource(kind,{type:'geojson',data:data[kind],attribution:'© OpenStreetMap contributors · ODbL'});
        const paint={'line-color':kind==='existing'?'#4d996f':'#2864b7','line-width':['interpolate',['linear'],['zoom'],10,2,14,4,18,7]};
        if(kind==='proposed') paint['line-dasharray']=[2,1.25];
        map.addLayer({id:kind,type:'line',source:kind,layout:{'line-join':'round','line-cap':'round'},paint});
        $(kind).disabled=false; $(kind).addEventListener('change',visibility);
        map.on('mouseenter',kind,()=>map.getCanvas().style.cursor=CycleEditor.active?'crosshair':'pointer');
        map.on('mouseleave',kind,()=>map.getCanvas().style.cursor=CycleEditor.active?'crosshair':'');
      }
      CycleEditor.init(map);
      CycleCoverage.init(map, data.metadata.generated_at);
      map.on('click',e=>{
        if(CycleEditor.active){if(popup)popup.remove();CycleEditor.add?.(e.lngLat);return;}
        const features=map.queryRenderedFeatures([[e.point.x-5,e.point.y-5],[e.point.x+5,e.point.y+5]],{layers:['existing','proposed']});
        if(features.length) select(features[0],e.lngLat);
        else {if(popup)popup.remove();CycleCoverage.select?.(e);}
      });
      $('reset-map').disabled=false;
      $('reset-map').addEventListener('click',()=>map.fitBounds(bounds,{padding:22,duration:0}));
      new ResizeObserver(() => { map.resize(); map.fitBounds(bounds,{padding:22,duration:0}); }).observe($('map'));
      visibility();
    });
  } catch(error) {finishPageLoad(true); $('status').textContent=`${error.message} Recargá la página para reintentar. Los datos también se pueden descargar.`; }
}
start();
