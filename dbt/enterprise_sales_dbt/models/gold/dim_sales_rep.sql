
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: dim_sales_rep
-- Layer: ANALYTICS (Gold)
-- Grain: One row per sales representative
-- ============================================================

{{ config(
    materialized='table',
    schema='ANALYTICS'
) }}

SELECT
    -- Sales representative identifiers
    sr.SALES_REP_ID,

    -- Representative information
    sr.FIRST_NAME,
    sr.LAST_NAME,
    TRIM(
        CONCAT(
            COALESCE(sr.FIRST_NAME, ''),
            ' ',
            COALESCE(sr.LAST_NAME, '')
        )
    ) AS SALES_REP_NAME,

    sr.EMAIL,
    sr.HIRE_DATE,
    sr.IS_ACTIVE,

    -- Territory information
    sr.TERRITORY_ID,
    t.TERRITORY_NAME,
    t.REGION,

    -- Source timestamp
    sr.CREATED_AT

FROM {{ ref('stg_sales_reps') }} sr

LEFT JOIN {{ ref('stg_territories') }} t
    ON sr.TERRITORY_ID = t.TERRITORY_ID
