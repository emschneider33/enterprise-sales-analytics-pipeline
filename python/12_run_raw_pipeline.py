"""Run and log the complete Enterprise Sales ELT pipeline.

Run from the enterprise_sales_pipeline project root:
    python python/12_run_raw_pipeline.py

This loads Snowflake RAW tables, then builds dbt STAGING/ANALYTICS models
and runs their data-quality tests. Each run gets its own logs/pipeline_*.log.
Scheduling will be added separately.
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON_FOLDER = PROJECT_ROOT / "python"
LOGS_FOLDER = PROJECT_ROOT / "logs"


# Dependency order matters:
# Reference data before transactional data; both RAW steps before dbt.
JOBS = [
    ("Reference tables", PYTHON_FOLDER / "11_load_reference_tables.py"),
    ("Incremental tables", PYTHON_FOLDER / "10_incremental_load.py"),
    ("dbt models and tests", PYTHON_FOLDER / "13_run_dbt.py"),
]


def main():
    started = time.perf_counter()
    start_datetime = datetime.now().astimezone()

    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

    log_path = LOGS_FOLDER / f"pipeline_{start_datetime:%Y%m%d_%H%M%S_%f}.log"

    pipeline_exit_code = 0

    with log_path.open("w", encoding="utf-8") as log_file:

        def report(message=""):
            """Write a pipeline status message to the console and log file."""

            print(message, flush=True)

            log_file.write(message + "\n")
            log_file.flush()

        report("\n========================================")
        report("ENTERPRISE SALES - COMPLETE ELT PIPELINE")
        report(f"Started: {start_datetime:%Y-%m-%d %H:%M:%S %Z}")
        report(f"Log file: {log_path}")
        report("========================================\n")

        for step_number, (job_name, script_path) in enumerate(JOBS, start=1):

            if not script_path.is_file():
                report(f"\nPIPELINE FAILED: Missing script: {script_path}")
                pipeline_exit_code = 1
                break

            report(f"\nSTEP {step_number}/{len(JOBS)}: {job_name}")

            step_started = time.perf_counter()

            # Stream child output to the terminal and log file.
            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"

            try:
                with subprocess.Popen(
                    [sys.executable, "-u", str(script_path)],
                    cwd=PROJECT_ROOT,
                    env=child_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                ) as process:

                    for line in process.stdout:
                        print(line, end="", flush=True)

                        log_file.write(line)
                        log_file.flush()

                    return_code = process.wait()

            except OSError as exc:
                report(f"PIPELINE FAILED: Could not start {job_name}: {exc}")
                pipeline_exit_code = 1
                break

            step_elapsed = time.perf_counter() - step_started

            if return_code != 0:

                report(
                    f"\nPIPELINE FAILED: {job_name} returned exit code "
                    f"{return_code} after {step_elapsed:.1f} seconds. "
                    "Later steps were not run."
                )

                pipeline_exit_code = return_code
                break

            report(
                f"STEP {step_number} completed successfully "
                f"in {step_elapsed:.1f} seconds."
            )

        elapsed = time.perf_counter() - started

        report("\n========================================")

        if pipeline_exit_code == 0:
            report("COMPLETE ELT PIPELINE FINISHED SUCCESSFULLY")
        else:
            report("COMPLETE ELT PIPELINE FAILED")

        report(f"Elapsed time: {elapsed:.1f} seconds")
        report(f"Full log: {log_path}")
        report("========================================\n")

    return pipeline_exit_code


if __name__ == "__main__":
    sys.exit(main())