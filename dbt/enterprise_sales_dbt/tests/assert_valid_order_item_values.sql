
-- ============================================================
-- Silver Layer Data Quality
-- Test: Validate order item financial values
--
-- A dbt test PASSES when this query returns zero rows.
-- ============================================================

SELECT
    ORDER_ITEM_ID,
    QUANTITY,
    UNIT_PRICE,
    UNIT_COST,
    DISCOUNT_PCT

FROM {{ ref('stg_order_items') }}

WHERE
    QUANTITY IS NULL
    OR QUANTITY <= 0

    OR UNIT_PRICE IS NULL
    OR UNIT_PRICE < 0

    OR UNIT_COST IS NULL
    OR UNIT_COST < 0

    OR DISCOUNT_PCT IS NULL
    OR DISCOUNT_PCT < 0
    OR DISCOUNT_PCT > 1
