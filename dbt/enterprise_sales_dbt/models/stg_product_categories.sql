
-- STAGING (Silver): Product Categories
-- Standardize category descriptions

{{ config(materialized='table') }}

SELECT
    CATEGORY_ID,

    TRIM(CATEGORY_NAME) AS CATEGORY_NAME,

    NULLIF(
        TRIM(CATEGORY_DESCRIPTION), ''
    ) AS CATEGORY_DESCRIPTION,

    LOADED_AT AS RAW_LOADED_AT,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS STAGED_AT

FROM {{ source('raw', 'product_categories') }}
