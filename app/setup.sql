-- ============================================================================
-- Verified Bank Research — setup.sql  (REAL data: free Financial Data Package)
-- ----------------------------------------------------------------------------
-- Same app, semantic view and agent as setup_synthetic.sql, but grounded on real
-- US bank call-report data from the free Snowflake Marketplace listing
-- "Financial Data Package" (SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE).
-- Mount the listing first (keep its default database name), then run this script
-- top to bottom. Run ONE of {setup.sql, setup_synthetic.sql}.
--
-- Peer groups are derived from total assets (Large >= $700B, Regional >= $50B,
-- otherwise Community). The Sample bundle and screenshots come from the synthetic
-- script; this real-data path was not part of the v2 live verification.
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
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE TO ROLE SNOWPACK_BANK_RESEARCH_ROLE;

-- ---------------------------------------------------------------------------
-- 2. Everything else runs as the pack role
-- ---------------------------------------------------------------------------
USE ROLE SNOWPACK_BANK_RESEARCH_ROLE;
USE WAREHOUSE SNOWPACK_BANK_RESEARCH_WH;
CREATE SCHEMA IF NOT EXISTS SNOWPACK_BANK_RESEARCH.CORE;
USE SCHEMA SNOWPACK_BANK_RESEARCH.CORE;

-- 2a. Wide fact view over the listing (one row per bank per quarter).
-- The source is entity-attribute-timeseries; the pivot keys on explicit FFIEC
-- variable codes to avoid unit ambiguity and keeps the latest vintage.
CREATE OR REPLACE VIEW BANK_QUARTERLY_METRICS
  COMMENT = 'One row per (bank, quarter) with headline call-report metrics as columns, keyed on explicit FFIEC variable codes to avoid unit ambiguity. Source: SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE (free).'
AS
WITH ts AS (
  SELECT ID_RSSD, VARIABLE, DATE, VALUE,
         ROW_NUMBER() OVER (PARTITION BY ID_RSSD, VARIABLE, DATE
                            ORDER BY _EFFECTIVE_START_TIMESTAMP DESC) AS rn
  FROM SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE.COMMERCIAL_BANKING.FINANCIAL_INSTITUTION_TIMESERIES_PIT
  WHERE VARIABLE IN ('ASSET','DEP','NETINCQ','ROA','ROE','EQTOT','EQV','LNCI','LNCRCD','LNREDOM')
)
SELECT
  e.ID_RSSD,
  e.NAME                 AS BANK_NAME,
  e.CITY,
  e.STATE_ABBREVIATION   AS STATE,
  e.FEDERAL_REGULATOR,
  e.CATEGORY,
  CASE WHEN MAX(CASE WHEN t.VARIABLE='ASSET' THEN t.VALUE END) >= 7e11 THEN 'Large'
       WHEN MAX(CASE WHEN t.VARIABLE='ASSET' THEN t.VALUE END) >= 5e10 THEN 'Regional'
       ELSE 'Community' END AS PEER_GROUP,
  e.IS_ACTIVE,
  t.DATE                 AS QUARTER_END,
  MAX(CASE WHEN t.VARIABLE='ASSET'   THEN t.VALUE END) AS TOTAL_ASSETS,
  MAX(CASE WHEN t.VARIABLE='DEP'     THEN t.VALUE END) AS TOTAL_DEPOSITS,
  MAX(CASE WHEN t.VARIABLE='NETINCQ' THEN t.VALUE END) AS NET_INCOME_QTR,
  MAX(CASE WHEN t.VARIABLE='ROA'     THEN t.VALUE END) AS RETURN_ON_ASSETS,
  MAX(CASE WHEN t.VARIABLE='ROE'     THEN t.VALUE END) AS RETURN_ON_EQUITY,
  MAX(CASE WHEN t.VARIABLE='EQTOT'   THEN t.VALUE END) AS TOTAL_EQUITY_CAPITAL,
  MAX(CASE WHEN t.VARIABLE='EQV'     THEN t.VALUE END) AS EQUITY_TO_ASSETS,
  MAX(CASE WHEN t.VARIABLE='LNCI'    THEN t.VALUE END) AS CI_LOANS,
  MAX(CASE WHEN t.VARIABLE='LNCRCD'  THEN t.VALUE END) AS CREDIT_CARD_LOANS,
  MAX(CASE WHEN t.VARIABLE='LNREDOM' THEN t.VALUE END) AS RE_LOANS_DOMESTIC
FROM SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE.COMMERCIAL_BANKING.FINANCIAL_INSTITUTION_ENTITIES e
JOIN ts t
  ON t.ID_RSSD = e.ID_RSSD::TEXT AND t.rn = 1
GROUP BY ALL;

CREATE OR REPLACE VIEW BANKS AS
SELECT ID_RSSD, BANK_NAME, CITY, STATE, FEDERAL_REGULATOR, PEER_GROUP
FROM BANK_QUARTERLY_METRICS QUALIFY ROW_NUMBER() OVER (PARTITION BY ID_RSSD ORDER BY QUARTER_END DESC) = 1;

-- 2b'. Watchlist rules (the Desk shows these; thresholds are illustrative) -----
CREATE OR REPLACE VIEW WATCHLIST_SIGNALS AS
WITH m AS (
  SELECT id_rssd, bank_name, quarter_end, total_assets, total_deposits, return_on_assets, equity_to_assets,
         MAX(quarter_end) OVER () AS latest
  FROM BANK_QUARTERLY_METRICS
), now_ago AS (
  SELECT n.id_rssd, n.bank_name,
         n.total_deposits / n.total_assets AS dep_now, a.total_deposits / a.total_assets AS dep_ago,
         n.return_on_assets AS roa_now, a.return_on_assets AS roa_ago, n.equity_to_assets AS eqta_now
  FROM m n JOIN m a ON a.id_rssd = n.id_rssd AND a.quarter_end = DATEADD(year, -1, n.latest)
  WHERE n.quarter_end = n.latest
)
SELECT id_rssd, bank_name, 'Deposit runoff' AS signal,
       'Deposits/assets ' || TO_CHAR(dep_ago * 100, 'FM90.0') || '% -> ' || TO_CHAR(dep_now * 100, 'FM90.0') || '% in a year' AS detail
FROM now_ago WHERE dep_ago - dep_now > 0.06
UNION ALL
SELECT m.id_rssd, m.bank_name, 'Quarterly loss',
       'ROA ' || TO_CHAR(m.return_on_assets * 100, 'FM90.00') || '% in quarter ending ' || m.quarter_end::STRING
FROM m WHERE m.return_on_assets < 0
UNION ALL
SELECT id_rssd, bank_name, 'ROA compression', 'ROA ' || TO_CHAR((roa_now - roa_ago) * 100, 'FMS0.00') || ' pp year over year'
FROM now_ago WHERE (roa_now - roa_ago) * 100 < -0.3
UNION ALL
SELECT id_rssd, bank_name, 'Thin capital', 'Equity/assets ' || TO_CHAR(eqta_now * 100, 'FM90.00') || '% (below 8.00%)'
FROM now_ago WHERE eqta_now < 0.08;

-- 2c. Data-source marker (the app reads this to show the right badge) ----------
CREATE OR REPLACE VIEW DATA_SOURCE_INFO AS
SELECT 'marketplace' AS mode,
       'Real data from the free Snowflake Marketplace listing SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE (FFIEC/FDIC call reports).' AS note;

-- 2d. Semantic view for Cortex Analyst -----------------------------------------
CREATE OR REPLACE SEMANTIC VIEW BANK_RESEARCH_SV
  TABLES ( banks AS SNOWPACK_BANK_RESEARCH.CORE.BANK_QUARTERLY_METRICS PRIMARY KEY (ID_RSSD, QUARTER_END)
           WITH SYNONYMS = ('banks','financial institutions','depository institutions')
           COMMENT = 'Quarterly call-report metrics per bank (FFIEC/FDIC call reports)' )
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
  COMMENT = 'Verified bank research semantic view (FFIEC/FDIC call reports).';

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
  COMMENT = 'Verified bank research agent (Cortex Analyst over BANK_RESEARCH_SV, real call-report data)'
  PROFILE = '{"display_name": "Bank Research Agent", "color": "orange"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto
  orchestration:
    capabilities:
      analytical_search: true
  instructions:
    response: 'You are a bank research analyst. Use ONLY figures returned by the Analyst tool; never invent numbers. ROA/ROE/equity ratios are fractions (0.015 = 1.5%). Express dollars in $B. Be concise, cite the quarter, and cite the quarter.'
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
FROM BANK_QUARTERLY_METRICS QUALIFY quarter_end = MAX(quarter_end) OVER () ORDER BY total_assets DESC LIMIT 20;
