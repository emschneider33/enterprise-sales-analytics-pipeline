# Enterprise Sales Pipeline — Validation Report

**Validation date:** November 16, 2026 (America/New_York)  
**Status:** Passed for the test scenarios listed below  
**Scope:** Synthetic source data in MySQL, Python extraction and upserts, Snowflake RAW, dbt STAGING/ANALYTICS, and scheduled-task invocation.

## Pipeline under test

`MySQL enterprise_sales_ops → Python reference/incremental loaders → Snowflake RAW → dbt STAGING → dbt ANALYTICS`

The orchestration command is `python python/12_run_raw_pipeline.py`. It calls:

1. `11_load_reference_tables.py` — full-source upserts of territories, sales reps, and product categories.
2. `10_incremental_load.py` — watermark-based upserts of products, customers, orders, and order items.
3. `13_run_dbt.py` — `EXECUTE DBT PROJECT ENTERPRISE_SALES_DW.OPS.ENTERPRISE_SALES_DBT ARGS = 'build --target dev'`.

Each execution writes a timestamped log beneath the locally ignored `logs/` directory.

## Test evidence and results

| Test | Expected | Observed | Status |
| --- | --- | --- | --- |
| MySQL change tracking | Changing the name of customer 1 automatically changes `updated_at`. | Name changed from `Pipeline Test Customer` to `Pipeline E2E Validation Customer`; `updated_at` changed from `2026-11-16 09:18:35` to `2026-11-16 11:22:35`. | **PASS** |
| Incremental change capture | Extract the modified customer and update its existing RAW row. | First run staged **1**, inserted **0**, updated **1**. | **PASS** |
| Cross-layer propagation | The changed name appears in RAW, STAGING, and ANALYTICS. | The test customer name matched in all three layers in a Snowflake worksheet (user-verified). | **PASS** |
| dbt build and tests | Models compile/build and data tests pass. | **14 table models**, **1 view model**, **50 tests**; `PASS=65 WARN=0 ERROR=0 SKIP=0 TOTAL=65`. | **PASS** |
| No-change rerun / idempotency | Unchanged source rows do not cause further destination writes. | Second run staged **1** overlapping customer record, inserted **0**, updated **0**. | **PASS** |
| Pipeline ordering | dbt executes only after both RAW loaders succeed. | Both captured runs completed Steps 1/3, 2/3, then 3/3 in order. | **PASS** |
| Task Scheduler manual invocation | The scheduled task starts the same Python orchestrator. | A manual run of the created task was reported successful. | **PASS (user-confirmed)** |

### Change-capture run

- **Start:** November 16, 2026, 11:23:52 Eastern.
- **CUSTOMERS previous watermark:** `2026-11-16 11:09:35.097327`.
- **CUSTOMERS source cutoff:** `2026-11-16 11:24:16.790623`.
- **CUSTOMERS:** 1 staged, 0 inserted, 1 updated.
- **dbt:** 65 passed, 0 warnings/errors/skips.
- **Total duration:** 69.1 seconds.
- **Local evidence log:** `logs/pipeline_20261116_112352_388884.log` (intentionally excluded from Git).

### No-change rerun

- **Start:** November 16, 2026, 11:27:55 Eastern.
- **CUSTOMERS previous watermark:** `2026-11-16 11:24:16.790623`.
- **CUSTOMERS source cutoff:** `2026-11-16 11:28:17.980865`.
- **CUSTOMERS:** 1 staged, 0 inserted, **0 updated**.
- **dbt:** 65 passed, 0 warnings/errors/skips.
- **Total duration:** 61.4 seconds.
- **Local evidence log:** `logs/pipeline_20261116_112755_040069.log` (intentionally excluded from Git).

The incremental loader intentionally rereads a five-minute overlap. A row can therefore be extracted again even though the Snowflake `MERGE` correctly recognizes that nothing has changed. An extracted count of 1 with zero destination updates is expected for this test.

## How to repeat the checks

1. Use a designated synthetic MySQL test customer. Record its current `customer_name` and `updated_at` before any mutation; do not modify production data.
2. Change the test name in MySQL and commit. Confirm that `updated_at` changes automatically.
3. Run `python python/12_run_raw_pipeline.py` from the repository root.
4. Check the `CUSTOMERS` section for an update and the dbt output for successful tests.
5. Run [`sql/08_validate_end_to_end_pipeline.sql`](../sql/08_validate_end_to_end_pipeline.sql) in Snowflake. Its first query checks customer 1 across RAW, STAGING, and ANALYTICS.
6. Without another MySQL change, rerun the Python pipeline. Confirm zero inserted and zero updated records for CUSTOMERS. A row can still be re-extracted within the overlap window.
7. Save test observations in this report. Restore a test customer's original name if the test scenario requires it.

## What has **not** been demonstrated yet

- A new order and order-item insert propagating all the way into a sales fact or mart.
- An intentionally induced source or dbt failure, including alerting and downstream-step suppression.
- Source deletions reaching Snowflake (current loaders use upserts, not deletion CDC).
- Guaranteed capture of changes arriving later than the five-minute overlap or with backdated timestamps.
- Historical tracking of changes to reference-table attributes such as sales-rep territory (no SCD Type 2 history).
- The first **unattended** 6:00 AM Eastern Windows Task Scheduler run. Only manual execution of the task has been confirmed so far.
- Automatic refresh of Power BI Desktop import data after a warehouse update.

The project demonstrates a working portfolio-scale ELT pipeline; it is not presented as production-grade CDC or a fully hosted, always-on scheduler.

## Repository and security notes

- **Commit:** Source code, dbt SQL/YAML, this report, and read-only validation SQL.
- **Do not commit:** `.env`, private keys, live credentials, execution logs, or sensitive customer extracts.
- Keep `/logs/` in `.gitignore`.
- The synthetic customer 1 currently has the validation name `Pipeline E2E Validation Customer`.
