"""
13_run_dbt.py

Executes the deployed Snowflake dbt project.

Runs:
    dbt build --target dev

A successful build:
1. Refreshes STAGING (Silver) models.
2. Refreshes ANALYTICS (Gold) models.
3. Executes dbt data-quality tests.

Exits with a nonzero status if the build fails.
"""

import os
import sys
import time
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv


# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

PRIVATE_KEY_PATH = Path.home() / "snowflake_keys" / "rsa_key.p8"

DBT_PROJECT = "ENTERPRISE_SALES_DW.OPS.ENTERPRISE_SALES_DBT"

DBT_COMMAND = (
    f"EXECUTE DBT PROJECT {DBT_PROJECT} "
    "ARGS = 'build --target dev'"
)


# --------------------------------------------------
# Snowflake connection
# --------------------------------------------------

def get_snowflake_connection():

    if not PRIVATE_KEY_PATH.is_file():
        raise FileNotFoundError(
            f"Snowflake private key not found: {PRIVATE_KEY_PATH}"
        )

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_LOGIN_NAME"),
        authenticator="SNOWFLAKE_JWT",
        private_key_file=str(PRIVATE_KEY_PATH),
        private_key_password=os.getenv(
            "SNOWFLAKE_KEY_PASSPHRASE"
        ),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="OPS",
        role=os.getenv("SNOWFLAKE_ROLE"),
        autocommit=True,
    )


# --------------------------------------------------
# Execute dbt project
# --------------------------------------------------

def run_dbt():

    print("\n========================================")
    print("ENTERPRISE SALES - DBT BUILD")
    print("========================================")

    print(f"\nProject: {DBT_PROJECT}")
    print("Command: dbt build --target dev")

    start_time = time.time()

    conn = None
    cursor = None

    try:

        print("\nConnecting to Snowflake...")

        conn = get_snowflake_connection()

        cursor = conn.cursor()

        print("Executing dbt build...\n")

        cursor.execute(DBT_COMMAND)

        query_id = cursor.sfqid

        result = cursor.fetchone()

        if result is None:
            raise RuntimeError(
                "Snowflake returned no dbt execution result."
            )

        success = result[0]
        exception = result[1]
        stdout = result[2]

        print("========================================")
        print("DBT EXECUTION OUTPUT")
        print("========================================\n")

        if stdout:
            print(stdout)

        print(f"\nSnowflake Query ID: {query_id}")

        elapsed = time.time() - start_time

        if str(success).strip().lower() not in ("true", "1"):

            raise RuntimeError(
                f"dbt build failed: {exception}"
            )

        print("\n========================================")
        print("DBT BUILD COMPLETED SUCCESSFULLY")
        print(f"Elapsed time: {elapsed:.1f} seconds")
        print("========================================")

        return 0

    except Exception as e:

        print(f"\nDBT BUILD FAILED: {e}", file=sys.stderr)

        return 1

    finally:

        if cursor is not None:
            cursor.close()

        if conn is not None:
            conn.close()


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":
    sys.exit(run_dbt())