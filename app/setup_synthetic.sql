-- ============================================================================
-- Verified Bank Research — setup_synthetic.sql  (no Marketplace listing needed)
-- ----------------------------------------------------------------------------
-- Builds the whole pack on SYNTHETIC data generated in your account:
-- 12 fictional banks x 8 quarters, generated deterministically (fixed seed
-- constants, no RANDOM), so every run produces identical numbers.
-- The planted stories are documented in data/README.md.
--
-- Real data is available too: for real US bank call-report data, mount the free
-- "Financial Data Package" (SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE) listing and
-- run setup.sql instead. Run ONE of {setup.sql, setup_synthetic.sql}.
--
-- Run top to bottom in one worksheet. Part 1 needs ACCOUNTADMIN (or a role that
-- can create roles, databases and warehouses); everything after it runs as the
-- least-privilege pack role SNOWPACK_BANK_RESEARCH_ROLE.
-- Cost: well under 0.1 warehouse credits on XSMALL; Cortex AI tokens are only
-- spent when you generate notes or ask the agent.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Role, database and warehouse (ACCOUNTADMIN)
-- ---------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;
CREATE ROLE IF NOT EXISTS SNOWPACK_BANK_RESEARCH_ROLE
  COMMENT = 'Least-privilege role for the Verified Bank Research Snow Pack';
SET MY_USER = CURRENT_USER();
GRANT ROLE SNOWPACK_BANK_RESEARCH_ROLE TO USER IDENTIFIER($MY_USER);

CREATE DATABASE IF NOT EXISTS SNOWPACK_BANK_RESEARCH;
CREATE WAREHOUSE IF NOT EXISTS SNOWPACK_BANK_RESEARCH_WH
  WITH WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;
GRANT OWNERSHIP ON DATABASE SNOWPACK_BANK_RESEARCH TO ROLE SNOWPACK_BANK_RESEARCH_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON WAREHOUSE SNOWPACK_BANK_RESEARCH_WH TO ROLE SNOWPACK_BANK_RESEARCH_ROLE COPY CURRENT GRANTS;
-- Cortex AI functions, Cortex Analyst and Cortex Agents
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE SNOWPACK_BANK_RESEARCH_ROLE;

-- ---------------------------------------------------------------------------
-- 2. Everything else runs as the pack role
-- ---------------------------------------------------------------------------
USE ROLE SNOWPACK_BANK_RESEARCH_ROLE;
USE WAREHOUSE SNOWPACK_BANK_RESEARCH_WH;
CREATE SCHEMA IF NOT EXISTS SNOWPACK_BANK_RESEARCH.CORE;
USE SCHEMA SNOWPACK_BANK_RESEARCH.CORE;

-- 2a. Banks and peer groups (coined, fictional names) -------------------------
CREATE OR REPLACE TABLE BANKS (
  ID_RSSD NUMBER, BANK_NAME STRING, CITY STRING, STATE STRING,
  FEDERAL_REGULATOR STRING, PEER_GROUP STRING, BASE_ASSETS NUMBER(38,0),
  BASE_DEP_RATIO FLOAT, BASE_ROA FLOAT, BASE_EQTA FLOAT
) COMMENT = 'SYNTHETIC fictional banks with their peer group';

INSERT INTO BANKS VALUES
  (90001,'Corvale National Bank, N.A.','New York','NY','OCC','Large',3180000000000,0.74,0.0118,0.094),
  (90002,'Halvern Bank & Trust','Boston','MA','FRS','Large',2060000000000,0.71,0.0142,0.098),
  (90003,'Brindlemoor Bank','Seattle','WA','OCC','Large',1430000000000,0.76,0.0101,0.101),
  (90004,'Quillmere Savings Bank','Chicago','IL','FDIC','Large',870000000000,0.79,0.0094,0.104),
  (90005,'Tarrowind Commercial Bank','Charlotte','NC','FRS','Regional',405000000000,0.77,0.0112,0.106),
  (90006,'Vessick Federal Savings','Columbus','OH','OCC','Regional',248000000000,0.80,0.0098,0.109),
  (90007,'Ombrel National Bank','Phoenix','AZ','OCC','Regional',152000000000,0.75,0.0130,0.102),
  (90008,'Kestrova Bank','San Diego','CA','FDIC','Regional',66000000000,0.78,0.0105,0.099),
  (90009,'Sallowmere Trust Company','Milwaukee','WI','FRS','Community',30500000000,0.82,0.0109,0.112),
  (90010,'Pellandry Community Bank','Denver','CO','FDIC','Community',12400000000,0.84,0.0096,0.071),
  (90011,'Morvantis Bank','Pittsburgh','PA','FDIC','Community',5300000000,0.83,0.0103,0.108),
  (90012,'Yarrowdel Savings Bank','Memphis','TN','FDIC','Community',2250000000,0.85,0.0091,0.115);

-- 2b. Deterministic quarterly metrics -----------------------------------------
-- N(k) is a fixed pseudo-noise in [-0.5, 0.5) from the bank id, the quarter
-- index and a per-metric seed constant (seed set 7919/104729/1299709).
-- q_ago = 0 is the latest quarter (2026-06-30), 7 is 2024-09-30.
CREATE OR REPLACE TABLE BANK_QUARTERLY_METRICS
  COMMENT = 'SYNTHETIC sample data (fictional banks), deterministic. Real FFIEC/FDIC data is available free on the Snowflake Marketplace: run setup.sql to switch.'
AS
WITH q AS (
  SELECT SEQ4() AS q_ago, DATEADD(quarter, -SEQ4(), '2026-06-30'::DATE) AS quarter_end
  FROM TABLE(GENERATOR(ROWCOUNT => 8))
),
g AS (
  SELECT b.*, q.q_ago, LAST_DAY(q.quarter_end) AS quarter_end,
         MOD(b.id_rssd * 7919 + q.q_ago * 104729 + 1299709, 1000) / 1000.0 - 0.5 AS n1,
         MOD(b.id_rssd * 104729 + q.q_ago * 7919 + 15485863, 1000) / 1000.0 - 0.5 AS n2,
         MOD(b.id_rssd * 1299709 + q.q_ago * 15485863 + 7919, 1000) / 1000.0 - 0.5 AS n3
  FROM BANKS b CROSS JOIN q
),
c AS (
  SELECT g.*,
    ROUND(base_assets * (1 - 0.011 * q_ago) * (1 + 0.006 * n1), -6) AS assets,
    -- Story 1: Kestrova deposit runoff (deposits/assets 0.78 -> 0.64)
    CASE WHEN id_rssd = 90008 THEN base_dep_ratio - 0.02 * (7 - q_ago)
         ELSE base_dep_ratio + 0.01 * n2 END AS dep_ratio,
    -- Story 2: Ombrel ROA compression, with a loss in 2025-12-31 (q_ago = 2)
    CASE WHEN id_rssd = 90007 AND q_ago = 2 THEN -0.0021
         WHEN id_rssd = 90007 THEN base_roa - 0.0012 * (7 - q_ago)
         ELSE base_roa + 0.0008 * n3 - 0.00012 * (7 - q_ago) END AS roa,
    -- Story 3: Pellandry thin capital (base 7.1%, others ~10%)
    base_eqta + 0.002 * n1 AS eqta
  FROM g
)
SELECT
  id_rssd, bank_name, city, state, federal_regulator, peer_group,
  'Commercial Bank'                              AS category,
  TRUE                                           AS is_active,
  quarter_end,
  assets                                         AS total_assets,
  ROUND(assets * dep_ratio, -6)                  AS total_deposits,
  ROUND(assets * roa / 4.0, -5)                  AS net_income_qtr,
  ROUND(roa, 6)                                  AS return_on_assets,
  ROUND(roa / eqta, 6)                           AS return_on_equity,
  ROUND(assets * eqta, -6)                       AS total_equity_capital,
  ROUND(eqta, 6)                                 AS equity_to_assets,
  ROUND(assets * (0.11 + 0.02 * n2), -6)         AS ci_loans,
  ROUND(assets * (0.03 + 0.01 * n3), -6)         AS credit_card_loans,
  ROUND(assets * (0.24 + 0.03 * n1), -6)         AS re_loans_domestic
FROM c;

-- 2c. Data-source marker (the app reads this to show the right badge) ----------
CREATE OR REPLACE VIEW DATA_SOURCE_INFO AS
SELECT 'synthetic' AS mode,
       'Synthetic sample data (fictional banks). Real US bank call-report data is available free on the Snowflake Marketplace (Financial Data Package); run setup.sql to switch.' AS note;

-- 2d. Semantic view for Cortex Analyst -----------------------------------------
CREATE OR REPLACE SEMANTIC VIEW BANK_RESEARCH_SV
  TABLES ( banks AS SNOWPACK_BANK_RESEARCH.CORE.BANK_QUARTERLY_METRICS PRIMARY KEY (ID_RSSD, QUARTER_END)
           WITH SYNONYMS = ('banks','financial institutions','depository institutions')
           COMMENT = 'Quarterly call-report metrics per bank (SYNTHETIC sample data)' )
  FACTS (
    banks.total_assets AS TOTAL_ASSETS, banks.total_deposits AS TOTAL_DEPOSITS,
    banks.net_income AS NET_INCOME_QTR, banks.return_on_assets AS RETURN_ON_ASSETS,
    banks.return_on_equity AS RETURN_ON_EQUITY, banks.equity_to_assets AS EQUITY_TO_ASSETS,
    banks.ci_loans AS CI_LOANS, banks.credit_card_loans AS CREDIT_CARD_LOANS
  )
  DIMENSIONS (
    banks.bank_name AS BANK_NAME WITH SYNONYMS = ('bank','institution','institution name') COMMENT = 'Legal name of the bank',
    banks.peer_group AS PEER_GROUP WITH SYNONYMS = ('peer group','size tier','tier') COMMENT = 'Large, Regional or Community',
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
    banks.avg_equity_to_assets AS AVG(banks.equity_to_assets) COMMENT = 'Average equity to assets (fraction)',
    banks.bank_count AS COUNT(DISTINCT banks.id_rssd) COMMENT = 'Number of distinct banks'
  )
  COMMENT = 'Verified bank research semantic view (SYNTHETIC sample data).';

-- 2e. Research notes written by the app ----------------------------------------
CREATE TABLE IF NOT EXISTS REPORTS (
  run_id          STRING DEFAULT UUID_STRING(),
  subject         STRING,
  peers           ARRAY,
  quarter_end     DATE,
  injected_claim  BOOLEAN,
  fact_pack       VARIANT,
  draft_md        STRING,
  report_md       STRING,
  status          STRING,       -- 'verified' | 'needs_review'
  claims_checked  INT,          -- claims the verifier checked
  edits_applied   INT,          -- number of claims the verifier rejected
  residual_hedges INT,
  findings        VARIANT,      -- verifier output: [{claim, verdict, reason}]
  model           STRING,
  draft_ms        INT,
  verify_ms       INT,
  created_at      TIMESTAMP_NTZ DEFAULT SYSDATE()
);

-- 2f. Conversational Cortex Agent over the semantic view ------------------------
CREATE OR REPLACE AGENT BANK_RESEARCH_AGENT
  COMMENT = 'Verified bank research agent (Cortex Analyst over BANK_RESEARCH_SV, synthetic data)'
  PROFILE = '{"display_name": "Bank Research Agent", "color": "orange"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto
  orchestration:
    capabilities:
      analytical_search: true
  instructions:
    response: 'You are a bank research analyst. Use ONLY figures returned by the Analyst tool; never invent numbers. ROA/ROE/equity ratios are fractions (0.015 = 1.5%). Express dollars in $B. Be concise, cite the quarter, and say the data is synthetic sample data.'
    orchestration: 'For any bank metric, ranking, or comparison, use the BankMetrics Analyst tool.'
    sample_questions:
      - question: 'Rank the Regional peer group by return on assets for 2026-06-30'
  tools:
    - tool_spec:
        type: cortex_analyst_text_to_sql
        name: BankMetrics
        description: 'Quarterly call-report metrics (assets, deposits, net income, ROA, ROE, capital, loans) per bank, with a peer group.'
  tool_resources:
    BankMetrics:
      semantic_view: SNOWPACK_BANK_RESEARCH.CORE.BANK_RESEARCH_SV
      execution_environment:
        type: warehouse
        warehouse: SNOWPACK_BANK_RESEARCH_WH
  $$;

-- 2g. Stage for the Streamlit in Snowflake app (see README, step 2) ------------
CREATE STAGE IF NOT EXISTS APP_STAGE DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Upload app/streamlit_app.py, app/research.py and app/environment.yml here';

SELECT bank_name, peer_group, quarter_end, total_assets, return_on_assets, equity_to_assets
FROM BANK_QUARTERLY_METRICS WHERE quarter_end = '2026-06-30' ORDER BY total_assets DESC;
