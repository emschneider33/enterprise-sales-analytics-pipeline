
-- ============================================================
-- Test: Monthly Sales Mart Unique Grain
-- Expected: Zero duplicate month/status combinations
-- ============================================================

SELECT
    MONTH_START_DATE,
    ORDER_STATUS,
    COUNT(*) AS RECORD_COUNT

FROM {{ ref('mart_monthly_sales') }}

GROUP BY
    MONTH_START_DATE,
    ORDER_STATUS

HAVING COUNT(*) > 1
