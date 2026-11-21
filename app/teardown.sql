-- ============================================================================
-- Verified Bank Research — teardown.sql
-- ----------------------------------------------------------------------------
-- Removes everything this Snow Pack created: the database (tables, views,
-- semantic view, agent, stage, Streamlit app), the warehouse and the pack role.
-- Safe to re-run, including on an account where the pack is already gone.
-- The database and warehouse are owned by the pack role, so they are dropped
-- as that role first; then ACCOUNTADMIN drops the role.
-- ============================================================================

USE ROLE ACCOUNTADMIN;
CREATE ROLE IF NOT EXISTS SNOWPACK_BANK_RESEARCH_ROLE;
GRANT ROLE SNOWPACK_BANK_RESEARCH_ROLE TO ROLE ACCOUNTADMIN;

USE ROLE SNOWPACK_BANK_RESEARCH_ROLE;
DROP DATABASE IF EXISTS SNOWPACK_BANK_RESEARCH;
DROP WAREHOUSE IF EXISTS SNOWPACK_BANK_RESEARCH_WH;

USE ROLE ACCOUNTADMIN;
DROP ROLE IF EXISTS SNOWPACK_BANK_RESEARCH_ROLE;

SHOW DATABASES LIKE 'SNOWPACK_BANK_RESEARCH';
