(function(root){
  const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().replace(/[^A-Z0-9 ]/g,' ').split(/\s+/).filter(x=>x&&!['AV','AVENIDA','CALLE','PRES','GRAL','DR','INT','DE','DEL','LA','EL'].includes(x)).sort().join(' ');
  function find(rows,input){
    const match=input.trim().match(/^(.+?)\s+(\d+)\s*$/);
    if(!match)return {error:'Ingresá calle y altura. Ej.: Ayacucho 1670.'};
    const name=normalize(match[1]),number=Number(match[2]);
    if(!name||!number)return {error:'Ingresá calle y altura.'};
    const named=rows.filter(r=>normalize(r.street)===name||normalize(r.alias)===name);
    if(!named.length)return {error:'No encontramos esa calle. Usá el nombre completo.'};
    const matches=named.filter(r=>r.ranges.some(([a,b])=>a>0&&b>0&&number>=Math.min(a,b)&&number<=Math.max(a,b)&&(a%2!==b%2||number%2===a%2)));
    if(!matches.length)return {error:'No encontramos esa altura en el callejero.'};
    return {matches};
  }
  if(typeof module!=='undefined')module.exports={find,normalize};else root.SchoolAddressSearch={find,normalize};
})(globalThis);
