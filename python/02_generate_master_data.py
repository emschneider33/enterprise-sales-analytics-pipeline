
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ----------------------------------
# 1. CONFIGURATION
# ----------------------------------

project_folder = Path(__file__).resolve().parent.parent
load_dotenv(project_folder / ".env")

database_url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME")
)

engine = create_engine(database_url)

# Fixed seeds make generated data reproducible
fake = Faker("en_US")
Faker.seed(42)
random.seed(42)

# ----------------------------------
# 2. DEFINE SALES TERRITORIES
# ----------------------------------

territories = [
    ("Charlotte Metro", "Southeast"),
    ("Atlanta Metro", "Southeast"),
    ("New York Metro", "Northeast"),
    ("Dallas Metro", "South Central"),
    ("Miami Metro", "Southeast"),
    ("Orlando Metro", "Southeast"),
    ("Nashville Metro", "Southeast"),
    ("Raleigh Metro", "Southeast"),
    ("Boston Metro", "Northeast"),
    ("Philadelphia Metro", "Northeast"),
    ("Washington DC Metro", "Mid-Atlantic"),
    ("Chicago Metro", "Midwest"),
    ("Detroit Metro", "Midwest"),
    ("Minneapolis Metro", "Midwest"),
    ("Houston Metro", "South Central"),
    ("Denver Metro", "Mountain"),
    ("Phoenix Metro", "Southwest"),
    ("Los Angeles Metro", "West"),
    ("San Francisco Metro", "West"),
    ("Seattle Metro", "Northwest")
]

# ----------------------------------
# 3. INSERT MISSING TERRITORIES
# ----------------------------------

with engine.begin() as connection:

    existing = connection.execute(
        text("SELECT territory_name FROM territories")
    ).scalars().all()

    existing_names = set(existing)

    for territory_name, region in territories:

        if territory_name not in existing_names:

            connection.execute(
                text("""
                    INSERT INTO territories
                        (territory_name, region)
                    VALUES
                        (:territory_name, :region)
                """),
                {
                    "territory_name": territory_name,
                    "region": region
                }
            )

    result = connection.execute(
        text("SELECT COUNT(*) FROM territories")
    )

    print("Total territories:", result.scalar())

# ----------------------------------
# 4. GENERATE SALES REPRESENTATIVES
# ----------------------------------

with engine.begin() as connection:

    territory_ids = connection.execute(
        text("SELECT territory_id FROM territories")
    ).scalars().all()

    existing_reps = connection.execute(
        text("SELECT COUNT(*) FROM sales_reps")
    ).scalar()

    reps_to_create = max(0, 100 - existing_reps)

    sales_reps = []

    for i in range(reps_to_create):

        first_name = fake.first_name()
        last_name = fake.last_name()

        # Unique synthetic email for each generated rep
        email = f"salesrep_{i + existing_reps + 1}@example.com"

        sales_reps.append({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "territory_id": random.choice(territory_ids),
            "hire_date": fake.date_between(
                start_date="-10y",
                end_date="-30d"
            )
        })

    if sales_reps:

        connection.execute(
            text("""
                INSERT INTO sales_reps
                    (first_name, last_name, email,
                     territory_id, hire_date)
                VALUES
                    (:first_name, :last_name, :email,
                     :territory_id, :hire_date)
            """),
            sales_reps
        )

    result = connection.execute(
        text("SELECT COUNT(*) FROM sales_reps")
    )

    print("Total sales representatives:", result.scalar())

engine.dispose()

print("Master data generation completed!")
