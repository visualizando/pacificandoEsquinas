const finishPageLoad = SiteUI.begin('Cargando datos y mapa…');
/* Independent from the corner pipeline: failures stay inside this subsection. */
(async function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const labels = {car:'Auto', walk:'A pie · más corto', step_free:'En bici o con cochecito'};
  const colors = {car:'#8db6ce',walk:'#ab4b08',step_free:'#8036ad'};
  const fmt = n => Math.round(n).toLocaleString('es-AR');
  const empty = {type:'FeatureCollection',features:[]};
  let map, reviewer, ready = false, markers = [], streetLabels = [];
  function text(tag, value, className) {
    const n = document.createElement(tag); n.textContent = value;
    if (className) n.className = className;
    return n;
  }
  try {
    const response = await fetch('../data/processed/tunnels-all.json');
    if (!response.ok) throw new Error('No se encontró el archivo de resultados.');
    const data = await response.json();
    if (data.schema_version !== 1 || !data.cases?.length) throw new Error('Formato de resultados no compatible.');
    for (const c of data.cases) {
      const option = text('option',c.name); option.value=c.id; $('tunnel-case').append(option);
    }
    $('tunnel-content').hidden = false;
    $('tunnel-status').textContent = 'Estimaciones OSM · auditoría de campo pendiente';
    const current = () => data.cases.find(c => c.id === $('tunnel-case').value);
    function mapLabels() {
      if(!ready)return;
      streetLabels.forEach(m=>m.remove());streetLabels=[];
      const c=current(),width=map.getContainer().clientWidth,height=map.getContainer().clientHeight;
      const center=map.project(c.center),occupied=[];
      // Keep the crossing and every route clear, including temporarily hidden modes.
      occupied.push([center.x-55,center.y-40,center.x+55,center.y+40]);
      for(const route of Object.values(c.directions.outbound.routes)){
        if(route.status!=='ok')continue;
        const points=route.geometry.coordinates.map(p=>map.project(p));
        for(let i=1;i<points.length;i++){
          const a=points[i-1],b=points[i],steps=Math.max(1,Math.ceil(Math.hypot(b.x-a.x,b.y-a.y)/8));
          for(let j=0;j<=steps;j++){
            const x=a.x+(b.x-a.x)*j/steps,y=a.y+(b.y-a.y)*j/steps;
            occupied.push([x-12,y-12,x+12,y+12]);
          }
        }
      }
      for(const p of [c.origin,c.destination]){const q=map.project(p);occupied.push([q.x-24,q.y-24,q.x+24,q.y+24]);}
      const candidates=[];
      for(const f of c.context.features){
        const name=f.properties.name||(f.properties.kind==='rail'?'Ferrocarril':'');if(!name)continue;
        const ps=f.geometry.coordinates;
        for(let i=1;i<ps.length;i++){
          const a=map.project(ps[i-1]),b=map.project(ps[i]);
          const x=(a.x+b.x)/2,y=(a.y+b.y)/2,length=Math.hypot(b.x-a.x,b.y-a.y);
          if(x<40||x>width-40||y<30||y>height-35||length<35)continue;
          const p=[(ps[i-1][0]+ps[i][0])/2,(ps[i-1][1]+ps[i][1])/2];
          let angle=Math.atan2(b.y-a.y,b.x-a.x)*180/Math.PI;
          if(angle>90)angle-=180;if(angle< -90)angle+=180;
          candidates.push({name,p,x,y,angle,length,score:Math.hypot(x-width/2,y-height/2),rail:f.properties.kind==='rail'});
        }
      }
      const used=new Set(),limit=width<500?10:18;
      for(const item of candidates.sort((a,b)=>a.score-b.score)){
        if(used.size>=limit)break;if(used.has(item.name))continue;
        const label=text('div',item.name.replace('Avenida ','Av. '),'tunnel-street-label'+(item.rail?' rail-label':''));
        const angle=item.angle*Math.PI/180,dx=12*Math.sin(angle),dy=-12*Math.cos(angle);
        const position=map.unproject([item.x+dx,item.y+dy]);
        const marker=new maplibregl.Marker({element:label,anchor:'center',rotation:item.angle,rotationAlignment:'viewport'}).setLngLat(position).addTo(map);
        const w=label.offsetWidth||100,h=label.offsetHeight||20;
        const bw=Math.abs(w*Math.cos(angle))+Math.abs(h*Math.sin(angle)),bh=Math.abs(w*Math.sin(angle))+Math.abs(h*Math.cos(angle));
        const box=[item.x+dx-bw/2-4,item.y+dy-bh/2-4,item.x+dx+bw/2+4,item.y+dy+bh/2+4];
        if(w>item.length||box[0]<8||box[2]>width-8||box[1]<8||box[3]>height-8||occupied.some(r=>box[0]<r[2]&&box[2]>r[0]&&box[1]<r[3]&&box[3]>r[1])){marker.remove();continue;}
        occupied.push(box);used.add(item.name);streetLabels.push(marker);
      }
    }
    function visibility() {
      if (!ready) return;
      document.querySelectorAll('[data-tunnel-mode]').forEach(input => {
        map.setLayoutProperty(`tunnel-${input.dataset.tunnelMode}`,'visibility',input.checked?'visible':'none');
      });
    }
    function render() {
      const c=current(), direction='outbound', d=c.directions.outbound;
      $('tunnels-heading').textContent=`${c.name} · mapa y análisis`;
      $('tunnel-osm-link').href=`https://www.openstreetmap.org/?mlat=${c.center[1]}&mlon=${c.center[0]}#map=18/${c.center[1]}/${c.center[0]}`;
      $('tunnel-osm-link').setAttribute('aria-label',`Ver en OpenStreetMap: ${c.name} (nueva pestaña)`);
      $('tunnel-endpoints').textContent = `A → B: ${c.endpoints}. Viendo ${direction==='outbound'?'ida (A → B)':'vuelta (B → A)'}. ${c.audit_status || 'Auditoría de campo pendiente'}`;
      $('tunnel-metrics').replaceChildren(window.TunnelChart.detail(c));
      const finding=$('tunnel-finding'); finding.replaceChildren();
      if(d.endpoint_audit?.reasons.length) {
        finding.append(text('h3','Revisar antes de comparar'));
        const list=text('ul','');d.endpoint_audit.reasons.forEach(reason=>list.append(text('li',reason)));finding.append(list);
      }
      if(c.id==='osm_440436964') finding.append(text('p','Altolaguirre: se corrigieron los extremos para que el auto atraviese el túnel en su mano permitida. La caminata calculada usa una vereda representada sobre el eje vial; falta auditar las conexiones con los pasos peatonales separados y las rampas. La igualdad de distancias no verifica que los accesos sean equivalentes.'));
      const external=text('p');
      for(const [mode,label] of [['walking','Contrastar a pie en Google Maps'],['driving','Contrastar en auto en Google Maps']]){
        const a=direction==='outbound'?c.origin:c.destination,b=direction==='outbound'?c.destination:c.origin;
        const link=text('a',label);link.href='https://www.google.com/maps/dir/?'+new URLSearchParams({api:'1',origin:a[1]+','+a[0],destination:b[1]+','+b[0],travelmode:mode});link.target='_blank';link.rel='noopener';external.append(link,document.createTextNode(' · '));
      }
      finding.append(external);
      const free=d.routes.step_free, walk=d.routes.walk;
      if (d.pedestrian_endpoints_comparable===false) finding.append(text('p','Las redes peatonales no pudieron usar extremos equivalentes. No se calcula el desvío sin escaleras; requiere revisar las conexiones.'));
      if (!d.valid_tunnel_crossing) finding.append(text('p','Comparación pendiente: la ruta vehicular no atraviesa el túnel seleccionado.'));
      else if (d.endpoint_audit?.comparison_usable) {
        const penalty=d.endpoint_audit;
        finding.append(text('p','A pie sin escaleras frente al auto','tunnel-penalty-title'));
        finding.append(text('p',`${penalty.extra_m<0?'−':'+'}${fmt(Math.abs(penalty.extra_m))} m · ${penalty.extra_percent<0?'−':'+'}${fmt(Math.abs(penalty.extra_percent))}% de recorrido`,'tunnel-penalty-value'));
        finding.append(text('p','Estimación entre los mismos puntos de referencia. La alternativa peatonal evita escaleras registradas; no demuestra que las rampas sean accesibles.'));
        if(d.step_free_penalty)finding.append(text('p',`Como comparación secundaria, evitar escaleras agrega ${fmt(d.step_free_penalty.extra_m)} m frente al camino peatonal más corto.`));
        finding.append(text('p',`OSM registra ${free.incline_way_count} tramos con pendiente en esta alternativa; puede haber más. Hace falta verificar las rampas, sus descansos y la posibilidad de pasar con una bicicleta.`));
      }
      if (c.id==='lacroze') finding.append(text('p','En Lacroze, el paso corto está marcado como no apto para silla de ruedas, pero OSM no detalla allí las escaleras. El conteo de cero no confirma su ausencia.'));
      if (c.id==='constituyentes') finding.append(text('p','Ubicación corregida: este itinerario cruza el Mitre junto a Monroe. El tramo Pareja–Asunción de la prueba inicial no atravesaba el ferrocarril.'));
      if (walk.status==='ok' && walk.implicit_sidewalk_m>0) finding.append(text('p',`${fmt(walk.implicit_sidewalk_m)} m del recorrido a pie usan calles cuya vereda se representa sobre el eje vial. Los cruces laterales requieren revisión.`));
      $('tunnel-provenance').replaceChildren(text('span',`OSM: ${c.snapshot_at || 'fecha no disponible'} · Método ${data.method_version}. Instantánea y parámetros conservados para reproducir el cálculo. `));
      const license=text('a','© OpenStreetMap contributors · ODbL 1.0'); license.href='https://www.openstreetmap.org/copyright'; $('tunnel-provenance').append(license);
      if (!ready) return;
      map.getSource('tunnel-context').setData(c.context);
      map.setFilter('context-corridor',['all',['==',['get','kind'],'street'],['==',['get','name'],c.corridor]]);
      const all=[];
      for (const mode of Object.keys(labels)) {
        const r=d.routes[mode];
        const source = r.status==='ok'?{type:'FeatureCollection',features:[{type:'Feature',properties:{mode},geometry:r.geometry}]}:empty;
        map.getSource(`tunnel-${mode}`).setData(source);
        if(r.status==='ok') all.push(...r.geometry.coordinates);
      }
      markers.forEach(m=>m.remove()); markers=[];
      for (const [letter,p] of [['A',c.origin],['B',c.destination]]) {
        const marker=text('div',letter,'tunnel-marker'); marker.setAttribute('aria-label',`Punto ${letter}`);
        markers.push(new maplibregl.Marker({element:marker}).setLngLat(p).addTo(map)); all.push(p);
      }
      const bounds=new maplibregl.LngLatBounds(); all.forEach(p=>bounds.extend(p));
      map.fitBounds(bounds,{padding:55,maxZoom:17,duration:0});
      mapLabels();
      visibility();
      reviewer?.refresh();
    }
    $('tunnel-case').addEventListener('change',render);
    document.querySelectorAll('[data-tunnel-mode]').forEach(input=>input.addEventListener('change',()=>reviewer?reviewer.paint():visibility()));
    render();
    if (!window.maplibregl) {
      finishPageLoad(true);
      $('tunnel-map').textContent='El mapa no pudo cargarse. Las mediciones y descargas siguen disponibles.';
      return;
    }
    map=new maplibregl.Map({container:'tunnel-map',center:current().center,zoom:15,style:{version:8,
      sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#f5f5f0'}}]}});
    map.addControl(new maplibregl.NavigationControl(),'top-right');
    map.on('moveend',mapLabels);
    map.on('resize',mapLabels);
    SiteUI.watchMap(map, finishPageLoad);
    map.on('load',()=>{
      map.addSource('tunnel-context',{type:'geojson',data:empty,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · ODbL 1.0'});
      map.addLayer({id:'context-streets',type:'line',source:'tunnel-context',filter:['==',['get','kind'],'street'],paint:{'line-color':'#e0e0d8','line-width':['interpolate',['linear'],['zoom'],13,0.7,17,2,19,4]}});
      map.addLayer({id:'context-rail',type:'line',source:'tunnel-context',filter:['==',['get','kind'],'rail'],paint:{'line-color':'#999990','line-width':2,'line-dasharray':[2,5]}});
      map.addLayer({id:'context-corridor',type:'line',source:'tunnel-context',filter:['==',['get','name'],''],paint:{'line-color':'#a7a79e','line-width':['interpolate',['linear'],['zoom'],13,1.5,17,4,19,6]}});
      for(const mode of Object.keys(labels)) {
        map.addSource(`tunnel-${mode}`,{type:'geojson',data:empty});
        const paint={'line-color':colors[mode],'line-width':mode==='car'?7:mode==='walk'?5:3,'line-opacity':0.95};
        // Car is added first: pedestrian routes remain above it.
        map.addLayer({id:`tunnel-${mode}`,type:'line',source:`tunnel-${mode}`,paint});
      }
      ready=true;
      reviewer=window.createEndpointReviewer({map,current,markers:()=>markers,restoreLayers:visibility});
      render();
    });
  } catch(error) {finishPageLoad(true);
    $('tunnel-status').textContent=`No se pudieron cargar los recorridos. ${error.message}`;
  }
})();
