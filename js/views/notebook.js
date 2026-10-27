import { api } from '../api.js';
import { e, safeURL } from '../ui.js';
import { mountPattern } from '../sketches/pattern-study.js';
import { mountReadingRoom } from '../reading-room.js?v=prasa-background-grid-1';
import { appURL } from '../paths.js';

const illustrationNames = ['rice', 'knit', 'clap', 'route', 'turns', 'cups'];
const paragraphs = text => String(text || '').split(/\n\s*\n/).filter(Boolean).map(text => `<p dir="auto">${e(text)}</p>`).join('');

export function columnHeading(label, index, level = 2) {
  return `<header class="column-heading">
    <h${level}><button type="button" data-expand-column aria-pressed="${index === 0}" aria-label="Expand ${String(index + 1).padStart(2, '0')} ${e(label)} column">
      <span class="column-number" aria-hidden="true">${String(index + 1).padStart(2, '0')}</span>
      <span class="column-title">${e(label)}</span><span class="column-arrow" aria-hidden="true">↗</span>
    </button></h${level}>
  </header>`;
}

function entryFigure(entry) {
  if (['rice-grid', 'prasa'].includes(entry.placeholder)) return projectMedia(entry);
  const media = entry.media?.[0];
  if (media) return `<figure class="notebook-figure">
    <a href="/practices/${e(entry.slug)}"><img src="${e(media.url)}" alt="${e(media.alt)}" loading="lazy" width="840" height="580"></a>
    <figcaption>${e(media.caption)}${media.credit ? ' · ' + e(media.credit) : ''}</figcaption>
  </figure>`;
  if (!illustrationNames.includes(entry.illustration)) return '';
  return `<figure class="notebook-figure">
    <a href="/practices/${e(entry.slug)}" aria-label="Read ${e(entry.title)}"><img src="${appURL('/assets/illustrations/' + entry.illustration + '.svg')}" alt="" loading="lazy" width="420" height="290"></a>
    <figcaption>illustration of a fictional development scenario</figcaption>
  </figure>`;
}

export function notebookEntry(entry, sources = [], all = []) {
  const parent = all.find(candidate => candidate.id === entry.parent_id);
  const citations = (entry.citations || []).map((citation, index) => {
    const source = sources.find(candidate => candidate.id === citation.source_id);
    return source ? `<a class="notebook-citation" href="/sources/${e(source.slug)}" aria-label="Source ${index + 1}: ${e(source.title)}">[${index + 1}]</a>` : '';
  }).join(' ');
  return `<article class="notebook-entry" data-notebook-entry>
    <h3 dir="auto"><a href="/practices/${e(entry.slug)}">${e(entry.title)} ↗</a></h3>
    ${entry.original_name ? `<p class="notebook-original" dir="auto">${e(entry.original_name)}${entry.language ? ' · ' + e(entry.language) : ''}</p>` : ''}
    <p class="notebook-credit">${e(entry.display_name)}<br>${entry.editorial ? e(entry.entry_type || 'project') : entry.relationship === 'source-based research' ? 'source-based account' : 'personal account'}${entry.demo && !entry.editorial ? ' · illustrative demo' : ''}</p>
    ${parent ? `<p class="notebook-connection">a variation of <a href="/practices/${e(parent.slug)}">${e(parent.title)}</a>. An account in its own right, alongside the first.</p>` : ''}
    <div class="notebook-prose">${paragraphs(entry.summary)}</div>
    ${entryFigure(entry)}
    <div class="notebook-prose">
      ${paragraphs(entry.context)}
      ${entry.similar ? paragraphs(entry.similar) : ''}
      ${entry.changes ? paragraphs(entry.changes) : ''}
      ${entry.materials ? `<p><span class="notebook-inline-label">materials:</span> ${e(entry.materials)}</p>` : ''}
      ${paragraphs(entry.account)}${citations ? `<p class="notebook-citations">${citations}</p>` : ''}
      ${entry.steps ? `<ol class="notebook-steps">${entry.steps.split('\n').filter(Boolean).map(step => `<li>${e(step)}</li>`).join('')}</ol>` : ''}
      ${paragraphs(entry.judgement)}
    </div>
    <p class="notebook-thread">${(entry.tags || []).slice(0, 2).map(tag => `<a href="/explore?tag=${encodeURIComponent(tag)}">${e(tag)}</a>`).join(' / ')}</p>
    <p class="notebook-entry-links"><a href="/practices/${e(entry.slug)}">read the complete account ↗</a> / <a href="/contribute?type=variation&parent=${e(entry.id)}">add your variation ↗</a></p>
  </article>`;
}

function column(id, label, index, content, level = 2) {
  return `<section class="reading-column" id="${id}" data-reading-column data-active="${index === 0}" aria-label="${e(label)}">
    ${columnHeading(label, index, level)}
    <div class="reading-copy">${content}</div>
  </section>`;
}

export function projectMedia(entry) {
  if (entry.placeholder === 'rice-grid') return `<figure class="project-media">
    <img src="${e(appURL(entry.project_image || '/project-images/experiments-with-rice.JPG'))}" alt="Hands arranging piles of rice grains on a metal tray." width="1350" height="1800" loading="lazy">
  </figure>`;
  if (entry.placeholder === 'prasa') return `<figure class="project-media">
    <img src="${e(appURL(entry.project_image || '/project-images/prasa-example.png'))}" alt="White poetic text arranged across a textured olive-green background." width="1800" height="1219" loading="lazy">
  </figure>`;
  return entryFigure(entry);
}

function projectCard(entry, { heading = true } = {}) {
  const external = safeURL(entry.external_url);
  const url = external || '/practices/' + encodeURIComponent(entry.slug);
  const target = external ? ' target="_blank" rel="noopener noreferrer"' : '';
  const account = entry.id === 'editorial-prasa' ? e(entry.account).replace('chandassu', '<em>chandassu</em>') : e(entry.account || entry.context);
  return `<article class="repository-project" aria-label="${e(entry.title)}" data-notebook-entry data-project-type="${e(entry.entry_type || 'practice')}">
    ${projectMedia(entry)}
    ${heading ? `<h3><a href="${e(url)}"${target}>${e(entry.title)}</a></h3>` : ''}
    <p class="project-attribution">${e(entry.display_name)}${entry.project_status ? ' · ' + e(entry.project_status) : ''}</p>
    <div class="notebook-prose"><p class="project-question">${e(entry.summary)}</p><p>${account}</p></div>
    <p class="project-topics">${(entry.tags || []).map(tag => `<a href="/explore?tag=${encodeURIComponent(tag)}">${e(tag)}</a>`).join(' · ')}</p>
    <p class="project-link"><a href="${e(url)}"${target}>${external ? 'read about the project' : entry.entry_type === 'practice' || entry.kind === 'variation' ? 'explore the practice' : 'explore the project'} →</a></p>
  </article>`;
}

export async function notebookHome(root, config, navigate) {
  const [entries, sources] = await Promise.all([api('/practices'), api('/sources')]);
  const params = new URLSearchParams(location.search);
  const filter = ['project', 'practice', 'experiment'].includes(params.get('view')) ? params.get('view') : 'all';
  const repository = entries.filter(entry => !entry.fictional).sort((a, b) => {
    const priority = ['editorial-rice', 'editorial-prasa'];
    return (priority.indexOf(a.id) < 0 ? 2 : priority.indexOf(a.id)) - (priority.indexOf(b.id) < 0 ? 2 : priority.indexOf(b.id));
  });
  const shown = repository.filter(entry => filter === 'all' || (entry.entry_type || 'practice') === filter);
  const left = shown.filter((_, index) => index % 2 === 0);
  const right = shown.filter((_, index) => index % 2 === 1);
  const paperURL = 'https://link.springer.com/article/10.1007/s00146-025-02689-w';
  const swalwellURL = 'https://mitpress.mit.edu/9780262365604/homebrew-gaming-and-the-beginnings-of-vernacular-digitality/';
  const aliURL = 'https://www.open.edu/openlearn/digital-computing/decolonising-computing';
  const readingIds = ['editorial-dhulipalla-2025', 'editorial-swalwell-2021', 'editorial-ali-decolonising', 'editorial-hui-2016'];
  const readings = readingIds.map(id => sources.find(source => source.id === id)).filter(Boolean);
  const introduction = `
    <div class="notebook-prose">
      <p>Vernacular computing considers how computation is shaped by the places, cultures, and everyday practices through which people make and share knowledge.</p>
      <p>Koundinya Dhulipalla (<a href="${paperURL}" target="_blank" rel="noopener noreferrer">source</a>) approaches it through culturally situated traditions, exploring how oral, poetic, and embodied knowledge can inform programming. Melanie Swalwell’s related concept of <a href="${swalwellURL}" target="_blank" rel="noopener noreferrer"><em>vernacular digitality</em></a> examines how people make digital technology their own through homebrew games, experimentation, and hardware hacking.</p>
    </div>
    ${config.mode === 'static' ? '<p class="notice">This notebook is read-only. Explore the projects and readings; contributions are not open on this site.</p>' : `<form class="definition-suggestion" id="definition-suggestion">
      <label for="your-definition">have a definition of your own? Let us know:</label>
      <div><textarea id="your-definition" name="definition" rows="2" maxlength="2000" required aria-label="Your definition of vernacular computing"></textarea><button type="submit" aria-label="Continue with your definition suggestion">→</button></div>
    </form>`}
    <section class="notebook-block notebook-prose">
      <h2 class="notebook-subheading">what does it mean here?</h2>
      <p>What might a recipe, a weaving pattern, a poem, or a homemade game reveal about how we organise information and work with rules?</p>
      <p>Source Culture brings together projects and practices that explore these questions. Some build computational systems from cultural forms. Others document everyday ways of sequencing, measuring, remembering, and making decisions.</p>
      <p>We’re interested in the people, materials, and contexts that give these practices meaning, and in what gets lost when we translate them into code.</p>
    </section>
    <section class="notebook-block notebook-prose">
      <h2 class="notebook-subheading">whose computation?</h2>
      <p>Whose knowledge shapes the tools we use? Whose ways of thinking become defaults?</p>
      <p><a href="${aliURL}" target="_blank" rel="noopener noreferrer">Decolonial computing</a> asks how computing participates in histories and structures of power. It invites us to examine whose perspectives are centred, how systems are made, and whom they serve.</p>
    </section>
    <section class="notebook-block reading-list" aria-labelledby="readings-title">
      <h2 class="notebook-subheading" id="readings-title">readings and connections</h2>
      ${readings.map(source => `<article class="reading-reference">
        <h3><a href="${e(safeURL(source.source.url))}" target="_blank" rel="noopener noreferrer">${e(source.title)}</a></h3>
        <p class="reading-byline">${e(source.source.creators)}${source.id === 'editorial-dhulipalla-2025' ? ' · published online 2025' : source.id === 'editorial-ali-decolonising' ? '' : ' · ' + e(source.source.date.slice(0, 4))}</p>
        <p>${e(source.source.annotation)}</p>
      </article>`).join('')}
    </section>`;

  const overview = `<section class="repository-overview" id="notebook-repository" data-focus-column="notebook-collection" aria-labelledby="repository-title">
    <h2 id="repository-title">a growing repository</h2>
    <p>Projects, experiments, and everyday practices exploring the relationships between computation, culture, and situated knowledge.</p>
    <p>${config.mode === 'static' ? 'Browse an approach and follow its sources.' : 'Browse an approach, follow its sources, or contribute something it brings to mind.'}</p>
    <div class="repository-filters" role="group" aria-label="Repository entry type">
      ${[['all', 'explore all'], ['project', 'projects'], ['practice', 'practices'], ['experiment', 'experiments']].map(([value, label]) => `<button type="button" data-repository-filter="${value}" aria-pressed="${filter === value}">${label}</button>`).join('')}
    </div>
    <p class="repository-results-count" role="status">${shown.length} ${filter === 'all' ? 'entries' : filter + (shown.length === 1 ? '' : 's')}</p>
  </section>`;

  const invitationTitle = 'what belongs here next?';
  const invitation = `<section class="repository-invitation notebook-prose">
    ${right.length ? `<h2 class="notebook-subheading">${invitationTitle}</h2>` : ''}
    <p>A project you’re making. A practice you’ve learned. A system someone devised for an everyday task.</p>
    ${config.mode === 'static' ? '<p>This version is read-only. Follow the projects and sources already in the notebook.</p><p><a href="/sources">browse the reading shelf →</a></p>' : '<p>Help this collection grow.</p><p><a href="/contribute?type=practice">share something you know →</a></p>'}
  </section>`;
  const pattern = `<details class="repository-pattern notebook-block">
    <summary>a small pattern study</summary><p>Illustrative experiment, not project documentation.</p>
    <div class="pattern-controls"><label for="pattern-rule">change direction every</label><input id="pattern-rule" type="range" min="1" max="6" value="3" aria-describedby="pattern-description"></div>
    <div id="pattern-canvas" class="pattern-canvas" aria-hidden="true"></div><p id="pattern-description" class="pattern-description"></p>
  </details>`;
  // The shared overview names the repository once. Each column takes its first
  // project's title, including after filtering; later cards keep their headings.
  const collectionTitle = left[0]?.title || 'nothing here yet';
  const projectsTitle = right[0]?.title || invitationTitle;
  const cards = entries => entries.map((entry, index) => projectCard(entry, { heading: index > 0 })).join('');
  const collection = `${cards(left)}${!shown.length ? '<p class="repository-empty">No ' + e(filter === 'all' ? 'entries' : filter + 's') + ' published here yet.</p>' : ''}`;
  const projects = `${cards(right)}${invitation}${pattern}`;
  const contribute = config.mode === 'static' ? `<div class="notebook-prose"><p>This notebook brings together projects, everyday practices, and readings about computation and culture.</p><p>This version is read-only. Contributions, source suggestions, corrections, and editor access are not open here.</p><p><a href="/explore">explore the collection →</a></p><p><a href="/sources">browse the reading shelf →</a></p></div>` : `<div class="notebook-prose">
      <p>This is a growing, living, evolving repository. And we would love your contribution.</p>
      <p>(P.S. You don’t need to write code or have a finished project.) </p>
    </div>
    <section class="notebook-block notebook-prose">
      <h2 class="notebook-subheading contribution-heading">share a project or practice</h2>
      <p>Tell us what it is, how it works, and your relationship to it. Add an image, a drawing, a link, or simply your own words.</p>
      <p><a href="/contribute?type=practice">share something you know →</a></p>
    </section>
    <section class="notebook-block notebook-prose">
      <h2 class="notebook-subheading contribution-heading">suggest a source</h2>
      <p>Found a useful paper, book, YouTube video, personal blog, interview, or project?</p>
      <p>Send it our way, with a few words about what it contributes.</p>
      <p><a href="/contribute?type=source">add a reference →</a></p>
    </section>
    <section class="notebook-block notebook-prose">
      <h2 class="notebook-subheading contribution-heading">do it differently?</h2>
      <p>If an entry reminds you of something you do, share your version. Different methods and experiences can sit alongside one another.</p>
      <p><a href="/explore?choose=variation">add a variation →</a></p>
    </section>
    <section class="notebook-block notebook-prose contribution-prompts">
      <h2 class="notebook-subheading">not sure where to begin?</h2>
      <p><a href="/contribute?type=practice&prompt=${encodeURIComponent('How do you measure without a measuring tool?')}">How do you measure without a measuring tool?</a><br>
      <a href="/contribute?type=practice&prompt=${encodeURIComponent('What have you learned by watching someone else?')}">What have you learned by watching someone else?</a><br>
      <a href="/contribute?type=practice&prompt=${encodeURIComponent('How do you know when something is ready?')}">How do you know when something is ready?</a></p>
    </section>
    <p class="contribution-permission">Contributions are reviewed before publication. Choose how you’d like to be credited, and share only material you have permission to make public.</p>`;

  root.innerHTML = `<nav class="notebook-jump" aria-label="Notebook sections">
      <button type="button" data-column-jump="notebook-introduction">01 about</button>
      <button type="button" data-column-jump="notebook-repository">02 repository</button>
      <button type="button" data-column-jump="notebook-variations">03 ${right[0] ? e(right[0].title) : 'add an entry'}</button>
      <button type="button" data-column-jump="notebook-connections">04 ${config.mode === 'static' ? 'this notebook' : 'contribute'}</button>
    </nav>
    <div class="reading-room repository-room" data-reading-room data-initial-column="${filter === 'all' ? 0 : 1}" aria-label="Project framing, repository, and contributions">
      ${column('notebook-introduction', 'what is vernacular computing?', 0, introduction, 1)}
      ${overview}
      ${column('notebook-collection', collectionTitle, 1, collection)}
      ${column('notebook-variations', projectsTitle, 2, projects)}
      ${column('notebook-connections', config.mode === 'static' ? 'this notebook' : 'contribute', 3, contribute)}
    </div>`;
  const disposeColumns = mountReadingRoom(root);
  const disposePattern = mountPattern(root);
  root.querySelectorAll('[data-repository-filter]').forEach(button => button.addEventListener('click', () => {
    const value = button.dataset.repositoryFilter;
    navigate(value === 'all' ? '/' : '/?view=' + value, { scroll: false });
  }));
  root.querySelector('#definition-suggestion')?.addEventListener('submit', event => {
    event.preventDefault();
    const account = new FormData(event.currentTarget).get('definition').trim();
    if (!account) return;
    navigate('/contribute?type=correction&prompt=' + encodeURIComponent('have a definition of your own?'), {
      state: { contribution: { kind: 'correction', title: 'a definition of vernacular computing', account } },
    });
  });
  return () => { disposeColumns(); disposePattern(); };
}

export function notebookResults(entries, sources, all) {
  const count = Math.min(4, entries.length);
  let offset = 0;
  return `<div class="reading-room reading-results" data-reading-room aria-label="Practice accounts in reading columns">${Array.from({ length: count }, (_, index) => {
    const length = Math.floor(entries.length / count) + (index < entries.length % count ? 1 : 0);
    const group = entries.slice(offset, offset + length);
    const label = `accounts ${String(offset + 1).padStart(2, '0')}–${String(offset + length).padStart(2, '0')}`;
    offset += length;
    return column(`results-column-${index}`, label, index, group.map(entry => notebookEntry(entry, sources, all)).join(''));
  }).join('')}</div>`;
}
