
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: stg_customers
-- Layer: STAGING (Silver)
-- Source: RAW.CUSTOMERS
-- Purpose: Clean and standardize customer records
-- ============================================================

{{ config(materialized='table') }}

SELECT
    -- Customer identifiers
    CUSTOMER_ID,
    SALES_REP_ID,

    -- Standardize customer name
    TRIM(CUSTOMER_NAME) AS CUSTOMER_NAME,

    -- Standardize customer classification
    UPPER(TRIM(CUSTOMER_TYPE)) AS CUSTOMER_TYPE,
    UPPER(TRIM(INDUSTRY)) AS INDUSTRY,

    -- Standardize contact information
    LOWER(NULLIF(TRIM(EMAIL), '')) AS EMAIL,
    NULLIF(TRIM(PHONE), '') AS PHONE,

    -- Standardize location information
    TRIM(CITY) AS CITY,
    UPPER(TRIM(STATE)) AS STATE,
    NULLIF(TRIM(ZIP_CODE), '') AS ZIP_CODE,

    -- Standardize customer status
    UPPER(TRIM(CUSTOMER_STATUS)) AS CUSTOMER_STATUS,

    -- Preserve source timestamps
    CREATED_AT,
    UPDATED_AT,

    -- Preserve RAW ingestion timestamp
    LOADED_AT AS RAW_LOADED_AT,

    -- Record when this staging model was built
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS STAGED_AT

FROM {{ source('raw', 'customers') }}
