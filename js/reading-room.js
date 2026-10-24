import { mountColumnGrids } from './sketches/column-grids.js?v=prasa-background-grid-1';

// All columns remain in the document and in reading order. Expanding one changes
// its reading width and type size, rather than hiding its neighbours' content.
export function mountReadingRoom(root) {
  const cleanups = [];
  root.querySelectorAll('[data-reading-room]').forEach(room => {
    const columns = Array.from(room.querySelectorAll(':scope > [data-reading-column]'));
    cleanups.push(mountColumnGrids(columns));
    const pointer = matchMedia('(hover: hover) and (pointer: fine)');
    const desktop = matchMedia('(min-width: 901px)');
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

    function activate(column) {
      for (const candidate of columns) {
        const active = candidate === column;
        candidate.dataset.active = String(active);
        candidate.querySelector('[data-expand-column]').setAttribute('aria-pressed', String(active));
      }
      room.dataset.activeColumn = String(columns.indexOf(column));
    }

    for (const column of columns) {
      const enter = event => {
        const editing = document.activeElement;
        if (room.contains(editing) && editing.matches('input,textarea,select') && !column.contains(editing)) return;
        if (desktop.matches && pointer.matches && event.pointerType !== 'touch') activate(column);
      };
      const focus = () => activate(column);
      const click = () => {
        activate(column);
        if (!desktop.matches) column.scrollIntoView({ block: 'start', behavior: reducedMotion.matches ? 'instant' : 'smooth' });
      };
      column.addEventListener('pointerenter', enter);
      column.addEventListener('focusin', focus);
      column.querySelector('[data-expand-column]').addEventListener('click', click);
      cleanups.push(() => {
        column.removeEventListener('pointerenter', enter);
        column.removeEventListener('focusin', focus);
        column.querySelector('[data-expand-column]').removeEventListener('click', click);
      });
    }

    root.querySelectorAll('[data-column-jump]').forEach(button => {
      const target = root.querySelector('#' + button.dataset.columnJump);
      const column = columns.find(item => item.id === (target?.dataset.focusColumn || button.dataset.columnJump));
      if (!target || !column) return;
      const jump = () => {
        activate(column);
        column.querySelector('[data-expand-column]').focus({ preventScroll: true });
        target.scrollIntoView({ block: 'start', behavior: reducedMotion.matches ? 'instant' : 'smooth' });
      };
      button.addEventListener('click', jump);
      cleanups.push(() => button.removeEventListener('click', jump));
    });
    activate(columns[Number(room.dataset.initialColumn) || 0] || columns[0]);
  });
  return () => cleanups.forEach(dispose => dispose());
}
