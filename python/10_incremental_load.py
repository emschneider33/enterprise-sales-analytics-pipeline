"""
Enterprise Sales Analytics Pipeline
File: 10_incremental_load.py

Purpose:
Incrementally load new and updated records from MySQL
into the Snowflake RAW layer.

Features:
- Automated Snowflake key-pair authentication
- Incremental loading using UPDATED_AT timestamps
- Snowflake watermark tracking
- Batch processing
- MERGE statements for inserts and updates
- Data validation
- Transaction management

Run from the project root:

    python python/10_incremental_load.py --tables customers

    python python/10_incremental_load.py
"""

import argparse
import os
from datetime import timedelta
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


# Number of records processed per batch
BATCH_SIZE = 5000


# Recheck the last five minutes of source timestamps.
# Overlapping records are safe because MERGE only updates
# records when their values have changed.

LOOKBACK_MINUTES = 5


# ============================================================
# 2. CONFIGURE SOURCE TABLES
# ============================================================

# These four tables contain UPDATED_AT timestamps.
#
# The remaining three tables will be handled separately
# because they do not have UPDATED_AT columns.


TABLE_CONFIG = {

    "products": {

        "primary_key": "PRODUCT_ID",

        "columns": [
            "PRODUCT_ID",
            "PRODUCT_SKU",
            "PRODUCT_NAME",
            "CATEGORY_ID",
            "UNIT_COST",
            "LIST_PRICE",
            "PRODUCT_STATUS",
            "CREATED_AT",
            "UPDATED_AT",
        ],
    },


    "customers": {

        "primary_key": "CUSTOMER_ID",

        "columns": [
            "CUSTOMER_ID",
            "CUSTOMER_NAME",
            "CUSTOMER_TYPE",
            "INDUSTRY",
            "EMAIL",
            "PHONE",
            "CITY",
            "STATE",
            "ZIP_CODE",
            "SALES_REP_ID",
            "CUSTOMER_STATUS",
            "CREATED_AT",
            "UPDATED_AT",
        ],
    },


    "orders": {

        "primary_key": "ORDER_ID",

        "columns": [
            "ORDER_ID",
            "CUSTOMER_ID",
            "ORDER_DATE",
            "ORDER_STATUS",
            "ORDER_CHANNEL",
            "SHIPPING_AMOUNT",
            "CREATED_AT",
            "UPDATED_AT",
        ],
    },


    "order_items": {

        "primary_key": "ORDER_ITEM_ID",

        "columns": [
            "ORDER_ITEM_ID",
            "ORDER_ID",
            "PRODUCT_ID",
            "QUANTITY",
            "UNIT_PRICE",
            "DISCOUNT_PCT",
            "UNIT_COST",
            "CREATED_AT",
            "UPDATED_AT",
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

            "port": int(
                os.getenv("DB_PORT", "3306")
            ),

            "user": required_env("DB_USER"),

            "password": required_env("DB_PASSWORD"),

            "database": required_env("DB_NAME"),

        },

    )


# ============================================================
# 5. CREATE SNOWFLAKE CONNECTION
# ============================================================

def create_snowflake_connection():

    # Use the existing private key from our previous lesson.

    private_key_path = (
        Path.home()
        / "snowflake_keys"
        / "rsa_key.p8"
    )

    if not private_key_path.is_file():

        raise FileNotFoundError(
            f"Snowflake private key not found: {private_key_path}"
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
# 6. READ CURRENT SNOWFLAKE WATERMARK
# ============================================================

def get_watermark(sf_cursor, table_name):

    sf_cursor.execute(

        """
        SELECT
            LAST_SUCCESSFUL_UPDATED_AT

        FROM OPS.LOAD_WATERMARKS

        WHERE SOURCE_TABLE = %s
        """,

        (table_name.upper(),),

    )

    rows = sf_cursor.fetchall()


    # Confirm that exactly one watermark record exists.

    if len(rows) != 1:

        raise ValueError(

            f"Expected exactly one OPS watermark for "
            f"{table_name}; found {len(rows)}. "
            f"Check 06_create_pipeline_control_tables.sql."

        )


    return rows[0][0]


# ============================================================
# 7. GET MYSQL SOURCE CUTOFF
# ============================================================

def get_source_cutoff(mysql_engine, table_name):

    """
    Get the current MySQL timestamp.

    This provides an upper boundary for the
    records extracted during the current run.
    """

    with mysql_engine.connect() as conn:

        cutoff = conn.execute(

            text("SELECT CURRENT_TIMESTAMP(6)")

        ).scalar_one()


        # Verify that the source contains no NULL timestamps.

        missing_timestamps = conn.execute(

            text(
                f"""
                SELECT COUNT(*)

                FROM {table_name}

                WHERE UPDATED_AT IS NULL
                """
            )

        ).scalar_one()


    if missing_timestamps:

        raise ValueError(

            f"{table_name} has {missing_timestamps} "
            f"NULL UPDATED_AT values. "
            f"These records require a loading rule."

        )


    return cutoff


# ============================================================
# 8. PREPARE DATAFRAME
# ============================================================

def prepare_dataframe(df, table_name):

    # Snowflake column names are uppercase.

    df.columns = df.columns.str.upper()


    # Preserve the DATE conversion from script 08.
    # This prevents the Snowflake DATE casting error
    # we encountered previously.

    if table_name == "orders":

        df["ORDER_DATE"] = pd.to_datetime(

            df["ORDER_DATE"],

            errors="raise"

        ).dt.date


    return df


# ============================================================
# 9. PROCESS INDIVIDUAL TABLE
# ============================================================

def process_table(mysql_engine, sf_conn, table_name):

    config = TABLE_CONFIG[table_name]

    columns = config["columns"]

    primary_key = config["primary_key"]

    column_sql = ", ".join(columns)

    target_table = table_name.upper()

    incoming_table = f"{target_table}_INCOMING"


    print(f"\n--- Processing {target_table} ---")


    cursor = sf_conn.cursor()


    try:

        # ====================================================
        # STEP A: READ PREVIOUS WATERMARK
        # ====================================================

        last_watermark = get_watermark(

            cursor,

            table_name

        )


        # Get current source cutoff.

        cutoff = get_source_cutoff(

            mysql_engine,

            table_name

        )


        # Recheck a small overlapping timestamp window.

        lower_bound = (

            last_watermark - timedelta(
                minutes=LOOKBACK_MINUTES
            )

            if last_watermark is not None

            else None

        )


        print(
            f"Previous watermark: "
            f"{last_watermark or 'NULL (initial backfill)'}"
        )

        print(f"Source cutoff: {cutoff}")


        # ====================================================
        # STEP B: CREATE TEMPORARY INCOMING TABLE
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
        # STEP C: BUILD INCREMENTAL MYSQL QUERY
        # ====================================================

        query_sql = f"""

            SELECT
                {column_sql}

            FROM {table_name}

            WHERE UPDATED_AT < :cutoff

        """


        query_params = {

            "cutoff": cutoff

        }


        # If a previous watermark exists, apply it.

        if lower_bound is not None:

            query_sql += """

                AND UPDATED_AT >= :lower_bound

            """

            query_params["lower_bound"] = lower_bound


        query_sql += f"""

            ORDER BY {primary_key}

        """


        total_extracted = 0


        # ====================================================
        # STEP D: EXTRACT MYSQL DATA IN BATCHES
        # ====================================================

        with mysql_engine.connect().execution_options(

            stream_results=True

        ) as mysql_conn:


            batches = pd.read_sql(

                text(query_sql),

                mysql_conn,

                params=query_params,

                chunksize=BATCH_SIZE,

                coerce_float=False,

            )


            for batch_number, df in enumerate(

                batches,

                start=1

            ):


                # Prepare data types.

                df = prepare_dataframe(

                    df,

                    table_name

                )


                # Validate primary keys.

                if df[primary_key].isna().any():

                    raise ValueError(

                        f"NULL {primary_key} "
                        f"in batch {batch_number}"

                    )


                if df[primary_key].duplicated().any():

                    raise ValueError(

                        f"Duplicate {primary_key} "
                        f"in batch {batch_number}"

                    )


                # ============================================
                # STEP E: BULK LOAD INTO SNOWFLAKE
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

                        f"Snowflake staging failed for "
                        f"{table_name}, batch {batch_number}"

                    )


                total_extracted += len(df)


                print(

                    f"Batch {batch_number}: "
                    f"{rows_loaded:,} rows staged"

                )


        # ====================================================
        # STEP F: VALIDATE STAGED RECORDS
        # ====================================================

        cursor.execute(

            f"""
            SELECT

                COUNT(*),

                COUNT(DISTINCT {primary_key}),

                MAX(UPDATED_AT)

            FROM RAW.{incoming_table}
            """

        )


        staged_count, distinct_keys, staged_max_updated = (
            cursor.fetchone()
        )


        if (

            staged_count != total_extracted

            or distinct_keys != staged_count

        ):

            raise ValueError(

                f"Staging validation failed for {table_name}. "
                f"Extracted: {total_extracted}, "
                f"Staged: {staged_count}, "
                f"Unique IDs: {distinct_keys}"

            )


        print(

            f"\nTotal records staged: {staged_count:,}"

        )


        inserted = 0

        updated = 0


        # ====================================================
        # STEP G: MERGE RECORDS INTO RAW TABLE
        # ====================================================

        if total_extracted > 0:


            # Check the existing destination row count.

            cursor.execute(

                f"""
                SELECT

                    COUNT(*),

                    COUNT(DISTINCT {primary_key})

                FROM RAW.{target_table}
                """

            )


            old_count, old_unique_count = cursor.fetchone()


            if old_count != old_unique_count:

                raise ValueError(

                    f"Duplicate primary keys already exist "
                    f"in RAW.{target_table}"

                )


            # Identify all non-primary-key columns.

            other_columns = [

                col for col in columns

                if col != primary_key

            ]


            # Detect changes using NULL-safe comparisons.

            change_conditions = " OR\n".join(

                f"target.{col} IS DISTINCT FROM source.{col}"

                for col in other_columns

            )


            # Update existing records.

            update_assignments = ",\n".join(

                [

                    f"{col} = source.{col}"

                    for col in other_columns

                ]

                + [

                    "LOADED_AT = CURRENT_TIMESTAMP()"

                ]

            )


            # Prepare values for new records.

            source_values = ", ".join(

                f"source.{col}"

                for col in columns

            )


            # Build MERGE statement.

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


            merge_result = cursor.fetchone()


            inserted = int(merge_result[0])

            updated = int(merge_result[1])


            print(f"Records inserted: {inserted:,}")

            print(f"Records updated: {updated:,}")


            # =================================================
            # STEP H: VALIDATE DESTINATION
            # =================================================

            cursor.execute(

                f"""
                SELECT

                    COUNT(*),

                    COUNT(DISTINCT {primary_key})

                FROM RAW.{target_table}
                """

            )


            new_count, new_unique_count = cursor.fetchone()


            if (

                new_count != old_count + inserted

                or new_unique_count != new_count

            ):

                raise ValueError(

                    f"Destination row count or "
                    f"primary key validation failed "
                    f"for {table_name}"

                )


            # Verify staged values match the RAW destination.

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


            mismatch_count = cursor.fetchone()[0]


            if mismatch_count:

                raise ValueError(

                    f"{mismatch_count} staged records "
                    f"do not match RAW.{target_table}"

                )


        # ====================================================
        # STEP I: CALCULATE NEW WATERMARK
        # ====================================================

        # Save the MySQL cutoff timestamp used for this run.
        #
        # Every eligible record before this cutoff was checked.
        # The five-minute overlap protects against some
        # late-arriving changes and timestamp precision issues.

        new_watermark = cutoff


        # ====================================================
        # STEP J: UPDATE SNOWFLAKE WATERMARK TABLE
        # ====================================================

        cursor.execute(

            """
            UPDATE OPS.LOAD_WATERMARKS

            SET

                LAST_SUCCESSFUL_UPDATED_AT = %s,

                LAST_SUCCESSFUL_RUN_AT =
                    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ,

                LAST_EXTRACTED_ROWS = %s

            WHERE SOURCE_TABLE = %s
            """,

            (

                new_watermark,

                total_extracted,

                target_table,

            ),

        )


        # ====================================================
        # STEP K: COMMIT SUCCESSFUL TRANSACTION
        # ====================================================

        # This commits the MERGE and watermark UPDATE together.

        sf_conn.commit()


        print("\nIncremental load completed.")

        print(f"Total extracted: {total_extracted:,}")

        print(f"Records inserted: {inserted:,}")

        print(f"Records updated: {updated:,}")

        print(f"New watermark: {new_watermark}")


    except Exception:

        # Undo uncommitted changes if any step fails.

        sf_conn.rollback()

        raise


    finally:

        cursor.close()


# ============================================================
# 10. EXECUTE INCREMENTAL PIPELINE
# ============================================================

def main():

    parser = argparse.ArgumentParser(

        description="Incremental MySQL to Snowflake RAW loader"

    )


    parser.add_argument(

        "--tables",

        nargs="+",

        choices=tuple(TABLE_CONFIG),

        default=list(TABLE_CONFIG),

        help="Select tables to load (default: all four)",

    )


    args = parser.parse_args()


    print("\nStarting incremental MySQL to Snowflake ELT...")

    print("Tables to process:", ", ".join(args.tables))


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

                "\nIncremental ELT pipeline "
                "completed successfully!"

            )


        finally:

            sf_conn.close()


    finally:

        mysql_engine.dispose()


# ============================================================
# 11. RUN SCRIPT
# ============================================================

if __name__ == "__main__":

    main()