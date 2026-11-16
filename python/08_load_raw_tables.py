
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


# ============================================================
# 1. Load environment variables
# ============================================================

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


# ============================================================
# 2. Configure source tables
# ============================================================

TABLE_CONFIG = {
    "product_categories": {
        "primary_key": "CATEGORY_ID",
        "columns": [
            "CATEGORY_ID",
            "CATEGORY_NAME",
            "CATEGORY_DESCRIPTION",
        ],
    },

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


# Number of records processed per batch
BATCH_SIZE = 5000

# For this lesson, load only the ORDERS table
TABLES_TO_LOAD = ["order_items"]


# ============================================================
# 3. Create database connections
# ============================================================

def create_mysql_engine():

    return create_engine(
        "mysql+pymysql://",
        connect_args={
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME"),
        },
    )


def create_snowflake_connection():

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        authenticator="OAUTH_AUTHORIZATION_CODE",
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="RAW",
        role=os.getenv("SNOWFLAKE_ROLE"),
        autocommit=False,
    )


# ============================================================
# 4. Prepare DataFrame data types
# ============================================================

def prepare_dataframe(df, table_name):

    # Snowflake column names are uppercase
    df.columns = df.columns.str.upper()

    # Convert DATE columns to native Python date objects.
    # This prevents timestamp values from being loaded
    # into Snowflake DATE columns.
    if table_name == "orders":

        df["ORDER_DATE"] = pd.to_datetime(
            df["ORDER_DATE"],
            errors="raise"
        ).dt.date

    return df


# ============================================================
# 5. Extract, bulk load, and MERGE a table
# ============================================================

def process_table(mysql_engine, sf_conn, table_name):

    config = TABLE_CONFIG[table_name]

    columns = config["columns"]
    primary_key = config["primary_key"]

    target_table = table_name.upper()
    incoming_table = f"{target_table}_INCOMING"

    column_sql = ", ".join(columns)

    total_extracted = 0

    cursor = sf_conn.cursor()

    try:

        # ====================================================
        # STEP A: Create an empty temporary incoming table
        # ====================================================

        cursor.execute(f"""
            CREATE OR REPLACE TEMP TABLE
                RAW.{incoming_table} AS

            SELECT {column_sql}
            FROM RAW.{target_table}
            WHERE 1 = 0
        """)

        print(f"Created temporary RAW.{incoming_table}")


        # ====================================================
        # STEP B: Extract MySQL records in batches
        # ====================================================

        query = text(f"""
            SELECT {column_sql}
            FROM {table_name}
            ORDER BY {primary_key}
        """)

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

                # Prepare column names and data types
                df = prepare_dataframe(df, table_name)

                # Validate primary keys
                if df[primary_key].isna().any():
                    raise ValueError(
                        f"NULL primary key in batch {batch_number}"
                    )

                if df[primary_key].duplicated().any():
                    raise ValueError(
                        f"Duplicate IDs in batch {batch_number}"
                    )

                # ============================================
                # STEP C: Bulk load the current batch
                # ============================================

                success, files, rows_loaded, output = write_pandas(
                    conn=sf_conn,
                    df=df[columns].reset_index(drop=True),
                    table_name=incoming_table,
                    database=os.getenv("SNOWFLAKE_DATABASE"),
                    schema="RAW",
                    chunk_size=BATCH_SIZE,
                    use_logical_type=True,
                )

                if not success or rows_loaded != len(df):
                    raise RuntimeError(
                        f"Bulk load failed for batch {batch_number}"
                    )

                total_extracted += len(df)

                print(
                    f"Batch {batch_number}: "
                    f"{rows_loaded:,} records staged"
                )


        # ====================================================
        # STEP D: Validate all staged records
        # ====================================================

        cursor.execute(f"""
            SELECT
                COUNT(*),
                COUNT(DISTINCT {primary_key})
            FROM RAW.{incoming_table}
        """)

        staged_count, staged_unique = cursor.fetchone()

        if (
            staged_count != total_extracted
            or staged_unique != total_extracted
        ):
            raise ValueError(
                "Staged row count or primary key validation failed"
            )

        if total_extracted == 0:
            print(f"No records found for {table_name}")
            return

        print(
            f"\nTotal records staged: {staged_count:,}"
        )


        # ====================================================
        # STEP E: Build a reusable MERGE statement
        # ====================================================

        other_columns = [
            col for col in columns
            if col != primary_key
        ]

        # Detect changes using NULL-safe comparisons
        change_conditions = " OR\n".join(
            f"target.{col} IS DISTINCT FROM source.{col}"
            for col in other_columns
        )

        # Update changed records
        update_assignments = ",\n".join(
            [
                f"{col} = source.{col}"
                for col in other_columns
            ]
            + ["LOADED_AT = CURRENT_TIMESTAMP()"]
        )

        # Insert new records
        source_values = ", ".join(
            f"source.{col}"
            for col in columns
        )

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


        # ====================================================
        # STEP F: Execute MERGE
        # ====================================================

        cursor.execute(merge_sql)

        result = cursor.fetchone()

        inserted = result[0]
        updated = result[1]

        print(f"Records inserted: {inserted:,}")
        print(f"Records updated: {updated:,}")


        # ====================================================
        # STEP G: Validate destination before committing
        # ====================================================

        cursor.execute(f"""
            SELECT
                COUNT(*),
                COUNT(DISTINCT {primary_key})
            FROM RAW.{target_table}
        """)

        total, unique_ids = cursor.fetchone()

        if (
            total != total_extracted
            or unique_ids != total
        ):
            raise ValueError(
                f"Destination validation failed for {table_name}"
            )

        # Commit successful MERGE
        sf_conn.commit()

        print(f"Snowflake total: {total:,}")
        print(f"Unique IDs: {unique_ids:,}")
        print(f"Validated RAW.{target_table}")


    except Exception:

        sf_conn.rollback()
        raise

    finally:

        cursor.close()


# ============================================================
# 6. Execute ELT pipeline
# ============================================================

def main():

    print("\nStarting MySQL to Snowflake ELT...\n")

    mysql_engine = create_mysql_engine()

    try:

        sf_conn = create_snowflake_connection()

        try:

            for table_name in TABLES_TO_LOAD:

                print(f"\nProcessing {table_name}...\n")

                process_table(
                    mysql_engine,
                    sf_conn,
                    table_name,
                )

            print(
                "\nELT pipeline completed successfully!"
            )

        finally:

            sf_conn.close()

    finally:

        mysql_engine.dispose()


if __name__ == "__main__":
    main()

