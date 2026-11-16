
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv


# ============================================================
# 1. Load environment variables
# ============================================================

project_folder = Path(__file__).resolve().parent.parent

load_dotenv(project_folder / ".env")


# ============================================================
# 2. Locate our existing Snowflake private key
# ============================================================

private_key_path = (
    Path.home() / "snowflake_keys" / "rsa_key.p8"
)

if not private_key_path.is_file():
    raise FileNotFoundError(
        f"Private key not found: {private_key_path}"
    )


# ============================================================
# 3. Retrieve authentication settings
# ============================================================

snowflake_login = os.getenv("SNOWFLAKE_LOGIN_NAME")

key_passphrase = os.getenv("SNOWFLAKE_KEY_PASSPHRASE")

if not snowflake_login or not key_passphrase:
    raise ValueError(
        "Missing Snowflake login name or key passphrase"
    )


# ============================================================
# 4. Connect using key-pair authentication
# ============================================================

print("Connecting to Snowflake...")

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=snowflake_login,

    authenticator="SNOWFLAKE_JWT",

    private_key_file=str(private_key_path),
    private_key_password=key_passphrase,

    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema="RAW",
    role=os.getenv("SNOWFLAKE_ROLE"),
)


# ============================================================
# 5. Verify connection
# ============================================================

try:
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                CURRENT_USER(),
                CURRENT_DATABASE(),
                CURRENT_WAREHOUSE()
        """)

        result = cursor.fetchone()

        print("\nConnection successful!")
        print(f"Snowflake user: {result[0]}")
        print(f"Database: {result[1]}")
        print(f"Warehouse: {result[2]}")

    finally:
        cursor.close()

finally:
    conn.close()

print("\nKey-pair authentication test completed!")
