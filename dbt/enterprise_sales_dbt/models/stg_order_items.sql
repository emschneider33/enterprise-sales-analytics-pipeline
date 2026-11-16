
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: stg_order_items
-- Layer: STAGING (Silver)
-- Source: RAW.ORDER_ITEMS
-- Purpose: Prepare order line items for analytics
-- ============================================================

{{ config(materialized='table') }}

SELECT
    -- Order line identifiers
    ORDER_ITEM_ID,
    ORDER_ID,
    PRODUCT_ID,

    -- Transaction quantities and financial values
    QUANTITY,
    UNIT_PRICE,
    DISCOUNT_PCT,
    UNIT_COST,

    -- Preserve source timestamps
    CREATED_AT,
    UPDATED_AT,

    -- Track data lineage
    LOADED_AT AS RAW_LOADED_AT,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS STAGED_AT

FROM {{ source('raw', 'order_items') }}
