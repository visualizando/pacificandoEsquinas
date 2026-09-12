/* Shared, zero-based distance chart. Icons describe use cases, not extra routes. */
window.TunnelChart = (() => {
  const fmt=n=>Math.round(n).toLocaleString('es-AR');
  function el(tag,value,cls){const n=document.createElement(tag);if(value)n.textContent=value;if(cls)n.className=cls;return n;}
  function icon(mode){
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg'),path=document.createElementNS(ns,'path');
    svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('class','mode-icon');svg.setAttribute('aria-hidden','true');
    const shapes={car:'M3 16V10L6 4H18L21 10V16Z M3 10H21 M6 16V20 M18 16V20 M6 13H8 M16 13H18',walk:'M12 3a2 2 0 1 0 .01 0 M10 9L7 13H3 M10 9L15 10L19 14 M10 9L9 16L5 22 M9 16L15 18L17 22',bike:'M5 13a4 4 0 1 0 .01 0 M19 13a4 4 0 1 0 .01 0 M5 17L10 8L15 17H5 M10 8H16L19 17 M14 4H17L16 8 M8 8H12',step_free:'M3 3H6L9 15H19L22 8H8 M12 8V2C17 2 20 4 22 8 M10 19a2 2 0 1 0 .01 0 M18 19a2 2 0 1 0 .01 0'};
    path.setAttribute('d',shapes[mode]);path.setAttribute('fill','none');path.setAttribute('stroke','currentColor');path.setAttribute('stroke-width','1.5');path.setAttribute('stroke-linejoin','round');path.setAttribute('stroke-linecap','round');svg.append(path);return svg;
  }
  function penaltyColor(audit){
    if(audit?.comparison_usable!==true||!Number.isFinite(audit.extra_m))return '#92928c';
    return audit.extra_m<5?'#32965b':audit.extra_m<=50?'#edc949':'#d64b40';
  }
  function bars(d,maximum,modes=['car','walk','step_free']){
    const chart=el('div',null,'crossing-bars'),labels={car:'En auto',walk:'A pie · camino más corto',step_free:'A pie · sin escaleras'};
    for(const mode of modes){
      const r=d.routes[mode],row=el('div',null,'distance-row '+mode),caption=el('span',null,'distance-label');
      if(mode==='step_free')caption.append(icon('walk'),icon('bike'));
      caption.append(icon(mode),el('span',labels[mode]));
      const track=el('span',null,'distance-track'),bar=el('span',null,'distance-bar');
      track.setAttribute('aria-hidden','true');bar.style.width=(100*(r.status==='ok'?r.distance_m:0)/Math.max(maximum,1))+'%';track.append(bar);
      row.append(caption,el('span',r.status==='ok'?fmt(r.distance_m)+' m':'Sin cálculo','distance-value'),track);chart.append(row);
    }
    return chart;
  }
  function detail(c){
    const d=c.directions.outbound,a=d.endpoint_audit,box=el('div',null,'crossing-detail');
    const usable=a?.comparison_usable===true;
    box.append(el('p',!usable?'Comparación pendiente':a.extra_m>0?'Este cruce alarga el recorrido sin escaleras':a.extra_m<0?'El recorrido sin escaleras es más corto que en auto':'No se calcula un recorrido extra sin escaleras','detail-verdict'));
    if(usable){
      const sign=a.extra_m<0?'−':'+';
      box.append(el('p',`${sign}${fmt(Math.abs(a.extra_percent))}%`,'detail-percent'));
      box.append(el('p',`${fmt(Math.abs(a.extra_m))} metros ${a.extra_m<0?'menos':'más'} que en auto`,'detail-extra'));
    }else box.append(el('p','Hay que revisar los puntos o los accesos antes de afirmar cuánto penaliza al peatón.','detail-extra'));
    box.append(bars(d,Math.max(1,...Object.values(d.routes).map(r=>r.distance_m||0)),['car','walk','step_free']));
    if(usable && d.step_free_penalty?.extra_m>0)box.append(el('p',`Evitar las escaleras añade ${fmt(d.step_free_penalty.extra_m)} m al camino peatonal más corto.`,'detail-context'));
    box.append(el('p','Con cochecito o llevando la bici a pie, las escaleras pueden obligar a un rodeo. El perfil sin escaleras no certifica rampas accesibles ni una ruta para pedalear.','detail-note'));
    box.append(el('p','Estimación OpenStreetMap · mismos puntos A y B · distancias en metros','detail-source'));
    return box;
  }
  return {bars,detail,penaltyColor};
})();
