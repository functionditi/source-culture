import { api, session, signOut, loadPrivateMedia } from '../api.js';
import { e, date, heading, toast, showError, sourceReference, link } from '../ui.js';
import { appURL } from '../paths.js';

export async function account(root, admin, navigate, config) {
  const token = new URLSearchParams(location.hash.slice(1)).get('token');
  const version = new URLSearchParams(location.search).get('v');
  const managePath = '/manage' + (version ? '?' + new URLSearchParams({ v: version }) : '');
  // Remove the link before any asynchronous requests, including session lookup.
  if (token) history.replaceState({}, '', appURL(managePath));
  if (token) {
    // Tokens stay in memory and are removed from browser history immediately.
    root.innerHTML = `${heading('your private notebook.', 'This access link works once and expires after 15 minutes.', 'private contributor access')}<section class="login-layout"><h2>ready to sign in?</h2><p>Your access link opens a private session for your contributions.</p><p data-error class="error" role="alert" tabindex="-1" hidden></p><button class="button primary" id="verify-link">sign in with this link ↗</button></section>`;
    root.querySelector('#verify-link').addEventListener('click', async event => {
      event.currentTarget.disabled = true;
      try { await api('/auth/verify', { token }); await session(); navigate(managePath, { replace: true }); }
      catch (error) { showError(root, error); root.querySelector('#verify-link').disabled = false; }
    });
    return;
  }
  const user = await session();
  if (!user || (admin && !user.editor)) {
    root.innerHTML = `${heading(admin ? 'a little editorial care.' : 'your private notebook.', admin ? 'The review queue is available to explicitly authorised editors.' : 'Check a submission, respond to feedback, revise an account, or withdraw it.', admin ? 'private / editor access' : 'private / contributor access')}<section class="login-layout"><h2>${user ? 'an editor account is needed.' : 'a link, just for you.'}</h2><p>${user ? 'This account has no editorial role. Only emails configured by the server operator can review contributions.' : 'Enter the private email you used to contribute. Sign-in links expire after 15 minutes and can be used once.'}</p>${config.mode === 'demo' ? '<p class="notice">Local demo: no email is sent. The server operator can read sign-in links with <code>python3 server/app.py --outbox</code>. This outbox is never available through the website.</p>' : '<p class="notice">A private sign-in link will be delivered to your email. It works once and expires in 15 minutes.</p>'}<p data-error class="error" role="alert" tabindex="-1" hidden></p><form id="login-form"><div class="field"><label for="login-email">private email</label><input type="email" id="login-email" name="email" required autocomplete="email" value="${e(user?.email || '')}"></div><button class="button primary">request a sign-in link ↗</button></form>${user ? '<button class="plain-button small" id="sign-out">sign out of this account</button>' : ''}</section>`;
    root.querySelector('#login-form').addEventListener('submit', async event => {
      event.preventDefault(); const button = event.currentTarget.querySelector('button'); button.disabled = true;
      try { const result = await api('/auth/request', { email: new FormData(event.currentTarget).get('email') }); toast(result.message); }
      catch (error) { showError(root, error); }
      finally { button.disabled = false; }
    });
    root.querySelector('#sign-out')?.addEventListener('click', async () => { await signOut(); navigate(admin ? '/admin' : '/manage', { replace: true }); });
    return;
  }
  const entries = await api(admin ? '/admin' : '/mine');
  const params = new URLSearchParams(location.search), kind = params.get('kind') || '', reviewId = params.get('review');
  let selected = entries.find(x => x.id === reviewId);
  if (selected) selected = await loadPrivateMedia(selected);
  const practices = selected?.kind === 'source' ? await api('/practices') : [];
  const queue = entries.filter(x => !kind || (kind === 'revision' ? x.number > 1 : x.kind === kind));
  root.innerHTML = `${heading(admin ? 'the review notebook.' : 'the things you’ve shared.', admin ? 'Read the account, follow its sources, and check the permissions before publishing.' : 'Every account has room to grow. A revision leaves the published version visible until it is reviewed.', admin ? 'private / editorial queue' : 'private / your contributions')}<div class="login-state"><span>signed in as ${e(user.email)}</span><div>${user.editor ? `<a class="text-link" href="${admin ? '/manage' : '/admin'}">${admin ? 'your contributions' : 'editorial queue'} ↗</a> · ` : ''}<button class="plain-button" id="sign-out">sign out</button></div></div><section class="page-section">${admin ? `<nav class="queue-tabs" aria-label="Review queue types">${[['', 'all'], ['practice', 'new practices'], ['variation', 'variations'], ['source', 'sources'], ['correction', 'corrections'], ['revision', 'revisions']].map(([k, label]) => `<a class="filter-chip" href="/admin${k ? '?kind=' + k : ''}" ${kind === k ? 'aria-current="page"' : ''}>${label}</a>`).join('')}</nav>` : ''}<p data-error class="error" role="alert" tabindex="-1" hidden></p>${selected ? reviewHTML(selected, practices, config) : queue.length ? queue.map(item => itemHTML(item, admin)).join('') : '<div class="empty"><h2>a quiet notebook.</h2><p>No contributions here yet.</p><a href="/contribute" class="button">share something you know ↗</a></div>'}</section>`;
  root.querySelector('#sign-out').addEventListener('click', async () => { await signOut(); navigate(admin ? '/admin' : '/manage', { replace: true }); });
  root.querySelectorAll('[data-withdraw]').forEach(button => button.addEventListener('click', () => {
    const id = button.dataset.withdraw;
    button.outerHTML = `<div class="notice" data-confirm="${e(id)}"><p>Withdraw this contribution now? Its public page and images will be hidden immediately. Minimal moderation records remain private.</p><div class="button-row"><button class="button small danger" data-confirm-withdraw="${e(id)}">yes, withdraw</button><button class="button small" data-cancel-withdraw>keep it</button></div></div>`;
    root.querySelector('[data-cancel-withdraw]').addEventListener('click', () => navigate(location.pathname + location.search, { replace: true, scroll: false }));
    root.querySelector('[data-confirm-withdraw]').addEventListener('click', async event => { event.currentTarget.disabled = true; try { const result = await api('/submissions/' + id + '/withdraw', {}); toast(result.message); navigate('/manage', { replace: true, scroll: false }); } catch (error) { showError(root, error); event.currentTarget.disabled = false; } });
  }));
  root.querySelector('#review-form')?.addEventListener('submit', async event => {
    event.preventDefault(); const button = event.submitter; button.disabled = true;
    const links = Array.from(root.querySelectorAll('[data-connection]')).map(row => Object.fromEntries(Array.from(row.querySelectorAll('[data-link-field]')).map(input => [input.dataset.linkField, input.value]))).filter(row => row.practice_id);
    const route = selected.kind === 'source' && selected.revision_state === 'published' ? '/connections' : '/review';
    try { const result = await api('/admin/' + selected.id + route, { ...Object.fromEntries(new FormData(event.currentTarget)), revision_id: selected.revision_id, links }); toast(result.message); navigate('/admin', { replace: true, scroll: false }); }
    catch (error) { showError(root, error); button.disabled = false; }
  });
  root.querySelector('#add-connection')?.addEventListener('click', () => { root.querySelector('#source-connections').insertAdjacentHTML('beforeend', connectionHTML(practices, config)); });
  root.querySelectorAll('[data-owner-confirm]').forEach(form => form.addEventListener('submit', async event => {
    event.preventDefault(); const button = form.querySelector('button'); button.disabled = true;
    try {
      const result = await api('/submissions/' + form.dataset.ownerConfirm + '/confirm', { publication_permission: true, rights_confirmation: true });
      toast(result.message); navigate('/manage', { replace: true, scroll: false });
    } catch (error) { showError(root, error); button.disabled = false; }
  }));
  root.querySelectorAll('[data-message-form]').forEach(form => form.addEventListener('submit', async event => {
    event.preventDefault(); const button = form.querySelector('button'); button.disabled = true;
    try { const result = await api('/submissions/' + form.dataset.messageForm + '/messages', { body: new FormData(form).get('body') }); toast(result.message); navigate(location.pathname + location.search, { replace: true, scroll: false }); }
    catch (error) { showError(root, error); button.disabled = false; }
  }));
}

function messagesHTML(item) {
  return `<details class="citation-disclosure"><summary>private editorial conversation (${item.messages.length})</summary>${item.messages.map(m => `<div class="feedback"><p>${e(m.body)}</p><p class="small">${date(m.created_at)}</p></div>`).join('')}<form data-message-form="${e(item.id)}"><div class="field"><label for="message-${e(item.id)}">respond privately to the editor or contributor</label><textarea id="message-${e(item.id)}" name="body" required></textarea></div><button class="button small">save private response ↗</button></form></details>`;
}

function connectionHTML(practices, config, target = '') {
  const id = 'connection-' + crypto.randomUUID();
  return `<fieldset class="reference-editor" data-connection><legend>source connection</legend><div class="field"><label for="${id}">practice (leave blank to skip)</label><select id="${id}" data-link-field="practice_id"><option value="">choose a practice…</option>${practices.map(p => `<option value="${e(p.id)}" ${p.id === target ? 'selected' : ''}>${e(p.title)}</option>`).join('')}</select></div><div class="field"><label for="${id}-relation">relationship</label><select id="${id}-relation" data-link-field="relationship">${config.relationships.map(r => `<option>${e(r)}</option>`).join('')}</select></div><div class="field"><label for="${id}-block">passage</label><select id="${id}-block" data-link-field="block_id"><option value="">further reading / no passage</option><option value="story">the story</option><option value="account">how it works</option><option value="judgement">how you know</option></select></div><div class="field"><label for="${id}-locator">page, chapter, or timestamp</label><input id="${id}-locator" data-link-field="locator"></div><div class="field"><label for="${id}-note">explain the connection</label><textarea id="${id}-note" data-link-field="annotation"></textarea></div></fieldset>`;
}

function itemHTML(item, admin) {
  const c = item.content;
  const confirmation = !admin && !item.confirmed && item.status !== 'withdrawn' ? `
    <details class="citation-disclosure"><summary>confirm this contribution before publication</summary>
      <p class="small">Confirm that the account submitted with your email is yours. This also confirms its attached source suggestions. You can revise or withdraw it instead.</p>
      <form data-owner-confirm="${e(item.id)}">
        <label class="check-label"><input type="checkbox" required><span>This is my contribution and I approve its recorded publication and reuse choices.</span></label>
        <label class="check-label"><input type="checkbox" required><span>I am entitled to share the text, sources, and attached media, with permission for identifiable people or attributed private accounts.</span></label>
        <button class="button small primary">confirm this account & permissions ↗</button>
      </form>
    </details>` : '';
  return `<article class="submission-card"><header><div><p class="eyebrow">${e(item.kind)} · revision ${item.number}${item.demo ? ' · local demo' : ''}</p><h2 dir="auto">${e(c.title)}</h2></div><span class="status ${item.status === 'published' ? 'published' : ''}">${e(item.status === 'withdrawn' ? 'withdrawn' : item.revision_state)}</span></header><p>${e(c.summary || c.source?.annotation || c.account)}</p><p class="small">${date(item.updated_at)} · ${item.email_verified ? 'email verified' : 'email verification needed'} · ${item.confirmed ? 'this account is confirmed' : 'this account needs contributor confirmation'}</p>${confirmation}${item.feedback.slice(0, 1).map(f => `<div class="feedback"><p class="eyebrow">editorial feedback / ${e(f.action)}</p><p>${e(f.feedback || 'Publication approved.')}</p></div>`).join('')}<div class="button-row">${admin ? `<a class="button small" href="/admin?review=${e(item.id)}">review account & permissions ↗</a>` : item.status !== 'withdrawn' ? `<a class="button small" href="/contribute?type=${e(item.kind)}&edit=${e(item.id)}">edit / submit a revision ↗</a><button class="button small danger" data-withdraw="${e(item.id)}">withdraw contribution</button>` : ''}${item.published_revision_id && item.status === 'published' ? `<a class="button small" href="/${item.kind === 'source' ? 'sources' : 'practices'}/${e(item.slug)}">view published version ↗</a>` : ''}</div>${messagesHTML(item)}</article>`;
}

function reviewHTML(item, practices, config) {
  const c = item.content;
  const old = item.published_content;
  const keys = ['title', 'summary', 'context', 'account', 'judgement', 'display_name', 'similar', 'changes', 'source', 'references', 'tags'];
  const changes = old ? keys.filter(k => JSON.stringify(old[k]) !== JSON.stringify(c[k])) : [];
  const connectionsOnly = item.kind === 'source' && item.revision_state === 'published';
  const alreadyReviewed = !['submitted', 'needs changes'].includes(item.revision_state);
  const decisionFields = connectionsOnly ? '<p class="small">This source is already published. Add annotated connections below.</p>' : `
    <div class="field">
      <label for="decision">decision</label>
      <select id="decision" name="action" required>
        <option value="">choose…</option>
        ${item.kind !== 'correction' ? '<option value="published">publish this revision</option>' : ''}
        <option value="needs changes">request changes</option>
        <option value="declined">decline with a reason</option>
      </select>
    </div>
    <div class="field"><label for="feedback">private feedback / reason</label><textarea id="feedback" name="feedback"></textarea></div>`;
  const reviewForm = item.status === 'withdrawn' ? '<p class="notice">Withdrawn accounts cannot be republished.</p>' : alreadyReviewed && !connectionsOnly ? '<p class="notice">This revision has already been reviewed. The contributor can propose a new revision.</p>' : `
    <form id="review-form">
      ${item.kind === 'source' ? `<h3>connect to practices</h3><div id="source-connections">${connectionHTML(practices, config, item.target_id)}</div><button class="button small" id="add-connection" type="button">another connection +</button>` : ''}
      ${decisionFields}
      <p class="small">Linked source suggestions must be reviewed and published before an account. Corrections are applied through an approved contributor revision, never a silent rewrite.</p>
      <button class="button primary">${connectionsOnly ? 'save source connections' : 'record decision'} ↗</button>
    </form>`;
  const displayValue = value => e(typeof value === 'object' ? JSON.stringify(value) : value);
  const comparison = old ? `
    <h3>changes from the published version</h3>
    ${changes.length ? `<table class="diff-table"><thead><tr><th>field</th><th>published</th><th>proposed</th></tr></thead><tbody>${changes.map(k => `<tr><th>${e(k)}</th><td>${displayValue(old[k])}</td><td>${displayValue(c[k])}</td></tr>`).join('')}</tbody></table>` : '<p class="small">No public text fields changed.</p>'}` : '';
  return `
    <p class="small"><a class="text-link" href="/admin">← back to the queue</a></p>
    <div class="review-layout">
      <article>
        <div class="public-preview">
          <p class="eyebrow">contributor’s proposed account · revision ${item.number}</p>
          <h2 dir="auto">${e(c.title)}</h2><p>${e(c.summary)}</p><p class="small">${e(c.display_name)}</p>
          ${c.source ? `<p>${e(sourceReference(c.source))}</p><p>${e(c.source.annotation)}</p><p>${link(c.source.url, 'open original source')}</p>` : ''}
          ${['context', 'account', 'judgement', 'similar', 'changes'].filter(k => c[k]).map(k => `<h3>${e(k)}</h3><p dir="auto">${e(c[k])}</p>`).join('')}
          ${(c.references || []).map(s => `<h3>proposed source</h3><p>${e(sourceReference(s))}</p><p>${e(s.relation)} · ${e(s.locator)}<br>${e(s.annotation)}</p><p>${link(s.url, 'open original source')}</p>`).join('')}
          ${item.media.map(m => `<figure class="article-media"><img src="${e(m.url)}" alt="${e(m.alt)}"><figcaption>${e(m.caption)} · ${e(m.credit)}</figcaption></figure>`).join('')}
        </div>
        ${comparison}
      </article>
      <aside class="review-panel">
        <h3>review with care.</h3>
        <p class="small">private contact: ${e(item.email)}<br>${item.email_verified ? 'verified email' : 'email not yet verified'}<br>${item.confirmed ? 'this specific account and its permissions are confirmed' : 'this account still needs contributor confirmation'}</p>
        <ul class="consent-list">
          <li>Publication permission: ${item.permission?.publication ? 'recorded for this revision' : 'no live permission record (seed data)'}</li>
          <li>Entitlement and third-party permission: ${item.permission ? 'contributor confirmed' : 'editorial listing; no contributor consent claimed'}</li>
          <li>Text reuse: ${e(c.reuse || 'no additional reuse licence')}</li>
          <li>Media: ${item.media.length} image(s), each with recorded permission</li>
        </ul>
        <p class="small">Check the account is intelligible, the attribution is appropriate, no private contact details are in the public text, and sources support the passages claimed. Request changes for material edits; let the contributor approve their account.</p>
        ${reviewForm}
        ${messagesHTML(item)}
      </aside>
    </div>`;
}
