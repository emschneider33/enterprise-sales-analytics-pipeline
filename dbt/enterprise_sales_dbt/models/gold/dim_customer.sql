
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: dim_customer
-- Layer: ANALYTICS (Gold)
-- Purpose: Customer dimension for sales reporting
-- Grain: One row per customer
-- ============================================================

{{ config(
    materialized='table',
    schema='ANALYTICS'
) }}

SELECT
    CUSTOMER_ID,
    CUSTOMER_NAME,
    CUSTOMER_TYPE,
    INDUSTRY,

    CITY,
    STATE,
    ZIP_CODE,

    SALES_REP_ID,
    CUSTOMER_STATUS,

    CREATED_AT,
    UPDATED_AT

FROM {{ ref('stg_customers') }}
