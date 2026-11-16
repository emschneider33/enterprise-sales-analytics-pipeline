
-- STAGING (Silver): Sales Representatives
-- Standardize employee names and contact information

{{ config(materialized='table') }}

SELECT
    SALES_REP_ID,
    TERRITORY_ID,

    TRIM(FIRST_NAME) AS FIRST_NAME,
    TRIM(LAST_NAME) AS LAST_NAME,

    LOWER(NULLIF(TRIM(EMAIL), '')) AS EMAIL,

    HIRE_DATE,
    IS_ACTIVE,

    CREATED_AT,
    LOADED_AT AS RAW_LOADED_AT,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS STAGED_AT

FROM {{ source('raw', 'sales_reps') }}
