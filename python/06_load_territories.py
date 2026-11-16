
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import snowflake.connector

load_dotenv()

# 1. Connect to the MySQL operational database
mysql_url = URL.create(
    "mysql+pymysql",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME"),
)

mysql_engine = create_engine(mysql_url)

# 2. Extract territories from MySQL
with mysql_engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT territory_id, territory_name, region, created_at
        FROM territories
        ORDER BY territory_id
    """)).fetchall()

print(f"Extracted {len(rows)} territories from MySQL")

# 3. Connect to Snowflake
sf_conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    authenticator="OAUTH_AUTHORIZATION_CODE",
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE"),
)

# 4. Load data into Snowflake
try:
    cursor = sf_conn.cursor()
    try:
        # For this initial full refresh, replace existing rows.
        cursor.execute("TRUNCATE TABLE RAW.TERRITORIES")

        insert_sql = """
            INSERT INTO RAW.TERRITORIES
                (TERRITORY_ID, TERRITORY_NAME, REGION, CREATED_AT)
            VALUES (%s, %s, %s, %s)
        """

        cursor.executemany(insert_sql, [tuple(row) for row in rows])
        sf_conn.commit()

        print(f"Loaded {len(rows)} territories into Snowflake")

    finally:
        cursor.close()
finally:
    sf_conn.close()
    mysql_engine.dispose()
