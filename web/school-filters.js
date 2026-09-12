(function(root){
  function select(data, filters){
    const levels=(filters.level||'').split(',').filter(Boolean);
    return data.features.flatMap(f=>{
      const p=f.properties;
      if(filters.noAvenues&&p.avenue||filters.oneWay&&!['CRECIENTE','DECRECIENTE'].includes(p.direction)) return [];
      const matches=p.schools.filter(link=>{
        const s=data.schools[link.id];
        return (filters.review||link.quality==='domicilio')&&(!levels.length||levels.some(level=>s.levels.includes(level)))&&(!filters.sector||s.sector===filters.sector)&&(!filters.commune||String(s.commune)===String(filters.commune));
      });
      return matches.length>=filters.minimum?[{...f,properties:{...p,matches}}]:[];
    });
  }
  function summarize(features,registry){
    const ids=new Set(features.flatMap(f=>f.properties.matches.map(s=>s.id)));
    const length=features.reduce((sum,f)=>sum+f.properties.length_m,0);
    const measured=features.filter(f=>Number.isFinite(f.properties.area_m2));
    return {blocks:features.length,establishments:ids.size,sites:new Set([...ids].map(id=>registry[id].site)).size,length,
      area:measured.reduce((sum,f)=>sum+f.properties.area_m2,0),
      measuredLength:measured.reduce((sum,f)=>sum+(f.properties.measured_length_m||0),0), measuredBlocks:measured.length};
  }
  const api={select,summarize};
  if(typeof module!=='undefined') module.exports=api; else root.SchoolFilters=api;
})(globalThis);
