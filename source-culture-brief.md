# Source Culture — website build brief for Codex

## 1. Task and outcome

Build Source Culture, a public, participatory repository of vernacular computing. People can explore everyday practices, contribute accounts from their own lives, add variations to existing entries, and share relevant sources including academic papers, books, YouTube videos, personal blogs, project documentation, interviews, and oral accounts.

Produce a responsive, accessible, functioning website using semantic HTML, plain CSS, vanilla JavaScript ES modules, and p5.js. This frontend stack is required. Do not use React, Next.js, Vue, JSX, TypeScript, Tailwind, or a component framework. Keep the code readable and editable by a designer familiar with HTML, CSS, JavaScript, and p5.js. Start by inspecting the repository, its instructions, and the supplied design assets. Reuse compatible conventions without replacing the requested stack.

Use HTML and CSS for the actual website interface and p5.js for a small, purposeful generative or interactive visual component. Keep persistent submissions, authentication, image storage, and editorial permissions in a separate backend/API or managed service. Plain HTML/CSS/p5.js cannot alone provide shared persistent contributions or secure moderation. Choose a minimal compatible backend, explain the choice briefly, and keep its integration behind a vanilla JavaScript data module. Do not introduce infrastructure solely for speculative future features.

Implement the core experience before extras. If production services or credentials are unavailable, deliver an explicitly labelled local demo with a replaceable data adapter and document what remains to connect. Never represent browser-only storage as a functioning public contribution system. Do not deploy publicly without instruction.

## 2. Concept and editorial position

Working project definition, to be presented as our framing rather than an established quotation:

“Vernacular computing explores how people organise information, follow and adapt instructions, recognise patterns, remember, measure, and make decisions through locally situated and culturally transmitted practices.”

The site asks: What counts as computing? Who gets to define it? What can everyday knowledge contribute to how we imagine computational systems?

Examples might involve cooking, craft, games, exchange, navigation, or coordination. They are invitations to investigate, not proof that every practice is a computer. Preserve context, relationships, skill, and ambiguity. Computational interpretations must identify their author and be open to correction. Do not claim that describing a practice algorithmically fully explains it.

The site should work for people who have never heard of vernacular computing. Lead with recognisable examples and personal stories. Introduce terminology gradually.

## 3. Audience and roles

- Visitors: browse, search, read, follow citations, and discover related entries without signing in.
- Contributors: describe practices, add variations, suggest sources, and manage their own submissions through email-based access. No public profile is required.
- Editors: review submissions, check attribution and source relevance, request changes, publish, and handle corrections or withdrawal.

Public display names can be real names, pseudonyms, or “anonymous contributor.” Contact email is private and must never be exposed through public APIs or page source.

## 4. Experience and visual direction

The experience should feel like a collective notebook and living collection. Use clear typography, a disciplined grid, generous whitespace, fine rules, and varied contribution media. Photographs, drawings, diagrams, and personal language supply the character.

The user will attach a folder containing reference images, a palette image, and typeface files. These assets are the primary visual direction and override generic aesthetic suggestions in this brief. Do not impose a predetermined off-white/black/accent scheme. Inspect the attached assets before styling. Do not claim to have inspected files that have not yet been supplied.

Prefer readable typography over decorative effects. Lowercase interface copy is appropriate, but preserve names, original-language text, and source titles as supplied.

Avoid generic dashboard styling, excessive rounded cards, gradients, stock cultural imagery, faux-aged textures, and a large empty hero. Do not imply these practices belong only to the past. Avoid national flags as shorthand for culture.

Use a responsive grid with consistent card anatomy and flexible image proportions. Preserve logical reading order. A text-only entry must look intentional. Use simple procedural motifs as decoration only when clearly separate from documentary evidence. Do not fabricate documentary images.

### Required asset review and application

1. Inventory the supplied folder recursively. Identify reference images, the palette, font files, and any accompanying notes or licence files. Inspect images visually rather than inferring their appearance from filenames.
2. Look for palette filenames including `palette.png`, `pallete.png`, `palette.jpg`, `palette.jpeg`, or the user-mentioned `palette.jtp`. Treat `.jtp` as a possible filename typo: inspect the actual file format, preserve the original, and make a correctly named working copy only if it is a valid supported image. If it is unreadable, report that specifically. If multiple palettes conflict, use an explicitly designated primary palette or ask which is primary.
3. Extract the actual swatch colours, prioritising printed hex values where supplied. Sample flat swatch interiors rather than anti-aliased edges or image backgrounds. Record hex values and map them to CSS custom properties for page background, surfaces, text, rules, accents, and focus states. Do not average the entire image into a new palette.
4. Use the supplied palette across both the DOM interface and p5.js visuals. Check text/background pairings for readability. Prefer accessible combinations within the palette; if an additional neutral or adjusted tone is necessary for accessibility, document that small departure instead of silently redesigning the palette.
5. Inspect supplied typefaces and available weights/styles. Load appropriate webfont files locally through `@font-face`, use `font-display: swap`, and provide sensible fallbacks. Use the supplied families for their intended roles where indicated; otherwise select a coherent heading/body/metadata hierarchy from those files. Respect included embedding permissions. Do not replace supplied fonts with Google Fonts by default or fake missing weights. If a file is unusable or its supplied licence excludes web embedding, flag that specific issue and use a clearly documented temporary fallback.
6. Summarise what the reference images establish: grid, density, image treatment, typography hierarchy, spacing, borders, navigation, and interaction tone. Apply those observations consistently. References guide design; they are not automatically publishable site content or documentary evidence.
7. Keep original assets unchanged. Put any web-ready derivatives in an organised assets folder. Record source filename, usage, extracted colour values, and font mapping in a short design-notes document.

If the folder has not yet been attached, implement semantic structure, flows, and the data layer with clearly marked provisional styles. Leave final palette/font decisions pending the assets rather than inventing an approved visual identity. Do not delay independent functional work.

### Role of p5.js

Include one compact visual exploration of sequence, repetition, or variation, informed by the reference images. A suitable starting point is a small grid where an HTML control changes a repeating rule and the p5.js sketch shows the result. Label it as an illustrative pattern experiment, not a documented cultural practice. Keep it secondary to the entries and contribution actions, without a full-screen canvas introduction.

Use p5.js instance mode and a dedicated container so sketches do not pollute global application state. Keep navigation, cards, article text, citations, search, forms, and buttons in semantic HTML. Do not draw the whole website or essential text into a canvas. Controls should be real labelled HTML inputs usable by keyboard and touch. Provide a nearby text description of the pattern and current rule; decorative canvases can be hidden from assistive technology.

Read colour values from the shared CSS design tokens so the sketch cannot drift from the supplied palette. Size the canvas to its container, handle resizing, cap rendering density when needed, stop unnecessary animation, and dispose of sketches when leaving a view. Use event-driven redraws for static patterns. Respect reduced-motion settings and offer pause controls for continuous animation. The repository must remain readable and usable if p5.js fails to load.

## 5. Navigation and pages

Primary navigation: explore / sources / about / share something you know.

Routes:

- `/`: homepage with an immediate selection of entries.
- `/explore`: searchable, filterable collection.
- `/practices/[slug]`: practice or variation detail.
- `/contribute`: contribution type selector and staged form.
- `/sources`: source catalogue.
- `/sources/[id]`: source metadata, annotation, and linked practices.
- `/about`: framing, editorial approach, participation and sharing guidance.
- `/manage`: private contributor access and submission management.
- `/admin`: authenticated editor queue and review views.

These paths describe the information architecture, not a requirement for a routing framework. Implement them with ordinary HTML pages and lightweight JavaScript routing or server routing. Configure direct navigation and refresh to work on the chosen host; document any static-host URL adaptation. Keep URLs stable. Redirect old slugs when an entry is renamed. Provide clear missing, withdrawn, loading, empty, and error states.

## 6. Homepage

Opening copy:

**source culture**

“a growing collection of everyday instructions, patterns, and ways of knowing”

Supporting prompt: “how do you know how to do what you do?”

Primary actions: “explore the collection” and “share something you know.”

Show entries within the first screen or immediately below the introduction. Each card includes title, short description, media or a designed text treatment, contributor attribution, and up to two activity tags. Distinguish a personal account from a source-based account with a quiet text label.

Include a small prompt strip: “how do you measure without a measuring tool?” or “what did someone teach you without writing it down?” Clicking a prompt starts a contribution with that prompt retained as context, without automatically filling the answer.

Include a brief explanation of the project and a link to About. Do not require visitors to read the definition before exploring.

## 7. Explore and discovery

Search titles, descriptions, original names, tags, and public contributor names. Keep search and filters in the URL so results can be shared and restored with the back button.

Initial activity categories: food and cooking; craft and making; games and play; remembering and recording; exchange and sharing; navigation and place; everyday coordination.

Optional logic tags: sequencing; repetition; conditions and decisions; counting and comparison; pattern recognition; memory and retrieval; distribution and coordination; measurement and estimation; error checking.

Allow multiple tags and suggestions for new terms. Logic tags are interpretations, not universal classifications. Never make contributors choose one to submit.

Offer newest and recently updated sorting. Do not build popularity rankings, likes, or follower counts. Use pagination or an accessible “load more” button. Show a useful empty state with a reset option and a contribution invitation.

Related entries should initially be based on explicit variation links and shared tags. Explain the connection with labels such as “another way to measure” or “also involves repetition.” No AI recommendation service is needed.

## 8. Practice detail page

Order the page around the practice first:

1. Title, original-language name if supplied, short description, attribution, and publication/update date.
2. Media with captions, credits, and accessible descriptions.
3. “the story”: how the contributor encountered or learned it; relevant household, place, or community context in their own terms.
4. “how it works”: materials and an ordered account of actions. Allow branching notes and images, but do not force every practice into a rigid recipe.
5. “how you know”: signs of success, adjustments, judgement, tacit skill, and what is difficult to explain.
6. Optional “a computational reading”: a clearly attributed interpretation, with uncertainty and limitations visible. Empty sections should disappear gracefully.
7. Inline citations and a readable “sources and connections” list.
8. Linked variations and related practices.
9. Actions: “do you do this differently?”, “suggest a source”, “suggest a correction”, and “share this entry.”

Distinguish a contributor's account, an editor's interpretation, and a sourced claim. Cite historical or scientific assertions where appropriate. Do not silently turn a single person's account into a statement about an entire culture.

Show a compact “cite this entry” disclosure containing title, display author, project name, date, stable URL, and revision information. Support copying a plain-text citation. This credits contributors when their accounts are reused in research.

## 9. Core user flows

### A. Discover

Homepage → explore or card → practice detail → related practice or source → optional contribution.

Visitors should encounter meaningful content without authentication or an introductory quiz.

### B. Share a practice

Contribute → choose “share a practice” → describe it → provide context → add optional documentation and sources → choose attribution and sharing preferences → preview → submit → confirmation and private management access.

Use five short stages with progress, back navigation, and preserved fields:

1. **What do you do?** Required title and short description. Optional original name and language.
2. **How did you learn it?** Required relationship to the practice: personal experience, learned from someone, observation, or source-based research. Ask for context in free text. Place and community fields are optional and self-described.
3. **Show how it works.** Require a written account or accessible description accompanying media. Offer optional steps, materials, signs of success, and adjustments. One concise account is sufficient; avoid forcing completion of every prompt.
4. **What would you like to attach?** Optional images, YouTube links, references, and explanatory notes. Source-based submissions require at least one identified source. Firsthand accounts do not require an academic citation.
5. **How should it be shared?** Public name or anonymity, private email, publication permission, media permissions, and optional reuse licence. Preview the public appearance and clearly identify information that stays private.

Save drafts deliberately and explain where they are saved. A local draft may be stored on the device with a clear “clear draft” action; do not store credentials or private access tokens there. Offer “email me a link to continue” if the backend supports it. Preserve input after validation or network errors. Show success only after the server confirms persistence.

### C. Add a variation

Practice → “do you do this differently?” → shorter form with parent entry visible → what is similar, what changes, and how you learned it → attribution and permission → preview → review submission.

A variation has its own author, sources, context, and stable page. It never overwrites the parent. Present both as related accounts without ranking either as the correct version.

### D. Help me think of something

Contribution page → optional prompt picker → select or skip a prompt → normal contribution form.

Prompts: measuring without a tool; remembering without writing; knowing when food is ready; a game learned by watching; organising turns; making something without written instructions. Keep this optional and lightweight.

### E. Suggest a source

Sources page or practice detail → add source type and bibliographic information → explain its relevance → optionally link a practice and specific passage → attribution → submit for review.

Support source-only contributions. A good reference does not need to become a complete practice entry immediately. Source suggestions and corrections use the same private access mechanism as other submissions and are never published automatically.

### F. Manage or withdraw

Private email access → submission status → edit, respond to editorial feedback, change attribution, or withdraw.

Use short-lived, single-use email sign-in links that establish a scoped session. A public submission ID must not grant editing access. Existing published content stays visible while an ordinary revision is reviewed; withdrawal should hide it immediately through a verified contributor action. Remove withdrawn material from public search and APIs. Explain any minimal retained moderation records in the privacy notice.

## 10. Sources and citations: a core feature

Support scholarly and informal sources with equally careful attribution. Source type indicates what an item is, not a quality score. Whether a source supports a particular claim depends on its content and context. A demonstration video can document a technique; that alone does not establish the technique's historical origin.

Supported types:

- Academic article or conference paper.
- Book or chapter.
- Thesis or dissertation.
- YouTube or other hosted video.
- Personal blog, essay, or newsletter.
- Artist/project website or documentation.
- Podcast or other audio.
- Interview or oral account.
- Archive, exhibition, or institutional webpage.
- Other, with a custom label.

Shared fields: type, title, creator/author/channel, publication date if known, language, URL if available, access date, short relevance annotation, and submitter. Academic additions: DOI, venue, volume/issue, page range. Book additions: publisher, edition, chapter and optional ISBN. Video/audio additions: platform, duration if known, and optional timestamp range. Oral accounts: speaker attribution or anonymity, interviewer if relevant, date if known, permission and a note on whether a public recording exists.

Allow unknown dates and creators without inventing values. Permit print and oral references without a URL. Preserve original titles and add optional translations. A required title or descriptive label plus known attribution is sufficient for an initial suggestion; editors can request missing details.

Each association between a source and an entry has a **relationship**:

- documents this practice;
- supports this specific claim;
- informs this interpretation;
- offers a related example;
- further reading or viewing.

Also store a note explaining the relationship and a locator: page, chapter, timestamp, section, or paragraph. The same source can serve different purposes in different entries.

Citations should attach to stable content block IDs rather than fragile raw text offsets. Render inline numbered links near the relevant passage, with a keyboard-accessible popover or footnote target. Display complete references below the entry with backlinks. A reference without a specific passage can appear under further reading; do not imply it supports every sentence.

Use consistent human-readable formatting rather than requiring contributors to know a citation style. Examples of formatting rules, using placeholders rather than invented references:

- Author. “Article title.” Venue, year. DOI/link. Relevant page.
- Channel. “Video title.” YouTube, date. Relevant timestamp and link.
- Author. “Post title.” Blog name, date or “date unknown.” Link.
- Speaker or chosen attribution. Personal account/interview, date if known. Shared with permission; recording unavailable if applicable.

Provide a “copy reference” button. Preserve supplied titles and dates; never generate plausible bibliographic metadata. Automatic metadata fetching is optional later. Manual entry must work fully in the first release.

## 11. Sources catalogue and media behaviour

The source catalogue lets visitors search titles, authors, annotations, and filter by type and topic. Cards show title, creator, type, date if known, and a short relevance note. Detail pages list associated practices and the relationship to each.

YouTube videos use click-to-load, privacy-conscious embeds with no autoplay and an external-link fallback. A cited timestamp should open the relevant point where supported. Do not download or rehost videos. For blogs and articles, link to the original and store metadata plus original annotations; do not copy full articles or scrape copyrighted images. Clearly label quotations and keep them limited.

Support ordinary Unicode and right-to-left text in titles and contributions. Store captions or summaries for media, with a clear distinction between an original transcript and a contributor-written summary.

If a link fails or embedding is disabled, retain the citation and show a useful fallback. “Link checked” and “editor reviewed” must mean exactly those things; neither proves the source's claims. Never label a source peer-reviewed solely because its type is “academic.”

## 12. Editorial workflow

Protected queue tabs: new practices, variations, sources, corrections, and revisions. States: draft → submitted → needs changes → published, with declined and withdrawn terminal outcomes as appropriate. Store reviews and publication events separately from content.

Editors see the public preview, private contact information, permissions, source annotations, and changes from the previous revision. They can request clarification, suggest tags, edit with attribution, publish, or decline with a reason. Material changes to a person's account should be returned for contributor approval. Do not make silent substantive rewrites.

Publication checks: intelligible account; appropriate attribution; permission to publish media and attributed oral material; no exposed private contact details; cited material actually relevant to linked claims; interpretations distinguished from reported experience.

Allow anyone to suggest a correction without publicly posting a comment. Use moderation and basic rate limits. Avoid a public discussion forum in version one.

## 13. Data model

Use persistent identifiers and explicit relationships. Suggested entities:

| Entity | Main fields |
| --- | --- |
| Contributor | ID, public display name, private email/auth identity, attribution preference |
| Practice | ID, slug, type, parent practice ID if variation, contributor ID, status, current published revision ID |
| PracticeRevision | ID, practice ID, title, original name, language, summary, context, relationship to practice, structured content blocks, proposed tags, dates |
| Media | ID, owner, storage key or external URL, type, alt text, caption, creator credit, permission, licence, publication state |
| Source | ID, type, title, creators, date with precision/unknown handling, URL, DOI, type-specific metadata, language, public annotation, review state |
| Citation | ID, practice revision ID, content block ID if applicable, source ID, relationship, locator, annotation |
| Tag and PracticeTag | ID, label, category, association author or origin |
| Submission/Review | ID, entity/revision reference, state, private feedback, editor ID, timestamps |
| Correction | ID, target entity, proposed correction, references, submitter, state |
| PermissionRecord | ID, owner/entity, consent version, publication scope, reuse choice, timestamp |

Separate public and private fields in server responses. Store source creator and source submitter separately. Deduplicate likely identical sources by canonical URL or DOI, while allowing editor decisions for different editions or versions. Do not merge distinct practices because titles are similar. Use database constraints to prevent dangling variation and citation links.

## 14. Permissions and contributor control

Publication permission and permission for third-party reuse are different choices. Default to credit plus no additional reuse licence unless the contributor deliberately selects one. Do not apply an open licence to the whole collection, or to linked third-party works, by default. Record separate rights for text and uploaded media when needed.

Use a short, understandable confirmation that the contributor is entitled to share the material and has permission for identifiable people or attributed private accounts where relevant. Explain that knowledge intended to remain private should not be uploaded. Offer approximate place descriptions; exact location is unnecessary.

Keep a visible correction/contact route. Add a concise privacy explanation covering private email, drafts, uploads, publishing, withdrawal, and retention. Do not present this project brief as legal advice or fabricate a compliance certification.

## 15. Technical requirements and scope

### Frontend organisation

Keep markup, styling, application logic, and sketches in separate readable files. Suggested structure, adaptable to the host:

```text
index.html
pages/                 # other HTML views, if using multiple pages
css/
  tokens.css           # supplied palette, typefaces, spacing variables
  base.css
  layout.css
  components.css
js/
  app.js
  api.js               # persistent backend adapter
  forms.js
  citations.js
  sketches/
    pattern-study.js
assets/
  fonts/
  images/
  references/          # local design inputs; exclude from public build if not site assets
data/
  demo.json            # explicitly illustrative local data
README.md
DESIGN-NOTES.md
```

Use CSS Grid/Flexbox, media queries, and CSS custom properties. Use native form controls and browser APIs where practical. Pin the p5.js dependency to a tested version; document loading it locally or from a versioned CDN. A lightweight development server or optional bundler is acceptable, but do not make a frontend framework a dependency. Document running over HTTP rather than opening files through `file://`.

Connect vanilla JavaScript to the backend through `api.js`. Keep demo and production adapters explicit; do not silently fall back to local storage after a production submission fails. Never place privileged database keys or moderation credentials in client-side JavaScript. Public service configuration is acceptable only with correct server-side permissions.

### Backend, media, and accessibility

Use server-side validation and authorization for every mutation. Public reads return published revisions only. Contributors can manage only their submissions; editors have explicitly granted roles. Protect unpublished media and private feedback. Add CSRF protection where applicable, output sanitization, request rate limits, and safe upload handling. Accept only intended file types with size limits, verify actual file type, and strip image location metadata from public derivatives.

MVP media: image upload, text, and externally hosted video/audio links. Defer raw video uploads and transcoding. Do not accept arbitrary embed HTML. Allowlist supported embed hosts and require safe HTTP(S) URLs. If remote metadata fetching is added, protect it against internal-network requests and redirects to private addresses.

Persist entries, sources, permissions, reviews, and citations in the database. Use object storage for images; do not put binary uploads in the source repository. Keep secrets server-side. Supply migrations, environment variable examples without credentials, and setup instructions. Email confirmation must reflect actual delivery capability; in local demo mode, use clearly marked development handling.

Accessibility: semantic headings, visible focus, labelled inputs, accessible errors, keyboard operation, non-colour status labels, readable contrast, reduced-motion support, and mobile layouts without horizontal overflow. Source popovers must work without hover. Preserve form data when moving between stages.

Performance: responsive compressed images, lazy loading below the fold, no autoplay or background video, and no third-party embeds until requested. Public entry pages should have meaningful metadata and share previews. Drafts, admin routes, and private management pages must not be indexed.

## 16. Seed content and factual integrity

Create 6–8 clearly labelled illustrative entries for development only, covering several activities and formats. Potential scenarios include measuring rice water, a clapping sequence, a knitting repeat, organising turns, and remembering directions. Include at least one linked variation and one text-only entry.

Use fictional demo attribution explicitly labelled as such. Do not invent community testimony, real people's quotations, historical origins, academic references, video URLs, DOIs, or interview permissions. Do not make a placeholder look like a real citation. Demo content must be excluded from a production publication by default.

Where real seed references are requested, retrieve and inspect each source, record accurate metadata, and annotate what it supports. Verify academic claims with appropriate original scholarship; inspect the actual creator's page or video for informal sources. A bibliography of impressive titles is not enough. Do not claim that this brief contains a researched bibliography: it specifies how the website should handle one.

## 17. MVP boundaries

Build now: homepage; explore/search/filter; practice pages; new practice and variation forms; source suggestions and catalogue; inline citations; contributor management; protected moderation; image uploads; responsive and accessible layouts; persistent backend.

Defer: public comments, likes, followers, reputation scores, interactive world map, automatic translation, AI-generated interpretations, automatic citation extraction, graph visualisation, raw video upload, and “share your attempt.” Keep schemas extensible without displaying unfinished controls.

## 18. Acceptance criteria

1. A visitor can find and read an entry, follow its cited passage to a source, and see why that source is linked.
2. Filters survive refresh and browser navigation; zero results offer a clear recovery.
3. A contributor can submit a firsthand account without an academic source or computational tag.
4. A source-based account prompts for an identified source; print and oral sources work without URLs.
5. A contributor can attach a paper, a YouTube timestamp, and a blog reference without fields or formatting breaking.
6. A source-only suggestion enters moderation and can later connect to multiple practices.
7. A variation keeps its own author and sources and never changes the parent entry.
8. A successful submission persists across sessions and is invisible publicly until approved.
9. Unauthorized users cannot read drafts, private emails, feedback, or unpublished uploads, or mutate another contributor's content.
10. Contributor edits create revisions; pending revisions do not overwrite the published version. Withdrawal removes public access.
11. Editors can review, request changes, and publish; ordinary visitors cannot access those actions.
12. Keyboard and mobile users can complete the form, inspect citations, and recover from validation errors without losing content.
13. Broken external media falls back to a source link; no external embed autoplays.
14. Demo records are unmistakable and cannot accidentally enter the production collection.
15. The frontend uses HTML, CSS, vanilla JavaScript, and p5.js without a frontend component framework. Essential content and actions remain in the DOM.
16. The supplied reference folder has been inspected; actual palette values and supplied typefaces are applied and documented. Any missing assets or provisional substitutions are explicitly listed.
17. The p5.js component uses the shared palette, works at mobile sizes, respects reduced motion, and does not block reading or contributing if it fails to load.
18. Deep links and refresh work in the documented hosting configuration, and client code contains no privileged backend secrets.

## 19. Implementation sequence and handoff

First inspect the repository and supplied reference/palette/typeface folder, summarise the design cues and colour/font mappings, and report a concise implementation plan using the required HTML/CSS/vanilla JavaScript/p5.js stack. Then build the visual foundation with clearly labelled demo data; implement the database and permission boundaries; connect submission, citation, and review workflows; verify the complete experience.

Test the meaningful risks: publication visibility, contributor/editor authorization, revision handling, citation and variation relationships, submission persistence, and validation failure recovery. Manually inspect desktop and mobile layouts and keyboard navigation. Do not stop at a static mockup when backend integration is feasible.

Deliver readable HTML/CSS/JavaScript and p5.js files, schema and migrations, safe demo seed data, asset mapping and design notes, setup instructions, a short explanation of the content/source model, test results, and an explicit list of any services still needing credentials. Keep deployment and unresolved production configuration clearly separate from completed functionality.

The guiding experience is: encounter a practice → recognise something from your life → share your version → discover how someone else does it differently.
