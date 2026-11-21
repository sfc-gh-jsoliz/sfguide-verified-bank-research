# Design: Assaywell Research

## Brand

**Assaywell Research** is a fictional bank research desk. An *assay* tests metal for purity, and a *hallmark* is the stamp that certifies it. The product works the same way: every research note is tested against governed figures before it gets its mark. (The name is coined; we found no financial firm by that name.)

- **Audience:** bank and financial-institution research analysts, credit analysts and their reviewers.
- **Voice:** a research editor. Short, exact, evidence-first. It says "Verified against 18 governed figures", never "AI-powered insights". Numbers come with their quarter and source.
- **Logo mark:** a hallmark punch: a rounded shield with a check stroke and a small bar under it, as inline SVG so there's no image file.

```svg
<svg viewBox="0 0 32 32" aria-hidden="true">
  <path d="M16 2.5 27 6.5v8.6c0 7.1-4.6 12.2-11 14.4C9.6 27.3 5 22.2 5 15.1V6.5Z" fill="#D9AE55" stroke="#16181D" stroke-width="1.6"/>
  <path d="m10.6 15.6 3.8 3.8 7.2-8" fill="none" stroke="#16181D" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M11 23.4h10" stroke="#16181D" stroke-width="1.6" stroke-linecap="round"/>
</svg>
```

## Design direction

### Palette

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F1F0EC` | `#121316` | Page (assay-office stone) |
| `--surface` | `#FFFFFF` | `#1A1C20` | Panels, tables, drawers |
| `--surface-2` | `#E8E7E1` | `#23262B` | Table heads, wells, skeletons |
| `--line` | `#D3D1C8` | `#32353B` | Rules and borders |
| `--ink` | `#1A1C21` | `#ECEAE3` | Text |
| `--muted` | `#585A60` | `#A3A39C` | Captions, axes |
| `--bar` | `#16181D` | `#0C0D0F` | Top bar (graphite, both modes) |
| `--brass` | `#7C5A12` | `#D9AE55` | Brand, links, active tab, subject-bank series |
| `--brass-fill` | `#D9AE55` | `#D9AE55` | Logo, primary button fill (dark text on it) |
| `--verified` | `#1B6646` | `#5CC995` | Verified hallmark, passing checks |
| `--review` | `#9C3F0B` | `#F0965A` | Needs review, unsupported claims |
| `--assay` | `#5B3970` | `#C9A2DB` | AI / verifier output, Cortex steps |

Contrast (checked with `scripts/contrast.py`): every text token passes WCAG AA (4.5:1) on `--bg`, `--surface` and its own 12% tinted pill. Ink on the brass button is 8.6:1.

### Typography
- **Newsreader** (serif, OFL) for headings and the research note body: it reads like a published note.
- **Inter Tight** (OFL) for UI text and tables.
- **JetBrains Mono** (OFL) for figures in tables, citations, SQL and the fact pack.
- Fonts ship as woff2 files in `docs/fonts/` (with OFL.txt). No CDN.

### Layout model
- **Top bar, no sidebar.** Graphite bar with logo, five tabs (Desk, Compose, Notes, Ask the desk, Data), the environment badge (Sample/Live switch) and a role chip ("Bank research analyst"). On phones the tabs become a horizontal scroller under the bar.
- **The note is a page with a margin.** A research note renders as a paper column with a right-hand *assay margin*: every figure in the note gets a numbered marker, and the margin lists its source row (`BANK_QUARTERLY_METRICS · bank · quarter · column`) with a pass/fail tick. On phones the margin folds under the note.
- **Desk** is a dashboard: four KPI tiles with trends, a peer chart, the coverage table with sort, filter and status pills, and a bank drawer.
- Density: medium. 14 px UI text, 17 px note text, 8 px spacing grid, 10 px radius.

### Charts
Hand-written SVG (no chart library, no CDN). The subject bank is a solid brass line or bar; peers are thin graphite lines; the peer median is dotted. Every chart has a legend and a hover/focus tooltip with the exact figure and quarter.

### Motion
- Staged pipeline steps tick in as each Cortex call finishes; the note text streams in word by word.
- The hallmark *stamps* onto a verified note (scale 1.25 → 1 with a short ink spread). Rejected claims get a struck-through rust highlight.
- Skeleton shimmer while loading, 150 ms hover lifts, animated KPI counters. All motion is disabled under `prefers-reduced-motion`.

## How it differs from the live catalog

We reviewed the landing pages and Try apps of Auto Finance Portfolio Analytics (dark green with lime, mono), Workforce Intelligence (violet with a serif), Collections Copilot (indigo with Bricolage Grotesque), Regulatory Change Tracker (forest green and red on warm paper), Payment Fraud Workbench (near-black with pink and amber), Client Account Views (saffron), Complaints Intelligence (burgundy and teal), Continuous Control Testing (vermilion on graph paper), Governed Context Layer (lime on graphite), Loan File Review (cobalt blueprint), Market Data Discovery (harbor navy) and Trade Reporting Validation (amber on black).

What we avoid:
- **No left rail or sidebar**, which most of those use. Navigation is a graphite top bar with tabs.
- **No lime, saffron, cobalt, navy, violet or burgundy brand colour.** Brass on graphite and stone is new to the catalog.
- **No KPI-grid hero.** The landing hero is a single research note being stamped with the hallmark, with the assay margin showing its sources.
- **No dark-first look.** Light by default (an editorial reading product), with a full dark mode via `prefers-color-scheme` and a toggle.
- The previous version of this pack used the shared sky-blue template look; v2 drops it completely.
