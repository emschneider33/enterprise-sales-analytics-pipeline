
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- File: 06_create_pipeline_control_tables.sql
-- Purpose: Create pipeline watermark tracking
-- ============================================================

USE WAREHOUSE SALES_ANALYTICS_WH;
USE DATABASE ENTERPRISE_SALES_DW;

-- STEP 1: Create a schema for pipeline operations

CREATE SCHEMA IF NOT EXISTS OPS;


-- STEP 2: Create the watermark control table

CREATE TABLE IF NOT EXISTS OPS.LOAD_WATERMARKS (

    SOURCE_TABLE VARCHAR(100) NOT NULL,

    LAST_SUCCESSFUL_UPDATED_AT TIMESTAMP_NTZ,

    LAST_SUCCESSFUL_RUN_AT TIMESTAMP_NTZ,

    LAST_EXTRACTED_ROWS NUMBER(38,0)

);


-- STEP 3: Register our incremental source tables
-- Do not overwrite any existing watermark values.

MERGE INTO OPS.LOAD_WATERMARKS AS target

USING (
    SELECT COLUMN1 AS SOURCE_TABLE
    FROM VALUES
        ('CUSTOMERS'),
        ('PRODUCTS'),
        ('ORDERS'),
        ('ORDER_ITEMS')
) AS source

ON target.SOURCE_TABLE = source.SOURCE_TABLE

WHEN NOT MATCHED THEN
    INSERT (
        SOURCE_TABLE,
        LAST_SUCCESSFUL_UPDATED_AT,
        LAST_SUCCESSFUL_RUN_AT,
        LAST_EXTRACTED_ROWS
    )
    VALUES (
        source.SOURCE_TABLE,
        NULL,
        NULL,
        NULL
    );


-- STEP 4: Verify our watermark table

SELECT *
FROM OPS.LOAD_WATERMARKS
ORDER BY SOURCE_TABLE;
