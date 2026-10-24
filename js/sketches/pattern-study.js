// p5 instance mode; CSS is the single source of palette values.
export function mountPattern(root) {
  const host = root.querySelector('#pattern-canvas');
  const control = root.querySelector('#pattern-rule');
  const description = root.querySelector('#pattern-description');
  if (!host || !control) return () => {};
  let sketch, observer, disposed = false;
  const describe = () => { description.textContent = `Every ${control.value} marks, the direction changes. This is an illustrative pattern experiment, not a documented cultural practice.`; };
  describe();
  const start = () => {
    if (disposed || !window.p5) { if (!disposed) host.textContent = 'The optional visual is unavailable. Change the rule to read its description below.'; return; }
    const style = getComputedStyle(document.documentElement);
    const colors = ['--sand', '--rust', '--olive', '--caramel', '--slate', '--ink'].map(token => style.getPropertyValue(token).trim());
    sketch = new window.p5(p => {
      p.setup = () => { p.createCanvas(host.clientWidth, 178).parent(host); p.pixelDensity(Math.min(window.devicePixelRatio || 1, 2)); p.noLoop(); host.querySelector('canvas').setAttribute('aria-hidden', 'true'); };
      p.draw = () => {
        p.background(colors[0]);
        const size = 30, cols = Math.floor((p.width - 30) / size), rows = 4, rule = Number(control.value);
        const x0 = (p.width - cols * size) / 2, y0 = 29;
        for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
          const flip = Math.floor((x + y) / rule) % 2;
          p.push(); p.translate(x0 + x * size + size / 2, y0 + y * size + size / 2); p.rotate(flip ? Math.PI / 2 : 0);
          p.stroke(colors[5]); p.strokeWeight(1); p.fill(colors[flip ? 1 : 2]); p.rect(-11, -7, 22, 14, 7); p.pop();
        }
      };
    }, host);
    observer = new ResizeObserver(() => { if (sketch?.canvas) { sketch.resizeCanvas(host.clientWidth, 178); sketch.redraw(); } });
    observer.observe(host);
  };
  const update = () => { describe(); sketch?.redraw(); };
  control.addEventListener('input', update);
  if (document.readyState === 'complete') start(); else window.addEventListener('load', start, { once: true });
  return () => { disposed = true; window.removeEventListener('load', start); control.removeEventListener('input', update); observer?.disconnect(); sketch?.remove(); };
}
