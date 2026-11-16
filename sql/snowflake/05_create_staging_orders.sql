
-- ============================================================
-- Enterprise Sales Data Pipeline
-- File: 05_create_staging_orders.sql
-- Purpose: Transform RAW (Bronze) orders into
--          STAGING (Silver) orders
-- ============================================================

USE DATABASE ENTERPRISE_SALES_DW;


-- ============================================================
-- STEP 1: Create the cleaned STAGING orders table
-- ============================================================

CREATE OR REPLACE TABLE STAGING.ORDERS AS

SELECT
    ORDER_ID,
    CUSTOMER_ID,
    ORDER_DATE,

    -- Standardize order status
    UPPER(TRIM(ORDER_STATUS)) AS ORDER_STATUS,

    -- Standardize order channel
    UPPER(TRIM(ORDER_CHANNEL)) AS ORDER_CHANNEL,

    -- Preserve financial values
    SHIPPING_AMOUNT,

    -- Preserve source timestamps
    CREATED_AT,
    UPDATED_AT,

    -- Track when the record entered Snowflake
    LOADED_AT AS RAW_LOADED_AT,

    -- Track when the staging transformation ran
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS STAGED_AT

FROM RAW.ORDERS;


-- ============================================================
-- STEP 2: Validate the STAGING table
-- ============================================================

SELECT
    COUNT(*) AS TOTAL_ORDERS,
    COUNT(DISTINCT ORDER_ID) AS UNIQUE_ORDERS,
    COUNT(STAGED_AT) AS RECORDS_WITH_STAGING_TIMESTAMP
FROM STAGING.ORDERS;
