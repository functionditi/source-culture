# Verification record

Verified locally on 23–24 October 2026. No public deployment was performed. Tests use temporary databases and do not alter the working demo collection.

Follow-up startup fix: four JavaScript client regression tests cover HTML 404/200 responses, valid JSON, server validation errors, malformed JSON, and preservation of failed submissions without retries or browser-storage fallback. The browser script also reproduces a static preview returning HTML for `/api/config`, checks the recovery screen, then enables the API and verifies the retry loads the collection. Use `npm run dev` / the VS Code “Source Culture: start app” task; Live Server alone cannot run the backend.

The four client tests passed for the startup follow-up, and the running app's `/api/config` and `/api/practices` responses were verified as JSON. The initial follow-up Chrome run was declined. A later browser run for the expanding-column redesign was approved and passed, including the static-preview recovery regression.

Layout follow-up: the Negotiating Ungers reference was inspected in Chrome before and after hover. The new homepage and collection passed browser checks for four visible reading columns, width and font enlargement on hover, selection retained after pointer exit, keyboard focus selection, mobile section-jump controls, reduced motion, PP Mori, and no horizontal overflow at 1440, 390, and 320 px. Desktop, expanded-column, and mobile screenshots were opened for visual review. The full existing contribution, sign-in, moderation, source, citation, and p5-failure flows also passed.

## Automated API checks

`npm test`: **18 Python API tests and 4 JavaScript client tests passed**.

Covered:

- SQLite persistence across store instances; pending submissions invisible publicly.
- Public response exclusion of private email, session credentials, editorial feedback, internal reference payloads, and private conversations.
- Ownership checks for private reads, revisions, withdrawal, confirmation, and editorial messages; explicitly authorised editor access.
- Immutable numbered revisions; pending/needs-changes revisions preserve the current published content; approved revisions replace the publication pointer.
- Variations retain their own author/content and do not change the parent.
- Single-use, expiring sign-in links and HttpOnly/SameSite cookies.
- Per-submission verified consent: knowing an already-verified email cannot impersonate its contributor or make a submission eligible for publication.
- Source-based validation; mixed paper/video/blog/oral metadata; print/oral sources without URLs; rejection of unsafe URLs and unconfirmed oral permissions.
- Source-only moderation and connections to several practices, with relationship/locator/annotation.
- Citation visibility when a source is withdrawn; stable block IDs and preservation of print source IDs across revisions.
- A contributor cannot read someone else's unpublished source revision through the references on their own practice.
- Actual image type verification, SVG rejection, WebP derivatives, metadata removal, private image HTTP authorization, and withdrawal visibility.
- CSRF and origin rejection through the actual HTTP server.
- Protection of private files and design inputs; deep-link/refresh responses, missing-entry 404s, public metadata, and content security headers.
- Exclusion of all seed and locally submitted development records in production data mode, including when reusing a demo database.
- Editorial preview loading is idempotent and never revives withdrawn records; project/practice/experiment classification is validated and does not grant editorial status to a contributor.

## Browser verification

`python3 tests/verify_browser.py`: **passed** in installed headless Chrome, with a temporary browser profile and database.

Checked desktop at 1440 px and mobile at 390 px and 320 px. Screenshots were opened and visually inspected for the homepage, mobile contribution stage, and source view. Checks include:

- PP Mori remains the reading-text family; PP Editorial New loads for project titles and display headings.
- Continuous reading columns, palette, procedural artwork, source details, readable forms, and no horizontal overflow at the tested widths.
- Search and multiple filters, useful zero-result recovery, URL state after refresh and browser back.
- Inline citation → specific source → explanation of the connection.
- Five-stage practice submission, native required-field validation, preserved input after back navigation, private email excluded from public preview, server-confirmed persistence.
- Development sign-in link, verified contributor confirmation, private management, explicit editor sign-in, and successful editorial publication.
- Source-only suggestion without a URL, followed by editor connections to two practices.
- Source-based empty-reference error, repeating paper/video/blog fields, YouTube timestamp URL preservation, Unicode title input, and attachment-stage layout at 320 px.
- p5 canvas, CSS-token palette, static event-driven behavior, and a blocked-library pass proving essential browsing and text descriptions remain available.
- Keyboard focus and reduced-motion browser setting; no JavaScript runtime exceptions in the checked flows.

The content update also passed checks for the four reading links, all/project/practice/experiment filters and empty recovery, the user's definition reaching the moderation form without appearing in the URL, and the rice project's local detail page and labelled placeholder. New desktop, expanded-column, and mobile screenshots were opened for visual review. The primary source pages for Dhulipalla, Swalwell, Ali, and Hui were inspected; bibliographic metadata and short relevance annotations are recorded separately from fictional development fixtures.

The Editorial New pairing passed the existing Chrome checks after the font update. Computed styles confirm Mori body text and Editorial New project titles, and the display face loads successfully. Updated desktop, expanded-column, and mobile screenshots were visually inspected; column expansion and the 1440, 390, and 320 px overflow checks still pass.

Appearance follow-up: the full browser flow passed with the palette and theme controls. The focused `python3 tests/verify_browser.py --appearance-only` check covers White, Olive, and Charcoal, including Olive as the default under both system preferences, the `<source culture>` wordmark, pure-white dark reading text and caramel accents, persistence across reload and navigation, and preserving typed text when switching. Computed body, small-heading, and link colours meet 4.5:1 against page and panel surfaces in every appearance; larger display headings use caramel. Screenshots cover 1440, 1024, 390, and 320 px; dark contribution forms were also checked. Visual review found a placeholder exceeding its narrow tablet column; its width is now constrained and the focused layout checks pass.

Column-grid follow-up, 24 October: `python3 tests/verify_browser.py --grids-only` passed. Decorative grids fill the remaining height after the reading content and finish at the same bottom edge after all four column expansions. Checks confirm two distinct original palette colours per grid, stable pairs during resize and appearance changes, hover over the artwork selecting its column, mobile section jumps, hidden grids in the stacked layout, filtered and collection views, and operation with p5 blocked. Desktop bottom-of-column and mobile screenshots were opened for visual review; the new module also passes Node's syntax check.

Heading and wordmark follow-up: the same focused check passed with the larger Editorial New column headings and the slim grid beside the logo. Browser styles confirm at least 28 px display type and caramel colour in the default appearance. The logo grid has ten cells in two rows, stays 18 px high, and remains visible on mobile. Updated desktop, 1024 px tablet, and 320 px mobile screenshots were visually inspected; column expansion, bottom fills, and section jumps continue to pass. The modified JavaScript modules pass syntax checks.

Prāsa image follow-up: `python3 tests/verify_browser.py --image-only` passed for the homepage, collection, and detail view. The supplied PNG loads with natural dimensions 2644 × 1790 and retains its proportions on desktop and mobile; the old placeholder copy is absent. Screenshots were visually inspected. The targeted HTTP protection test passed with the exact image path allowed, `image/png` and a valid PNG signature, while private paths remain inaccessible. The restarted local preview returns HTTP 200 for the image.

Cached-image and grid-background follow-up: a browser reproduction confirmed that an hour-cached renderer can retain the old Prāsa placeholder. `--cache-only` now passes with that legacy client graph warmed into the cache: a normal visit fetches the versioned renderer and displays the PNG with caching still enabled. Local-demo JS/CSS responses use `no-cache`; image responses keep their existing policy. The targeted HTTP route test and `--image-only` pass, including image loading before hover. Updated `--grids-only` checks pass for both column and wordmark grids: one resolved cell colour exactly matches the active page background in White, Olive, and Charcoal, and the distinct random palette accent stays fixed. Updated screenshots were visually reviewed, and the live preview serves the PNG and revalidating client module successfully.

Blue-heading and logo-grid refinement: `--grids-only` passes with the three contribution headings at the exact slate colour `rgb(99,120,163)`, zero-width vertical borders on reading columns and the repository overview, and two distinct non-background colours in the logo grid under every appearance. Column fills retain their background-plus-accent rule. Desktop and mobile screenshots were visually inspected; expansion, theme changes, section jumps, and grid sizing continue to pass.

Denser-grid and header-spacing follow-up: the column patterns now repeat in both directions, doubling their rows and columns. The header retains its five-column, two-row pattern at 32 px high and stretches between the wordmark and Explore with 16 px spacing on desktop. The existing `--grids-only` browser check passes with the updated header sizing assertion, including 1440, 1024, 390, and 320 px layouts, all column expansions, appearance changes, collection/filter views, and p5 unavailable. Desktop, tablet, mobile, and bottom-of-column screenshots were visually inspected; the grid module passes Node's syntax check.

Header-background colour follow-up: the Source Culture grid now pairs the current page background with a stable palette accent. `--grids-only` passes with the header colour assertion updated for White, Olive, and Charcoal; the desktop screenshot was visually inspected and the grid module passes Node's syntax check.

Automatic image-treatment follow-up: five `test_project_images.py` tests pass for EXIF orientation, orange/white endpoints, source preservation, metadata omission, repeatable grain, cache reuse and invalidation after source/settings changes, transparency, size limits, supported uppercase JPEG names, and rejection of symlinks/traversal. The targeted HTTP protection test passes for both processed WebPs and private-path rejection. `--image-only` passes for treated rice and Prāsa images before hover, in filtered collection views, and on desktop/mobile detail pages; generated files and browser screenshots were visually inspected. `--cache-only` also passes after switching to the processed route. `npm run images:build` successfully warmed both files, and the live preview returns `200 image/webp` for the rice photograph. Originals remain in `assets/projects`; the default display copies are 1350 × 1800 and 1800 × 1219.

Repository-title and blue-duotone follow-up: `npm test` passes all 23 Python and 4 JavaScript tests, including slate-blue/white image endpoints. `npm run images:build` regenerates both existing project display copies using `#6378A3` and `#FFFFFF`, retaining grain and original files. `--image-only` passes for distinct featured-project column headings, updates after all four category filters, a single title per featured project, image loading before hover, collection/detail views, and desktop/mobile proportions and overflow. `--grids-only` passes with the revised heading heights, all four column expansions, background-aware fills, theme changes, mobile jumps, and p5 blocked. Generated blue images and desktop/mobile repository screenshots were visually inspected. The live preview at port 8000 serves the treated rice image as `200 image/webp`.

Olive-duotone follow-up: the image recipe now maps shadows to palette olive `#49512C` and highlights to white `#FFFFFF`, retaining the existing grain. Both project display copies regenerate successfully with `npm run images:build`; the five focused image tests pass, including olive/white endpoints, orientation, original preservation, and cache invalidation. The Prāsa derivative was visually inspected and the modified JavaScript passes its syntax check.

Header-grid row follow-up, 24 October: the wordmark grid now has four rows and twenty cells within the existing 32 px height. `python3 tests/verify_browser.py --grids-only` passes with the updated cell and row assertions, including desktop/mobile layouts, all appearances, column expansion, and collection views. Desktop and 320 px mobile screenshots were visually inspected, and the grid module passes Node's syntax check.

Link-treatment follow-up: every link uses `#BA3D05` behind white, underlined text, including navigation, wordmarks, inline references, and linked buttons. `python3 tests/verify_browser.py --appearance-only` passes with its existing colour assertions updated for the shared treatment and contrast measured against the link background. White, Olive, and Charcoal appearances, saved preferences, preserved form input, and 1440, 1024, 390, and 320 px layouts pass. Desktop and mobile screenshots were visually inspected.

Blue-link and menu follow-up: links now use `#6378A3` with white, underlined text. Header links, including the wordmark and menu, have transparent backgrounds and use the appearance's reading text. `--appearance-only` passes in all three appearances at desktop, tablet, and mobile widths with the exact link colours checked; the prior orange-background link contrast assertion was removed because the user now specifies the blue/white pair. Desktop and mobile screenshots were visually inspected for the blue links and transparent menu.

Unique bottom-grid colours follow-up: the four column grids choose accents without replacement from the five-colour palette. The existing `--grids-only` check passes with a uniqueness assertion in its shared colour checks, covering homepage, filtered and collection views, all four expansions, appearance changes, and p5 unavailable. Background cells still match the page, and each accent stays fixed while resizing or switching appearance. The bottom-of-column screenshot was visually inspected; Node's syntax check passes.

Screenshots are in ignored `test-results/` after running the script. Browser interaction found and resolved a duplicate fragment-navigation race during sign-in; the final flow passes.

## Limits

This is functional local-demo verification, not a production launch certification or a complete screen-reader audit. Live SMTP delivery, object storage, a production HTTP host, commercial font web licences, real third-party video availability, multi-process rate limiting, and a production retention/contact policy remain unconfigured or unverified. Video failure retains an original-source link by design; no real documentary video was invented for testing.
