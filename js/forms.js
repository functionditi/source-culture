import { api } from './api.js';
import { e, heading, toast, showError, sourceReference } from './ui.js';
import { scopeLinks } from './paths.js';

const DRAFT_KEY = 'source-culture-deliberate-draft-v1';
const prompts = ['measuring without a tool', 'remembering without writing', 'knowing when food is ready', 'a game learned by watching', 'organising turns', 'making something without written instructions'];
const titleCase = text => text.charAt(0).toUpperCase() + text.slice(1);
const field = (name, label, value = '', { required = false, type = 'text', hint = '', rows = false, readonly = false } = {}) => `<div class="field"><label for="f-${e(name)}">${e(label)}${required || readonly ? '' : ' <span class="muted">(optional)</span>'}</label>${rows ? `<textarea dir="auto" id="f-${e(name)}" name="${e(name)}" ${required ? 'required' : ''} ${hint ? `aria-describedby="hint-${e(name)}"` : ''}>${e(value)}</textarea>` : `<input dir="auto" id="f-${e(name)}" name="${e(name)}" type="${type}" value="${e(value)}" ${required ? 'required' : ''} ${hint ? `aria-describedby="hint-${e(name)}"` : ''} ${type === 'email' ? 'autocomplete="email"' : ''} ${readonly ? 'readonly' : ''}>`}${hint ? `<p class="hint" id="hint-${e(name)}">${e(hint)}</p>` : ''}</div>`;
const select = (name, label, value, options, required = false) => `<div class="field"><label for="f-${e(name)}">${e(label)}</label><select name="${e(name)}" id="f-${e(name)}" ${required ? 'required' : ''}><option value="">choose one…</option>${options.map(v => `<option value="${e(v)}" ${v === value ? 'selected' : ''}>${e(titleCase(v))}</option>`).join('')}</select></div>`;
const check = (name, label, value, required = false) => `<label class="check-label"><input type="checkbox" name="${e(name)}" ${value ? 'checked' : ''} ${required ? 'required' : ''}><span>${e(label)}</span></label>`;
const disclosure = (id, label, content, open = false) => `<details data-disclosure="${e(id)}" ${open ? 'open' : ''}><summary>${e(label)}</summary>${content}</details>`;
// Reuse the contributor's opening words for collection listings when they do
// not supply a separate description. Existing descriptions survive revisions.
const summaryFor = data => data.summary?.trim() || data.account?.trim().split(/\n/)[0].slice(0, 240) || '';

export function sourceFields(s, prefix, config, index = 0, removable = false) {
  const key = name => `${prefix}.${name}`;
  const f = (name, label, options = {}) => field(key(name), label, s[name], options);
  let specific = '';
  if (s.type === 'academic article' || s.type === 'thesis or dissertation') specific = `${f('doi', 'DOI')}${f('venue', 'journal, conference, or institution')}<div class="field-row">${f('volume', 'volume / issue')}${f('pages', 'page range')}</div>`;
  if (s.type === 'book or chapter') specific = `<div class="field-row">${f('publisher', 'publisher')}${f('edition', 'edition')}</div><div class="field-row">${f('chapter', 'chapter')}${f('isbn', 'ISBN')}</div>`;
  if (s.type === 'video' || s.type === 'podcast or audio') specific = `<div class="field-row">${f('platform', 'platform')}${f('duration', 'duration')}</div>`;
  if (s.type === 'interview or oral account') specific = `${f('interviewer', 'interviewer')}${f('recording', 'public recording', { hint: 'Leave blank if there is no public recording.' })}`;
  if (s.type === 'other') specific = f('custom_type', 'describe the source type');
  return `<section class="reference-editor">${removable ? `<h3>reference ${index + 1}</h3>` : ''}${select(key('type'), 'what kind of source?', s.type, config.source_types, true)}${f('title', 'title or descriptive label', { required: true })}${f('url', 'link', { type: 'url' })}${f('annotation', 'why are you sharing it?', { rows: true, required: !removable })}${s.type === 'interview or oral account' ? check(key('oral_permission'), 'I have permission to share this oral account with the agreed attribution, or an anonymised reference I am entitled to share.', s.oral_permission, true) : ''}${disclosure(prefix + '-details', 'Add citation details', `${f('creators', 'author, creator, or speaker', { hint: 'Use the agreed attribution for an oral account.' })}<div class="field-row">${f('date', 'publication date')}${f('language', 'language')}</div>${specific}${select(key('relation'), 'how does it connect?', s.relation || 'further reading or viewing', config.relationships, true)}${f('locator', 'page, chapter, or timestamp')}${removable ? select(key('block_id'), 'attach to a passage', s.block_id, ['story', 'account', 'judgement']) : ''}${f('translation', 'translated title')}${f('access_date', 'date accessed', { type: 'date' })}`)}${removable ? `<button type="button" class="plain-button" data-remove-ref="${index}">remove reference</button>` : ''}</section>`;
}

function preview(data, kind) {
  return `<div class="public-preview">
    <h3 dir="auto">${e(kind === 'source' ? data.source.title : data.title)}</h3>
    <p class="small" data-preview-credit>shared by ${e(data.display_name || 'anonymous contributor')}</p>
    ${data.summary ? `<p>${e(data.summary)}</p>` : ''}
    ${data.original_name ? `<p dir="auto">${e(data.original_name)}${data.language ? ' · ' + e(data.language) : ''}</p>` : ''}
    ${kind === 'source' ? `<p>${e(sourceReference(data.source))}</p><p>${e(data.source.annotation)}</p>` : `
      ${data.context ? `<h4>the story</h4><p>${e(data.context)}</p>` : ''}
      ${data.similar ? `<h4>what stays. what changes.</h4><p>${e(data.similar)}<br>${e(data.changes)}</p>` : ''}
      <p>${e(data.account)}</p>
      ${data.materials ? `<p>materials: ${e(data.materials)}</p>` : ''}
      ${data.steps ? `<p>${e(data.steps)}</p>` : ''}
      ${data.judgement ? `<h4>how you know</h4><p>${e(data.judgement)}</p>` : ''}`}
    ${data.references?.length ? `<h4>references</h4>${data.references.map(r => `<p>${e(sourceReference(r))}<br>${e(r.annotation)}</p>`).join('')}` : ''}
    ${data.images?.map(m => `<figure class="article-media"><img src="data:${e(m.mime)};base64,${e(m.data)}" alt="${e(m.alt)}"><figcaption>${e(m.caption)}${m.credit ? ' · ' + e(m.credit) : ''}</figcaption></figure>`).join('') || ''}
    <p class="small" data-preview-reuse>reuse: ${e(data.reuse)}</p>
  </div>`;
}

export async function contribute(root, config, navigate, user) {
  const params = new URLSearchParams(location.search);
  let kind = params.get('type') || (params.get('prompt') ? 'practice' : '');
  if (!kind) {
    root.innerHTML = `<div class="contribution-page">
      ${heading('share something you know.', 'An everyday practice, a project, or something worth reading.', 'contribute')}
      <nav class="contribution-choices" aria-label="What would you like to share?">
        <a href="/contribute?type=practice">Share a project or practice</a>
        <a href="/contribute?type=source">Suggest a source</a>
      </nav>
      <p>Contributions are reviewed before publication. Choose how you’d like to be credited, and share only material you have permission to make public.</p>
      ${disclosure('ideas', 'Need an idea?', `<ul class="contribution-prompts">${prompts.map(p => `<li><a href="/contribute?type=practice&prompt=${encodeURIComponent(p)}">${e(p)}</a></li>`).join('')}</ul>`)}
      <p class="contribution-manage"><a href="/manage">Manage your contributions</a></p>
    </div>`;
    scopeLinks(root);
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
  const hasContext = ['practice', 'variation'].includes(kind);
  const labels = hasContext ? ['your contribution', 'add context', 'review & share'] : [kind === 'source' ? 'the source' : 'the correction', 'review & share'];
  const openDetails = new Set();
  let step = 0, disposed = false;
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
    const credit = form.querySelector('[data-preview-credit]');
    if (credit) credit.textContent = 'shared by ' + (data.display_name || 'anonymous contributor');
    const reuse = form.querySelector('[data-preview-reuse]');
    if (reuse) reuse.textContent = 'reuse: ' + data.reuse;
  }
  const contextFields = () => `${field('context', 'a little of the story', data.context, { rows: true, hint: 'Who taught you? Where did it start?' })}<div class="field-row">${field('place', 'place', data.place)}${field('community', 'household, group, or community', data.community)}</div><div class="field-row">${field('original_name', 'original name', data.original_name)}${field('language', 'language', data.language)}</div>${select('entry_type', 'file as', data.entry_type || 'practice', ['project', 'practice', 'experiment'])}${field('summary', 'short description for the collection', data.summary, { hint: 'Leave blank to use the beginning of your account.' })}`;
  const accountDetails = () => `${field('materials', 'materials or tools', data.materials)}${field('steps', 'steps', data.steps, { rows: true, hint: 'One action per line, if useful.' })}${field('judgement', 'how do you know it is working?', data.judgement, { rows: true })}`;
  function attachments() {
    return `${data.relationship === 'source-based research' ? '<p class="intro">Add at least one source for a research-based account. A link is optional.</p>' : ''}${data.references.map((r, i) => sourceFields(r, 'ref.' + i, config, i, true)).join('')}<button type="button" id="add-reference" class="plain-button">Add a source or media link</button><div class="upload-box"><label for="image-upload">Attach images</label><p id="image-upload-hint">JPEG, PNG, or WebP · up to 5 MB each · four maximum.</p><input id="image-upload" type="file" accept="image/jpeg,image/png,image/webp" multiple aria-describedby="image-upload-hint">${data.keep_media?.length ? `<p>${data.keep_media.length} existing image(s) will be kept.</p>` : ''}${data.images.map((m, i) => `<div class="image-editor"><img src="data:${e(m.mime)};base64,${e(m.data)}" alt="Image attachment preview">${field('image.' + i + '.alt', 'describe the image for someone who cannot see it', m.alt, { required: true })}${field('image.' + i + '.caption', 'caption', m.caption)}${field('image.' + i + '.credit', 'creator credit', m.credit)}${check('image.' + i + '.permission', 'I have permission to publish this image, including identifiable people or private accounts.', m.permission, true)}<button type="button" class="plain-button" data-remove-image="${i}">remove image</button></div>`).join('')}</div>`;
  }
  const sharing = () => `${field('display_name', 'name or pseudonym for credit', data.display_name, { hint: 'Leave blank for “anonymous contributor”.' })}${field('email', 'private email', data.email, { required: !user, type: 'email', readonly: !!user, hint: 'For private access and editorial contact.' })}${select('reuse', 'may others reuse your contribution?', data.reuse, ['credit; no additional reuse licence', 'CC BY 4.0 — credit required', 'CC BY-SA 4.0 — credit and share alike'], true)}<p class="hint">Applies only to material you own. Linked sources keep their own terms.</p>${check('publication_permission', 'Source Culture may publish this contribution after review.', data.publication_permission, true)}${check('rights_confirmation', 'I have the right and any necessary permissions to share this material. I have left out knowledge intended to stay private.', data.rights_confirmation, true)}<p class="private-note"><a href="/about#privacy">Privacy & sharing</a> · You can revise or withdraw your contribution.</p>`;
  const contentForStage = () => {
    const label = labels[step];
    if (label === 'your contribution') return `${field('title', 'what would you call it?', data.title, { required: true })}${field('account', 'tell us about it', data.account, { required: true, rows: true })}${kind === 'variation' ? `${field('similar', 'what is similar?', data.similar, { required: true, rows: true })}${field('changes', 'what changes in your version?', data.changes, { required: true, rows: true })}` : ''}`;
    if (label === 'add context') return `${select('relationship', 'how do you know about it?', data.relationship, ['personal experience', 'learned from someone', 'observation', 'source-based research'], true)}${disclosure('context', 'Add the story or original name', contextFields())}${disclosure('account-details', 'Add materials, steps, or signs of success', accountDetails())}${disclosure('attachments', 'Add images or sources', attachments(), data.relationship === 'source-based research')}`;
    if (label === 'the source') return sourceFields(data.source, 'source', config);
    if (label === 'the correction') return `${field('title', 'what needs a closer look?', data.title, { required: true })}${field('account', 'tell us what needs correcting', data.account, { required: true, rows: true })}${disclosure('context', 'Add context', field('context', 'additional context', data.context, { rows: true }))}`;
    return `${disclosure('preview', 'Preview your contribution', preview(data, kind))}${sharing()}<p class="review-note">Reviewed before publication. Your email stays private.</p>`;
  };
  function render() {
    if (disposed) return;
    root.querySelectorAll('details[data-disclosure]').forEach(detail => {
      if (detail.open) openDetails.add(detail.dataset.disclosure);
      else openDetails.delete(detail.dataset.disclosure);
    });
    const finalStage = step === labels.length - 1;
    const title = editId ? 'revise your contribution.' : kind === 'variation' ? 'add your variation.' : kind === 'source' ? 'suggest a source.' : kind === 'correction' ? 'suggest a correction.' : 'share something you know.';
    root.innerHTML = `<div class="contribution-page">
      <header class="page-heading">
        <p class="contribution-progress" id="contribution-progress-label">${step + 1} of ${labels.length}</p>
        <progress class="contribution-progress-bar" value="${step + 1}" max="${labels.length}" aria-labelledby="contribution-progress-label" aria-valuetext="${step + 1} of ${labels.length}: ${e(labels[step])}"></progress>
        <h1 tabindex="-1" id="stage-title">${e(step ? labels[step] + '.' : title)}</h1>
      </header>
      <section class="form-panel" aria-labelledby="stage-title">
        ${data.prompt ? `<p class="prompt-context">${e(data.prompt)}</p>` : ''}
        ${parent ? `<p class="prompt-context">${kind === 'variation' ? 'a variation of' : 'connected to'} <a href="/${parent.kind === 'source' ? 'sources' : 'practices'}/${e(parent.slug)}">${e(parent.title)}</a></p>` : ''}
        <p data-error class="error" role="alert" tabindex="-1" hidden></p>
        <form id="contribution-form">
          ${contentForStage()}
          <div class="form-nav">
            <button type="button" class="plain-button" id="form-back">${step ? 'Back' : 'Choose contribution type'}</button>
            <button type="submit" class="button primary">${finalStage ? editId ? 'Submit revision for review' : 'Submit for review' : 'Continue'}</button>
          </div>
        </form>
        ${disclosure('draft', 'Draft options', `<div class="draft-actions"><button type="button" class="plain-button" id="save-draft">Save on this device</button><button type="button" class="plain-button" id="clear-draft">Clear saved draft</button></div><p class="hint">Saved only when you choose. Private email, images, permissions, and sign-in details are excluded.</p>`)}
      </section>
    </div>`;
    root.querySelectorAll('details[data-disclosure]').forEach(detail => {
      if (openDetails.has(detail.dataset.disclosure)) detail.open = true;
    });
    const form = root.querySelector('#contribution-form');
    scopeLinks(root);
    form.addEventListener('input', capture);
    // Reveal any collapsed fields before native validation moves focus to them.
    form.addEventListener('invalid', event => {
      for (let detail = event.target.closest('details'); detail; detail = detail.parentElement.closest('details')) detail.open = true;
    }, true);
    form.addEventListener('change', event => {
      capture();
      if (event.target.name?.endsWith('.type') || event.target.name === 'relationship') {
        const name = event.target.name;
        render();
        root.querySelector(`[name="${name}"]`).focus();
      }
    });
    form.addEventListener('submit', async event => {
      event.preventDefault(); capture();
      if (!finalStage) {
        if (labels[step] === 'add context' && data.relationship === 'source-based research' && !data.references.length) { showError(root, new Error('Add at least one identified source for a source-based account. Print and oral references do not need a URL.')); return; }
        step++;
        render(); root.querySelector('#stage-title').focus(); return;
      }
      const submit = form.querySelector('[type=submit]'); submit.disabled = true;
      try {
        const payload = { ...data, summary: hasContext ? summaryFor(data) : data.summary, title: kind === 'source' ? data.source.title : data.title, tags: [...new Set([...data.tags, ...(data.suggested_tags || '').split(',').map(t => t.trim()).filter(Boolean)])] };
        const result = await api(editId ? '/submissions/' + editId + '/revisions' : '/submissions', payload);
        try { localStorage.removeItem(DRAFT_KEY); } catch {}
        root.innerHTML = `<section class="confirmation contribution-page"><p class="eyebrow">awaiting review</p><h1>thank you for adding<br>your bit.</h1><p>Your ${editId ? 'revision' : 'contribution'} has been saved. It is private while an editor reviews it.${editId ? ' The existing published version stays visible during review.' : ''}</p>${config.mode === 'demo' ? '<p class="notice">Local demo: no email has been sent. Request a private management link below; it will be written to the development outbox. After signing in, confirm this account and its sharing permissions before an editor can publish it.</p>' : '<p>Request a private access link to confirm this contribution and its permissions, and manage it later.</p>'}<p class="small">reference: ${e(result.id)} · this ID does not grant editing access.</p><p data-error class="error" role="alert" tabindex="-1" hidden></p><div class="button-row"><button class="button primary" id="request-management">Request private access</button><a href="/explore">Back to the collection</a></div></section>`;
        root.querySelector('#request-management').addEventListener('click', async event => {
          const button = event.currentTarget; button.disabled = true;
          try { const result = await api('/auth/request', { email: data.email || user?.email }); toast(result.message); button.textContent = config.mode === 'demo' ? 'link requested — see the development outbox' : 'link requested — check your inbox'; }
          catch (error) { showError(root, error); button.disabled = false; }
        });
        scopeLinks(root);
        window.scrollTo(0, 0); document.querySelector('#main').focus();
      } catch (error) { showError(root, error); submit.disabled = false; }
    });
    root.querySelector('#form-back').addEventListener('click', () => { capture(); if (step) step--; else { navigate('/contribute'); return; } render(); root.querySelector('#stage-title').focus(); });
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
