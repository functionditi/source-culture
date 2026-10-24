# Source Culture

A working **local demo** of a collective notebook of everyday knowledge. Built with semantic HTML, plain CSS, vanilla JavaScript ES modules, and a small p5.js pattern study. There is no frontend framework or build step.

The supplied fonts, primary palette (`palette/image copy.png`), and all three visual references inform the design. See [DESIGN-NOTES.md](DESIGN-NOTES.md).

The homepage and collection now follow the user's [Negotiating Ungers](https://www.negotiating-ungers.eu/) layout reference: continuous text and images in four reading columns. Hovering or focusing a desktop column widens it and enlarges its text. Heading buttons also select a column. On smaller screens the streams stack and section controls support touch navigation. The supplied PP Editorial New fonts give section headings and project titles an editorial voice; PP Mori carries body text, navigation, and forms.

The header offers White, Olive, and Charcoal appearances, with Olive as the default. Dark reading text is pure white (`#FFF`), with caramel display headings and accents. Olive uses white links with caramel underlines; Charcoal uses caramel links. White keeps olive text, brick headings, and pure-orange links. An explicit appearance choice is saved on the device and applies before the page paints. Changing appearance preserves open form input. The wordmark reads `<source culture>`.

Shorter desktop columns fill their remaining height with alternating rectangular grids inspired by the supplied `drawHDB` study. Each grid pairs the active page background with a random palette accent. The background follows appearance changes and the accent stays fixed during hover, resizing, and theme changes. Accents exclude the three appearance backgrounds so the pair stays distinct. The artwork uses CSS grid, works without p5 or a brush library, and is hidden in the stacked mobile layout.

The numbered column headings use larger Editorial New type, coloured caramel in dark appearances and brick in White. The three contribution section headings use the palette's slate blue (`#6378A3`). Column spacing remains open, without vertical divider rules. A slim four-row grid sits beside the header wordmark and stays visible on mobile; it pairs the current page background with a stable palette accent.

Local-demo JavaScript and CSS revalidate on each visit. The changed image/grid module chain uses a version query to replace older cached code, including the former Prāsa placeholder renderer, on a normal reload.

The supplied homepage copy is arranged as a definition and four readings in column 1, a shared project repository in columns 2–3, and contribution guidance in column 4. The central columns take their featured project titles (“experiments with rice” and “Prāsa”) beneath one shared repository introduction. Repository filters select projects, practices, and experiments, updating those titles to match. The definition field carries the visitor's own text into the moderated contribution form; it does not submit or publish it automatically. The rice project has a local detail page, and Prāsa links to Dhulipalla's article.

## Run locally

Requires Python 3.11+ and Pillow. Node is optional; npm scripts are convenient aliases for Python commands.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
EDITOR_EMAILS=editor@example.test .venv/bin/python server/app.py
```

Open **http://127.0.0.1:8000**. If Pillow is already installed, `EDITOR_EMAILS=editor@example.test npm run dev` also works. Use HTTP rather than opening `index.html` through `file://`.

In VS Code, **Terminal → Run Task → Source Culture: start app** runs the same server. Live Server’s “Go Live” button only serves files and does not run the Python API. A page opened on port 5502 will therefore receive an HTML 404 for `/api/config`. The site now explains this and offers an “open the local app” link instead of showing a JSON parser error. Run the app and use port 8000 for browsing, submissions, and private management.

The server handles all documented routes and deep-link refreshes: `/`, `/explore`, `/practices/[slug]`, `/contribute`, `/sources`, `/sources/[id]`, `/about`, `/manage`, and `/admin`. This is not a static-only application: putting only `index.html` on a static host will not provide its API. A reverse proxy must forward the complete application, including `/api` and `/media`.

## Try the complete flow

1. Read a practice and follow its numbered citation to the source and its annotated connection.
2. Share a practice through the five stages. Firsthand accounts require neither an academic source nor a logic tag. Source-based accounts require an identified reference; print and oral sources work without a URL. You can add several references, image attachments, and external media links.
3. Preview and submit. Only a successful database transaction produces confirmation. The account remains private.
4. Request management access using the private email supplied. **The demo sends no email.** Read the private server-side development outbox:

   ```sh
   .venv/bin/python server/app.py --outbox
   ```

   Open the appropriate link and press “sign in with this link”. For a submission made before signing in, review it in your private notebook and choose “confirm this account & permissions”. This prevents someone else from publishing under a previously verified email. Links expire after 15 minutes, work once, and establish an HttpOnly session. No access tokens are stored in localStorage. The outbox, database, uploads directory, design inputs, and environment files are never served as static files.

5. To review, request a link at `/admin` for the email explicitly listed in `EDITOR_EMAILS`. Read that link in the same private terminal outbox. There is no default editor role and entering an editor email does not itself sign you in.
6. Publish source suggestions before the practice that cites them. Reviewers can request changes or decline with a reason. Source-only suggestions can be connected to several practices with a relationship, locator, and explanatory note, during review or later.
7. In `/manage`, respond privately to feedback, submit a revision, change public attribution, or withdraw. Pending revisions leave the published revision visible. Verified withdrawal immediately removes public content and image access.

The public submission ID is a reference number, not an editing credential. The site has no public profiles, popularity ranking, likes, comments, or follower counts.

## Data and backend choice

Python’s standard library plus SQLite keeps the backend small and inspectable, with no managed-service credentials required for local use. Shared state belongs to the server, not a browser. Database transactions persist contributions across browser sessions and server restarts. `js/api.js` is the replaceable vanilla-JavaScript API adapter.

The default ignored `.runtime/` contains SQLite, a private development outbox, and sanitised image files. Keep it on a durable volume to retain submissions. `DATA_DIR` selects a different directory; use the same value for the server and outbox command. Do not commit or publish this directory. Back up the database and image directory together.

Schema: [server/migrations/001_initial.sql](server/migrations/001_initial.sql). The migration runs idempotently on startup.

- `contributors` contains private email and verification state; it is never exposed publicly.
- `entities` holds persistent identifiers, stable slugs, kind, parent/target links, publication state, and the current published revision pointer.
- `revisions` contains immutable proposed public content with numbered versions. Ordinary revisions do not change slugs. `aliases` supports redirects if slugs are deliberately migrated later.
- `citations` joins a specific revision and stable block ID (`story`, `account`, `judgement`) to a source, with a relationship, locator, and annotation. Associations with no passage are further reading. Source creator and source submitter are distinct.
- Source metadata lives in source-entity revisions: known bibliographic fields, Unicode titles, optional URLs/dates/creators, and type-specific fields. Nothing is inferred or fetched automatically. Existing published sources with the same canonical URL/DOI, edition, title, creator, and date can be reused. Distinct print/oral items are not merged by title.
- `media` records image ownership, descriptions, caption, credit, permission, and storage key. Pillow verifies the actual type, rejects unsupported/oversized images, applies orientation, resizes to 1800 px, and writes a fresh WebP with no location metadata. No raw video uploads or arbitrary embed HTML are accepted.
- `permissions`, `confirmations`, `reviews`, and `messages` retain consent, verified per-revision approval, editorial events, and private conversations separately from public content.

Public responses are explicit allowlists of published revisions. Citation visibility also checks the source’s live publication state. Internal reference payloads, emails, editorial conversations, and storage keys are not in public responses. All writes validate on the server; owner/editor checks, same-origin JSON requests, session CSRF tokens, basic rate limits, safe text rendering, a restrictive content security policy, and private image authorization are included.

Images currently use the server’s private filesystem as **local demo storage**. Access passes through the authorised `/media/[id]` handler with `no-store`; a storage key is never a public URL. A production object-storage adapter must preserve that authorization boundary and only issue short-lived private signed URLs for unpublished images.

## Demo content and assets

Seven fictional development practices, one linked variation, one text-only practice, and one explicitly fictional internal scenario source are in `data/demo.json`. There are no fabricated academic references, documentary photographs, testimonies, DOIs, or video links. SVGs are original explanatory illustrations and are labelled accordingly. Reference images are design inputs, never site content.

`data/editorial.json` separately contains the two user-supplied project listings and four real readings. These are not fictional testimony. Their author/title/date metadata was checked against the supplied publisher and institution pages. The paper first appeared online on 19 October 2025 and is assigned to the journal's 2026 volume. Records are loaded into SQLite idempotently for the local preview; existing revisions and withdrawals are never overwritten. An internal reserved owner identity identifies editorial records without claiming the named authors submitted them or granted any new permissions. Like the other local preview records, they remain excluded in production mode by default.

The repository uses the supplied `assets/projects/experiments-with-rice.JPG` and `assets/projects/prasa-example.png`, with an automatic duotone-and-grain treatment across the homepage, collection, and detail views. The homepage excludes the fictional fixture entries, while `/explore` retains their explicit demo labels for testing the original practice flows. New contributor entries carry an `entry_type` of `project`, `practice`, or `experiment` and still require ordinary moderation.

Project images are displayed through `/project-images/<original filename>`. Pillow corrects EXIF orientation, limits the longest edge to 1800 px, converts to greyscale, normalises the tonal range, maps shadows to the palette's olive green `#49512C` and highlights to `#FFFFFF`, then adds stable monochromatic grain. Originals stay untouched. Treated WebP copies live in ignored `.runtime/project-images/` (or `DATA_DIR/project-images`) and are reused until the source contents or settings change. JPEG, PNG, WebP, and TIFF files are supported, including uppercase extensions. Only image files directly inside `assets/projects` can use this route; symlinks and traversal paths are rejected.

Edit [data/project-image-style.json](data/project-image-style.json) to adjust colours, `noise` (0–64; default 8), `autocontrast` (percent trimmed from each end; default 1), `max_edge`, or WebP `quality`. The image request automatically regenerates a changed recipe. To prebuild every supported file in the folder:

```sh
npm run images:build
```

Adding an image does not create a repository entry. Reference it through the processed-image route when assigning project media; the two existing project views are already connected. This reproduces the described treatment with adjustable settings rather than claiming Photoshop's unspecified ink curves and noise settings are identical.

**All submissions created in demo mode, as well as seed entities, are marked as development data.** `APP_MODE=production` excludes them from public collection/detail APIs and the editor queue, even if a development database is accidentally reused. Prefer a fresh production database regardless. Do not mark development records as production content.

The p5 library is locally vendored at **2.3.3**, with its licence notice. Its instance-mode pattern sketch reads CSS palette tokens, uses `noLoop()`/event-driven redraws, observes container size, caps pixel density, and disposes on navigation. It has no continuous motion. HTML controls and a text description work when the library is blocked. See the official [p5 download page](https://p5js.org/download/) and [`noLoop` reference](https://p5js.org/reference/p5/noLoop/).

YouTube players are explicitly click-to-load through the privacy-enhanced host, without autoplay. Supported timestamps are retained and an original-source link stays available if embedding fails. Other hosted audio/video sources remain ordinary links; no external metadata is fetched.

## Verification

```sh
npm test
# or: .venv/bin/python -m unittest discover -s tests -v
python3 tests/verify_browser.py
```

The second command uses installed Chrome (macOS path by default, override `CHROME_BIN`) with a temporary profile and an isolated database. It uses the Chrome DevTools protocol, requires permission to open local sockets/Chrome, and writes screenshots to ignored `test-results/`. It does not change your working demo database.

See [docs/VERIFICATION.md](docs/VERIFICATION.md) for the checked behaviors and limits.

## Production connections still required

This checkout is **not publicly deployed** and the standard-library HTTP server is a local development server. `APP_MODE=production` is a data-isolation/SMTP integration mode, not a claim of completed production hosting.

Before launch, supply:

- A production API host/process with HTTPS and a durable database volume (or replace the backend while keeping the API contract). Configure `BASE_URL` to the exact public origin. No static-host-only deployment.
- SMTP delivery credentials: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Production never silently falls back to the development outbox. Delivery failures are shown without pretending an email was sent. Live delivery has not been tested here.
- Private object storage and an image-storage adapter, preserving upload validation, metadata removal, ownership, and unpublished-media protections. No storage bucket credentials are present or tested.
- Explicit editor emails, operational backups, shared/edge rate limiting for multiple workers, and a configured contact/retention policy.
- The web embedding licences for the supplied commercial typefaces; no licence documents were included. Font metadata and current local usage are documented in the design notes.

`.env.example` lists configuration names without credentials. The application reads environment variables; it does not automatically load `.env`. Keep SMTP and storage credentials server-side.
