import { scopeLinks } from './paths.js';

let shown = false;

// Show once per page load, without interrupting filters or in-app navigation.
export function showWelcome(config) {
  if (shown) return () => { };

  const dialog = document.createElement('dialog');
  dialog.className = 'welcome-dialog';
  dialog.setAttribute('aria-labelledby', 'welcome-title');
  dialog.setAttribute('aria-describedby', 'welcome-message');
  dialog.innerHTML = `
    <button class="welcome-close" type="button" aria-label="Close welcome message">×</button>
    <h2 id="welcome-title"><span class="wordmark welcome-wordmark"><span class="wordmark-bracket">&lt;</span><span class="wordmark-source">source</span> <span class="wordmark-culture">culture</span><span class="wordmark-bracket">&gt;</span></span> is very much a work in progress.</h2>
    <p id="welcome-message">Feedback and contributions are very welcome!</p>
    <div class="welcome-links">${config.mode === 'static'
      ? '<a href="/about#participate">About contributing</a>'
      : '<a href="/contribute?type=correction&prompt=Feedback%20on%20Source%20Culture">Share feedback</a><a href="/contribute">Contribute</a>'}</div>
    <button class="welcome-continue" type="button" autofocus>Keep exploring!</button>`;
  scopeLinks(dialog);

  const remove = () => {
    document.documentElement.classList.remove('welcome-open');
    dialog.remove();
  };
  const close = () => dialog.close();
  dialog.querySelector('.welcome-close').addEventListener('click', close);
  dialog.querySelector('.welcome-continue').addEventListener('click', close);
  dialog.addEventListener('close', remove, { once: true });
  dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab' || event.ctrlKey || event.metaKey || event.altKey) return;
    const controls = [...dialog.querySelectorAll('button:not([disabled]), a[href]')];
    const current = controls.indexOf(document.activeElement);
    const next = current < 0 ? (event.shiftKey ? controls.length - 1 : 0) : (current + (event.shiftKey ? -1 : 1) + controls.length) % controls.length;
    event.preventDefault();
    controls[next].focus();
  });
  dialog.addEventListener('click', event => {
    if (event.target.closest('a[href]')) close();
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) close();
  });

  document.body.append(dialog);
  document.documentElement.classList.add('welcome-open');
  dialog.showModal();
  shown = true;

  return () => {
    if (dialog.open) dialog.close();
    remove();
  };
}
