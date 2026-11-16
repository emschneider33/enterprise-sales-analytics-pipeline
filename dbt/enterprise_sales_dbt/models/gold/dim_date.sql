
-- ============================================================
-- Enterprise Sales Analytics Pipeline
-- Model: dim_date
-- Layer: ANALYTICS (Gold)
-- Grain: One row per calendar date
-- Purpose: Support time-based reporting and analysis
-- ============================================================

{{ config(
    materialized='table',
    schema='ANALYTICS'
) }}

WITH date_bounds AS (

    -- Start at January 1 of the earliest order year.
    -- End at December 31 of the year after the later
    -- of the latest order year and current year.

    SELECT
        DATE_FROM_PARTS(
            YEAR(MIN(ORDER_DATE)), 1, 1
        ) AS START_DATE,

        DATE_FROM_PARTS(
            GREATEST(
                YEAR(MAX(ORDER_DATE)),
                YEAR(CURRENT_DATE())
            ) + 1,
            12,
            31
        ) AS END_DATE

    FROM {{ ref('stg_orders') }}

),

date_numbers AS (

    -- Generate sequential day offsets from 0 to 9999

    SELECT
        ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1
            AS DAY_OFFSET

    FROM TABLE(GENERATOR(ROWCOUNT => 10000))

),

date_spine AS (

    -- Generate one row for each date in our calendar

    SELECT
        DATEADD(
            DAY,
            n.DAY_OFFSET,
            b.START_DATE
        ) AS CALENDAR_DATE

    FROM date_bounds b

    CROSS JOIN date_numbers n

    WHERE DATEADD(
        DAY,
        n.DAY_OFFSET,
        b.START_DATE
    ) <= b.END_DATE

)

SELECT
    -- Unique date identifier (example: 20261113)
    TO_NUMBER(
        TO_CHAR(CALENDAR_DATE, 'YYYYMMDD')
    ) AS DATE_KEY,

    CALENDAR_DATE,

    -- Calendar attributes
    YEAR(CALENDAR_DATE) AS CALENDAR_YEAR,
    QUARTER(CALENDAR_DATE) AS CALENDAR_QUARTER,
    MONTH(CALENDAR_DATE) AS MONTH_NUMBER,

    TRIM(
        TO_CHAR(CALENDAR_DATE, 'MMMM')
    ) AS MONTH_NAME,

    TO_CHAR(CALENDAR_DATE, 'YYYY-MM')
        AS YEAR_MONTH,

    -- Weekly reporting (ISO weeks start Monday)
    WEEKISO(CALENDAR_DATE) AS WEEK_NUMBER,
    YEAROFWEEKISO(CALENDAR_DATE) AS WEEK_YEAR,

    -- Daily reporting
    DAY(CALENDAR_DATE) AS DAY_OF_MONTH,
    DAYNAME(CALENDAR_DATE) AS DAY_NAME,
    DAYOFWEEKISO(CALENDAR_DATE) AS DAY_OF_WEEK,

    -- Weekend identification
    CASE
        WHEN DAYOFWEEKISO(CALENDAR_DATE) IN (6, 7)
            THEN TRUE
        ELSE FALSE
    END AS IS_WEEKEND

FROM date_spine
