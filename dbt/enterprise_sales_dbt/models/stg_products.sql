
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: stg_products
-- Layer: STAGING (Silver)
-- Source: RAW.PRODUCTS
-- Purpose: Clean and standardize product data
-- ============================================================

{{ config(materialized='table') }}

SELECT
    -- Product identifiers
    PRODUCT_ID,
    CATEGORY_ID,

    -- Standardize product information
    UPPER(TRIM(PRODUCT_SKU)) AS PRODUCT_SKU,
    TRIM(PRODUCT_NAME) AS PRODUCT_NAME,

    -- Preserve financial values
    UNIT_COST,
    LIST_PRICE,

    -- Standardize product status
    UPPER(TRIM(PRODUCT_STATUS)) AS PRODUCT_STATUS,

    -- Preserve source timestamps
    CREATED_AT,
    UPDATED_AT,

    -- Track data lineage
    LOADED_AT AS RAW_LOADED_AT,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS STAGED_AT

FROM {{ source('raw', 'products') }}
