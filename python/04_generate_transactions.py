
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ------------------------------------
# 1. CONFIGURATION
# ------------------------------------

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

TOTAL_ORDERS = 100_000
BATCH_SIZE = 5_000
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2026, 10, 31, 23, 59, 59)

# ------------------------------------
# 2. LOAD SOURCE REFERENCE DATA
# ------------------------------------

with engine.connect() as connection:

    customer_ids = connection.execute(
        text("SELECT customer_id FROM customers ORDER BY customer_id")
    ).scalars().all()

    products = connection.execute(
        text("""
            SELECT product_id, list_price, unit_cost
            FROM products
            ORDER BY product_id
        """)
    ).mappings().all()

if not customer_ids or not products:
    raise RuntimeError(
        "Customers and products must be populated first."
    )

# Convert database rows into simple dictionaries
product_list = [dict(p) for p in products]

# ------------------------------------
# 3. GENERATE TRANSACTION BATCHES
# ------------------------------------

date_range_seconds = int(
    (END_DATE - START_DATE).total_seconds()
)

for batch_start in range(1, TOTAL_ORDERS + 1, BATCH_SIZE):

    batch_end = min(
        batch_start + BATCH_SIZE - 1,
        TOTAL_ORDERS
    )

    orders_batch = []
    items_batch = []

    for order_id in range(batch_start, batch_end + 1):

        # Each order has a reproducible random sequence
        rng = random.Random(100_000 + order_id)

        customer_id = rng.choice(customer_ids)

        order_date = START_DATE + timedelta(
            seconds=rng.randint(0, date_range_seconds)
        )

        order_status = rng.choices(
            ["Completed", "Pending", "Canceled"],
            weights=[85, 10, 5]
        )[0]

        order_channel = rng.choice([
            "Direct Sales",
            "E-Commerce",
            "Inside Sales"
        ])

        shipping_amount = round(
            rng.uniform(0, 35), 2
        )

        orders_batch.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "order_date": order_date,
            "order_status": order_status,
            "order_channel": order_channel,
            "shipping_amount": shipping_amount
        })

        # Each order contains between 1 and 5 lines
        number_of_items = rng.randint(1, 5)

        selected_products = rng.sample(
            product_list,
            number_of_items
        )

        for line_number, product in enumerate(
            selected_products, start=1
        ):

            quantity = rng.randint(1, 20)

            # Use historical transaction price/cost snapshots
            unit_price = Decimal(str(product["list_price"]))
            unit_cost = Decimal(str(product["unit_cost"]))

            discount_pct = Decimal(
                str(rng.choice([0, 0.05, 0.10, 0.15, 0.20]))
            )

            # Stable order-item ID for safe reruns
            order_item_id = (
                (order_id - 1) * 5 + line_number
            )

            items_batch.append({
                "order_item_id": order_item_id,
                "order_id": order_id,
                "product_id": product["product_id"],
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "unit_cost": unit_cost
            })

    # ------------------------------------
    # 4. INSERT BATCH INTO MYSQL
    # ------------------------------------

    with engine.begin() as connection:

        connection.execute(
            text("""
                INSERT INTO orders (
                    order_id,
                    customer_id,
                    order_date,
                    order_status,
                    order_channel,
                    shipping_amount
                )
                VALUES (
                    :order_id,
                    :customer_id,
                    :order_date,
                    :order_status,
                    :order_channel,
                    :shipping_amount
                )
                ON DUPLICATE KEY UPDATE
                    order_id = order_id
            """),
            orders_batch
        )

        connection.execute(
            text("""
                INSERT INTO order_items (
                    order_item_id,
                    order_id,
                    product_id,
                    quantity,
                    unit_price,
                    discount_pct,
                    unit_cost
                )
                VALUES (
                    :order_item_id,
                    :order_id,
                    :product_id,
                    :quantity,
                    :unit_price,
                    :discount_pct,
                    :unit_cost
                )
                ON DUPLICATE KEY UPDATE
                    order_item_id = order_item_id
            """),
            items_batch
        )

    print(
        f"Processed orders {batch_start:,} "
        f"through {batch_end:,}"
    )

engine.dispose()

print("Transaction generation completed!")
