
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: stg_orders
-- Layer: STAGING (Silver)
-- Source: RAW.ORDERS
-- Purpose: Clean and standardize order records
-- ============================================================

{{ config(materialized='table') }}

SELECT
    ORDER_ID,
    CUSTOMER_ID,
    ORDER_DATE,

    -- Standardize status and channel
    UPPER(TRIM(ORDER_STATUS)) AS ORDER_STATUS,
    UPPER(TRIM(ORDER_CHANNEL)) AS ORDER_CHANNEL,

    -- Preserve financial and source data
    SHIPPING_AMOUNT,
    CREATED_AT,
    UPDATED_AT,

    -- Preserve the original ingestion timestamp
    LOADED_AT AS RAW_LOADED_AT,

    -- Record the staging transformation time
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS STAGED_AT

FROM {{ source('raw', 'orders') }}
