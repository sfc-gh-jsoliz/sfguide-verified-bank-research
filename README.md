# Verified Bank Research

A grounded, self-verifying research assistant for **a bank/FIG research or credit team**: pick a bank and its peers, and Snowflake Cortex writes a one-page research note (scale, profitability, capital) using **only** governed call-report data, then a verifier fact-checks the draft and flags it **Verified** or **Needs review**.

## What it shows

- A **gallery** of generated research notes, each badged Verified or Needs review.
- A **sidebar** to generate a new note from a subject bank, peers, and a reporting quarter.
- The grounding pattern end to end: a governed **semantic view** → a verified **fact pack** of the only numbers the model may cite → a **grounded draft** written under strict DATA RULES → a **verifier** pass that catches any unsupported or hedged claim.

Capabilities: Cortex `AI_COMPLETE`, Cortex Analyst, Cortex Agents, Semantic Views, Streamlit in Snowflake, Snowflake SQL.

## How it works

- The **Streamlit app** builds a fact pack from the data and calls Cortex **`AI_COMPLETE`** twice — once to draft the note under DATA RULES, once to verify it against the fact pack — then stores the result in a table and renders the gallery.
- **Setup** also creates a Cortex **Analyst semantic view** and a Cortex **Agent** over it. These are explorable independently in Snowsight (AI & ML → Agents, and the semantic view in your schema) so a user can chat with the data in natural language. The Streamlit app itself does not call the agent — it calls `AI_COMPLETE` directly against the fact pack.
- Both setup scripts produce the identical `BANK_QUARTERLY_METRICS` shape, so the app, semantic view, and agent are unchanged whether running on synthetic or real data.

## Prerequisites

- A Snowflake account.
- A role that can **`CREATE DATABASE`** and **`CREATE WAREHOUSE`** (setup creates a dedicated database and warehouse).
- Snowflake **Cortex** available in your region (the app uses `AI_COMPLETE`; default model `claude-sonnet-4-5` — change the `MODEL` parameter if your account differs).
- **Streamlit in Snowflake** to run the app.
- Sample (synthetic) mode is fully self-contained — there is nothing to buy and no listing to mount.

## Setup

1. **Create the objects (synthetic sample data):** run [`app/setup_synthetic.sql`](app/setup_synthetic.sql). It creates the dedicated database, schema, and warehouse and builds everything on fictional-bank data — no Marketplace listing required.
2. **Deploy the app:** create a Streamlit in Snowflake from [`app/streamlit_app.py`](app/streamlit_app.py) (upload to a stage and `CREATE STREAMLIT`, or paste it into a new Streamlit in Snowsight). It shows a "sample data" banner.
3. **Explore the agent (optional):** in Snowsight → AI & ML → Agents, open **Bank Research Agent**, or query the semantic view directly.
4. **Open the notebook (optional):** [`notebook/lab-01-verified-institution-agent.ipynb`](notebook/) walks through the full pattern (semantic view → fact pack → grounded draft → verifier) cell by cell.

To run on **real** data instead, [`app/setup.sql`](app/setup.sql) documents the free/real data swap: it grounds on real US bank call-report data from the free **Financial Data Package** (`SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE`) public listing. Mount that listing, then run `setup.sql` in place of the synthetic script — the app, semantic view, and agent are unchanged.

## Objects created

All objects are created in the dedicated database/schema below. Names and purpose are enumerated from [`app/setup_synthetic.sql`](app/setup_synthetic.sql) and [`app/setup.sql`](app/setup.sql).

| Object | Type | Purpose |
|---|---|---|
| `SNOWPACK_BANK_RESEARCH` | Database | Dedicated, isolated home for this pack |
| `SNOWPACK_BANK_RESEARCH.CORE` | Schema | Holds all tables, views, and the agent |
| `SNOWPACK_BANK_RESEARCH_WH` | Warehouse (XSMALL) | Compute for setup and the app |
| `BANK_QUARTERLY_METRICS` | Table (synthetic) / View (real) | One row per bank per quarter: assets, deposits, net income, ROA/ROE, capital, loans |
| `DATA_SOURCE_INFO` | View | Marker the app reads to show the sample vs. live banner |
| `BANK_RESEARCH_SV` | Semantic view | Cortex Analyst model over the metrics for natural-language queries |
| `REPORTS` | Table | Stores generated research notes with their Verified / Needs review status |
| `BANK_RESEARCH_AGENT` | Cortex Agent | Conversational agent over the semantic view, usable in Snowsight |
| `streamlit_app.py` | Streamlit app | The research-note gallery and generation UI |

## Cost & time

- Setup and app deployment take only a few minutes.
- Compute runs on an **XSMALL** warehouse; all queries are small (a dozen fictional banks over a handful of quarters).
- Generating a note calls `AI_COMPLETE` twice, so expect a small amount of Cortex AI token cost per note; everything else is negligible.

## Known limitations

- Sample mode uses **synthetic, fictional-bank data** — illustrative only, not real institutions.
- The hosted static landing/try page uses **mocked AI responses**, not live inference.
- This is an **illustrative example, not a production system** — review, test, and add governance before any real use.

## Cleanup

Run [`app/teardown.sql`](app/teardown.sql) to drop the dedicated database (and everything in it) and the dedicated warehouse.

## Learn more

- [Cortex AISQL (`AI_COMPLETE`)](https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql)
- [Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
- [Cortex Analyst](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)
- [Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)

## License

Apache 2.0 (see [`LICENSE`](LICENSE)). Illustrative example, as-is, not supported by Snowflake Support. Review and test before any production use.
