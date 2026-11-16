-- 07_execute_dbt_pipeline.sql
-- Execute deployed dbt project
-- Refresh Silver (STAGING) and Gold (ANALYTICS) layers
-- Run dbt data-quality tests


EXECUTE DBT PROJECT ENTERPRISE_SALES_DW.OPS.ENTERPRISE_SALES_DBT
    ARGS = 'build --target dev';