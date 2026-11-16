
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: dim_product
-- Layer: ANALYTICS (Gold)
-- Grain: One row per product
-- ============================================================

{{ config(
    materialized='table',
    schema='ANALYTICS'
) }}

SELECT
    -- Product identifiers
    p.PRODUCT_ID,
    p.PRODUCT_SKU,
    p.PRODUCT_NAME,

    -- Category information
    p.CATEGORY_ID,
    c.CATEGORY_NAME,
    c.CATEGORY_DESCRIPTION,

    -- Product financial information
    p.UNIT_COST,
    p.LIST_PRICE,

    -- Product attributes
    p.PRODUCT_STATUS,

    -- Source timestamps
    p.CREATED_AT,
    p.UPDATED_AT

FROM {{ ref('stg_products') }} p

LEFT JOIN {{ ref('stg_product_categories') }} c
    ON p.CATEGORY_ID = c.CATEGORY_ID
