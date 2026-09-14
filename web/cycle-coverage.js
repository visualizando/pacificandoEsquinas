'use strict';
window.CycleCoverage={
  mode:'off',
  async init(map, networkGeneratedAt){
    const status=document.getElementById('coverage-status'),legend=document.getElementById('coverage-legend');
    const toggle=document.getElementById('coverage-toggle');
    let popup,populationData;
    const measure=document.getElementById('histogram-measure');
    const near=document.createElement('span'),ramp=document.createElement('div'),far=document.createElement('span');
    near.textContent='Cerca · 0 m';far.textContent='Lejos · 1.000 m o más';ramp.className='coverage-ramp';ramp.setAttribute('aria-hidden','true');
    legend.replaceChildren(near,ramp,far);
    try{
      const response=await fetch('../data/processed/cycle-coverage.json?v=1',{cache:'no-store'});
      if(!response.ok)throw Error('No se pudo cargar la distancia por manzana. Recargá para reintentar.');
      const data=await response.json();
      if(data.metadata.network_generated_at!==networkGeneratedAt)throw Error('Las distancias requieren actualizarse para la nueva propuesta.');
      function histogram(){
        const field=measure.value||'population';
        CycleHistogram.render(populationData.features,{weightField:field});
        const source=document.getElementById('population-source');source.hidden=false;
        source.textContent='Población por radio censal: año pendiente de confirmar.';
        document.getElementById('histogram-method').textContent='Cada barra muestra el total de la población elegida. Los tonos claros indican mayor cercanía; el rojo oscuro, mayor distancia.';
        document.getElementById('distance-histogram').setAttribute('aria-label','Dos barras al 100% de población por distancia a ciclovías');
      }
      measure.addEventListener('change',histogram);
      map.addSource('coverage',{type:'geojson',data});
      map.addLayer({id:'coverage',type:'fill',source:'coverage',layout:{visibility:'none'},paint:{'fill-color':'#fff5f0'}},'block-edges');
      function change(){
        CycleCoverage.mode=toggle.checked?(document.getElementById('proposed').checked?'total':'current'):'off';
        const enabled=CycleCoverage.mode!=='off';
        map.setLayoutProperty('coverage','visibility',enabled?'visible':'none');legend.hidden=!enabled;
        if(popup)popup.remove();
        if(enabled){
          const field=CycleCoverage.mode==='current'?'current_m':'total_m';
          map.setPaintProperty('coverage','fill-color',['interpolate',['linear'],['get',field],0,'#fff5f0',500,'#fb6a4a',1000,'#b30000']);
        }
        status.textContent=enabled?`${CycleCoverage.mode==='current'?'Red actual':'Con la propuesta'} · Seleccioná una manzana para ver las distancias.`:'Sombreado apagado.';
      }
      this.update=change;toggle.disabled=false;toggle.addEventListener('change',change);change();
      this.select=e=>{
        if(this.mode==='off')return;
        const feature=map.queryRenderedFeatures(e.point,{layers:['coverage']})[0];if(!feature)return;
        const p=feature.properties,content=document.createElement('div'),title=document.createElement('h3');title.textContent=`Manzana ${p.block_id}`;content.append(title);
        const fmt=n=>Math.round(n).toLocaleString('es-AR');
        for(const text of [`Red actual: ${fmt(p.current_m)} m`,`Con la propuesta: ${fmt(p.total_m)} m`,`Se acerca ${fmt(p.current_m-p.total_m)} m con la propuesta.`,`Distancia aproximada en línea recta.`]){const para=document.createElement('p');para.textContent=text;content.append(para);}
        document.getElementById('selection').replaceChildren(content.cloneNode(true));
        if(popup)popup.remove();popup=new maplibregl.Popup().setLngLat(e.lngLat).setDOMContent(content).addTo(map);
      };
      try{
        const response=await fetch('../data/processed/cycle-population.json?v=1',{cache:'no-store'});
        if(!response.ok)throw Error('No se pudo cargar la población.');
        populationData=await response.json();
        if(populationData.metadata.network_generated_at!==networkGeneratedAt)throw Error('Es necesario recalcular las distancias de población.');
        measure.disabled=false;[...measure.options].forEach(option=>option.disabled=false);measure.value='population';histogram();
      }catch(e){const source=document.getElementById('population-source');source.hidden=false;source.textContent=e.message+' El análisis de manzanas sigue disponible.';document.getElementById('histogram-summary').textContent='Comparación de población no disponible.';}
    }catch(e){status.textContent=e.message;document.getElementById('histogram-summary').textContent=e.message;}
  }
};
