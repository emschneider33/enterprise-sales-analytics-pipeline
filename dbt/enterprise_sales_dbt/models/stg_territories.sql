
-- STAGING (Silver): Territories
-- Standardize sales territory information

{{ config(materialized='table') }}

SELECT
    TERRITORY_ID,

    TRIM(TERRITORY_NAME) AS TERRITORY_NAME,
    UPPER(TRIM(REGION)) AS REGION,

    CREATED_AT,
    LOADED_AT AS RAW_LOADED_AT,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS STAGED_AT

FROM {{ source('raw', 'territories') }}
