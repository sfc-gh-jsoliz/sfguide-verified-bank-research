# Self-review (v2 rebuild, November 2026)

Checked on branch `v2-rebuild` of the fork. Live runs were in a Snowflake test account with key-pair auth only. The hosted checks ran against the fork's Pages preview (`sfc-gh-ooral.github.io/sfguide-verified-bank-research/`), because the upstream site serves `main` until this is merged.

## Build standard: "Before you call it done"

| Item | Result | Evidence |
|---|---|---|
| App runs from a fresh clone in mock mode | Pass | Fresh clone, no Snowflake env: Streamlit `AppTest` starts in Sample mode with no exceptions and 5 tabs; `docs/try/` serves from `python3 -m http.server` |
| Setup, live mode, cleanup in a clean role | Pass | `teardown.sql` then `setup_synthetic.sql` from clean (11.1 s); app run as `SNOWPACK_BANK_RESEARCH_ROLE`; `teardown.sql` then `SHOW DATABASES/WAREHOUSES/ROLES LIKE 'SNOWPACK_BANK%'` all empty; second teardown also succeeds |
| Files and git history grepped for secrets, account identifiers and user names | Pass for files; history reported to the maintainers separately | No account identifiers, hostnames, keys or real bank names in files or in this branch's text diffs |
| Pages URL and `/try/` checked signed out, phone width and dark mode | Pass (fork preview) | Every JS/CSS/JSON/font referenced returns 200; no horizontal scroll at 390 px or 1440 px in light and dark; no console errors |
| Every story beat visible in a screenshot | Pass | ROA compression and loss (`01-desk`, `02-compose`), deposit runoff (`07-bank`), thin capital (`01-desk`), planted claim caught (`04-note-review`) |

## v2 additions

| Item | Result |
|---|---|
| `docs/DESIGN.md` with brand, palette, type, layout, charts, motion and the packs it avoids | Pass |
| Branded shell: top nav, logo, role chip, Sample/Live badge | Pass (hosted and Streamlit) |
| KPI tiles with trends, charts with tooltips and legends, sortable and filterable tables with pills, drawers, empty/loading/error states | Pass |
| Motion: transitions, skeletons, hover, animated counters, reduced-motion support | Pass |
| WCAG AA contrast | Pass (`scripts/contrast.py`) |
| AI: 4–8 s staged steps, streaming reveal, sources, "Sample AI response" label | Pass |
| Seeded deterministic generator plus `data/README.md` | Pass (identical `HASH_AGG` over three generations) |
| Only Live-run capabilities claimed; docs checked | Pass (AI_COMPLETE, structured output, Cortex Agents via DATA_AGENT_RUN, Cortex Analyst, semantic view, SQL); all doc links return 200 |
| `docs/.nojekyll` | Pass |

## CONTRIBUTING Musts

| Must | Result |
|---|---|
| Business problem first; one industry (Banking) and function (Research) | Pass |
| Public `sfguide-` repo with Apache 2.0 LICENSE | Pass (his repo; LICENSE unchanged) |
| GitHub Pages enabled | Pass on the fork preview; **his repo must switch Pages to `/docs`** (V2-CHANGES.md) |
| Landing: problem and outcome on the first screen | Pass |
| Landing: screenshots of the running app, each with a caption naming the capability and alt text | Pass (6 figures plus the hero) |
| Landing: capability named per step; only tested capabilities | Pass |
| Landing: visible disclaimer; links to repo and docs | Pass |
| No Snowflake logo files; no internal sales motions | Pass |
| End-user app with a real workflow | Pass |
| No-account mode on bundled synthetic data, simulated output labeled | Pass |
| Live mode on Snowflake | Pass (Streamlit locally with key-pair auth; SiS object created and staged but not opened in Snowsight) |
| Synthetic data; self-contained setup with dedicated DB and XSMALL warehouse | Pass |
| Cleanup removes everything | Pass |
| No credentials, account identifiers or internal hostnames in code, screenshots or history | Pass for code and screenshots; history reported to the maintainers separately |
| User names redacted in output | Pass (`<YOUR_USER>` placeholders) |
| No customer names or identifiable logic; no internal programs | Pass at HEAD; **v1 history, see Open items** |
| GA features, preview features labeled | Pass (no preview features used) |
| README: prerequisites, run steps and objects, cost and time, limitations, Customize with Cortex Code, owner and review date, license and disclaimer | Pass |
| Outcomes as possibilities; synthetic results qualified | Pass |

## Shoulds

| Should | Result |
|---|---|
| Several screenshots telling the story | Pass |
| Prerequisites, time and cost near the top of the landing page | Pass |
| Phone width and dark mode | Pass |
| No trackers; no CDN | Pass |
| Sample/Live switch with setup steps when Live has no connection | Pass |
| Realistic AI delays with truthful steps; measured latency shown in Live | Pass |
| Capability badges on components | Pass |
| Least-privilege path | Pass |
| Edition note | Pass (Standard or higher) |
| Template repository, description and topics | Skipped: repository settings belong to the owner (V2-CHANGES.md step 3) |
| Short captioned video or GIF | Skipped: screenshots cover the workflow |
| Setup runs top to bottom with no find-and-replace | Pass |

## Open items (need a maintainer decision)

1. **His `main` history** still contains the v1 defaults: four real US bank names, and references to another non-public application and its internal object names. Removed at HEAD here; history is unchanged.
2. `app/setup.sql` (real data) wasn't re-run: the Marketplace listing wasn't mounted in the test account.
