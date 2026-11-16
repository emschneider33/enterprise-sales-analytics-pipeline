
import os

from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Step 1: Find and load the .env file
# The .env file is located in the main project folder
project_folder = Path(__file__).resolve().parent.parent
load_dotenv(project_folder / ".env")

# Step 2: Retrieve MySQL connection information
db_host = os.getenv("DB_HOST")
db_port = int(os.getenv("DB_PORT", "3306"))
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

# Step 3: Build the MySQL connection URL
database_url = URL.create(
    drivername="mysql+pymysql",
    username=db_user,
    password=db_password,
    host=db_host,
    port=db_port,
    database=db_name
)

# Step 4: Create the SQLAlchemy engine
engine = create_engine(database_url)

# Step 5: Connect to MySQL and run test queries
with engine.connect() as connection:

    # Verify which database we're connected to
    result = connection.execute(
        text("SELECT DATABASE() AS database_name")
    )

    print("Connected to:", result.scalar())

    # Count the number of tables
    result = connection.execute(
        text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = :schema_name
              AND table_type = 'BASE TABLE'
        """),
        {"schema_name": db_name}
    )

    print("Number of tables:", result.scalar())

print("Database connection successful!")

# Step 6: Close the engine's connection pool
engine.dispose()
