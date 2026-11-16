
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: fact_sales
-- Layer: ANALYTICS (Gold)
-- Grain: One row per order item
-- Purpose: Transaction-level sales financial analysis
-- ============================================================

{{ config(
    materialized='table',
    schema='ANALYTICS'
) }}

WITH order_lines AS (

    -- Combine order details with individual line items

    SELECT
        oi.ORDER_ITEM_ID,
        oi.ORDER_ID,

        -- Date dimension relationship
        o.ORDER_DATE,
        TO_NUMBER(
            TO_CHAR(o.ORDER_DATE, 'YYYYMMDD')
        ) AS DATE_KEY,

        -- Dimension relationships
        o.CUSTOMER_ID,
        oi.PRODUCT_ID,
        c.SALES_REP_ID,

        -- Order attributes
        o.ORDER_STATUS,
        o.ORDER_CHANNEL,

        -- Transaction values
        oi.QUANTITY,
        oi.UNIT_PRICE,
        oi.DISCOUNT_PCT,
        oi.UNIT_COST

    FROM {{ ref('stg_order_items') }} oi

    INNER JOIN {{ ref('stg_orders') }} o
        ON oi.ORDER_ID = o.ORDER_ID

    LEFT JOIN {{ ref('stg_customers') }} c
        ON o.CUSTOMER_ID = c.CUSTOMER_ID

),

line_amounts AS (

    -- Calculate initial financial metrics

    SELECT
        *,

        ROUND(
            QUANTITY * UNIT_PRICE, 2
        ) AS GROSS_SALES_AMOUNT,

        ROUND(
            QUANTITY * UNIT_PRICE * DISCOUNT_PCT, 2
        ) AS DISCOUNT_AMOUNT,

        ROUND(
            QUANTITY * UNIT_COST, 2
        ) AS TOTAL_COST_AMOUNT

    FROM order_lines

)

SELECT
    -- Keys
    ORDER_ITEM_ID,
    ORDER_ID,
    DATE_KEY,
    CUSTOMER_ID,
    PRODUCT_ID,
    SALES_REP_ID,

    -- Order details
    ORDER_DATE,
    ORDER_STATUS,
    ORDER_CHANNEL,

    -- Original transaction values
    QUANTITY,
    UNIT_PRICE,
    DISCOUNT_PCT,
    UNIT_COST,

    -- Financial calculations
    GROSS_SALES_AMOUNT,
    DISCOUNT_AMOUNT,

    GROSS_SALES_AMOUNT
        - DISCOUNT_AMOUNT AS NET_SALES_AMOUNT,

    TOTAL_COST_AMOUNT,

    GROSS_SALES_AMOUNT
        - DISCOUNT_AMOUNT
        - TOTAL_COST_AMOUNT AS GROSS_PROFIT_AMOUNT

FROM line_amounts
