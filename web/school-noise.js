const finishschool_noise = SiteUI.begin('Cargando análisis…');
/* Historical baseline, deliberately independent of proposal filters. */
(async () => {
  const summary = document.getElementById('noise-summary');
  try {
    const response = await fetch('../data/processed/school-noise.json');
    if (!response.ok) throw new Error('noise data unavailable');
    const data = await response.json();
    const rows = data.rows.filter(r => r.coverage_pct >= 80 && r.high_pct !== null);
    const high = rows.filter(r => r.high_pct >= 50).length;
    const number = n => n.toLocaleString('es-AR');
    summary.textContent = `${number(high)} de ${number(rows.length)} cuadras con cobertura suficiente tienen al menos la mitad de su recorrido con datos en zonas de 65 dBA o más.`;
    document.getElementById('noise-coverage').textContent = `Se muestran ${number(rows.length)} de ${number(data.rows.length)} cuadras: al menos el 80% de sus puntos debe tener datos. Las restantes no se consideran silenciosas; quedan fuera del gráfico.`;
    const svg = document.getElementById('noise-chart'), ns = 'http://www.w3.org/2000/svg';
    function el(tag, attrs, text) { const node = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k,v]) => node.setAttribute(k,v)); if (text) node.textContent = text; svg.append(node); return node; }
    const width = Math.max(360, Math.min(760, svg.clientWidth));
    svg.setAttribute('viewBox', `0 0 ${width} 300`);
    const right = width - 30;
    const max = Math.max(1, ...rows.map(r => r.schools));
    const x = v => 55 + v / 100 * (right - 55), y = v => 250 - v / max * 215;
    el('text', {x:55,y:17}, 'Escuelas por cuadra');
    for (let value=0; value<=max; value+=Math.max(1,Math.ceil(max/5))) {
      el('line', {x1:55,x2:right,y1:y(value),y2:y(value),stroke:'#e0e3de'});
      el('text', {x:45,y:y(value)+4,'text-anchor':'end'}, String(value));
    }
    for (const value of [0,25,50,75,100]) el('text', {x:x(value),y:271,'text-anchor':'middle'}, `${value}%`);
    el('text', {x:width/2,y:295,'text-anchor':'middle'}, 'Recorrido con datos en zonas ≥65 dBA');
    const points = rows.map(r => {
      el('circle', {cx:x(r.high_pct),cy:y(r.schools),r:3,fill:'#216a52','fill-opacity':.3});
      return {r,x:x(r.high_pct),y:y(r.schools)};
    });
    const highlight = el('circle', {r:5,fill:'none',stroke:'#102f22','stroke-width':2,visibility:'hidden'});
    const overlay = el('rect', {x:50,y:25,width:right-45,height:230,fill:'transparent'});
    const note = document.getElementById('noise-point');
    overlay.addEventListener('pointermove', event => {
      const point = new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());
      const nearest = points.reduce((best,p) => Math.hypot(p.x-point.x,p.y-point.y)<Math.hypot(best.x-point.x,best.y-point.y)?p:best,points[0]);
      if (!nearest) return;
      highlight.setAttribute('cx',nearest.x); highlight.setAttribute('cy',nearest.y); highlight.setAttribute('visibility','visible');
      note.textContent = `${nearest.r.street} · ${nearest.r.schools} escuelas · ${number(nearest.r.high_pct)}% del recorrido con datos ≥65 dBA`;
    });
    overlay.addEventListener('pointerleave', () => { highlight.setAttribute('visibility','hidden'); note.textContent='Cada punto representa una cuadra. Los puntos pueden superponerse.'; });
  } catch (error) { summary.textContent = 'No se pudo cargar el cruce de ruido. Recargá la página para reintentar.'; }
})().finally(() => finishschool_noise());
