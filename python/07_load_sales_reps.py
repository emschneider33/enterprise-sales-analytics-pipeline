
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# 1. Load environment variables
# ============================================================

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


# ============================================================
# 2. Extract sales reps from MySQL
# ============================================================

def extract_sales_reps():

    mysql_engine = create_engine(
        "mysql+pymysql://",
        connect_args={
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME"),
        },
    )

    try:
        query = text("""
            SELECT
                sales_rep_id,
                first_name,
                last_name,
                email,
                territory_id,
                hire_date,
                is_active,
                created_at
            FROM sales_reps
            ORDER BY sales_rep_id
        """)

        with mysql_engine.connect() as connection:
            df = pd.read_sql(query, connection)

        print(f"Extracted {len(df):,} sales reps from MySQL")

        if df["sales_rep_id"].isna().any():
            raise ValueError("Source contains NULL sales rep IDs")

        if df["sales_rep_id"].duplicated().any():
            raise ValueError("Source contains duplicate sales rep IDs")

        # Convert MySQL's 0/1 values to Python booleans
        df["is_active"] = df["is_active"].map(
            lambda value: None if pd.isna(value) else bool(value)
        )

        return df

    finally:
        mysql_engine.dispose()


# ============================================================
# 3. Convert pandas values for Snowflake
# ============================================================

def convert_value(value):

    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if hasattr(value, "item"):
        return value.item()

    return value


# ============================================================
# 4. Load incoming data and MERGE into Snowflake
# ============================================================

def merge_sales_reps(df):

    if df.empty:
        print("No sales reps to process")
        return

    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        authenticator="OAUTH_AUTHORIZATION_CODE",
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="RAW",
        role=os.getenv("SNOWFLAKE_ROLE"),
        autocommit=False,
    )

    try:
        cursor = conn.cursor()

        try:
            # STEP A: Create an empty temporary incoming table
            # Its data types come from the existing RAW table.

            cursor.execute("""
                CREATE OR REPLACE TEMPORARY TABLE
                    RAW.SALES_REPS_INCOMING AS

                SELECT
                    SALES_REP_ID,
                    FIRST_NAME,
                    LAST_NAME,
                    EMAIL,
                    TERRITORY_ID,
                    HIRE_DATE,
                    IS_ACTIVE,
                    CREATED_AT
                FROM RAW.SALES_REPS
                WHERE 1 = 0
            """)

            # STEP B: Load extracted MySQL records
            # into the temporary incoming table.

            columns = [
                "sales_rep_id",
                "first_name",
                "last_name",
                "email",
                "territory_id",
                "hire_date",
                "is_active",
                "created_at",
            ]

            rows = [
                tuple(convert_value(value) for value in row)
                for row in df[columns].itertuples(
                    index=False, name=None
                )
            ]

            cursor.executemany("""
                INSERT INTO RAW.SALES_REPS_INCOMING (
                    SALES_REP_ID,
                    FIRST_NAME,
                    LAST_NAME,
                    EMAIL,
                    TERRITORY_ID,
                    HIRE_DATE,
                    IS_ACTIVE,
                    CREATED_AT
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, rows)

            print(
                f"Staged {len(rows):,} incoming sales reps"
            )

            # STEP C: MERGE incoming records into RAW
            # Update only changed records.
            # Insert records that do not exist.

            cursor.execute("""
                MERGE INTO RAW.SALES_REPS AS target

                USING RAW.SALES_REPS_INCOMING AS source

                ON target.SALES_REP_ID = source.SALES_REP_ID

                WHEN MATCHED AND (
                    target.FIRST_NAME IS DISTINCT FROM source.FIRST_NAME
                    OR target.LAST_NAME IS DISTINCT FROM source.LAST_NAME
                    OR target.EMAIL IS DISTINCT FROM source.EMAIL
                    OR target.TERRITORY_ID IS DISTINCT FROM source.TERRITORY_ID
                    OR target.HIRE_DATE IS DISTINCT FROM source.HIRE_DATE
                    OR target.IS_ACTIVE IS DISTINCT FROM source.IS_ACTIVE
                    OR target.CREATED_AT IS DISTINCT FROM source.CREATED_AT
                )

                THEN UPDATE SET
                    FIRST_NAME = source.FIRST_NAME,
                    LAST_NAME = source.LAST_NAME,
                    EMAIL = source.EMAIL,
                    TERRITORY_ID = source.TERRITORY_ID,
                    HIRE_DATE = source.HIRE_DATE,
                    IS_ACTIVE = source.IS_ACTIVE,
                    CREATED_AT = source.CREATED_AT,
                    LOADED_AT = CURRENT_TIMESTAMP()

                WHEN NOT MATCHED THEN
                    INSERT (
                        SALES_REP_ID,
                        FIRST_NAME,
                        LAST_NAME,
                        EMAIL,
                        TERRITORY_ID,
                        HIRE_DATE,
                        IS_ACTIVE,
                        CREATED_AT
                    )
                    VALUES (
                        source.SALES_REP_ID,
                        source.FIRST_NAME,
                        source.LAST_NAME,
                        source.EMAIL,
                        source.TERRITORY_ID,
                        source.HIRE_DATE,
                        source.IS_ACTIVE,
                        source.CREATED_AT
                    )
            """)

            result = cursor.fetchone()

            inserted = result[0]
            updated = result[1]

            conn.commit()

            print(f"Records inserted: {inserted}")
            print(f"Records updated: {updated}")

            # STEP D: Validate the destination

            cursor.execute("""
                SELECT
                    COUNT(*),
                    COUNT(DISTINCT SALES_REP_ID)
                FROM RAW.SALES_REPS
            """)

            total, unique_ids = cursor.fetchone()

            print(f"Snowflake total records: {total}")
            print(f"Unique sales rep IDs: {unique_ids}")

            cursor.execute("""
                SELECT FIRST_NAME, LAST_NAME
                FROM RAW.SALES_REPS
                WHERE SALES_REP_ID = 1
            """)

            rep = cursor.fetchone()

            if rep:
                print(f"Sales Rep 1: {rep[0]} {rep[1]}")

            if total != len(df) or unique_ids != len(df):
                raise ValueError(
                    "Snowflake row counts do not match MySQL"
                )

        except Exception:
            conn.rollback()
            raise

        finally:
            cursor.close()

    finally:
        conn.close()


# ============================================================
# 5. Run the ELT pipeline
# ============================================================

def main():

    print("\nStarting Sales Reps ELT Pipeline...\n")

    # Extract
    sales_reps_df = extract_sales_reps()

    # Load and merge
    merge_sales_reps(sales_reps_df)

    print("\nELT pipeline completed successfully!")


if __name__ == "__main__":
    main()
