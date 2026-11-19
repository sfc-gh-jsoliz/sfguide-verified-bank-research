-- ============================================================================
-- Verified Bank Research — teardown.sql
-- ----------------------------------------------------------------------------
-- Removes everything this Snow Pack created. Drops the dedicated database
-- (and all objects within it) and the dedicated warehouse. Safe to re-run.
-- ============================================================================

DROP DATABASE IF EXISTS SNOWPACK_BANK_RESEARCH;
DROP WAREHOUSE IF EXISTS SNOWPACK_BANK_RESEARCH_WH;
