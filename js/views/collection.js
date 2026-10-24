import { api } from '../api.js';
import { e, heading, empty } from '../ui.js';
import { mountReadingRoom } from '../reading-room.js?v=prasa-background-grid-1';
import { notebookResults } from './notebook.js?v=prasa-background-grid-1';

const shorter = category => ({ 'remembering and recording': 'remembering', 'exchange and sharing': 'exchange & sharing', 'navigation and place': 'navigation & place', 'everyday coordination': 'coordination' }[category] || category);
const filterChips = (categories, selected, home = false) => `<div class="filter-bar" role="group" aria-label="Filter by activity"><button class="filter-chip" data-tag="" aria-pressed="${selected.length === 0}">all practices</button>${categories.map(t => `<button class="filter-chip" data-tag="${e(t)}" aria-pressed="${selected.includes(t)}">${e(shorter(t))}</button>`).join('')}</div>`;
function bindChips(root, params, navigate, home = false) {
  root.querySelectorAll('[data-tag]').forEach(button => button.addEventListener('click', () => {
    const tag = button.dataset.tag;
    const tags = new Set(home ? [] : params.getAll('tag'));
    if (!tag) tags.clear(); else if (tags.has(tag)) tags.delete(tag); else tags.add(tag);
    params.delete('tag'); tags.forEach(t => params.append('tag', t));
    params.delete('limit'); navigate('/explore' + (params.size ? '?' + params : ''), { scroll: false });
  }));
}
export { notebookHome as home } from './notebook.js?v=prasa-background-grid-1';
export async function explore(root, config, navigate) {
  const params = new URLSearchParams(location.search), tags = params.getAll('tag'), q = params.get('q') || '', sort = params.get('sort') || 'newest';
  const [entries, sources] = await Promise.all([api('/practices'), api('/sources')]);
  const needle = q.toLocaleLowerCase();
  const matching = entries.filter(x => (!needle || [x.title, x.summary, x.original_name, x.display_name, ...(x.tags || [])].join(' ').toLocaleLowerCase().includes(needle)) && tags.every(t => (x.tags || []).includes(t)));
  matching.sort((a, b) => String(b[sort === 'updated' ? 'updated_at' : 'created_at']).localeCompare(String(a[sort === 'updated' ? 'updated_at' : 'created_at'])));
  const limit = Math.max(6, Math.min(200, Number(params.get('limit')) || 6));
  root.innerHTML = `${heading('the things we know.', 'A pinch, a pattern, a way of finding your way. Explore the practices people carry through everyday life.', 'explore / the collection')}<section class="page-section">${params.get('choose') === 'variation' ? '<p class="notice">Choose an entry below and follow “add your variation” to share another way of doing it.</p>' : ''}<form id="search-form" class="search-row" role="search"><div class="search-field"><label for="search">look for a practice, a person, a familiar word</label><input id="search" type="search" name="q" value="${e(q)}" placeholder="try ‘measuring’, ‘memory’, ‘cooking’…"></div><div><label for="sort">order by</label><select id="sort" name="sort"><option value="newest" ${sort === 'newest' ? 'selected' : ''}>newest additions</option><option value="updated" ${sort === 'updated' ? 'selected' : ''}>recently updated</option></select></div><button class="button dark" type="submit">search ↗</button></form>${filterChips(config.activities, tags)}<div class="results-meta" aria-live="polite"><span>${matching.length} ${matching.length === 1 ? 'practice' : 'practices'}${tags.length ? ' · ' + tags.map(e).join(' + ') : ''}</span>${q || tags.length ? '<a class="text-link" href="/explore">clear search & filters ×</a>' : '<span>many ways of doing. no single right answer.</span>'}</div>${matching.length ? `${notebookResults(matching.slice(0, limit), sources, entries)}${matching.length > limit ? '<button class="button load-more" id="load-more">load more practices ↓</button>' : ''}` : empty('nothing here just yet.', 'Try another word, remove a filter, or add something the collection is missing.')}</section>`;
  bindChips(root, params, navigate);
  const search = root.querySelector('#search-form');
  const update = event => { event.preventDefault(); const data = new FormData(search); params.set('q', data.get('q')); params.set('sort', data.get('sort')); params.delete('limit'); navigate('/explore?' + params, { scroll: false }); };
  search.addEventListener('submit', update); root.querySelector('#sort').addEventListener('change', update);
  root.querySelector('#load-more')?.addEventListener('click', () => { params.set('limit', limit + 6); navigate('/explore?' + params, { scroll: false }); });
  return mountReadingRoom(root);
}
