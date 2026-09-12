/* Canvas composition keeps the map sharp without a DOM screenshot dependency. */
function selectionCaption(){
  return [[...document.querySelectorAll('[data-level][aria-pressed="true"]')].map(b=>b.textContent).join(' + '),
    $('avenue-label').textContent,$('direction-label').textContent,$('multiple').textContent,
    $('sector').value||'Todas las gestiones',$('commune').selectedOptions[0].textContent,
    $('review').checked?'Incluye ubicaciones aproximadas':'Solo por domicilio'];
}
function createShareImage(){
  if(!map||!loaded||!map.isSourceLoaded('selection')||!map.areTilesLoaded()||map.isMoving())throw Error('Esperá a que termine de cargar el mapa.');
  const canvas=document.createElement('canvas');canvas.width=1440;canvas.height=1060;
  const ctx=canvas.getContext('2d');ctx.fillStyle='#fafbf8';ctx.fillRect(0,0,1440,1060);
  const text=(value,x,y,font='20px system-ui',color='#163c2b')=>{ctx.font=font;ctx.fillStyle=color;ctx.fillText(value,x,y);};
  text('Calles escolares · Buenos Aires',40,58,'bold 32px system-ui');
  let x=40,y=102;ctx.font='18px system-ui';
  for(const label of selectionCaption()){
    const w=ctx.measureText(label).width+24;
    if(x+w>1400){x=40;y+=38;}
    ctx.fillStyle='#e3eade';ctx.fillRect(x,y-23,w,31);text(label,x+12,y,'18px system-ui');x+=w+10;
  }
  const top=y+32, mapWidth=900, mapHeight=760;
  const source=map.getCanvas(), ratio=Math.min(mapWidth/source.width,mapHeight/source.height);
  const width=source.width*ratio,height=source.height*ratio;
  ctx.fillStyle='#edf0e8';ctx.fillRect(40,top,mapWidth,mapHeight);
  ctx.drawImage(source,40+(mapWidth-width)/2,top+(mapHeight-height)/2,width,height);
  let metricY=top+10;
  document.querySelectorAll('#metrics .metric').forEach(metric=>{
    const label=metric.querySelector('.metric-head').textContent;
    const value=metric.querySelector('strong').textContent;
    const note=metric.querySelector('.bar-scale').textContent;
    text(label,980,metricY+20,'18px system-ui');
    ctx.fillStyle='#e3e6de';ctx.fillRect(980,metricY+34,420,44);
    ctx.fillStyle='#9bc5aa';ctx.fillRect(980,metricY+34,420*parseFloat(metric.querySelector('.bar-fill').style.width)/100,44);
    text(value,992,metricY+64,'bold 24px system-ui');
    text(note,980,metricY+103,'16px system-ui');metricY+=145;
  });
  const legendY=top+mapHeight+28;
  ctx.fillStyle='#79ae8c';ctx.fillRect(40,legendY-12,26,7);text('1 escuela',76,legendY,'17px system-ui');
  ctx.fillStyle='#3d8a61';ctx.fillRect(195,legendY-12,26,7);text('2 escuelas',231,legendY,'17px system-ui');
  ctx.fillStyle='#176044';ctx.fillRect(360,legendY-12,26,7);text('3 o más',396,legendY,'17px system-ui');
  text('Totales de la selección en CABA · mapa: vista actual',980,top+620,'16px system-ui');
  text('BA Data · CC-BY-2.5-AR · veredas 2019 · manzanas esquemáticas',40,1030,'16px system-ui');
  return new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(Error('No se pudo crear la imagen.')),'image/png'));
}
let shareURL;
$('copy-image').addEventListener('click',async()=>{
  const button=$('copy-image');button.disabled=true;$('copy-status').textContent='Preparando imagen…';$('save-image').hidden=true;
  let blobPromise;
  try{
    blobPromise=createShareImage();
    // Start clipboard write during the click gesture; encoding can finish asynchronously.
    if(!navigator.clipboard?.write||typeof ClipboardItem==='undefined')throw Error('clipboard unavailable');
    await navigator.clipboard.write([new ClipboardItem({'image/png':blobPromise})]);
    $('copy-status').textContent='Imagen copiada.';
  }catch(error){
    if(blobPromise){
      try{const blob=await blobPromise;if(shareURL)URL.revokeObjectURL(shareURL);shareURL=URL.createObjectURL(blob);$('save-image').href=shareURL;$('save-image').hidden=false;$('copy-status').textContent='No se pudo copiar. Podés descargarla.';}
      catch{$('copy-status').textContent='No se pudo crear la imagen. Intentá de nuevo.';}
    }else $('copy-status').textContent=error.message;
  }finally{button.disabled=false;}
});
