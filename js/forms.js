import { api } from './api.js';
import { e, heading, toast, showError, sourceReference } from './ui.js';

const DRAFT_KEY = 'source-culture-deliberate-draft-v1';
const prompts = ['measuring without a tool', 'remembering without writing', 'knowing when food is ready', 'a game learned by watching', 'organising turns', 'making something without written instructions'];
const titleCase = text => text.charAt(0).toUpperCase() + text.slice(1);
const field = (name, label, value = '', { required = false, type = 'text', hint = '', rows = false, readonly = false } = {}) => `<div class="field"><label for="f-${e(name)}">${e(label)}${required ? ' <span class="required" aria-label="required">*</span>' : ' <span class="muted">(optional)</span>'}</label>${rows ? `<textarea dir="auto" id="f-${e(name)}" name="${e(name)}" ${required ? 'required' : ''}>${e(value)}</textarea>` : `<input dir="auto" id="f-${e(name)}" name="${e(name)}" type="${type}" value="${e(value)}" ${required ? 'required' : ''} ${type === 'email' ? 'autocomplete="email"' : ''} ${readonly ? 'readonly' : ''}>`}${hint ? `<p class="hint">${e(hint)}</p>` : ''}</div>`;
const select = (name, label, value, options, required = false) => `<div class="field"><label for="f-${e(name)}">${e(label)}${required ? ' <span class="required">*</span>' : ''}</label><select name="${e(name)}" id="f-${e(name)}" ${required ? 'required' : ''}><option value="">choose one…</option>${options.map(v => `<option value="${e(v)}" ${v === value ? 'selected' : ''}>${e(titleCase(v))}</option>`).join('')}</select></div>`;
const check = (name, label, value, required = false) => `<label class="check-label"><input type="checkbox" name="${e(name)}" ${value ? 'checked' : ''} ${required ? 'required' : ''}><span>${e(label)}${required ? ' *' : ''}</span></label>`;

export function sourceFields(s, prefix, config, index = 0, removable = false) {
  const key = name => `${prefix}.${name}`;
  const f = (name, label, options = {}) => field(key(name), label, s[name], options);
  let specific = '';
  if (s.type === 'academic article' || s.type === 'thesis or dissertation') specific = `${f('doi', 'DOI')}${f('venue', 'journal, conference, or institution')}<div class="field-row">${f('volume', 'volume / issue')}${f('pages', 'page range')}</div>`;
  if (s.type === 'book or chapter') specific = `<div class="field-row">${f('publisher', 'publisher')}${f('edition', 'edition')}</div><div class="field-row">${f('chapter', 'chapter')}${f('isbn', 'ISBN')}</div>`;
  if (s.type === 'video' || s.type === 'podcast or audio') specific = `<div class="field-row">${f('platform', 'platform')}${f('duration', 'duration')}</div>`;
  if (s.type === 'interview or oral account') specific = `${f('interviewer', 'interviewer')}${f('recording', 'is a public recording available?', { hint: '“No public recording” is a valid answer. Never invent permission or a recording.' })}${check(key('oral_permission'), 'I have permission to share this oral account with the chosen speaker attribution, or I am sharing an anonymised reference I am entitled to share.', s.oral_permission, true)}`;
  if (s.type === 'other') specific = f('custom_type', 'describe the source type');
  return `<section class="reference-editor"><h3>${removable ? 'reference ' + (index + 1) : 'about the source'}</h3>${select(key('type'), 'what kind of source?', s.type, config.source_types, true)}${f('title', 'title or descriptive label', { required: true })}${f('creators', 'creator / author / channel / speaker', { hint: 'Leave blank if unknown. For an oral account, use the agreed attribution or “anonymous speaker”.' })}<div class="field-row">${f('date', 'publication date', { hint: 'A year, an approximate date, or blank if unknown.' })}${f('language', 'language')}</div>${f('url', 'original URL', { type: 'url', hint: 'Print and oral sources do not need a URL. For a video, you can include a timestamp in the link.' })}${specific}${f('annotation', 'why is this source relevant?', { rows: true, required: !removable })}${select(key('relation'), 'how does it connect?', s.relation || 'further reading or viewing', config.relationships, true)}${f('locator', 'page, chapter, section, or timestamp')}${removable ? select(key('block_id'), 'attach citation to this passage (optional)', s.block_id, ['story', 'account', 'judgement']) : ''}<details><summary>translation and access details (optional)</summary>${f('translation', 'translated title')}${f('access_date', 'date you accessed it', { type: 'date' })}</details>${removable ? `<button type="button" class="plain-button" data-remove-ref="${index}">remove this reference ×</button>` : ''}</section>`;
}

function preview(data, kind) {
  return `<div class="public-preview"><p class="eyebrow">public preview / ${e(kind)}</p><h2 dir="auto">${e(kind === 'source' ? data.source.title : data.title)}</h2><p>${e(data.summary)}</p><p class="small">shared by ${e(data.display_name || 'anonymous contributor')}</p>${data.original_name ? `<p dir="auto">${e(data.original_name)} · ${e(data.language)}</p>` : ''}${kind === 'source' ? `<p>${e(sourceReference(data.source))}</p><p>${e(data.source.annotation)}</p>` : `<h3>the story</h3><p>${e(data.context)}</p>${data.similar ? `<h3>what stays. what changes.</h3><p>${e(data.similar)}<br>${e(data.changes)}</p>` : ''}<h3>${kind === 'correction' ? 'suggested correction' : 'how it works'}</h3><p>${e(data.account)}</p>${data.materials ? `<p>materials: ${e(data.materials)}</p>` : ''}${data.steps ? `<p>${e(data.steps)}</p>` : ''}${data.judgement ? `<h3>how you know</h3><p>${e(data.judgement)}</p>` : ''}`}${data.references?.length ? `<h3>suggested references</h3>${data.references.map(r => `<p>${e(sourceReference(r))}<br>${e(r.relation)} · ${e(r.locator)}<br>${e(r.annotation)}</p>`).join('')}` : ''}${data.images?.map(m => `<figure class="article-media"><img src="data:${e(m.mime)};base64,${e(m.data)}" alt="${e(m.alt)}"><figcaption>${e(m.caption)} · ${e(m.credit)}</figcaption></figure>`).join('') || ''}<p class="notice">Your private email, access links, and editorial messages will never appear here. Publication is subject to review. Reuse choice: ${e(data.reuse || 'credit; no additional reuse licence')}.</p></div>`;
}

export async function contribute(root, config, navigate, user) {
  const params = new URLSearchParams(location.search);
  let kind = params.get('type') || (params.get('prompt') ? 'practice' : '');
  if (!kind) {
    const options = [ ['practice', '↗', 'share a project or practice', 'A familiar way of making, remembering, measuring, or getting things done.'], ['source', '↳', 'suggest a source', 'A paper, a video, a book, a conversation. Something that opens up a connection.'] ];
    root.innerHTML = `${heading('what do you know?', 'Something ordinary is a good place to start. You don’t need a theory, an academic reference, or a perfect explanation.', 'contribute / add a little to the notebook')}<div class="type-options">${options.map(([type, symbol, title, text]) => `<a href="/contribute?type=${type}" class="type-option"><span class="type-symbol" aria-hidden="true">${symbol}</span><h2>${title}</h2><p>${text}</p><span class="text-link small">start here ↗</span></a>`).join('')}</div><section class="prompt-picker"><h2>need a place to start?</h2><div class="filter-bar">${prompts.map(p => `<a class="filter-chip" href="/contribute?type=practice&prompt=${encodeURIComponent(p)}">${e(p)} ↗</a>`).join('')}</div></section><p class="small page-section"><a class="text-link" href="/manage">already shared something? manage your contributions ↗</a></p>`;
    return;
  }
  if (!['practice', 'variation', 'source', 'correction'].includes(kind)) throw new Error('This contribution type is unavailable.');
  let data = { kind, title: '', summary: '', relationship: '', references: [], images: [], tags: [], source: { type: '' }, display_name: '', reuse: 'credit; no additional reuse licence', prompt: params.get('prompt') || '', parent_id: params.get('parent') || '', target_id: params.get('target') || '', email: user?.email || '' };
  const editId = params.get('edit');
  let saved = null, parent = null;
  if (editId) {
    const existing = await api('/submissions/' + encodeURIComponent(editId));
    kind = existing.kind;
    data = { ...data, ...existing.content, kind, parent_id: existing.parent_id, target_id: existing.target_id, keep_media: existing.media.map(m => m.id), email: user?.email || '', images: [], publication_permission: false, rights_confirmation: false };
  } else {
    try { saved = JSON.parse(localStorage.getItem(DRAFT_KEY)); } catch {}
    if (saved?.kind === kind && saved.parent_id === data.parent_id && saved.target_id === data.target_id) {
      data = { ...data, ...saved, email: user?.email || '', images: [], publication_permission: false, rights_confirmation: false };
      toast('Your deliberately saved device draft has been restored. Images and private email were not stored.');
    }
  }
  if (data.parent_id || data.target_id) {
    const all = [...await api('/practices'), ...await api('/sources')];
    parent = all.find(x => x.id === (data.parent_id || data.target_id));
    if (!parent) throw new Error('The entry you are responding to is unavailable.');
  }
  const incoming = history.state?.contribution;
  if (!editId && incoming?.kind === kind) {
    if (typeof incoming.title === 'string') data.title = incoming.title;
    if (typeof incoming.account === 'string') data.account = incoming.account;
  }
  if (kind === 'variation' && !parent) throw new Error('Open a practice and choose “do you do this differently?” to begin a variation.');
  const labels = kind === 'practice' ? ['what you do', 'how you learned', 'how it works', 'attachments', 'sharing'] : kind === 'variation' ? ['your variation', 'attachments', 'sharing'] : kind === 'source' ? ['the source', 'sharing'] : ['the correction', 'sharing'];
  let step = 0, isPreview = false, disposed = false;
  function capture() {
    const form = root.querySelector('#contribution-form');
    if (!form) return;
    for (const input of form.querySelectorAll('[name]')) {
      if (input.type === 'file' || input.name === 'tags[]') continue;
      const value = input.type === 'checkbox' ? input.checked : input.value;
      const parts = input.name.split('.');
      if (parts[0] === 'ref') { data.references[Number(parts[1])][parts[2]] = value; }
      else if (parts[0] === 'source') { data.source[parts[1]] = value; }
      else if (parts[0] === 'image') { data.images[Number(parts[1])][parts[2]] = value; }
      else data[input.name] = value;
    }
    if (form.querySelector('[name="tags[]"]')) data.tags = Array.from(form.querySelectorAll('[name="tags[]"]:checked')).map(x => x.value);
  }
  const contextFields = () => `${select('relationship', 'what is your relationship to it?', data.relationship, ['personal experience', 'learned from someone', 'observation', 'source-based research'], true)}${field('context', 'tell us a little of the story', data.context, { rows: true, hint: 'Who taught you? What do you remember? Describe the context in your own terms.' })}<div class="field-row">${field('place', 'place (your own description)', data.place, { hint: 'An approximate place is enough. Exact locations are unnecessary.' })}${field('community', 'household, group, or community (your own terms)', data.community)}</div>`;
  const accountFields = () => `${field('account', 'describe what you do', data.account, { required: true, rows: true, hint: 'One concise written account is enough. If you attach media, describe what it shows here too.' })}<details><summary>add materials, steps, or signs of success (optional)</summary><div class="field">${field('materials', 'materials or tools', data.materials)}${field('steps', 'a sequence, if useful', data.steps, { rows: true, hint: 'One action per line. You do not have to make this a recipe.' })}${field('judgement', 'how do you know it is working?', data.judgement, { rows: true, hint: 'Think about adjustments, sensory cues, or things that are hard to put into words.' })}</div></details>`;
  function attachments() {
    return `<p class="intro">Firsthand accounts don’t need an academic citation. Source-based accounts need at least one identified source. Print and oral references can have no URL.</p>${data.references.map((r, i) => sourceFields(r, 'ref.' + i, config, i, true)).join('')}<button type="button" id="add-reference" class="button">add a source or media link +</button><div class="upload-box"><label for="image-upload">attach an image (optional)</label><p>JPEG, PNG, or WebP · up to 5 MB each · four images maximum. Private until the submission is published. Location metadata is stripped on the server.</p><input id="image-upload" type="file" accept="image/jpeg,image/png,image/webp" multiple>${data.keep_media?.length ? `<p>${data.keep_media.length} existing image(s) will be kept in this revision.</p>` : ''}${data.images.map((m, i) => `<div class="image-editor"><img src="data:${e(m.mime)};base64,${e(m.data)}" alt="Image attachment preview">${field('image.' + i + '.alt', 'describe the image for someone who cannot see it', m.alt, { required: true })}${field('image.' + i + '.caption', 'caption', m.caption)}${field('image.' + i + '.credit', 'creator credit', m.credit)}${check('image.' + i + '.permission', 'I have permission to publish this image, including identifiable people or private accounts where relevant.', m.permission, true)}<button type="button" class="plain-button" data-remove-image="${i}">remove image ×</button></div>`).join('')}</div>`;
  }
  const sharing = () => `${field('display_name', 'public name or pseudonym', data.display_name, { hint: 'Leave blank to be credited as “anonymous contributor”. No public profile is created.' })}${field('email', 'private email', data.email, { required: !user, type: 'email', readonly: !!user, hint: 'Only used for private access and editorial contact. Never shown on the public entry.' })}<div class="field">${select('reuse', 'permission for others to reuse your contribution', data.reuse, ['credit; no additional reuse licence', 'CC BY 4.0 — credit required', 'CC BY-SA 4.0 — credit and share alike'])}<p class="hint">Publication permission is separate from a reuse licence. This applies only to material you own, never to linked third-party works.</p></div>${check('publication_permission', 'I give Source Culture permission to publish this contribution after editorial review.', data.publication_permission, true)}${check('rights_confirmation', 'I am entitled to share this material and have permission for identifiable people or attributed private accounts. I have kept knowledge intended to remain private out of this submission.', data.rights_confirmation, true)}<p class="private-note">Your email stays private. You can revise your contribution or withdraw it through verified access. <a href="/about#privacy" class="text-link">privacy & sharing guidance ↗</a></p>`;
  const contentForStage = () => {
    const label = labels[step];
    if (label === 'what you do') return `${select('entry_type', 'what are you sharing?', data.entry_type || 'practice', ['project', 'practice', 'experiment'], true)}${field('title', 'what would you call it?', data.title, { required: true, hint: 'A familiar, descriptive name is a good place to start.' })}${field('summary', 'a short description', data.summary, { required: true, rows: true })}<div class="field-row">${field('original_name', 'original name', data.original_name)}${field('language', 'language', data.language)}</div><fieldset class="field"><legend>where might it belong? (optional)</legend>${config.activities.map(t => `<label class="check-label"><input type="checkbox" name="tags[]" value="${e(t)}" ${data.tags.includes(t) ? 'checked' : ''}>${e(t)}</label>`).join('')}</fieldset>${field('suggested_tags', 'suggest another term', data.suggested_tags, { hint: 'Separate terms with commas. No computational classification is required.' })}`;
    if (label === 'how you learned') return contextFields();
    if (label === 'how it works') return accountFields();
    if (label === 'your variation') return `${field('title', 'a name for your variation', data.title, { required: true })}${field('summary', 'a short description', data.summary, { required: true })}${field('similar', 'what is similar?', data.similar, { required: true, rows: true })}${field('changes', 'what changes in your version?', data.changes, { required: true, rows: true })}${contextFields()}${accountFields()}`;
    if (label === 'attachments') return attachments();
    if (label === 'the source') return sourceFields(data.source, 'source', config) + `<fieldset class="field"><legend>topics (optional)</legend>${config.activities.map(t => `<label class="check-label"><input type="checkbox" name="tags[]" value="${e(t)}" ${data.tags.includes(t) ? 'checked' : ''}>${e(t)}</label>`).join('')}</fieldset>`;
    if (label === 'the correction') return `${field('title', 'what needs a closer look?', data.title, { required: true })}${field('account', 'describe the correction and any supporting references', data.account, { required: true, rows: true })}${field('context', 'additional context', data.context, { rows: true })}`;
    return sharing();
  };
  function render() {
    if (disposed) return;
    root.innerHTML = `${heading(editId ? 'a new revision.' : kind === 'variation' ? 'another way of doing.' : kind === 'source' ? 'add a connection.' : kind === 'correction' ? 'help us get it right.' : 'share something you know.', 'A little context goes a long way. Write in your own words; we’ll read it with care.', editId ? 'contribute / revise your account' : 'contribute / ' + kind)}<div class="contribution-layout"><aside class="contribution-sidebar"><h2>a little at a time.</h2><ol class="step-list">${labels.map((label, i) => `<li ${step === i ? 'aria-current="step"' : ''}>${e(label)}</li>`).join('')}</ol><p>Nothing is published automatically. An editor reviews your account, its context, and your sharing preferences.</p>${config.mode === 'demo' ? '<p>Local demo: submissions are stored in SQLite on this server. Sign-in links go to a private development outbox, not to your inbox.</p>' : '<p>Your contribution stays private until it is reviewed. Request a sign-in link to manage it through your email.</p>'}</aside><section class="form-panel">${data.prompt ? `<p class="prompt-context">your starting question: <strong>${e(data.prompt)}</strong></p>` : ''}${parent ? `<p class="prompt-context">${kind === 'variation' ? 'your variation sits alongside' : 'connected to'}: <a class="text-link" href="/${parent.kind === 'source' ? 'sources' : 'practices'}/${e(parent.slug)}">${e(parent.title)} ↗</a></p>` : ''}<h2 tabindex="-1" id="stage-title">${isPreview ? 'take a look before sharing.' : kind !== 'practice' && step === 0 ? ({ source: 'tell us about the source.', variation: 'what changes in your version?', correction: 'what needs a closer look?' })[kind] : ['what do you do?', 'how did you learn it?', 'show how it works.', 'what would you like to attach?', 'how should it be shared?'][kind === 'practice' ? step : labels[step] === 'sharing' ? 4 : 3]}</h2><p data-error class="error" role="alert" tabindex="-1" hidden></p><form id="contribution-form">${isPreview ? preview(data, kind) : contentForStage()}<div class="form-nav"><button type="button" class="button" id="form-back">← ${isPreview ? 'back to sharing' : step ? 'back' : 'choose contribution type'}</button><button type="submit" class="button primary">${isPreview ? editId ? 'submit revision for review ↗' : 'submit for review ↗' : step === labels.length - 1 ? 'preview contribution ↗' : 'continue →'}</button></div></form><div class="draft-actions"><button type="button" class="plain-button" id="save-draft">save a draft on this device</button><button type="button" class="plain-button" id="clear-draft">clear device draft</button></div><p class="small muted">Device drafts are saved only when you choose. Private email, permission checkboxes, images, and sign-in credentials are excluded.</p></section></div>`;
    const form = root.querySelector('#contribution-form');
    form.addEventListener('input', capture);
    form.addEventListener('change', event => {
      capture();
      if (event.target.name?.endsWith('.type')) {
        const name = event.target.name;
        render();
        root.querySelector(`[name="${name}"]`).focus();
      }
    });
    form.addEventListener('submit', async event => {
      event.preventDefault(); capture();
      if (!isPreview) {
        if (labels[step] === 'attachments' && data.relationship === 'source-based research' && !data.references.length) { showError(root, new Error('Add at least one identified source for a source-based account. Print and oral references do not need a URL.')); return; }
        if (step < labels.length - 1) step++; else isPreview = true;
        render(); root.querySelector('#stage-title').focus(); return;
      }
      const submit = form.querySelector('[type=submit]'); submit.disabled = true;
      try {
        const payload = { ...data, title: kind === 'source' ? data.source.title : data.title, tags: [...new Set([...data.tags, ...(data.suggested_tags || '').split(',').map(t => t.trim()).filter(Boolean)])] };
        const result = await api(editId ? '/submissions/' + editId + '/revisions' : '/submissions', payload);
        try { localStorage.removeItem(DRAFT_KEY); } catch {}
        root.innerHTML = `<section class="confirmation"><span class="success-mark" aria-hidden="true">✳</span><p class="eyebrow">saved on this server / awaiting review</p><h1>thank you for adding<br>your bit.</h1><p>Your ${editId ? 'revision' : 'contribution'} has been saved. It is private while an editor reviews it.${editId ? ' The existing published version stays visible during review.' : ''}</p>${config.mode === 'demo' ? '<p class="notice">Local demo: no email has been sent. Request a private management link below; it will be written to the development outbox. After signing in, confirm this account and its sharing permissions before an editor can publish it.</p>' : '<p class="notice">Your contribution has been saved. Request a management link below to receive private email access. After signing in, confirm this specific account and its sharing permissions.</p>'}<p class="small">reference: ${e(result.id)} · this ID does not grant editing access.</p><p data-error class="error" role="alert" tabindex="-1" hidden></p><div class="button-row"><button class="button primary" id="request-management">request private management access ↗</button><a class="button" href="/explore">back to the collection ↗</a></div></section>`;
        root.querySelector('#request-management').addEventListener('click', async event => {
          const button = event.currentTarget; button.disabled = true;
          try { const result = await api('/auth/request', { email: data.email || user?.email }); toast(result.message); button.textContent = config.mode === 'demo' ? 'link requested — see the development outbox' : 'link requested — check your inbox'; }
          catch (error) { showError(root, error); button.disabled = false; }
        });
        window.scrollTo(0, 0); document.querySelector('#main').focus();
      } catch (error) { showError(root, error); submit.disabled = false; }
    });
    root.querySelector('#form-back').addEventListener('click', () => { capture(); if (isPreview) isPreview = false; else if (step) step--; else { navigate('/contribute'); return; } render(); root.querySelector('#stage-title').focus(); });
    root.querySelector('#add-reference')?.addEventListener('click', () => { capture(); data.references.push({ type: '', title: '', relation: 'further reading or viewing' }); render(); root.querySelector(`[name="ref.${data.references.length - 1}.type"]`).focus(); });
    root.querySelectorAll('[data-remove-ref]').forEach(button => button.addEventListener('click', () => { capture(); data.references.splice(Number(button.dataset.removeRef), 1); render(); }));
    root.querySelectorAll('[data-remove-image]').forEach(button => button.addEventListener('click', () => { capture(); data.images.splice(Number(button.dataset.removeImage), 1); render(); }));
    root.querySelector('#image-upload')?.addEventListener('change', async event => {
      capture();
      try {
        for (const file of event.target.files) {
          if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024 || data.images.length + (data.keep_media?.length || 0) >= 4) throw new Error('Use up to four JPEG, PNG, or WebP images, each smaller than 5 MB.');
          const raw = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file); });
          data.images.push({ data: raw.split(',')[1], mime: file.type, alt: '', caption: '', credit: '', permission: false });
        }
        render();
      } catch (error) { showError(root, error); }
    });
    root.querySelector('#save-draft').addEventListener('click', () => {
      capture(); const { email, images, publication_permission, rights_confirmation, keep_media, ...publicDraft } = data;
      publicDraft.source = { ...publicDraft.source, oral_permission: false };
      publicDraft.references = publicDraft.references.map(reference => ({ ...reference, oral_permission: false }));
      try { localStorage.setItem(DRAFT_KEY, JSON.stringify(publicDraft)); toast('Draft saved on this device. Private email and images are excluded.'); } catch { toast('Device storage is unavailable. Your work remains in this open form.'); }
    });
    root.querySelector('#clear-draft').addEventListener('click', () => { try { localStorage.removeItem(DRAFT_KEY); toast('The saved device draft has been cleared. Your open form is unchanged.'); } catch { toast('Device storage is unavailable.'); } });
  }
  render();
  return () => { disposed = true; };
}
