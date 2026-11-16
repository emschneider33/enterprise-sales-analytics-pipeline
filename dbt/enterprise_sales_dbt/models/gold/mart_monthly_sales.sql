
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: mart_monthly_sales
-- Layer: ANALYTICS (Gold)
-- Grain: One row per month and order status
-- ============================================================

{{ config(
    materialized='table',
    schema='ANALYTICS'
) }}

WITH monthly_sales AS (

    SELECT
        DATE_TRUNC(
            'MONTH', ORDER_DATE
        )::DATE AS MONTH_START_DATE,

        ORDER_STATUS,

        COUNT(DISTINCT ORDER_ID) AS TOTAL_ORDERS,
        COUNT(*) AS TOTAL_LINE_ITEMS,
        SUM(QUANTITY) AS TOTAL_UNITS,

        SUM(GROSS_SALES_AMOUNT) AS GROSS_SALES,
        SUM(DISCOUNT_AMOUNT) AS TOTAL_DISCOUNTS,
        SUM(NET_SALES_AMOUNT) AS NET_SALES,
        SUM(TOTAL_COST_AMOUNT) AS TOTAL_COST,
        SUM(GROSS_PROFIT_AMOUNT) AS GROSS_PROFIT

    FROM {{ ref('fact_sales') }}

    GROUP BY
        DATE_TRUNC('MONTH', ORDER_DATE)::DATE,
        ORDER_STATUS

)

SELECT
    MONTH_START_DATE,
    ORDER_STATUS,

    TOTAL_ORDERS,
    TOTAL_LINE_ITEMS,
    TOTAL_UNITS,

    GROSS_SALES,
    TOTAL_DISCOUNTS,
    NET_SALES,
    TOTAL_COST,
    GROSS_PROFIT,

    ROUND(
        GROSS_PROFIT / NULLIF(NET_SALES, 0) * 100,
        2
    ) AS GROSS_MARGIN_PCT

FROM monthly_sales
