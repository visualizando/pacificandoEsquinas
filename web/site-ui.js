/* Shared loading feedback. Each operation releases only its own token. */
window.SiteUI = (() => {
  const pending = new Set();
  let failed = false;
  function render() {
    const el = document.getElementById('site-loading');
    if (!el) return;
    el.hidden = !pending.size && !failed;
    el.classList.toggle('has-error', failed && !pending.size);
    el.querySelector('span').textContent = pending.size
      ? [...pending].at(-1).label
      : 'No se pudo completar la carga. Recargá la página para reintentar.';
  }
  function begin(label) {
    const token = {label};
    pending.add(token); render();
    let done = false;
    const timeout = setTimeout(() => finish(true), 90000);
    function finish(error = false) {
      if (done) return;
      done = true; clearTimeout(timeout); failed ||= error; pending.delete(token); render();
    }
    return finish;
  }
  function watchMap(map, finish) {
    const onIdle = () => { cleanup(); finish(); };
    const onError = () => { cleanup(); finish(true); };
    const timer = setTimeout(onError, 90000);
    function cleanup() {
      clearTimeout(timer); map.off('idle', onIdle); map.off('error', onError);
    }
    map.once('idle', onIdle); map.once('error', onError);
  }
  document.addEventListener('DOMContentLoaded', () => {
    render();
    const header = document.querySelector('.site-header');
    if (header) {
      const measure = () => document.documentElement.style.setProperty('--site-header-height', `${header.offsetHeight}px`);
      measure();
      new ResizeObserver(measure).observe(header);
    }
    const back = document.querySelector('[data-analysis-back]');
    if (!back || !document.referrer) return;
    const previous = new URL(document.referrer);
    const names = { 'index.html': 'los análisis', 'analisis.html': 'Pacificando esquinas', 'tuneles.html': 'Túneles antipeatonales', 'escuelas.html': 'Calles escolares', 'ciclovias.html': 'Red de ciclovías', 'report.html': 'las propuestas' };
    const file = previous.pathname.split('/').pop();
    const sameDirectory = previous.pathname.slice(0, previous.pathname.lastIndexOf('/')) === location.pathname.slice(0, location.pathname.lastIndexOf('/'));
    if (previous.origin === location.origin && sameDirectory && previous.pathname !== location.pathname && names[file]) {
      back.href = previous.href;
      back.querySelector('span').textContent = `← Volver a ${names[file]}`;
    }
  });
  return {begin, watchMap};
})();
