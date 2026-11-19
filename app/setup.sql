-- ============================================================================
-- HOL-01: Verified Institution Research Agent  —  setup.sql
-- ----------------------------------------------------------------------------
-- Builds the foundation for the app on FREE Snowflake public data
-- (SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE) — so this runs in any account that
-- has mounted the free "Financial Data Package" listing from the Snowflake
-- Marketplace.
--
-- Objects created (all in SNOWPACK_BANK_RESEARCH.CORE):
--   1. BANK_QUARTERLY_METRICS   — deduped wide fact view (one row / bank / qtr)
--   2. BANK_RESEARCH_SV         — Cortex Analyst semantic view over (1)
--   3. REPORTS                  — output table for generated research notes
--
-- Run top-to-bottom as a role that can CREATE DATABASE and CREATE WAREHOUSE.
-- Re-runnable (CREATE OR REPLACE / IF NOT EXISTS).
-- ============================================================================

-- Dedicated, isolated environment for this Snow Pack.
CREATE DATABASE IF NOT EXISTS SNOWPACK_BANK_RESEARCH;
CREATE SCHEMA IF NOT EXISTS SNOWPACK_BANK_RESEARCH.CORE;
CREATE WAREHOUSE IF NOT EXISTS SNOWPACK_BANK_RESEARCH_WH WITH WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE INITIALLY_SUSPENDED=TRUE;
USE WAREHOUSE SNOWPACK_BANK_RESEARCH_WH;
USE SCHEMA SNOWPACK_BANK_RESEARCH.CORE;

-- ----------------------------------------------------------------------------
-- 1. Wide fact view
-- The source is an entity-attribute-timeseries (EAV) model. The SAME metric
-- label (e.g. "Total deposits") maps to MULTIPLE variable codes with different
-- units (USD vs Percent), so we key the pivot on explicit FFIEC VARIABLE CODES
-- and keep loan BALANCES (LN* codes), not charge-offs/recoveries.
--   ASSET=total assets, DEP=deposits, NETINCQ=quarterly net income,
--   ROA/ROE=returns, EQTOT=equity capital, EQV=equity/assets,
--   LNCI=C&I loans, LNCRCD=credit-card loans, LNREDOM=domestic RE loans.
-- The PIT view carries multiple vintages per key; we keep the latest effective.
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 2. Cortex Analyst semantic view
-- Gives the agent a natural-language "data pack" tool: dimensions describe the
-- grain, metrics are the verified aggregates. Synonyms + comments steer Analyst.
-- NOTE: object comments MUST use `COMMENT = '...'` and synonyms `WITH SYNONYMS = (...)`.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE SEMANTIC VIEW BANK_RESEARCH_SV
  TABLES (
    banks AS SNOWPACK_BANK_RESEARCH.CORE.BANK_QUARTERLY_METRICS
      PRIMARY KEY (ID_RSSD, QUARTER_END)
      WITH SYNONYMS = ('banks','financial institutions','depository institutions')
      COMMENT = 'Quarterly FFIEC/FDIC call-report metrics per US bank'
  )
  FACTS (
    banks.total_assets          AS TOTAL_ASSETS,
    banks.total_deposits        AS TOTAL_DEPOSITS,
    banks.net_income            AS NET_INCOME_QTR,
    banks.return_on_assets      AS RETURN_ON_ASSETS,
    banks.return_on_equity      AS RETURN_ON_EQUITY,
    banks.equity_to_assets      AS EQUITY_TO_ASSETS,
    banks.ci_loans              AS CI_LOANS,
    banks.credit_card_loans     AS CREDIT_CARD_LOANS
  )
  DIMENSIONS (
    banks.bank_name          AS BANK_NAME          WITH SYNONYMS = ('bank','institution','institution name') COMMENT = 'Legal name of the bank',
    banks.state              AS STATE              WITH SYNONYMS = ('headquarters state'),
    banks.city               AS CITY,
    banks.federal_regulator  AS FEDERAL_REGULATOR  WITH SYNONYMS = ('regulator','primary regulator'),
    banks.quarter_end        AS QUARTER_END        WITH SYNONYMS = ('quarter','period','as of date','reporting date'),
    banks.report_year        AS YEAR(QUARTER_END)  WITH SYNONYMS = ('year')
  )
  METRICS (
    banks.total_assets_usd      AS SUM(banks.total_assets)            COMMENT = 'Total assets in USD',
    banks.total_deposits_usd    AS SUM(banks.total_deposits)          COMMENT = 'Total deposits in USD',
    banks.net_income_qtr_usd    AS SUM(banks.net_income)              COMMENT = 'Quarterly net income in USD',
    banks.avg_return_on_assets  AS AVG(banks.return_on_assets)        COMMENT = 'Average ROA (fraction; 0.015 = 1.5 percent)',
    banks.avg_return_on_equity  AS AVG(banks.return_on_equity)        COMMENT = 'Average ROE (fraction)',
    banks.bank_count            AS COUNT(DISTINCT banks.id_rssd)      COMMENT = 'Number of distinct banks'
  )
  COMMENT = 'Verified bank research semantic view on free Snowflake public financial data (FFIEC/FDIC call reports).';

-- ----------------------------------------------------------------------------
-- 2b. Data-source marker (the app reads this to show the right banner)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW DATA_SOURCE_INFO AS
SELECT 'marketplace' AS mode,
       'Live data from the free Snowflake Marketplace listing SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE (FFIEC/FDIC call reports).' AS note;

-- ----------------------------------------------------------------------------
-- 3. Output table for generated research notes
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS REPORTS (
  run_id          STRING      DEFAULT UUID_STRING(),
  subject         STRING,
  draft_md        STRING,
  report_md       STRING,
  status          STRING,       -- 'verified' | 'needs_review'
  edits_applied   INT,
  residual_hedges INT,
  created_at      TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ----------------------------------------------------------------------------
-- 4. (Optional) Conversational Cortex Agent over the semantic view
-- Built in the notebook's "Extension A". Included here so the whole stack is
-- reproducible from setup.sql. Chat with it in Snowsight > AI & ML > Agents.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE AGENT BANK_RESEARCH_AGENT
  COMMENT = 'HOL-01 verified bank research agent (Cortex Analyst over BANK_RESEARCH_SV)'
  PROFILE = '{"display_name": "Bank Research Agent", "color": "blue"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto
  orchestration:
    capabilities:
      analytical_search: true
  instructions:
    response: 'You are a buy-side bank analyst. Use ONLY figures returned by the Analyst tool; never invent numbers. ROA/ROE/equity ratios are fractions (0.015 = 1.5%). Express dollars in $B/$T. Be concise and cite the quarter.'
    orchestration: 'For any bank metric, ranking, or comparison, use the BankMetrics Analyst tool.'
    sample_questions:
      - question: 'Top 5 banks by total assets in 2026'
  tools:
    - tool_spec:
        type: cortex_analyst_text_to_sql
        name: BankMetrics
        description: 'Quarterly FFIEC/FDIC call-report metrics (assets, deposits, net income, ROA, ROE, capital, loans) per US bank.'
  tool_resources:
    BankMetrics:
      semantic_view: SNOWPACK_BANK_RESEARCH.CORE.BANK_RESEARCH_SV
  $$;

-- Quick smoke test (optional):
-- SELECT * FROM SEMANTIC_VIEW(BANK_RESEARCH_SV
--   METRICS total_assets_usd DIMENSIONS bank_name, report_year)
--   WHERE report_year = 2026 ORDER BY total_assets_usd DESC LIMIT 5;
