
-- ============================================================
-- Test: FACT_SALES financial reconciliation
-- Purpose: Verify Gold against Silver source transactions
-- Pass condition: Zero rows returned
-- ============================================================

WITH source_lines AS (

    SELECT
        oi.ORDER_ITEM_ID,
        oi.ORDER_ID,
        oi.PRODUCT_ID,

        o.CUSTOMER_ID,
        c.SALES_REP_ID,
        o.ORDER_STATUS,

        TO_NUMBER(
            TO_CHAR(o.ORDER_DATE, 'YYYYMMDD')
        ) AS DATE_KEY,

        -- Independently calculate expected amounts
        ROUND(
            oi.QUANTITY * oi.UNIT_PRICE, 2
        ) AS GROSS_SALES_AMOUNT,

        ROUND(
            oi.QUANTITY * oi.UNIT_PRICE * oi.DISCOUNT_PCT, 2
        ) AS DISCOUNT_AMOUNT,

        ROUND(
            oi.QUANTITY * oi.UNIT_COST, 2
        ) AS TOTAL_COST_AMOUNT

    FROM {{ ref('stg_order_items') }} oi

    INNER JOIN {{ ref('stg_orders') }} o
        ON oi.ORDER_ID = o.ORDER_ID

    LEFT JOIN {{ ref('stg_customers') }} c
        ON o.CUSTOMER_ID = c.CUSTOMER_ID

),

expected AS (

    SELECT
        *,

        GROSS_SALES_AMOUNT
            - DISCOUNT_AMOUNT AS NET_SALES_AMOUNT,

        GROSS_SALES_AMOUNT
            - DISCOUNT_AMOUNT
            - TOTAL_COST_AMOUNT AS GROSS_PROFIT_AMOUNT

    FROM source_lines

)

SELECT
    COALESCE(e.ORDER_ITEM_ID, f.ORDER_ITEM_ID)
        AS ORDER_ITEM_ID

FROM expected e

FULL OUTER JOIN {{ ref('fact_sales') }} f
    ON e.ORDER_ITEM_ID = f.ORDER_ITEM_ID

WHERE
    -- Missing or unexpected transactions
    e.ORDER_ITEM_ID IS NULL
    OR f.ORDER_ITEM_ID IS NULL

    -- Incorrect transaction attributes
    OR e.ORDER_ID IS DISTINCT FROM f.ORDER_ID
    OR e.CUSTOMER_ID IS DISTINCT FROM f.CUSTOMER_ID
    OR e.PRODUCT_ID IS DISTINCT FROM f.PRODUCT_ID
    OR e.SALES_REP_ID IS DISTINCT FROM f.SALES_REP_ID
    OR e.DATE_KEY IS DISTINCT FROM f.DATE_KEY
    OR e.ORDER_STATUS IS DISTINCT FROM f.ORDER_STATUS

    -- Incorrect financial calculations
    OR e.GROSS_SALES_AMOUNT
        IS DISTINCT FROM f.GROSS_SALES_AMOUNT

    OR e.DISCOUNT_AMOUNT
        IS DISTINCT FROM f.DISCOUNT_AMOUNT

    OR e.NET_SALES_AMOUNT
        IS DISTINCT FROM f.NET_SALES_AMOUNT

    OR e.TOTAL_COST_AMOUNT
        IS DISTINCT FROM f.TOTAL_COST_AMOUNT

    OR e.GROSS_PROFIT_AMOUNT
        IS DISTINCT FROM f.GROSS_PROFIT_AMOUNT
