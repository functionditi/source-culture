import { e, date, safeURL, sourceReference, copy, link } from './ui.js';
import { appURL } from './paths.js';

export function referencesHTML(entry, sources) {
  return `<ol class="reference-list">${(entry.citations || []).map((c, i) => {
    const source = sources.find(s => s.id === c.source_id);
    if (!source) return '';
    return `<li id="reference-${i + 1}"><a href="/sources/${e(source.slug)}">${e(source.title)}</a><p>${e(source.source.creators || 'creator unknown')} · ${e(source.source.date || 'date unknown')}</p><p><strong>${e(c.relationship)}</strong>${c.locator ? ' · ' + e(c.locator) : ''}</p><p>${e(c.annotation)}</p>${c.block_id ? `<a href="#${e(c.block_id)}" class="small">back to passage ↑</a>` : ''}</li>`;
  }).join('')}</ol>`;
}
export function citeDisclosure(entry) {
  return `<details class="citation-disclosure"><summary>cite this entry</summary><p id="entry-citation">${e(entry.display_name)}. “${e(entry.title)}.” Source Culture, ${date(entry.updated_at)}. Revision ${entry.revision}. ${e(location.origin + appURL('/practices/' + entry.slug))}</p><button class="button small" id="copy-citation">copy citation ↗</button></details>`;
}
export function bindCitation(root) {
  root.querySelector('#copy-citation')?.addEventListener('click', event => copy(root.querySelector('#entry-citation').textContent, event.currentTarget));
}
export function videoHTML(source) {
  if (source.type !== 'video' || !safeURL(source.url)) return '';
  const url = new URL(source.url), host = url.hostname.replace(/^www\./, '');
  const id = host === 'youtu.be' ? url.pathname.slice(1) : ['youtube.com', 'm.youtube.com'].includes(host) ? (url.searchParams.get('v') || url.pathname.match(/^\/(?:shorts|embed)\/([a-zA-Z0-9_-]+)/)?.[1]) : null;
  if (!id || !/^[\w-]{11}$/.test(id)) return '';
  const raw = url.searchParams.get('t') || source.locator || '', match = raw.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/);
  const stamp = /^\d+$/.test(raw) ? Number(raw) : match ? Number(match[1] || 0) * 3600 + Number(match[2] || 0) * 60 + Number(match[3] || 0) : /^\d+:\d{2}/.test(raw) ? raw.split(':').reduce((a, x) => a * 60 + Number(x), 0) : 0;
  return `<div class="video-placeholder" data-video="${e(id)}" data-start="${Math.min(stamp || 0, 86400)}"><p>Loading the video connects to YouTube. Nothing plays automatically. If the player is unavailable, use the original source link.</p><button class="button small" id="load-video">load video player ↗</button><p>${link(source.url, 'watch at the original source')}</p></div>`;
}
export function bindVideo(root) {
  root.querySelector('#load-video')?.addEventListener('click', event => {
    const host = event.currentTarget.closest('[data-video]');
    const iframe = document.createElement('iframe'); iframe.title = 'Source video — playback controlled by you'; iframe.src = `https://www.youtube-nocookie.com/embed/${host.dataset.video}?autoplay=0&start=${host.dataset.start}`; iframe.loading = 'lazy'; iframe.allowFullscreen = true; iframe.referrerPolicy = 'no-referrer';
    event.currentTarget.replaceWith(iframe);
  });
}
