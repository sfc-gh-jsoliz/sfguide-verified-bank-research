# Snow Packs v2: instructions for your CoCo

Use this as a prompt or checklist to bring a Snow Pack up to the v2 bar. It applies along with the catalog's CONTRIBUTING.md, which wins if anything conflicts.

## Goal
The app and landing page should look and feel like a commercial enterprise product that a first-time visitor wants to use, not a starter template. Two packs that set the bar:
- Auto Finance Portfolio Analytics: https://sfc-gh-ooral.github.io/sfguide-auto-finance-portfolio-analytics/try/
- Workforce Intelligence: https://sfc-gh-ooral.github.io/sfguide-workforce-intelligence/try/

Match their polish and depth, but don't copy their look.

## 1. Design first: `docs/DESIGN.md`
Before writing UI code, write `docs/DESIGN.md` with:
- **A visual brand:** logo mark as inline SVG, voice, palette and type, suited to the pack's audience. Don't invent a coined product name. Title the app with the pack's plain name, for example "Workforce Intelligence". A short, real, plain-English word that fits the job is fine only if it reads naturally, like "Odometer" for auto-finance portfolio analytics; when in doubt, use no name.
- **A design direction:** palette with hex values, typography, layout model, density, chart style and motion.
- **What makes it distinct:** look at at least 5 packs in the live catalog and name what you are avoiding. No two packs should share a palette, layout or hero treatment.

## 2. The app
- A branded app shell: sidebar or top navigation, logo, user/role chip, and an environment badge for Sample or Live.
- Rich, purpose-built screens:
  - KPI tiles with trends;
  - real charts with tooltips and legends;
  - data tables with sort, filter and status pills;
  - detail drawers or panels;
  - empty, loading and error states.
- Motion with taste: transitions, skeleton loaders, hover states, subtle gradients or glass, animated counters.
- Tailwind design tokens taken from DESIGN.md, and dark mode if the design calls for it. Contrast at least WCAG AA.
- Works at 390 px and on desktop with no horizontal scroll.
- A Sample/Live switch, with no silent fallback to sample data in Live mode.

## 3. AI interactions
- A realistic 4–8 second delay with staged reasoning steps, for example "Reading 1,204 records… Grouping by segment… Drafting summary…".
- A streaming-style text reveal, with citations or sources where they make sense.
- A clear "Sample AI response" label in Sample mode.

## 4. Data and claims
- A seeded, deterministic synthetic data generator: fixed seed, and re-running gives identical output. Document the planted stories in `data/README.md`.
- Synthetic data only: no real company or customer names.
- Check the current Snowflake docs for every feature you use, and label preview features as Preview. Only claim capabilities you actually ran in Live mode.

## 5. Landing page: `docs/index.html`
- Its own visual identity, matching the app's brand.
- A problem-first headline, captioned screenshots from `docs/images/`, alt text that matches each image, the disclaimer, and docs links.
- No CDN scripts.

## 6. Hosted example: `docs/try/`
- `npm run build:example` writes `docs/.nojekyll`. Without it, GitHub Pages drops the `_next` folder and the app renders blank.
- After deploying, check that every JS and CSS file referenced from `/try/index.html` returns 200.

## 7. Self-review before you call it done
- Go through every CONTRIBUTING Must and Should, and report each as pass, fail or skipped (with a reason).
- Run a leak scan of files and full git history for account identifiers, user names, secrets and real company names.
- Commit and push after every finished step.
