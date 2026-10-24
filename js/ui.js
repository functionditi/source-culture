export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
export const e = escapeHTML;
export function safeURL(value) {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : ''; } catch { return ''; }
}
export const date = value => value ? new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(value)) : 'date unknown';
export const link = (url, label) => safeURL(url) ? `<a href="${e(safeURL(url))}" target="_blank" rel="noopener noreferrer">${e(label)} ↗</a>` : '';
export function toast(message) {
  const target = document.querySelector('#toast');
  target.textContent = message;
  target.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { target.hidden = true; }, 4500);
}
export async function copy(text, trigger) {
  try { await navigator.clipboard.writeText(text); toast('Copied to your clipboard.'); }
  catch { const box = document.createElement('textarea'); box.value = text; trigger.after(box); box.focus(); box.select(); toast('Select and copy the text shown here.'); }
}
export function heading(title, description = '', eyebrow = 'the collective notebook') {
  return `<header class="page-heading"><p class="eyebrow">${e(eyebrow)}</p><h1>${e(title)}</h1>${description ? `<p>${e(description)}</p>` : ''}</header>`;
}
export function card(entry, index = 0) {
  const image = entry.media?.[0];
  const art = ['rice', 'knit', 'clap', 'route', 'turns', 'cups'].includes(entry.illustration) ? entry.illustration : null;
  const visual = image ? `<img src="${e(image.url)}" alt="${e(image.alt)}" loading="lazy" width="420" height="280">` : art ? `<img src="/assets/illustrations/${art}.svg" alt="" loading="lazy" width="420" height="290"><span class="image-label">illustration · fictional scenario</span>` : `<div class="text-art"><span class="star" aria-hidden="true">✳</span><blockquote>${e(entry.title)}</blockquote></div><span class="image-label">a written account</span>`;
  return `<article class="entry-card"><a class="media-link" href="/practices/${e(entry.slug)}" aria-label="Read ${e(entry.title)}">${visual}<span class="card-index" aria-hidden="true">${String(index + 1).padStart(2, '0')} ↗</span></a><div class="card-body"><div class="card-meta"><span>${entry.relationship === 'source-based research' ? 'source-based account' : 'personal account'}${entry.kind === 'variation' ? ' · variation' : ''}</span>${entry.demo ? '<span>illustrative demo</span>' : ''}</div><h3><a href="/practices/${e(entry.slug)}">${e(entry.title)}</a><span aria-hidden="true">↗</span></h3><p>${e(entry.summary)}</p><div class="card-bottom"><span>${e(entry.display_name)}</span><div class="card-tags">${(entry.tags || []).slice(0, 2).map(t => `<a class="tag" href="/explore?tag=${encodeURIComponent(t)}">${e(t)}</a>`).join('')}</div></div></div></article>`;
}
export function empty(title, text) {
  return `<div class="empty"><h2>${e(title)}</h2><p>${e(text)}</p><div class="button-row"><a class="button" href="/explore">reset the filters ↗</a><a class="button primary" href="/contribute">share something you know ↗</a></div></div>`;
}
export function sourceReference(source) {
  const s = source.source || source;
  return `${s.creators || 'creator unknown'}. “${s.title}.” ${s.venue || s.publisher || s.platform || s.custom_type || s.type}, ${s.date || 'date unknown'}.${s.locator ? ` ${s.locator}.` : ''}${s.url ? ` ${s.url}` : ''}${s.doi ? ` DOI: ${s.doi}` : ''}`;
}
export function showError(container, error) {
  const target = container.querySelector('[data-error]');
  target.textContent = error.message;
  target.hidden = false;
  target.focus();
}
