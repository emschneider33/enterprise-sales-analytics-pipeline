"""
Enterprise Sales Analytics Pipeline
File: 11_load_reference_tables.py

Purpose:
Load small MySQL reference tables into Snowflake RAW
using full-source upserts.

Tables:
- territories
- sales_reps
- product_categories

These tables do not have UPDATED_AT timestamps.

Features:
- Automated Snowflake key-pair authentication
- Full-source extraction
- Data type conversions
- Batch processing
- MERGE for inserts and updates
- Data validation
- Transaction management

Note:
This script does not automatically delete Snowflake records
that have been removed from MySQL.
"""

import argparse
import os
from pathlib import Path

import pandas as pd
import snowflake.connector

from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas
from sqlalchemy import create_engine, text


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

BATCH_SIZE = 5000


# ============================================================
# 2. CONFIGURE REFERENCE TABLES
# ============================================================

TABLE_CONFIG = {

    "territories": {

        "primary_key": "TERRITORY_ID",

        "columns": [
            "TERRITORY_ID",
            "TERRITORY_NAME",
            "REGION",
            "CREATED_AT",
        ],
    },

    "sales_reps": {

        "primary_key": "SALES_REP_ID",

        "columns": [
            "SALES_REP_ID",
            "FIRST_NAME",
            "LAST_NAME",
            "EMAIL",
            "TERRITORY_ID",
            "HIRE_DATE",
            "IS_ACTIVE",
            "CREATED_AT",
        ],
    },

    "product_categories": {

        "primary_key": "CATEGORY_ID",

        "columns": [
            "CATEGORY_ID",
            "CATEGORY_NAME",
            "CATEGORY_DESCRIPTION",
        ],
    },

}


# ============================================================
# 3. VALIDATE ENVIRONMENT VARIABLES
# ============================================================

def required_env(name):

    value = os.getenv(name)

    if not value:

        raise ValueError(
            f"Missing {name} in your .env file"
        )

    return value


# ============================================================
# 4. CREATE MYSQL CONNECTION
# ============================================================

def create_mysql_engine():

    return create_engine(

        "mysql+pymysql://",

        connect_args={

            "host": required_env("DB_HOST"),

            "port": int(os.getenv("DB_PORT", "3306")),

            "user": required_env("DB_USER"),

            "password": required_env("DB_PASSWORD"),

            "database": required_env("DB_NAME"),

        },

    )


# ============================================================
# 5. CREATE SNOWFLAKE CONNECTION
# ============================================================

def create_snowflake_connection():

    private_key_path = (
        Path.home()
        / "snowflake_keys"
        / "rsa_key.p8"
    )

    if not private_key_path.is_file():

        raise FileNotFoundError(
            f"Snowflake key not found: {private_key_path}"
        )

    return snowflake.connector.connect(

        account=required_env("SNOWFLAKE_ACCOUNT"),

        user=required_env("SNOWFLAKE_LOGIN_NAME"),

        authenticator="SNOWFLAKE_JWT",

        private_key_file=str(private_key_path),

        private_key_password=required_env(
            "SNOWFLAKE_KEY_PASSPHRASE"
        ),

        warehouse=required_env("SNOWFLAKE_WAREHOUSE"),

        database=required_env("SNOWFLAKE_DATABASE"),

        schema="RAW",

        role=required_env("SNOWFLAKE_ROLE"),

        autocommit=False,

    )


# ============================================================
# 6. PREPARE DATAFRAME
# ============================================================

def prepare_dataframe(df, table_name):

    # Snowflake column names are uppercase.

    df.columns = df.columns.str.upper()

    if table_name == "sales_reps":

        # Convert MySQL HIRE_DATE to a Python date object.
        # Snowflake expects DATE rather than TIMESTAMP.

        df["HIRE_DATE"] = pd.to_datetime(

            df["HIRE_DATE"],

            errors="raise"

        ).dt.date

        # ================================================
        # Convert MySQL TINYINT to Snowflake BOOLEAN
        # ================================================

        # MySQL stores IS_ACTIVE as:
        # 1 = Active
        # 0 = Inactive
        #
        # Snowflake stores BOOLEAN as:
        # TRUE = Active
        # FALSE = Inactive

        # Validate the source values.

        if (
            df["IS_ACTIVE"].isna().any()
            or not df["IS_ACTIVE"].isin([0, 1]).all()
        ):

            raise ValueError(
                "IS_ACTIVE must contain only 0 or 1"
            )

        # Convert integers into actual Boolean values.

        df["IS_ACTIVE"] = df["IS_ACTIVE"].astype(bool)

    return df


# ============================================================
# 7. PROCESS ONE REFERENCE TABLE
# ============================================================

def process_table(mysql_engine, sf_conn, table_name):

    config = TABLE_CONFIG[table_name]

    primary_key = config["primary_key"]

    columns = config["columns"]

    column_sql = ", ".join(columns)

    target_table = table_name.upper()

    incoming_table = f"{target_table}_INCOMING"

    cursor = sf_conn.cursor()

    print(
        f"\n--- Processing {target_table} "
        f"(full-source upsert) ---"
    )

    try:

        # ====================================================
        # STEP A: CREATE TEMPORARY INCOMING TABLE
        # ====================================================

        cursor.execute(

            f"""
            CREATE OR REPLACE TEMP TABLE
                RAW.{incoming_table} AS

            SELECT
                {column_sql}

            FROM RAW.{target_table}

            WHERE 1 = 0
            """

        )

        print(
            f"Created temporary RAW.{incoming_table}"
        )

        # ====================================================
        # STEP B: EXTRACT ALL MYSQL RECORDS
        # ====================================================

        query = text(

            f"""
            SELECT
                {column_sql}

            FROM {table_name}

            ORDER BY {primary_key}
            """

        )

        total_extracted = 0

        with mysql_engine.connect().execution_options(

            stream_results=True

        ) as mysql_conn:

            batches = pd.read_sql(

                query,

                mysql_conn,

                chunksize=BATCH_SIZE,

                coerce_float=False,

            )

            for batch_number, df in enumerate(

                batches,

                start=1

            ):

                if df.empty:
                    continue

                # Prepare data types.

                df = prepare_dataframe(
                    df,
                    table_name
                )

                # ============================================
                # VALIDATE PRIMARY KEYS
                # ============================================

                if df[primary_key].isna().any():

                    raise ValueError(
                        f"NULL {primary_key} in {table_name}"
                    )

                if df[primary_key].duplicated().any():

                    raise ValueError(
                        f"Duplicate {primary_key} "
                        f"in batch {batch_number}"
                    )

                # ============================================
                # STEP C: BULK LOAD INTO SNOWFLAKE
                # ============================================

                success, files, rows_loaded, output = write_pandas(

                    conn=sf_conn,

                    df=df[columns].reset_index(drop=True),

                    table_name=incoming_table,

                    database=required_env(
                        "SNOWFLAKE_DATABASE"
                    ),

                    schema="RAW",

                    chunk_size=BATCH_SIZE,

                    use_logical_type=True,

                )

                if not success or rows_loaded != len(df):

                    raise RuntimeError(
                        f"Staging failed for {table_name} "
                        f"batch {batch_number}"
                    )

                total_extracted += len(df)

                print(
                    f"Batch {batch_number}: "
                    f"{rows_loaded:,} rows staged"
                )

        # ====================================================
        # STEP D: VALIDATE STAGED RECORDS
        # ====================================================

        cursor.execute(

            f"""
            SELECT

                COUNT(*),

                COUNT(DISTINCT {primary_key})

            FROM RAW.{incoming_table}
            """

        )

        staged_count, staged_distinct = cursor.fetchone()

        if (
            staged_count != total_extracted
            or staged_distinct != staged_count
        ):

            raise ValueError(
                f"Staging validation failed for {table_name}"
            )

        print(
            f"Total records staged: {staged_count:,}"
        )

        # ====================================================
        # CHECK EXISTING DESTINATION RECORDS
        # ====================================================

        cursor.execute(

            f"""
            SELECT

                COUNT(*),

                COUNT(DISTINCT {primary_key})

            FROM RAW.{target_table}
            """

        )

        old_count, old_distinct = cursor.fetchone()

        if old_count != old_distinct:

            raise ValueError(
                f"Duplicate keys exist in RAW.{target_table}"
            )

        inserted = 0

        updated = 0

        # ====================================================
        # STEP E: BUILD AND EXECUTE MERGE
        # ====================================================

        if total_extracted > 0:

            # Identify non-primary-key columns.

            other_columns = [

                col for col in columns

                if col != primary_key

            ]

            # Detect changes using NULL-safe comparisons.

            change_conditions = " OR\n".join(

                f"target.{col} IS DISTINCT FROM source.{col}"

                for col in other_columns

            )

            # Prepare UPDATE assignments.

            update_assignments = ",\n".join(

                [

                    f"{col} = source.{col}"

                    for col in other_columns

                ]

                + [

                    "LOADED_AT = CURRENT_TIMESTAMP()"

                ]

            )

            # Prepare INSERT values.

            source_values = ", ".join(

                f"source.{col}"

                for col in columns

            )

            # ================================================
            # BUILD MERGE STATEMENT
            # ================================================

            merge_sql = f"""

                MERGE INTO RAW.{target_table} AS target

                USING RAW.{incoming_table} AS source

                ON target.{primary_key} = source.{primary_key}

                WHEN MATCHED AND (

                    {change_conditions}

                )

                THEN UPDATE SET

                    {update_assignments}

                WHEN NOT MATCHED THEN

                    INSERT ({column_sql})

                    VALUES ({source_values})

            """

            # Execute MERGE.

            cursor.execute(merge_sql)

            result = cursor.fetchone()

            inserted = int(result[0])

            updated = int(result[1])

            print(
                f"Records inserted: {inserted:,}"
            )

            print(
                f"Records updated: {updated:,}"
            )

            # ====================================================
            # STEP F: VALIDATE DESTINATION
            # ====================================================

            cursor.execute(

                f"""
                SELECT

                    COUNT(*),

                    COUNT(DISTINCT {primary_key})

                FROM RAW.{target_table}
                """

            )

            new_count, new_distinct = cursor.fetchone()

            if (
                new_count != old_count + inserted
                or new_distinct != new_count
            ):

                raise ValueError(
                    f"Destination validation failed "
                    f"for {table_name}"
                )

            # ================================================
            # VERIFY STAGED VALUES MATCH DESTINATION
            # ================================================

            differences = " OR\n".join(

                f"target.{col} IS DISTINCT FROM source.{col}"

                for col in other_columns

            )

            cursor.execute(

                f"""
                SELECT COUNT(*)

                FROM RAW.{incoming_table} AS source

                LEFT JOIN RAW.{target_table} AS target

                    ON source.{primary_key} = target.{primary_key}

                WHERE

                    target.{primary_key} IS NULL

                    OR ({differences})
                """

            )

            mismatches = cursor.fetchone()[0]

            if mismatches:

                raise ValueError(
                    f"{mismatches} records do not match "
                    f"RAW.{target_table}"
                )

        # ====================================================
        # STEP G: COMMIT CHANGES
        # ====================================================

        sf_conn.commit()

        print("\nReference-table load completed.")

        print(
            f"Source records checked: {total_extracted:,}"
        )

        print(
            f"New records inserted: {inserted:,}"
        )

        print(
            f"Changed records updated: {updated:,}"
        )

        print(
            f"Completed {target_table}"
        )

    except Exception:

        sf_conn.rollback()

        raise

    finally:

        cursor.close()


# ============================================================
# 8. EXECUTE REFERENCE TABLE PIPELINE
# ============================================================

def main():

    parser = argparse.ArgumentParser(

        description="MySQL to Snowflake reference-table loader"

    )

    parser.add_argument(

        "--tables",

        nargs="+",

        choices=tuple(TABLE_CONFIG),

        default=list(TABLE_CONFIG),

        help="Select reference tables (default: all three)",

    )

    args = parser.parse_args()

    print(
        "\nStarting MySQL to Snowflake reference-table upsert..."
    )

    print(
        "Tables:", ", ".join(args.tables)
    )

    mysql_engine = create_mysql_engine()

    try:

        sf_conn = create_snowflake_connection()

        try:

            for table_name in args.tables:

                process_table(

                    mysql_engine,

                    sf_conn,

                    table_name,

                )

            print(
                "\nReference-table pipeline "
                "completed successfully!"
            )

        finally:

            sf_conn.close()

    finally:

        mysql_engine.dispose()


# ============================================================
# 9. RUN SCRIPT
# ============================================================

if __name__ == "__main__":

    main()