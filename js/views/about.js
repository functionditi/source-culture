import { browseHeader } from './browse.js';

export function about(root, config = {}) {
  const readOnly = config.mode === 'static';
  const privacy = readOnly
    ? `<p>This site does not accept submissions or sign-ins, collect contact emails, or create account sessions.</p><p>Your appearance choice is saved in this browser. This site uses no analytics. External sites have their own privacy practices.</p>`
    : `<p>Your email is used for sign-in and editorial contact and stays private. You can be credited by name, a pseudonym, or “anonymous contributor”.</p><p>Only you and authorised editors can see unpublished contributions and feedback. You can revise or withdraw your work through private access. Withdrawal removes public entries and images; content, ownership, consent, and moderation records remain private for follow-up.</p><p>Device drafts are saved only when you choose, without email, images, or permissions. This site uses no analytics.</p>${config.mode === 'demo' ? '<p>Local preview: sign-in links go to the development outbox; no email is sent.</p>' : ''}<p><a href="/manage">Manage your contributions</a></p>`;
  const sharing = readOnly
    ? '<p>Credit the authors and source creators. Inclusion in this notebook grants no extra reuse licence; linked works keep their own rights. Use “cite this entry” for a project reference.</p>'
    : '<p>Share material you have permission to make public, with agreed credit for people and private accounts. Leave out knowledge intended to stay private.</p><p>Publication permission and reuse are separate choices. The default grants no extra reuse licence; linked sources keep their own rights. Editors ask you to approve material changes.</p>';

  root.innerHTML = `<div class="browse-page about-page">
    ${browseHeader('about.')}
    <section class="about-intro" id="framing" aria-labelledby="about-intro-title">
      <h2 id="about-intro-title">knowledge lives in people.</h2>
      <p>Source Culture brings together projects, practices, and readings about <em>vernacular computing</em>: how people organise, measure, remember, and make decisions through everyday knowledge.</p>
    </section>
    <div class="about-overview">
      <section id="editorial" aria-labelledby="about-context-title">
        <h2 id="about-context-title">context matters.</h2>
        <p>Each account keeps its author, setting, and sources. A computational reading is one interpretation, open to correction.${readOnly ? '' : ' Contributions are reviewed before publication.'}</p>
      </section>
      <section id="participate" aria-labelledby="about-participate-title">
        <h2 id="about-participate-title">${readOnly ? 'a notebook to explore.' : 'add your bit.'}</h2>
        <p>${readOnly ? 'Browse the collection and follow its sources. This edition is read-only.' : 'Share a project, an everyday practice, a source, or another way of doing something. A starting point is enough.'}</p>
        <a href="${readOnly ? '/explore' : '/contribute'}">${readOnly ? 'Explore the collection' : 'Share something you know'}</a>
      </section>
    </div>
    <div class="about-details">
      <details id="sharing"><summary>Sharing & credit</summary>${sharing}</details>
      <details id="privacy"><summary>Privacy</summary>${privacy}</details>
    </div>
  </div>`;

  // Contribution and footer links can open a particular disclosure directly.
  function revealLinkedSection() {
    const section = [...root.querySelectorAll('.about-details details')].find(detail => location.hash === '#' + detail.id);
    if (!section) return;
    section.open = true;
    if (root.isConnected) section.scrollIntoView({ block: 'start' });
  }
  revealLinkedSection();
  window.addEventListener('hashchange', revealLinkedSection);
  return () => window.removeEventListener('hashchange', revealLinkedSection);
}
