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
      : 'No se pudo completar la carga. RecargÃ¡ la pÃ¡gina para reintentar.';
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
  document.addEventListener('DOMContentLoaded', render);
  return {begin, watchMap};
})();
