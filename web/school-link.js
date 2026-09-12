function restoreSchoolLink(){
  const p=new URLSearchParams(location.hash.slice(1));
  for(const id of ['level','sector','commune','minimum']){
    if(!p.has(id))continue;
    const value=p.get(id);
    const allowed={level:['','inicial','primaria','secundaria','superior','otros'],sector:['','Estatal','Privada'],commune:['',...Array.from({length:15},(_,i)=>String(i+1))],minimum:['1','2','3']};
    if(id==='level')$(id).value=[...new Set(value.split(',').filter(v=>v&&allowed.level.includes(v)))].join(',');
    else if(allowed[id].includes(value))$(id).value=value;
  }
  for(const id of ['no-avenues','one-way','review'])if(p.has(id))$(id).checked=p.get(id)==='1';
}
function schoolLink(){
  const url=new URL(location.href),p=new URLSearchParams();
  for(const id of ['level','sector','commune','minimum'])p.set(id,$(id).value);
  for(const id of ['no-avenues','one-way','review'])p.set(id,$(id).checked?'1':'0');
  url.hash=p.toString();return url.href;
}
document.getElementById('copy-link').addEventListener('click',async()=>{
  const link=schoolLink();
  try{await navigator.clipboard.writeText(link);$('copy-status').textContent=['localhost','127.0.0.1'].includes(location.hostname)?'Enlace copiado · funciona en esta computadora.':'Enlace copiado.';}
  catch{$('copy-status').textContent=link;}
});
