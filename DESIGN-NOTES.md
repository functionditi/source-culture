# Design inputs and application

Reviewed recursively on 23 October 2026. Original supplied files are unchanged. No accompanying notes or licence files were supplied.

## Primary palette

The user explicitly selected **`palette/image copy.png`** after being shown that two palettes were present. It is the sole primary palette. Printed hex labels take precedence over slight raster/compression variation, except for the demonstrably duplicated slate-blue label described below.

| Token | Hex | Application |
| --- | --- | --- |
| `--caramel` / `--rule` | `#DD9645` | Column rules, panel edges, selected appearance, illustrative artwork |
| `--rust` / `--accent` | `#BA3D04` | Interactive accents and the shared artwork palette |
| `--link-background` | `#6378A3` | Link backgrounds in all appearances, with transparent header links |
| `--link-text` | `#FFFFFF` | Link text and underlines; header links use the appearance's reading text |
| `--olive` | `#49512C` | White-mode body text, Olive background, labels on sand |
| `--slate` | `#6378A3` | Three contribution section headings, illustration fields, shared pattern palette |
| `--sand` | `#DEC199` | Notice banner, numbered markers, primary buttons, image placeholders, pattern ground |
| `--brick` | `#9E2524` | White-mode headings |
| `--ink` | `#120F05` | Charcoal background and illustration outlines |
| `--paper` | `#F4F4F4` | White background and appearance swatch |

The slate-blue block has a rotated `#9E2524` label that repeats the brick-red label and cannot describe the visible blue. Its flat interior is `(99,120,163)` / `#6378A3` (80,313 identical pixels); use that actual sampled swatch. The light unlabelled rectangle’s flat interior is `(244,244,244)` / `#F4F4F4`. Other printed RGB labels also repeat inconsistently; use the clearly printed hex labels above rather than those repeated RGB lines. Swatch interiors were inspected visually and measured, not averaged across the image.

The secondary `palette/image.png` was inspected and retained as an unused input. Its printed palette is `#C8C8C8`, `#86986C`, `#ACC4F9`, `#FF5900`, `#0D0D0D`, `#B06944`, `#FAB42A`, `#0C76FF`, `#FFB0D6`, `#E7E7E7`. It does not override the selected palette.

The header's White, Olive, and Charcoal buttons switch the full interface. Olive is the default, regardless of the system light/dark preference; an explicit device preference persists across navigation and reload, and is applied by an external script before styles paint. The HTML also declares Olive for the initial render. Appearance changes update CSS tokens without replacing forms or their contents. Storage failures leave switching functional. DOM and p5 share `css/tokens.css` palette values; artwork keeps its original swatches.

The White appearance uses the requested swatches directly for olive reading text and brick headings. Caramel rules and sand elements provide more colour throughout. Dark appearances use pure white and the original caramel. Links use the user-requested `#6378A3` background, white text, and a white underline. Links in the header, including its wordmark and menu, have transparent backgrounds and use the appearance's reading text so they remain visible on every theme. Wrapped inline links retain their background on each line, and the treatment persists on hover and focus:

| Appearance | Background | Surface | Reading text | Small headings | Links |
| --- | --- | --- | --- | --- | --- |
| White | `#F4F4F4` | `#EEE7DD` | `#49512C` | `#9E2524` | White, underlined, on `#6378A3`; transparent header |
| Olive | `#49512C` | `#3B4225` | `#FFF` | `#FFF` | White, underlined, on `#6378A3`; transparent header |
| Charcoal | `#120F05` | `#26291C` | `#FFF` | `#DD9645` | White, underlined, on `#6378A3`; transparent header |

Readability checks use WCAG relative luminance: White-mode text/paper is 7.65:1 and brick/paper 6.96:1. Browser checks require at least 4.5:1 for reading text against page and panel surfaces; the explicitly requested link colours are checked by their exact values. Large display headings use caramel in both dark appearances; caramel/Olive is 3.41:1, suitable for this larger type. Small Olive headings stay white. Sand elements use olive text (4.88:1). Slate remains in decorative artwork.

## Visual references

All three images were opened and visually inspected:

- `references/image.png`: Soundit event poster. A dense, modular two-column composition; bold sans hierarchy; boxed panels; thin outlines inside stronger boundaries; sequences of small rounded bars; directional arrows; recurring graphic symbols. Applied as a disciplined collection grid, fine card boundaries, numbered indexes, small sequence motifs, and direct navigation. The site's card grid remains square-edged and readable, rather than reproducing the poster's heavy framing.
- `references/image copy.png`: Rio graphic over a beach photograph. Oversized gestural letterforms; paths and directional connections; limited spot-colour combinations; radial symbols and repeating dots. Applied through arrows, route illustration, and compact p5 study. The photograph is not reused as documentary evidence. The initial asterisk identity was removed at the user's request.
- `references/image copy 2.png`: Paired mutton recipe posters. Strong typographic hierarchy; alternate colourways of one composition; an emphasis on family attribution; image and text working together. Applied through prominent contributor credit, consistent card anatomy, varied palette fields, and a clear display hierarchy. No portraits, cultural claims, faux ageing, or food photography were fabricated.

The current layout follows the user's later reference, [Negotiating Ungers](https://www.negotiating-ungers.eu/). Its live page, inline layout styles, and hover interaction were inspected, including desktop screenshots before and after moving to the second column. The reference uses four simultaneous text streams, gives the active stream about twice its neighbours' width, enlarges its typography, and lets text and images reflow continuously down the page.

Source Culture now uses the supplied column-specific copy: vernacular/decolonial framing and four readings in column 1; a shared repository heading, category controls, and the rice/Prāsa project grid across columns 2–3; and contribution guidance in column 4. The central introduction spans the two project columns while each reading column still expands independently. Column 02 takes its first project's title, “experiments with rice,” and column 03 takes “Prāsa”; that title appears once, above its image, rather than repeating “repository” or the project title. Filters update the titles with the featured entries. An empty column offers “what belongs here next?” or the empty-results message. Continuous paragraphs, indented successive paragraphs, inline links, and attribution retain the reference's reading character. The searchable collection uses the same reading columns, preserving result order. PP Mori body text is paired with Editorial New headings and the selected caramel/rust palette. Earlier poster references still inform the illustrations and numbering; the later website reference governs the layout.

On desktop the active column grows to a 2.25 share of available width and increases its text size. Hover, keyboard focus, or the column-heading button selects it; the most recently selected column stays wide when the pointer leaves. No adjacent content is hidden. Below 901 px the streams stack at a consistent reading size, with a compact section-jump navigation for touch. Reduced-motion settings disable resizing transitions. No dashboard chrome, gradients, stock cultural imagery, flags, or artificial paper texture.

The user's later `drawHDB` code and checkerboard reference inform decorative grids beneath shorter columns, on both the homepage and the collection. Alternating flat rectangles use weighted column widths and uniform or weighted floor heights; one arrangement keeps the supplied `[1,4,1,2,1]` spacing and ten floors. Each grid pairs `var(--background)` with one random primary-palette accent, chosen once per rendered column. Background cells follow White, Olive, or Charcoal immediately; the accent stays fixed while columns expand and themes change. Accent choices are caramel, pure orange, slate, sand, and brick, excluding the three appearance backgrounds so the pattern always remains visible. CSS flex and grid fill the available space to the common bottom edge, with no fixed artwork height, canvas allocation, brush library, texture, or animation loop. Grids sit after reading content, ignore pointer input, are hidden from assistive technology, and disappear when columns stack on mobile. They are decorative studies, not project documentation.

The four bottom grids draw their accents randomly without replacement from the five available colours, so no two bottom grids share an accent. Each keeps its selected accent through resizing and appearance changes; the header grid selects its colour independently.

## Fonts

All 14 OTF files were inspected with fontTools. Existing files are loaded directly; no derivative fonts or remote Google Fonts are used. `font-display: swap`, real weight/style mappings, sensible fallbacks, and `font-synthesis: none` are defined in `css/tokens.css`.

Typography updated at the user's request: PP Mori carries continuous body text, navigation, forms, metadata, and bibliographic titles. PP Editorial New regular carries display headings, numbered column headings, narrative section headings, and project titles. The four column headings use 28–36 px type on desktop and 30 px on mobile, with their index and arrow above the title. They use caramel in Olive and Charcoal, and brick in White. Editorial New italic appears in the wordmark. Both families use their supplied italic files; display text uses the real regular weight rather than a synthetic bold.

The header and footer wordmarks read `<source culture>`, with real escaped angle brackets, PP Mori for “source,” and Editorial New italic for “culture.”

A slim, 32 px-high four-row grid sits beside the header wordmark. It uses the same rectangle generator as the column fills and the supplied `[1,4,1,2,1]` widths. At the user's request, this logo grid pairs the current page background with either brick red (`#9E2524`) or orange (`#BA3D04`), chosen once per page load. The accent stays fixed across client-side navigation and appearance changes. It is decorative and stays visible on mobile; column fills retain their background-plus-accent rule.

The contribution headings “share a project or practice,” “suggest a source,” and “do it differently?” use the original slate-blue swatch (`#6378A3`) in every appearance. Vertical rules between reading columns and beside the shared repository overview have been removed, retaining the existing gutters and horizontal heading rules.

The text-only wordmark pairs “source” in PP Mori regular with “culture” in PP Editorial New italic, aligned on their baseline in the header and footer. The favicon uses a small, square version of the sketch's alternating grid, with `[1,4,1,2,1]` column widths and four equal rows in brick and paper. The starburst symbol is removed from all three locations.

| Supplied file | Inspected family/style | Use |
| --- | --- | --- |
| `PPMori-Regular_2.otf` | PP Mori / Regular | Body, navigation, forms, labels, metadata, 400 |
| `PPMori-Semibold.otf` | PP Mori Semibold / Regular | Semibold UI, 600 |
| `PPMori-RegularItalic.otf` | PP Mori / Italic | Body emphasis, 400 |
| `PPEditorialNew-Regular-BF644b214ff145f.otf` | PP Editorial New / Regular | Display and section headings, project titles, 400 |
| `PPEditorialNew-Italic-BF644b214fb0c0a.otf` | PP Editorial New / Italic | Wordmark and display emphasis, 400 |
| `PPMori-Black.otf` | PP Mori Black / Regular | Inventoried; unused |
| `PPMori-BlackItalic.otf` | PP Mori Black / Italic | Inventoried; unused |
| `PPMori-Extralight_2.otf` | PP Mori Extralight / Regular | Inventoried; unused |
| `PPMori-ExtralightItalic.otf` | PP Mori Extralight / Italic | Inventoried; unused |
| `PPMori-SemiboldItalic.otf` | PP Mori Semibold / Italic | Genuine semibold italic, 600 |
| `PPEditorialNew-Ultralight-BF644b21500d0c0.otf` | PP Editorial New / Ultralight | Inventoried; unused |
| `PPEditorialNew-UltralightItalic-BF644b214ff1e9b.otf` | PP Editorial New / Ultralight Italic | Inventoried; unused |
| `PPEditorialNew-Ultrabold-BF644b21500840c.otf` | PP Editorial New / Ultrabold | Inventoried; unused |
| `PPEditorialNew-UltraboldItalic-BF644b214faef01.otf` | PP Editorial New / Ultrabold Italic | Inventoried; unused |

Font permissions: Mori files report OS/2 `fsType=0`; Editorial files report `fsType=4` (Preview & Print embedding). These technical flags are not a webfont licence. No supplied licence establishes public web embedding rights. The requested fonts are used in this local private prototype; suitable licences must be supplied before public distribution. No embedding restrictions were removed or altered, and missing weights are not synthesised.

## New assets

`assets/illustrations/{rice,knit,clap,route,turns,cups}.svg` are original code-native illustrations using the primary palette. Their use is explicitly labelled as illustration of fictional development scenarios. The recipe-memory example intentionally has a designed text treatment. No reference image is served as collection content. No AI-generated documentary images were created.

The earlier `assets/illustrations/rice-grid.svg` is retained as an unused placeholder asset. The repository now uses the supplied rice photograph, `assets/projects/experiments-with-rice.JPG`, and `assets/projects/prasa-example.png`. Both originals were visually inspected. The rice image's EXIF orientation is corrected for display; its treated copy is 1350 × 1800, while Prāsa's is 1800 × 1219. Descriptive alt text accompanies both, with no cropping or placeholder captions.

`server/project_images.py` implements the requested repeatable image treatment using the existing Pillow dependency. It reads `data/project-image-style.json`: grayscale with 1% autocontrast, palette olive-green `#49512C` shadows and `#FFFFFF` highlights, then monochromatic uniform noise of ±8 RGB levels, WebP quality 92, and a maximum edge of 1800 px. The latest olive-green/white treatment replaces the earlier blue/white recipe. Tonal normalisation keeps the already-treated Prāsa source from being washed out by a second colour mapping. These are adjustable defaults for the described Photoshop process, not a claim of matching unspecified Photoshop curves exactly.

Project images are processed on first request through `/project-images/<filename>`, then cached by source contents, style settings, and recipe version in the ignored runtime directory. Noise is seeded from that fingerprint, so texture does not change on reload. Original files are never overwritten; derivatives omit source metadata. The same renderer powers `npm run images:build` for the whole folder. Browser responses revalidate so replacing an original or editing the style is reflected on the next image request.

`assets/vendor/p5-2.3.3.min.js` and `p5-LICENSE.txt` are the pinned local library and its upstream notice. The sketch has real HTML controls, a current-rule text description, event-driven redraws, and no continuous animation. Blocking the optional library must not block reading or contributing.
