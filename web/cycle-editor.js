'use strict';
window.CycleEditor={
  active:false,
  async init(map){
    const el=id=>document.getElementById(id),key='pacificando-cycle-draft-v1';
    let router, routes=[],active=0,markers=[],history=[],ready=false;
    const message=text=>{el('draw-status').textContent=text;};
    const snapshot=()=>JSON.stringify({routes,active});
    const remember=()=>{history.push(snapshot());if(history.length>50)history.shift();};
    const featureCollection=features=>({type:'FeatureCollection',features});
    const recalc=r=>{const result=router.route(r.points);return {name:r.name,...result};};
    function save(){try{localStorage.setItem(key,JSON.stringify({version:1,corridors:routes.map(r=>({name:r.name,points:r.points}))}));return true;}catch(e){message('No se pudo guardar en este navegador. Usá Descargar propuesta.');return false;}}
    function render(){
      map.getSource('my-routes').setData(featureCollection(routes.filter(r=>r.coordinates.length>1).map(r=>({type:'Feature',properties:{},geometry:{type:'LineString',coordinates:r.coordinates}}))));
      markers.forEach(m=>m.remove());markers=[];
      el('my-corridors').replaceChildren(...routes.map((r,i)=>new Option(`${r.name} · ${(r.length/1000).toLocaleString('es-AR',{maximumFractionDigits:2})} km`,String(i))));el('my-corridors').value=String(active);
      const visible=CycleEditor.active||el('show-draft').checked;
      map.setLayoutProperty('my-routes','visibility',visible?'visible':'none');
      const current=visible?routes[active]:null;
      if(current)current.points.forEach((p,i)=>{
        const button=document.createElement('button');button.className='draw-marker';button.textContent=String(i+1);button.setAttribute('aria-label',`Punto ${i+1}. Arrastrar para mover. Suprimir para eliminar.`);
        const marker=new maplibregl.Marker({element:button,draggable:CycleEditor.active}).setLngLat(p).addTo(map);markers.push(marker);button.setAttribute('aria-label',`Punto ${i+1}. Arrastrar para mover; Suprimir para eliminar.`);
        marker.on('dragend',()=>{const q=marker.getLngLat();modify(points=>{points[i]=[q.lng,q.lat];});});
        button.addEventListener('click',e=>e.stopPropagation());
        button.addEventListener('keydown',e=>{if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();modify(points=>points.splice(i,1));}});
      });
      el('draw-undo').disabled=!history.length;el('draw-delete').disabled=!routes[active];
      el('draw-export').disabled=!routes.length;el('my-corridors').disabled=!routes.length;
      el('draw-toggle').setAttribute('aria-pressed',String(CycleEditor.active));
      el('draw-toggle').textContent=CycleEditor.active?'Terminar dibujo':'Dibujar propuesta';
      map.getCanvas().style.cursor=CycleEditor.active?'crosshair':'';
      if(CycleEditor.active)map.doubleClickZoom.disable();else map.doubleClickZoom.enable();
      save();
    }
    function modify(change){
      const visible=CycleEditor.active||el('show-draft').checked;
      map.setLayoutProperty('my-routes','visibility',visible?'visible':'none');
      const current=visible?routes[active]:null;if(!current)return;
      const points=current.points.map(p=>[...p]);
      try{change(points);const next=recalc({...current,points});remember();routes[active]=next;render();message('Trazado actualizado. Se guarda automáticamente en este navegador.');}catch(e){render();message(e.message);}
    }
    function newRoute(){remember();routes.push(recalc({name:`Corredor ${routes.length+1}`,points:[]}));active=routes.length-1;CycleEditor.active=true;el('show-draft').checked=true;render();message('Marcá el inicio y luego los puntos por donde querés pasar. Arrastrá los puntos para corregirlos.');}
    function validate(value){
      if(value?.version!==1||!Array.isArray(value.corridors)||value.corridors.length>100)throw Error('El archivo no es una propuesta compatible.');
      let count=0;
      return value.corridors.map((r,i)=>{if(!Array.isArray(r.points)||(count+=r.points.length)>1000||r.points.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>typeof v!=='number'||!Number.isFinite(v))))throw Error('El archivo contiene puntos inválidos o demasiados puntos.');return recalc({name:typeof r.name==='string'?r.name.slice(0,80):`Corredor ${i+1}`,points:r.points});});
    }
    map.addSource('my-routes',{type:'geojson',data:featureCollection([])});
    map.addLayer({id:'my-routes',type:'line',source:'my-routes',layout:{'line-cap':'round','line-join':'round'},paint:{'line-color':'#6941b0','line-width':5}});
    try{const response=await fetch('../data/processed/cycle-routing.json?v=1');if(!response.ok)throw Error('No se pudo cargar el callejero para dibujar. Recargá para reintentar.');router=new CycleRouter(await response.json());ready=true;
      try{const stored=localStorage.getItem(key);if(stored)routes=validate(JSON.parse(stored));}catch(e){message('No se pudo restaurar el borrador anterior. Podés cargar un archivo guardado.');}
      ['draw-toggle','draw-new','draw-import'].forEach(id=>el(id).disabled=false);render();
      message(routes.length?'Borrador recuperado. Seleccioná un corredor para seguir editándolo.':'Activá Dibujar propuesta y marcá puntos sobre las calles.');
    }catch(e){message(e.message);return;}
    el('draw-toggle').onclick=()=>{if(!routes.length){newRoute();return;}CycleEditor.active=!CycleEditor.active;if(CycleEditor.active)el('show-draft').checked=true;render();message(CycleEditor.active?'Marcá puntos para continuar. Arrastrá los existentes para moverlos.':'Dibujo pausado. Tu propuesta permanece guardada.');};
    el('show-draft').onchange=()=>{if(!el('show-draft').checked)CycleEditor.active=false;render();};
    el('draw-panel').addEventListener('toggle',()=>{if(!el('draw-panel').open&&CycleEditor.active)el('draw-toggle').click();});
    el('draw-new').onclick=newRoute;
    el('my-corridors').onchange=()=>{active=Number(el('my-corridors').value);render();};
    el('draw-undo').onclick=()=>{const state=JSON.parse(history.pop());routes=state.routes;active=state.active;render();message('Último cambio deshecho.');};
    el('draw-delete').onclick=()=>{remember();routes.splice(active,1);active=Math.max(0,active-1);render();message('Corredor eliminado. Podés recuperarlo con Deshacer.');};
    el('draw-export').onclick=()=>{const payload={version:1,osm_date:router.osm_date,corridors:routes.map(r=>({name:r.name,points:r.points})),geometry:featureCollection(routes.filter(r=>r.coordinates.length>1).map(r=>({type:'Feature',properties:{name:r.name,length_m:r.length},geometry:{type:'LineString',coordinates:r.coordinates}})))};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='mi-propuesta-ciclovias.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message('Propuesta descargada. Conserva los puntos para futuras optimizaciones.');};
    el('draw-import').onclick=()=>el('draw-file').click();
    el('draw-file').onchange=async()=>{const file=el('draw-file').files[0];if(!file)return;try{if(file.size>5e6)throw Error('El archivo supera los 5 MB.');const imported=validate(JSON.parse(await file.text()));remember();routes=imported;active=0;el('show-draft').checked=true;render();message('Propuesta cargada y ajustada al callejero actual. Podés deshacer la carga.');}catch(e){message(e.message);}finally{el('draw-file').value='';}};
    this.add=lngLat=>{if(!ready||!CycleEditor.active)return;if(!routes.length)newRoute();modify(points=>{const p=router.nodes[router.nearest([lngLat.lng,lngLat.lat])];if(points.length&&points.at(-1)[0]===p[0]&&points.at(-1)[1]===p[1])throw Error('Ese punto ya es el último del corredor.');points.push(p);});};
  }
};
