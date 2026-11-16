-- 08_validate_end_to_end_pipeline.sql
-- Enterprise Sales: read-only Snowflake validation queries.
-- Run in a Snowflake SQL worksheet after the full Python ELT pipeline finishes.
-- Tested against the synthetic customer_id = 1 on 2026-11-16.
-- This script does not modify data or rerun dbt.

-- 1. Verify that a MySQL customer update propagated through all three layers.
-- Expected customer name: Pipeline E2E Validation Customer
-- Expected: three rows and VALIDATION_STATUS = PASS on every row.
WITH customer_snapshots AS (
    SELECT 'RAW' AS data_layer, customer_id, customer_name
    FROM ENTERPRISE_SALES_DW.RAW.CUSTOMERS
    WHERE customer_id = 1

    UNION ALL

    SELECT 'STAGING' AS data_layer, customer_id, customer_name
    FROM ENTERPRISE_SALES_DW.STAGING.STG_CUSTOMERS
    WHERE customer_id = 1

    UNION ALL

    SELECT 'ANALYTICS' AS data_layer, customer_id, customer_name
    FROM ENTERPRISE_SALES_DW.ANALYTICS.DIM_CUSTOMER
    WHERE customer_id = 1
)
SELECT
    data_layer,
    customer_id,
    customer_name,
    CASE
        WHEN COUNT(*) OVER () = 3
         AND COUNT_IF(customer_name = 'Pipeline E2E Validation Customer') OVER () = 3
        THEN 'PASS'
        ELSE 'FAIL'
    END AS validation_status
FROM customer_snapshots
ORDER BY data_layer;

-- 2. Compare customer row counts across RAW, STAGING and ANALYTICS.
-- These are informational counts. Investigate discrepancies before assuming
-- they are failures: transformations can intentionally filter or deduplicate.
SELECT 'RAW' AS data_layer, COUNT(*) AS customer_rows
FROM ENTERPRISE_SALES_DW.RAW.CUSTOMERS

UNION ALL

SELECT 'STAGING' AS data_layer, COUNT(*) AS customer_rows
FROM ENTERPRISE_SALES_DW.STAGING.STG_CUSTOMERS

UNION ALL

SELECT 'ANALYTICS' AS data_layer, COUNT(*) AS customer_rows
FROM ENTERPRISE_SALES_DW.ANALYTICS.DIM_CUSTOMER
ORDER BY data_layer;

-- 3. Inspect the persisted customer incremental-load watermark.
-- A successful no-change rerun can stage a record from the 5-minute overlap
-- while still reporting zero inserted and zero updated records.
SELECT *
FROM ENTERPRISE_SALES_DW.OPS.LOAD_WATERMARKS;

-- dbt quality results and idempotency counts are evidenced by the pipeline
-- execution output, not these read-only SELECT statements.
-- See docs/VALIDATION.md for observed run results and known limitations.
