# Data

All data in this pack is **synthetic**. The banks are fictional, with coined names, and any resemblance to a real institution is unintended.

## The generator

`app/setup_synthetic.sql` builds `BANK_QUARTERLY_METRICS`: 12 banks × 8 quarters (2024-09-30 to 2026-06-30), 96 rows.

- **Deterministic:** there is no `RANDOM()`. Variation comes from fixed pseudo-noise, `MOD(id_rssd * 7919 + q_ago * 104729 + 1299709, 1000) / 1000 - 0.5` and two siblings with other prime seeds. Re-running the script gives identical rows. Check it with `SELECT HASH_AGG(*) FROM BANK_QUARTERLY_METRICS;` after two runs.
- **Peer groups:** Large (4 banks, $0.87T to $3.18T in assets), Regional (4, $66B to $405B) and Community (4, $2.3B to $31B), stored in `BANKS.PEER_GROUP`.
- **Metrics:** total assets, deposits, quarterly net income, ROA, ROE, equity capital, equity/assets, and C&I, credit-card and domestic real-estate loans. Ratios are fractions (0.0115 = 1.15%), the same shape as the real-data view in `app/setup.sql`.

## Planted stories

| Bank | Peer group | Story | Where it shows |
|---|---|---|---|
| Ombrel National Bank | Regional | ROA compression to 0.46% in 2026-06-30 (down 0.48 pp from a year earlier), with a quarterly loss (ROA -0.21%) in 2025-12-31 | Watchlist "ROA compression" and "Quarterly loss", ROA chart, its notes |
| Kestrova Bank | Regional | Deposit runoff: deposits/assets falls 2 pp per quarter, from 72.0% to 64.0% over the year | Watchlist "Deposit runoff", bank profile |
| Pellandry Community Bank | Community | Thin capital: equity/assets 7.18%, against about 10% to 11.5% for every other bank | Watchlist "Thin capital", coverage table |
| Every bank | | One **test draft** per bank with a planted, hedged ROE forecast ("will likely reach around 18.5%…") added after the takeaway | The verifier should reject it; Notes library, "Planted claims caught" KPI |

Watchlist thresholds (view `WATCHLIST_SIGNALS`; the same rules run in the hosted example): deposits/assets down more than 6 pp in a year, any quarterly loss, ROA down more than 0.30 pp year over year, equity/assets below 8%. On this data set they flag exactly the three planted banks.

## Captured Sample data (`data/sample/`)

`scripts/capture_sample.py` runs the live pipeline in `app/research.py` and saves what it returns:

| File | Contents |
|---|---|
| `metrics.json`, `banks.json` | `BANK_QUARTERLY_METRICS` and the bank directory, read back from Snowflake |
| `notes.json` | 24 notes for 2026-06-30: one clean draft and one test draft per bank, peers = the bank's peer group. Each holds the fact pack, the draft, the verifier findings, the figure-to-source matches and the measured AI_COMPLETE timings |
| `agent.json` | Cortex Agent answers to four suggested questions, with the SQL Cortex Analyst generated and the rows it returned |

`bash scripts/build_example.sh` copies these files to `docs/try/data/` (the hosted example) and `app/sample/` (the Streamlit app's Sample mode).

AI output varies between runs, so a fresh capture can differ in wording, in the number of claims checked, and sometimes in a verdict. Notes that come back Needs review without a planted claim are kept as captured: they show the verifier catching a real drafting slip.
