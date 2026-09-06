/* Independent from the corner pipeline: failures stay inside this subsection. */
(async function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const labels = {car:'Auto', walk:'A pie · más corto', step_free:'A pie · sin escaleras registradas'};
  const colors = {car:'#1466a3',walk:'#ab4b08',step_free:'#8036ad'};
  const fmt = n => Math.round(n).toLocaleString('es-AR');
  const empty = {type:'FeatureCollection',features:[]};
  let map, ready = false, markers = [], streetLabels = [];
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
    function visibility() {
      if (!ready) return;
      document.querySelectorAll('[data-tunnel-mode]').forEach(input => {
        map.setLayoutProperty(`tunnel-${input.dataset.tunnelMode}`,'visibility',input.checked?'visible':'none');
      });
    }
    function render() {
      const c=current(), direction=$('tunnel-direction').value, d=c.directions[direction];
      $('tunnels-heading').textContent=`${c.name} · mapa y análisis`;
      $('tunnel-endpoints').textContent = `A → B: ${c.endpoints}. Viendo ${direction==='outbound'?'ida (A → B)':'vuelta (B → A)'}. ${c.audit_status || 'Auditoría de campo pendiente'}`;
      $('tunnel-metrics').replaceChildren();
      for (const [mode,label] of Object.entries(labels)) {
        const r=d.routes[mode], card=text('article','','tunnel-metric');
        card.style.setProperty('--route',colors[mode]);
        card.append(text('h3',label));
        if (r.status!=='ok') {
          card.append(text('p','Sin ruta calculable','tunnel-distance'),text('p','La red o los extremos requieren revisión. No demuestra que el cruce sea imposible.','tunnel-detail'));
        } else {
          card.append(text('p',`${fmt(r.distance_m)} m`,'tunnel-distance'));
          card.append(text('p',mode==='car'?(d.valid_tunnel_crossing?'Referencia vehicular':'No atraviesa el túnel elegido'):r.extra_m==null?'Comparación no validada':`${r.extra_m>=0?'+':'−'}${fmt(Math.abs(r.extra_m))} m respecto al auto`,'tunnel-extra'));
          card.append(text('p',`${r.model_minutes.toLocaleString('es-AR')} min teóricos · ${r.turns_approx} giros aprox.`,'tunnel-detail'));
          if (mode!=='car') {
            card.append(text('p',`${r.step_way_count} tramos de escalera registrados · ${r.mapped_crossings} cruces mapeados`,'tunnel-detail'));
            if (r.wheelchair_no_way_count) card.append(text('p','Incluye tramos marcados como no aptos para silla de ruedas.','tunnel-detail'));
          }
          card.append(text('p',`Ajuste a la red: ${r.snap_m.map(n=>fmt(n)+' m').join(' / ')}`,'tunnel-detail'));
        }
        $('tunnel-metrics').append(card);
      }
      const finding=$('tunnel-finding'); finding.replaceChildren();
      const free=d.routes.step_free, walk=d.routes.walk;
      if (d.pedestrian_endpoints_comparable===false) finding.append(text('p','Las redes peatonales no pudieron usar extremos equivalentes. No se calcula el desvío sin escaleras; requiere revisar las conexiones.'));
      if (!d.valid_tunnel_crossing) finding.append(text('p','Comparación pendiente: la ruta vehicular no atraviesa el túnel seleccionado.'));
      else if (free.status==='ok' && walk.status==='ok' && d.step_free_penalty) {
        const penalty=d.step_free_penalty;
        finding.append(text('p','El costo de evitar las escaleras','tunnel-penalty-title'));
        finding.append(text('p',`+${fmt(penalty.extra_m)} m · +${fmt(penalty.extra_percent)}% de recorrido`,'tunnel-penalty-value'));
        finding.append(text('p','Diferencia frente al camino peatonal más corto. Es un esfuerzo adicional para quienes llevan cochecitos, acompañan una bicicleta o necesitan evitar escalones.'));
        finding.append(text('p',`OSM registra ${free.incline_way_count} tramos con pendiente en esta alternativa; puede haber más. Hace falta verificar las rampas, sus descansos y la posibilidad de pasar con una bicicleta.`));
      }
      if (c.id==='lacroze') finding.append(text('p','En Lacroze, el paso corto está marcado como no apto para silla de ruedas, pero OSM no detalla allí las escaleras. El conteo de cero no confirma su ausencia.'));
      if (c.id==='constituyentes') finding.append(text('p','Ubicación corregida: este itinerario cruza el Mitre junto a Monroe. El tramo Pareja–Asunción de la prueba inicial no atravesaba el ferrocarril.'));
      if (walk.status==='ok' && walk.implicit_sidewalk_m>0) finding.append(text('p',`${fmt(walk.implicit_sidewalk_m)} m del recorrido a pie usan calles cuya vereda se representa sobre el eje vial. Los cruces laterales requieren revisión.`));
      $('tunnel-provenance').replaceChildren(text('span',`OSM: ${c.snapshot_at || 'fecha no disponible'} · Método ${data.method_version}. Instantánea y parámetros conservados para reproducir el cálculo. `));
      const license=text('a','© OpenStreetMap contributors · ODbL 1.0'); license.href='https://www.openstreetmap.org/copyright'; $('tunnel-provenance').append(license);
      if (!ready) return;
      map.getSource('tunnel-context').setData(c.context);
      streetLabels.forEach(m=>m.remove()); streetLabels=[];
      const names=new Map();
      for(const f of c.context.features) {
        if(f.properties.kind!=='street' || !f.properties.name || f.properties.name===c.corridor) continue;
        const ps=f.geometry.coordinates, p=ps[Math.floor(ps.length/2)];
        const distance=Math.hypot((p[0]-c.center[0])*.82,p[1]-c.center[1]);
        if(distance<.004 && (!names.has(f.properties.name) || names.get(f.properties.name).distance>distance)) names.set(f.properties.name,{p,distance});
      }
      for(const [name,{p}] of [...names].sort((a,b)=>a[1].distance-b[1].distance).slice(0,7)) {
        const label=text('div',name.replace('Avenida ','Av. '),'tunnel-street-label');
        streetLabels.push(new maplibregl.Marker({element:label,anchor:'bottom-left',offset:[5,-5]}).setLngLat(p).addTo(map));
      }
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
      visibility();
    }
    $('tunnel-case').addEventListener('change',render);
    $('tunnel-direction').addEventListener('change',render);
    document.querySelectorAll('[data-tunnel-mode]').forEach(input=>input.addEventListener('change',visibility));
    render();
    if (!window.maplibregl) {
      $('tunnel-map').textContent='El mapa no pudo cargarse. Las mediciones y descargas siguen disponibles.';
      return;
    }
    map=new maplibregl.Map({container:'tunnel-map',center:current().center,zoom:15,style:{version:8,
      sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#f5f5f0'}}]}});
    map.addControl(new maplibregl.NavigationControl(),'top-right');
    map.on('load',()=>{
      map.addSource('tunnel-context',{type:'geojson',data:empty,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · ODbL 1.0'});
      map.addLayer({id:'context-streets',type:'line',source:'tunnel-context',filter:['==',['get','kind'],'street'],paint:{'line-color':'#b7b7ac','line-width':1}});
      map.addLayer({id:'context-rail',type:'line',source:'tunnel-context',filter:['==',['get','kind'],'rail'],paint:{'line-color':'#55554f','line-width':3,'line-dasharray':[3,2]}});
      for(const mode of Object.keys(labels)) {
        map.addSource(`tunnel-${mode}`,{type:'geojson',data:empty});
        const paint={'line-color':colors[mode],'line-width':mode==='car'?7:mode==='walk'?5:3,'line-opacity':0.95};
        if(mode==='step_free') paint['line-dasharray']=[3,2];
        map.addLayer({id:`tunnel-${mode}`,type:'line',source:`tunnel-${mode}`,paint});
      }
      ready=true; render();
    });
  } catch(error) {
    $('tunnel-status').textContent=`No se pudieron cargar los recorridos. ${error.message}`;
  }
})();
