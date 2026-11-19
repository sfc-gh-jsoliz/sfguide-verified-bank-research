-- ============================================================================
-- HOL-01 — setup_synthetic.sql  (TRY mode: NO Marketplace listing required)
-- ----------------------------------------------------------------------------
-- Stands up the SAME app/agent as setup.sql, but on SYNTHETIC data generated
-- in-account — so anyone can try it without mounting any Marketplace listing.
--
-- >>> REAL DATA IS AVAILABLE. <<<
-- This is sample data with FICTIONAL banks. For real US bank call-report data,
-- mount the FREE "Financial Data Package" (SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE)
-- listing from the Snowflake Marketplace and run setup.sql instead — the app,
-- semantic view, and agent all work unchanged against the real data.
--
-- Creates the same objects as setup.sql in SNOWPACK_BANK_RESEARCH.CORE:
--   BANK_QUARTERLY_METRICS (here: a TABLE of synthetic rows, not a view),
--   DATA_SOURCE_INFO (mode = 'synthetic'), BANK_RESEARCH_SV, REPORTS, agent.
-- Run ONE of {setup.sql, setup_synthetic.sql}, not both.
-- ============================================================================

-- Dedicated, isolated environment for this Snow Pack.
CREATE DATABASE IF NOT EXISTS SNOWPACK_BANK_RESEARCH;
CREATE SCHEMA IF NOT EXISTS SNOWPACK_BANK_RESEARCH.CORE;
CREATE WAREHOUSE IF NOT EXISTS SNOWPACK_BANK_RESEARCH_WH WITH WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE INITIALLY_SUSPENDED=TRUE;
USE WAREHOUSE SNOWPACK_BANK_RESEARCH_WH;
USE SCHEMA SNOWPACK_BANK_RESEARCH.CORE;

-- 1. Synthetic fact table (fictional banks; deterministic, no RANDOM) -----------
CREATE OR REPLACE TABLE BANK_QUARTERLY_METRICS
  COMMENT = 'SYNTHETIC sample data (fictional banks). Real FFIEC/FDIC data is available free on the Snowflake Marketplace — run setup.sql to switch.'
AS
WITH banks AS (
  SELECT * FROM VALUES
    (90001,'Summit National Bank','New York','NY','OCC',3200000000000),
    (90002,'Harbor Point Bank, N.A.','Boston','MA','OCC',2100000000000),
    (90003,'Cascade Trust Company','Seattle','WA','FRS',1450000000000),
    (90004,'Meridian Commercial Bank','Chicago','IL','FDIC',880000000000),
    (90005,'Granite State Bank & Trust','Manchester','NH','FDIC',420000000000),
    (90006,'Blue Ridge National Bank','Charlotte','NC','OCC',260000000000),
    (90007,'Pacifica Bank','San Francisco','CA','FRS',155000000000),
    (90008,'Sunbelt Community Bank','Phoenix','AZ','FDIC',68000000000),
    (90009,'Lakeshore Federal Savings','Milwaukee','WI','OCC',31000000000),
    (90010,'Ironwood Savings Bank','Denver','CO','FDIC',12500000000),
    (90011,'Keystone Union Bank','Pittsburgh','PA','FDIC',5400000000),
    (90012,'Delta Regional Bank','Memphis','TN','FDIC',2300000000)
    AS b(id_rssd, bank_name, city, state, federal_regulator, base_assets)
),
quarters AS (
  SELECT DATEADD(quarter, -SEQ4(), '2026-06-30'::date) AS quarter_end
  FROM TABLE(GENERATOR(ROWCOUNT => 8))
),
grid AS (
  SELECT b.*, q.quarter_end,
         DATEDIFF(quarter, q.quarter_end, '2026-06-30') AS q_ago   -- 0 = latest
  FROM banks b CROSS JOIN quarters q
),
calc AS (
  SELECT
    id_rssd, bank_name, city, state, federal_regulator, quarter_end,
    -- mild deterministic growth back through time, + per-bank variation
    ROUND(base_assets * (1 - 0.012 * q_ago) * (1 + 0.004 * (id_rssd % 7)), 0) AS total_assets,
    0.006 + 0.0009 * (id_rssd % 9) - 0.0003 * q_ago                            AS roa_frac
  FROM grid
)
SELECT
  id_rssd,
  bank_name,
  city,
  state,
  federal_regulator,
  'Commercial Bank'                         AS category,
  TRUE                                      AS is_active,
  quarter_end,
  total_assets                              AS total_assets,
  ROUND(total_assets * 0.72, 0)             AS total_deposits,
  ROUND(total_assets * roa_frac / 4.0, 0)   AS net_income_qtr,
  ROUND(roa_frac, 6)                        AS return_on_assets,
  ROUND(roa_frac / 0.10, 6)                 AS return_on_equity,       -- equity ~10% of assets
  ROUND(total_assets * 0.10, 0)             AS total_equity_capital,
  0.10                                      AS equity_to_assets,
  ROUND(total_assets * 0.12, 0)             AS ci_loans,
  ROUND(total_assets * 0.03, 0)             AS credit_card_loans,
  ROUND(total_assets * 0.25, 0)             AS re_loans_domestic
FROM calc;

-- 2. Data-source marker (the app reads this to show the right banner) ----------
CREATE OR REPLACE VIEW DATA_SOURCE_INFO AS
SELECT 'synthetic' AS mode,
       'Synthetic sample data (fictional banks), no Marketplace listing required. Real US bank call-report data is available FREE on the Snowflake Marketplace (Financial Data Package / SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE). Run setup.sql to switch this app to real data.' AS note;

-- 3. Semantic view (identical to setup.sql) ------------------------------------
CREATE OR REPLACE SEMANTIC VIEW BANK_RESEARCH_SV
  TABLES ( banks AS SNOWPACK_BANK_RESEARCH.CORE.BANK_QUARTERLY_METRICS PRIMARY KEY (ID_RSSD, QUARTER_END)
           WITH SYNONYMS = ('banks','financial institutions','depository institutions')
           COMMENT = 'Quarterly call-report metrics per US bank (SYNTHETIC sample data)' )
  FACTS (
    banks.total_assets AS TOTAL_ASSETS, banks.total_deposits AS TOTAL_DEPOSITS,
    banks.net_income AS NET_INCOME_QTR, banks.return_on_assets AS RETURN_ON_ASSETS,
    banks.return_on_equity AS RETURN_ON_EQUITY, banks.equity_to_assets AS EQUITY_TO_ASSETS,
    banks.ci_loans AS CI_LOANS, banks.credit_card_loans AS CREDIT_CARD_LOANS
  )
  DIMENSIONS (
    banks.bank_name AS BANK_NAME WITH SYNONYMS = ('bank','institution','institution name') COMMENT = 'Legal name of the bank',
    banks.state AS STATE WITH SYNONYMS = ('headquarters state'),
    banks.city AS CITY,
    banks.federal_regulator AS FEDERAL_REGULATOR WITH SYNONYMS = ('regulator','primary regulator'),
    banks.quarter_end AS QUARTER_END WITH SYNONYMS = ('quarter','period','as of date','reporting date'),
    banks.report_year AS YEAR(QUARTER_END) WITH SYNONYMS = ('year')
  )
  METRICS (
    banks.total_assets_usd AS SUM(banks.total_assets) COMMENT = 'Total assets in USD',
    banks.total_deposits_usd AS SUM(banks.total_deposits) COMMENT = 'Total deposits in USD',
    banks.net_income_qtr_usd AS SUM(banks.net_income) COMMENT = 'Quarterly net income in USD',
    banks.avg_return_on_assets AS AVG(banks.return_on_assets) COMMENT = 'Average ROA (fraction; 0.015 = 1.5 percent)',
    banks.avg_return_on_equity AS AVG(banks.return_on_equity) COMMENT = 'Average ROE (fraction)',
    banks.bank_count AS COUNT(DISTINCT banks.id_rssd) COMMENT = 'Number of distinct banks'
  )
  COMMENT = 'Verified bank research semantic view (SYNTHETIC sample data).';

-- 4. Output table + agent (identical to setup.sql) -----------------------------
CREATE TABLE IF NOT EXISTS REPORTS (
  run_id          STRING      DEFAULT UUID_STRING(),
  subject         STRING, draft_md STRING, report_md STRING,
  status          STRING, edits_applied INT, residual_hedges INT,
  created_at      TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE AGENT BANK_RESEARCH_AGENT
  COMMENT = 'HOL-01 verified bank research agent (synthetic sample data)'
  PROFILE = '{"display_name": "Bank Research Agent", "color": "blue"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto
  orchestration:
    capabilities:
      analytical_search: true
  instructions:
    response: 'You are a buy-side bank analyst. Use ONLY figures returned by the Analyst tool; never invent numbers. ROA/ROE/equity ratios are fractions (0.015 = 1.5%). Express dollars in $B/$T. Be concise and cite the quarter. Note: this instance may be running on synthetic sample data.'
    orchestration: 'For any bank metric, ranking, or comparison, use the BankMetrics Analyst tool.'
    sample_questions:
      - question: 'Top 5 banks by total assets in 2026'
  tools:
    - tool_spec:
        type: cortex_analyst_text_to_sql
        name: BankMetrics
        description: 'Quarterly call-report metrics (assets, deposits, net income, ROA, ROE, capital, loans) per US bank.'
  tool_resources:
    BankMetrics:
      semantic_view: SNOWPACK_BANK_RESEARCH.CORE.BANK_RESEARCH_SV
  $$;

-- Smoke test:
-- SELECT bank_name, quarter_end, total_assets, return_on_assets
-- FROM BANK_QUARTERLY_METRICS WHERE quarter_end='2026-06-30' ORDER BY total_assets DESC;
