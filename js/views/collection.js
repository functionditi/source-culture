import { api } from '../api.js';
import { e } from '../ui.js';
import { appURL } from '../paths.js';
import { browseHeader, browseSearch, filterSelect, bindBrowseSearch } from './browse.js';

export { notebookHome as home } from './notebook.js?v=prasa-background-grid-1';

function galleryEntry(entry) {
  const url = '/practices/' + encodeURIComponent(entry.slug);
  const media = entry.media?.[0];
  const projectImage = entry.placeholder === 'rice-grid' ? '/project-images/experiments-with-rice.JPG' : entry.placeholder === 'prasa' ? '/project-images/prasa-example.png' : '';
  const image = media?.url || (projectImage && appURL(entry.project_image || projectImage));
  const alt = media?.alt || (entry.placeholder === 'rice-grid' ? 'Hands arranging rice grains on a tray.' : 'Poetic text arranged across an olive background.');
  return `<article class="gallery-entry" data-notebook-entry>
    <a class="gallery-image" href="${e(url)}" aria-label="Read ${e(entry.title)}">${image ? `<img src="${e(image)}" alt="${e(alt)}" width="800" height="600" loading="lazy">` : `<span class="gallery-text-preview">${e(entry.summary || entry.title)}</span>`}</a>
    <h2><a href="${e(url)}" dir="auto">${e(entry.title)}</a></h2>
    ${entry.display_name ? `<p class="gallery-credit" dir="auto">${e(entry.display_name)}</p>` : ''}
    ${image && entry.summary ? `<p class="gallery-summary" dir="auto">${e(entry.summary)}</p>` : ''}
  </article>`;
}

export async function explore(root, config, navigate) {
  const params = new URLSearchParams(location.search);
  const tags = params.getAll('tag'), query = params.get('q') || '', sort = params.get('sort') || 'newest', view = ['project', 'practice', 'experiment'].includes(params.get('view')) ? params.get('view') : '';
  const entries = await api('/practices');
  const needle = query.toLocaleLowerCase();
  const matching = entries.filter(entry => (!needle || [entry.title, entry.summary, entry.original_name, entry.display_name, ...(entry.tags || [])].join(' ').toLocaleLowerCase().includes(needle)) && tags.every(tag => (entry.tags || []).includes(tag)) && (!view || (entry.entry_type || 'practice') === view));
  matching.sort((a, b) => String(b[sort === 'updated' ? 'updated_at' : 'created_at']).localeCompare(String(a[sort === 'updated' ? 'updated_at' : 'created_at'])));
  const limit = Math.max(6, Math.min(200, Number(params.get('limit')) || 12));
  const filtersActive = !!(tags.length || view || sort !== 'newest');
  const filtered = !!(query || filtersActive);
  const choosingVariation = params.get('choose') === 'variation';
  const filters = filterSelect('entry-type', 'view', 'Show', view, [['', 'Everything'], ['project', 'Projects'], ['practice', 'Practices'], ['experiment', 'Experiments']])
    + filterSelect('activity', 'tag', 'Topic', tags[0] || '', [['', 'All topics'], ...config.activities.map(tag => [tag, tag])])
    + filterSelect('sort', 'sort', 'Order', sort, [['newest', 'Newest additions'], ['updated', 'Recently updated']]);
  root.innerHTML = `<div class="browse-page explore-page">
    ${browseHeader('explore.', config.mode === 'static' ? null : { href: '/contribute?type=practice', label: 'Share something' })}
    ${choosingVariation ? '<p class="browse-note">Choose an entry to add your variation.</p>' : ''}
    ${browseSearch({ id: 'search-form', inputId: 'search', query, placeholder: 'Search the collection', filters, active: filtersActive, hidden: choosingVariation ? '<input type="hidden" name="choose" value="variation">' : '' })}
    <p class="browse-results-meta" role="status"><span>${matching.length} ${matching.length === 1 ? 'entry' : 'entries'}</span>${filtered ? `<a href="/explore${choosingVariation ? '?choose=variation' : ''}">Clear filters</a>` : ''}</p>
    ${matching.length ? `<div class="explore-gallery">${matching.slice(0, limit).map(galleryEntry).join('')}</div>${matching.length > limit ? '<button class="plain-button load-more" id="load-more">Show more</button>' : ''}` : '<div class="browse-empty empty"><h2>No matches yet.</h2><p>Try another search or clear the filters.</p></div>'}
  </div>`;
  bindBrowseSearch(root, 'search-form', '/explore', navigate);
  root.querySelector('#load-more')?.addEventListener('click', () => { params.set('limit', limit + 12); navigate('/explore?' + params, { scroll: false }); });
}
