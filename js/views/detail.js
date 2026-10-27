import { api } from '../api.js';
import { e, date, card, heading, sourceReference, copy, link } from '../ui.js';
import { projectMedia } from './notebook.js?v=prasa-background-grid-1';
import { referencesHTML, citeDisclosure, bindCitation, videoHTML, bindVideo } from '../citations.js';
import { appURL } from '../paths.js';
import { browseHeader, browseSearch, filterSelect, bindBrowseSearch } from './browse.js';

export async function practice(root, slug, navigate) {
  const [entry, all, sources] = await Promise.all([api('/practices/' + encodeURIComponent(slug)), api('/practices'), api('/sources')]);
  if (entry.redirect) { navigate('/practices/' + entry.redirect, { replace: true }); return; }
  const citationMarkers = block => (entry.citations || []).map((c, i) => c.block_id === block ? ` <a class="citation-ref" href="#reference-${i + 1}" aria-label="Source ${i + 1} for this passage">[${i + 1}]</a>` : '').join('');
  const parent = all.find(x => x.id === entry.parent_id);
  const variations = all.filter(x => x.parent_id === entry.id || (entry.parent_id && x.id === entry.parent_id));
  const related = all.filter(x => x.id !== entry.id && !variations.includes(x) && (x.tags || []).some(t => entry.tags?.includes(t))).slice(0, 3);
  const art = ['rice', 'knit', 'clap', 'route', 'turns', 'cups'].includes(entry.illustration) ? entry.illustration : '';
  const media = entry.media?.length ? entry.media.map(m => `<figure class="article-media"><img src="${e(m.url)}" alt="${e(m.alt)}"><figcaption>${e(m.caption)}${m.credit ? ' · credit: ' + e(m.credit) : ''}${m.licence ? ' · ' + e(m.licence) : ''}</figcaption></figure>`).join('') : entry.placeholder ? projectMedia(entry) : art ? `<figure class="article-media"><img src="${appURL('/assets/illustrations/' + art + '.svg')}" alt="A simple diagram for this fictional example."><figcaption>Original illustration · an illustrative scenario, not documentary evidence.</figcaption></figure>` : '';
  root.innerHTML = `<header class="page-heading article-head"><a class="eyebrow text-link" href="/explore">← back to the collection</a><h1 dir="auto">${e(entry.title)}</h1>${entry.original_name ? `<p dir="auto">${e(entry.original_name)}${entry.language ? ' · ' + e(entry.language) : ''}</p>` : ''}<p dir="auto">${e(entry.summary)}</p><div class="article-attribution"><span>${entry.editorial ? 'project by' : 'shared by'} ${e(entry.display_name)}</span><span>${date(entry.created_at)} · updated ${date(entry.updated_at)}</span><span>${entry.editorial ? 'editorial project listing' : entry.relationship === 'source-based research' ? 'source-based account' : 'personal account'}</span>${entry.demo && !entry.editorial ? '<span class="demo-label">local development example</span>' : ''}</div></header>${parent ? `<p class="notice">a variation of <a class="text-link" href="/practices/${e(parent.slug)}">${e(parent.title)} ↗</a> — another account, with its own author and context.</p>` : ''}<div class="article-layout"><article class="article-main">${media}${entry.fictional ? '<p class="notice">This is an invented development scenario. Attribution is fictional. It does not represent community testimony.</p>' : ''}${entry.context ? `<section id="story"><h2>the story</h2><p dir="auto">${e(entry.context)}${citationMarkers('story')}</p></section>` : ''}${entry.kind === 'variation' ? `<section><h2>what stays. what changes.</h2><p>${e(entry.similar)}</p><p>${e(entry.changes)}</p></section>` : ''}<section id="account"><h2>${e(entry.account_heading || 'how it works')}</h2>${entry.materials ? `<p><strong>what you need:</strong> ${e(entry.materials)}</p>` : ''}<p dir="auto">${e(entry.account)}${citationMarkers('account')}</p>${entry.steps ? `<ol>${entry.steps.split('\n').filter(Boolean).map(x => `<li>${e(x)}</li>`).join('')}</ol>` : ''}</section>${entry.judgement ? `<section id="judgement"><h2>how you know</h2><p dir="auto">${e(entry.judgement)}${citationMarkers('judgement')}</p></section>` : ''}${entry.interpretation ? `<section class="interpretation"><p class="eyebrow">one interpretation, open to correction</p><h2>a computational reading</h2><p>${e(entry.interpretation.text)}</p><p class="small">interpretation by ${e(entry.interpretation.author)}</p></section>` : ''}${entry.citations?.length ? `<section><h2>sources and connections</h2>${referencesHTML(entry, sources)}</section>` : ''}${citeDisclosure(entry)}</article><aside class="article-aside"><section><h2>filed under</h2><div class="card-tags">${entry.tags?.map(t => `<a class="tag" href="/explore?tag=${encodeURIComponent(t)}">${e(t)}</a>`).join('') || 'no tags yet'}</div><p class="small muted">Logic tags are interpretations, not universal classifications.</p></section><section><h2>there’s another way.</h2><p>A different measure? A small adjustment? Add your version alongside this one.</p><a class="button primary" href="/contribute?type=variation&parent=${e(entry.id)}">do you do this differently? ↗</a><a class="button" href="/contribute?type=source&target=${e(entry.id)}">suggest a source ↗</a><a class="button" href="/contribute?type=correction&target=${e(entry.id)}">suggest a correction ↗</a><button class="button" id="share-entry">share this entry ↗</button></section><section><h2>sharing with care</h2><p>${e(entry.reuse || 'Credit the contributor. No additional reuse licence has been granted.')}</p><a class="text-link" href="/about#sharing">read the sharing guidance ↗</a></section></aside></div>${variations.length ? `<section class="page-section"><div class="section-heading"><h2>another way to do it</h2><span class="small">linked variations</span></div><div class="entries-grid">${variations.map(card).join('')}</div></section>` : ''}${related.length ? `<section class="page-section"><div class="section-heading"><h2>a thread to follow</h2><span class="small">connected by shared activity or logic tags</span></div><div class="entries-grid">${related.map(card).join('')}</div></section>` : ''}`;
  bindCitation(root);
  root.querySelector('#share-entry').addEventListener('click', async event => { const data = { title: entry.title, url: location.href }; if (navigator.share) { try { await navigator.share(data); } catch {} } else await copy(location.href, event.currentTarget); });
  document.title = `${entry.title} — source culture`;
  document.querySelector('meta[name=description]').content = entry.summary;
}

export async function sources(root, config, navigate) {
  const params = new URLSearchParams(location.search), q = params.get('q') || '', type = params.get('type') || '', topic = params.get('topic') || '';
  const entries = await api('/sources');
  const themes = [
    { id: 'vernacular', label: 'Vernacular computing', tags: ['vernacular computing', 'vernacular digitality', 'poetry', 'language', 'cultural knowledge', 'games and play', 'homebrew', 'hardware hacking'] },
    { id: 'culture-power', label: 'Culture & power', tags: ['decolonial computing', 'knowledge', 'power', 'cosmotechnics', 'philosophy', 'technology'] },
  ];
  const theme = themes.find(item => item.id === params.get('theme'));
  const found = entries.filter(entry => (!theme || entry.tags?.some(tag => theme.tags.includes(tag.toLocaleLowerCase()))) && (!type || entry.source.type === type) && (!topic || entry.tags?.includes(topic)) && [entry.title, entry.source.creators, entry.source.annotation, ...(entry.tags || [])].join(' ').toLocaleLowerCase().includes(q.toLocaleLowerCase()));
  const availableFormats = new Set(entries.map(entry => entry.source.type));
  if (type) availableFormats.add(type);
  const controls = `<div class="source-filter-controls">
    <fieldset class="source-theme-filters"><legend>Theme</legend>${[{ id: '', label: 'All' }, ...themes].map(item => `<label class="source-theme"><input type="radio" id="source-theme-${item.id || 'all'}" name="theme" value="${item.id}" ${item.id === (theme?.id || '') ? 'checked' : ''}><span>${e(item.label)}</span></label>`).join('')}</fieldset>
    ${filterSelect('source-type', 'type', 'Format', type, [['', 'All formats'], ...config.source_types.filter(value => availableFormats.has(value)).map(value => [value, value])])}
  </div>`;
  root.innerHTML = `<div class="browse-page sources-page">
    ${browseHeader('sources.', config.mode === 'static' ? null : { href: '/contribute?type=source', label: 'Suggest a source' })}
    ${browseSearch({ id: 'source-search', inputId: 'q', query: q, placeholder: 'Search titles or authors', controls, hidden: topic ? `<input type="hidden" name="topic" value="${e(topic)}">` : '' })}
    <p class="browse-results-meta" role="status"><span>${found.length} ${found.length === 1 ? 'source' : 'sources'}${topic ? ' · ' + e(topic) : ''}</span>${q || type || topic || theme ? '<a href="/sources">Clear filters</a>' : ''}</p>
    <div class="source-list">${found.map(entry => {
      const source = entry.source;
      const year = source.date?.match(/\b\d{4}\b/)?.[0] || source.date;
      const metadata = [source.creators, year, source.custom_type || source.type].filter(Boolean).join(' · ');
      return `<article class="source-card"><h2 dir="auto"><a href="/sources/${e(entry.slug)}">${e(entry.title)}</a></h2><p class="source-byline" dir="auto">${e(metadata)}</p></article>`;
    }).join('')}</div>
    ${!found.length ? '<div class="browse-empty empty"><h2>No matches yet.</h2><p>Try another search or clear the filters.</p></div>' : ''}
  </div>`;
  bindBrowseSearch(root, 'source-search', '/sources', navigate);
}

export async function source(root, slug, navigate) {
  const [entry, practices] = await Promise.all([api('/sources/' + encodeURIComponent(slug)), api('/practices')]);
  if (entry.redirect) { navigate('/sources/' + entry.redirect, { replace: true }); return; }
  const s = entry.source;
  const linked = practices.flatMap(p => (p.citations || []).filter(c => c.source_id === entry.id).map(c => ({ p, c })));
  const fields = { 'creator / author / channel': s.creators || 'creator unknown', 'published': s.date || 'date unknown', 'language': s.language, 'DOI': s.doi, 'venue': s.venue, 'volume / issue': s.volume, 'pages': s.pages, 'publisher': s.publisher, 'edition': s.edition, 'chapter': s.chapter, 'ISBN': s.isbn, 'platform': s.platform, 'duration': s.duration, 'passage / timestamp': s.locator, 'interviewer': s.interviewer, 'recording': s.recording, 'accessed': s.access_date, 'translated title': s.translation };
  root.innerHTML = `${heading(entry.title, s.annotation, `${s.custom_type || s.type}${entry.demo && !entry.editorial ? ' / development example' : ''}`)}<div class="article-layout"><article class="article-main">${entry.fictional ? '<p class="notice">This source is an explicitly fictional internal scenario for testing citations. It is not a researched reference or a real oral account.</p>' : ''}<dl class="source-metadata">${Object.entries(fields).filter(([, v]) => v).map(([k, v]) => `<dt>${e(k)}</dt><dd dir="auto">${e(v)}</dd>`).join('')}</dl>${s.url ? `<p>${link(s.url, 'open the original source')}</p>` : '<p class="small">No public URL is supplied. Print and oral sources can be cited without a link.</p>'}${videoHTML(s)}<h2>connections to the collection</h2>${linked.length ? linked.map(({ p, c }) => `<section class="citation-connection"><h3><a class="text-link" href="/practices/${e(p.slug)}${c.block_id ? '#' + e(c.block_id) : ''}">${e(p.title)} ↗</a></h3><p>${e(c.relationship)}${c.locator ? ' · ' + e(c.locator) : ''}</p><p>${e(c.annotation)}</p></section>`).join('') : '<p>Not connected to a published practice yet. A source can stand on its own.</p>'}</article><aside class="article-aside"><section><h2>copy reference</h2><p id="source-reference" class="break-word">${e(sourceReference(entry))}</p><button id="copy-reference" class="button">copy reference ↗</button></section><section><h2>a note on relevance</h2><p>A source can document a technique without establishing its origin. Each connection explains what the source contributes to a particular account.</p></section><section><a class="button" href="/contribute?type=correction&target=${e(entry.id)}">suggest a correction ↗</a></section></aside></div>`;
  root.querySelector('#copy-reference').addEventListener('click', event => copy(sourceReference(entry), event.currentTarget)); bindVideo(root);
  document.title = `${entry.title} — source culture`;
}
