# Verified Bank Research: v2 changes

This branch brings the pack up to the Snow Packs v2 bar (see [COCO-V2-INSTRUCTIONS.md](COCO-V2-INSTRUCTIONS.md)). It keeps the pack's data stories, Snowflake features, stack (Streamlit in Snowflake for Live, a static page for the no-account example, plus the notebook) and owner line. What changed is the app, the landing page, the polish, and a few correctness and confidentiality fixes found along the way.

## Summary

| Area | v1 | v2 |
|---|---|---|
| Brand | Shared sky-blue template look | **Verified Bank Research**: graphite and brass, hallmark logo, serif notes ([docs/DESIGN.md](docs/DESIGN.md)) |
| Hosted example | One static page with client-side, template-generated notes | Five-screen app in `docs/try/` replaying output **captured from a live run**, labeled "Sample AI response" |
| Streamlit app | Gallery + sidebar form, no Sample mode | Branded shell, Sample/Live switch, five tabs matching the hosted example, no silent fallback |
| Verifier | Free-text JSON, sometimes unparseable | `AI_COMPLETE` **structured output** (`response_format`), one verdict per claim |
| Citations | None | Deterministic figure-to-source-row matcher; the assay margin shows the source of every figure |
| Agent | Created in setup, not used by the app | **Ask the desk** calls it via `DATA_AGENT_RUN` in Live mode |
| Data | 12 banks with linear formulas | 12 coined banks, 3 peer groups, seeded pseudo-noise, 3 planted stories ([data/README.md](data/README.md)) |
| Access | Run everything as the setup role | Least-privilege role `SNOWPACK_BANK_RESEARCH_ROLE` owns the pack |
| Site layout | Pages from the repo root | Pages from `/docs` (landing, `try/`, images, fonts) |

## Screen by screen

### Landing page (`docs/index.html`, was `index.html`)
- **What:** New identity: graphite hero split into a stamped verified note, a problem-first headline, a five-step "how a note earns its hallmark" flow with the capability behind each step, six captioned screenshots, requirements and measured cost, and the disclaimer. Self-hosted fonts (OFL), no scripts, dark mode.
- **Why:** v2 needs a landing page with its own identity, every capability named and every screenshot captioned. The old three-step page used the shared template look.

### Desk (new)
- **What:** KPI tiles with trends and animated counters (assets under coverage, median ROA, clean drafts verified, planted claims caught), an 8-quarter ROA chart per peer group with a dotted peer median, tooltips and legend, a watchlist panel, and a coverage table with sort, search, peer-group and status filters and status pills. A bank profile drawer shows six metric cards with sparklines and that bank's watchlist signals.
- **Why:** v1 opened on a gallery with no context. Analysts start from coverage and exceptions, so the planted stories (ROA compression with a loss, deposit runoff, thin capital) now surface on the first screen through the `WATCHLIST_SIGNALS` view.

### Compose (was the sidebar form)
- **What:** Subject, peers, quarter and a "plant an unsupported claim" toggle. Five staged pipeline steps tick off with their live timings, then the note streams in, gets its hallmark, and opens with the assay margin.
- **Why:** The pipeline (fact pack, draft, verify) is the pack's story, so it is now visible step by step. The planted-claim toggle keeps v1's "try breaking the verifier" idea as a one-click demo.
- **Correctness fixes found while testing live:** the v1 prompts let the model convert units and compute changes itself, and the verifier then disagreed about rounding (for example, rejecting a correct 0.88% for 0.8764%). The fact pack now carries SQL-formatted `*_display` strings, year-over-year changes in pp and the asset rank, and both prompts work from those. On the captured run, 12/12 clean drafts were Verified and 12/12 planted claims were caught, on synthetic data.

### Notes (was the gallery)
- **What:** A sortable, filterable table of `REPORTS` (status, test-draft tag, claims checked, rejected, figures traced, run time). Each row opens a wide drawer with the note, the verifier findings, the per-figure sources and the fact pack JSON.
- **Why:** A gallery of cards doesn't scale or show why a note passed. The table and drawer make the verification evidence reviewable.

### Ask the desk (new)
- **What:** Chat with `BANK_RESEARCH_AGENT`. Shows staged steps, the answer, the rows returned and the SQL Cortex Analyst generated. Sample mode replays four captured questions.
- **Why:** v1 claimed Cortex Agents and Cortex Analyst, but the app never called them. v2 claims only what runs in Live mode, so the agent is now part of the app.

### Data (new)
- **What:** The objects, the semantic view's dimensions and metrics, the DATA RULES and the verifier's output schema.
- **Why:** Reviewers in regulated teams ask "what is the model told and what is it allowed to see?" This screen answers that.

### SQL, notebook and scripts
- `app/setup_synthetic.sql`: role and ownership, `BANKS` with peer groups, a deterministic generator (re-runs give an identical `HASH_AGG`), `WATCHLIST_SIGNALS`, a richer `REPORTS` table, the agent with a warehouse execution environment, and an app stage.
- `app/setup.sql` (real data): same structure; peer groups derived from total assets. **Not re-run for v2**, because the listing wasn't mounted in the test account.
- `app/teardown.sql`: drops as the owning role, then drops the role, and is safe to re-run.
- `app/research.py`: the shared live pipeline used by the app and `scripts/capture_sample.py`.
- Notebook: the fact-pack, draft and verify cells now use the same logic as the app. Default banks switched to the synthetic ones.
- `scripts/`: `capture_sample.py` (Live to Sample data), `build_example.sh`, `capture_screenshots.py`, `contrast.py` (WCAG check of the design tokens).

## What you need to do after merging

1. **GitHub Pages:** Settings > Pages > Deploy from a branch > `main`, folder **`/docs`** (was `/ (root)`). `docs/.nojekyll` is included.
2. Wait for the Pages build, then check `/try/` loads and its `app.css`, `app.js` and `data/*.json` return 200.
3. Optional but recommended: Settings > General > **Template repository**, and add topics such as `snowflake`, `cortex`, `banking`, `streamlit`.
4. To rebuild the Sample data and screenshots after changing prompts or data:
   ```bash
   # 1. run app/setup_synthetic.sql in your account
   SNOWFLAKE_ACCOUNT=<account> SNOWFLAKE_USER=<user> SNOWFLAKE_PRIVATE_KEY_PATH=<key.p8> \
     python scripts/capture_sample.py          # about 10 minutes; --resume continues a partial run
   bash scripts/build_example.sh               # copies data to docs/try/data and app/sample, writes docs/.nojekyll
   python3 -m http.server 8766 --bind 127.0.0.1 --directory docs &
   python scripts/capture_screenshots.py       # docs/images/*.jpg and docs/catalog/*.jpg (960x600, under 100 KB)
   # 2. run app/teardown.sql
   ```
5. The catalog entry will need new card images (`docs/catalog/verified-bank-research-1..7.jpg`) and updated alt text and features; the catalog maintainers handle that PR.

## Confidentiality

v2 uses synthetic data and coined bank names only.
