
-- ============================================================
-- Enterprise Sales Pipeline
-- File: 04_merge_sales_reps.sql
-- Purpose: Demonstrate UPDATE, INSERT, and SKIP using MERGE
-- This exercise does not modify the actual RAW sales reps.
-- ============================================================

USE DATABASE ENTERPRISE_SALES_DW;


-- STEP 1: Create a separate practice table
-- Start with one existing sales representative.


-- STEP 1: Create a practice table with explicit data types

CREATE OR REPLACE TABLE STAGING.SALES_REPS_MERGE_DEMO (
    SALES_REP_ID NUMBER(38,0),
    FIRST_NAME VARCHAR(100),
    LAST_NAME VARCHAR(100)
);

-- Insert our starting record
INSERT INTO STAGING.SALES_REPS_MERGE_DEMO (
    SALES_REP_ID,
    FIRST_NAME,
    LAST_NAME
)
VALUES (1, 'Jonathan', 'Smith');



-- STEP 2: MERGE two incoming records
-- ID 1: Existing record with a changed first name
-- ID 101: New record that does not exist in the demo table

MERGE INTO STAGING.SALES_REPS_MERGE_DEMO AS target

USING (
    SELECT
        column1::INT AS SALES_REP_ID,
        column2::VARCHAR AS FIRST_NAME,
        column3::VARCHAR AS LAST_NAME
    FROM VALUES
        (1, 'Johnny', 'Smith'),
        (101, 'Emily', 'Davis')
) AS source

ON target.SALES_REP_ID = source.SALES_REP_ID

-- Update only if something changed
WHEN MATCHED AND (
    target.FIRST_NAME IS DISTINCT FROM source.FIRST_NAME
    OR target.LAST_NAME IS DISTINCT FROM source.LAST_NAME
)
THEN UPDATE SET
    FIRST_NAME = source.FIRST_NAME,
    LAST_NAME = source.LAST_NAME

-- Insert records that do not exist
WHEN NOT MATCHED THEN
    INSERT (
        SALES_REP_ID,
        FIRST_NAME,
        LAST_NAME
    )
    VALUES (
        source.SALES_REP_ID,
        source.FIRST_NAME,
        source.LAST_NAME
    );


-- STEP 3: Verify the results

SELECT
    SALES_REP_ID,
    FIRST_NAME,
    LAST_NAME
FROM STAGING.SALES_REPS_MERGE_DEMO
ORDER BY SALES_REP_ID;

