const finishschool_crashes = SiteUI.begin('Cargando análisis…');
(async()=>{
 const summary=document.getElementById('crash-summary');
 try{
  const response=await fetch('../data/processed/school-crashes.json?v=schools4');
  if(!response.ok)throw Error();
  const data=await response.json(), total=data.school_rows.length, affected=data.school_rows.filter(r=>r.events>0).length;
  const fmt=n=>n.toLocaleString('es-AR',{maximumFractionDigits:1});
  summary.textContent=`${fmt(affected)} de ${fmt(total)} escuelas analizadas (${fmt(affected/total*100)}%) tienen al menos un siniestro con víctimas registrado a 50 m o menos de alguna de sus cuadras entre las 07:00 y las 18:00 (2019–2025).`;
  const container=document.getElementById('crash-bars');
  for(const [label,predicate] of [['Sin siniestros con víctimas registrados',n=>n===0],['Entre 1 y 5 siniestros',n=>n>=1&&n<=5],['Entre 6 y 20 siniestros',n=>n>=6&&n<=20],['Más de 20 siniestros',n=>n>20]]){
   const count=data.school_rows.filter(r=>predicate(r.events)).length,row=document.createElement('div'),caption=document.createElement('p'),track=document.createElement('div'),fill=document.createElement('span');
   caption.textContent=`${label}: ${fmt(count)} escuelas · ${fmt(count/total*100)}%`;
   track.className='crash-track';fill.style.width=`${count/total*100}%`;track.append(fill);row.append(caption,track);container.append(row);
  }
  document.getElementById('crash-deaths').textContent=`${fmt(data.nearby_unique_events)} hechos distintos: ${fmt(data.nearby_severity.LEVE)} leves, ${fmt(data.nearby_severity.GRAVE)} graves y ${fmt(data.nearby_severity.MORTAL)} mortales.`;
  document.getElementById('crash-missing').textContent=`De ${data.events_total} siniestros con víctimas en esa franja en CABA, ${data.unlocated_events} no tienen coordenadas utilizables y quedan fuera del cruce. ${data.unknown_time_events} hechos sin hora válida también quedan fuera. ${data.unlinked_schools} escuela sin cuadra asignada queda fuera del análisis. Los resultados incluyen todas las escuelas vinculadas, sin aplicar los filtros de la propuesta.`;
 }catch(e){summary.textContent='No se pudo cargar el cruce vial. Recargá la página para reintentar.';}
})().finally(() => finishschool_crashes());
