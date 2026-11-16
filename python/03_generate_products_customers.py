
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ---------------------------------
# 1. DATABASE CONNECTION
# ---------------------------------

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

fake = Faker("en_US")
Faker.seed(123)
random.seed(123)

# ---------------------------------
# 2. PRODUCT CATEGORIES
# ---------------------------------

categories = [
    "Office Supplies", "Electronics", "Computers",
    "Networking", "Printers", "Storage",
    "Furniture", "Safety Equipment", "Tools",
    "Packaging", "Cleaning Supplies", "Lighting",
    "Electrical", "Industrial Supplies", "Hardware",
    "Medical Supplies", "Laboratory Supplies",
    "Automotive", "HVAC", "Plumbing",
    "Building Materials", "Security",
    "Telecommunications", "Food Service",
    "Maintenance"
]

with engine.begin() as connection:

    existing_categories = set(
        connection.execute(
            text("SELECT category_name FROM product_categories")
        ).scalars().all()
    )

    for category in categories:
        if category not in existing_categories:
            connection.execute(
                text("""
                    INSERT INTO product_categories
                        (category_name)
                    VALUES (:category_name)
                """),
                {"category_name": category}
            )

    category_ids = connection.execute(
        text("SELECT category_id FROM product_categories")
    ).scalars().all()

    print("Product categories:", len(category_ids))

# ---------------------------------
# 3. GENERATE PRODUCTS
# ---------------------------------

with engine.begin() as connection:

    existing_skus = set(
        connection.execute(
            text("SELECT product_sku FROM products")
        ).scalars().all()
    )

    products = []

    for i in range(1, 1001):

        sku = f"SKU-{i:05d}"

        if sku in existing_skus:
            continue

        unit_cost = round(random.uniform(5, 500), 2)
        markup = random.uniform(1.2, 2.5)
        list_price = round(unit_cost * markup, 2)

        products.append({
            "product_sku": sku,
            "product_name": f"{fake.word().title()} Product {i}",
            "category_id": random.choice(category_ids),
            "unit_cost": unit_cost,
            "list_price": list_price,
            "product_status": random.choices(
                ["Active", "Discontinued"],
                weights=[95, 5]
            )[0]
        })

    if products:
        connection.execute(
            text("""
                INSERT INTO products
                    (product_sku, product_name, category_id,
                     unit_cost, list_price, product_status)
                VALUES
                    (:product_sku, :product_name, :category_id,
                     :unit_cost, :list_price, :product_status)
            """),
            products
        )

    print("Products generated:", len(products))

# ---------------------------------
# 4. GENERATE CUSTOMERS
# ---------------------------------

with engine.begin() as connection:

    sales_rep_ids = connection.execute(
        text("SELECT sales_rep_id FROM sales_reps")
    ).scalars().all()

    existing_customers = connection.execute(
        text("SELECT COUNT(*) FROM customers")
    ).scalar()

    customers_to_create = max(0, 5000 - existing_customers)

    customer_types = [
        "Small Business", "Mid-Market", "Enterprise"
    ]

    industries = [
        "Healthcare", "Manufacturing", "Retail",
        "Technology", "Construction", "Distribution",
        "Professional Services", "Hospitality"
    ]

    customers = []

    for i in range(customers_to_create):

        customers.append({
            "customer_name": fake.company(),
            "customer_type": random.choices(
                customer_types,
                weights=[55, 30, 15]
            )[0],
            "industry": random.choice(industries),
            "email": f"customer_{i + existing_customers + 1}@example.com",
            "phone": fake.phone_number()[:30],
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.postcode(),
            "sales_rep_id": random.choice(sales_rep_ids),
            "customer_status": random.choices(
                ["Active", "Inactive"],
                weights=[90, 10]
            )[0]
        })

    if customers:
        connection.execute(
            text("""
                INSERT INTO customers
                    (customer_name, customer_type, industry,
                     email, phone, city, state, zip_code,
                     sales_rep_id, customer_status)
                VALUES
                    (:customer_name, :customer_type, :industry,
                     :email, :phone, :city, :state, :zip_code,
                     :sales_rep_id, :customer_status)
            """),
            customers
        )

    print("Customers generated:", len(customers))

engine.dispose()

print("Product and customer generation completed!")
