"""
Sets up a persistent SQLite database simulating the company's global
warehouse/producer network - replaces the in-memory generate_mock_network()
with a real, queryable data store.

Run this once to create and populate data/warehouse_network.db.
"""
"""
Expanded Supply Chain Management schema - separates producers from
warehouses, and adds products, batches, inventory, shipments, and routes.
This replaces the earlier flat "warehouse_network.db" with a proper
multi-table SCM structure, sitting alongside the CRM (crm.db).

Run this once to create and populate data/scm.db.
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "scm.db")

PRODUCTS = ["Wheat", "Barley", "Rice", "Corn", "Soybeans"]
REGIONS = ["North America", "South America", "Europe", "Asia", "Africa", "Oceania"]

PRODUCER_NAME_PARTS = [
    "Golden", "Prairie", "Highland", "River Valley", "Sunrise", "Meadow", "Delta",
    "Coastal", "Heartland", "Blue Ridge", "Sierra", "Northern", "Southern", "Great Plains",
]
PRODUCER_SUFFIXES = ["Farms", "Cooperative", "Agri Group", "Growers Association", "Estates"]

WAREHOUSE_CITIES = [
    ("Rotterdam", "Europe"), ("Hamburg", "Europe"), ("Odessa", "Europe"),
    ("New Orleans", "North America"), ("Vancouver", "North America"), ("Chicago", "North America"),
    ("Santos", "South America"), ("Buenos Aires", "South America"), ("Rosario", "South America"),
    ("Singapore", "Asia"), ("Mumbai", "Asia"), ("Shanghai", "Asia"),
    ("Alexandria", "Africa"), ("Durban", "Africa"), ("Casablanca", "Africa"),
    ("Melbourne", "Oceania"), ("Auckland", "Oceania"),
]


def create_and_populate(n_producers=100, n_warehouses=50, n_batches=250, n_shipments=150):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for table in ["producers", "warehouses", "products", "batches", "inventory", "shipments", "routes"]:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    cursor.execute("""
        CREATE TABLE products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            default_shelf_life_days INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE producers (
            producer_id TEXT PRIMARY KEY,
            producer_name TEXT NOT NULL,
            region TEXT NOT NULL,
            primary_product TEXT NOT NULL,
            reliability_score REAL NOT NULL,
            typical_lead_time_days REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE warehouses (
            warehouse_id TEXT PRIMARY KEY,
            city TEXT NOT NULL,
            region TEXT NOT NULL,
            capacity_tons REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE batches (
            batch_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            producer_id TEXT NOT NULL,
            harvest_date TEXT NOT NULL,
            quantity_tons REAL NOT NULL,
            quality_grade TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (product_id),
            FOREIGN KEY (producer_id) REFERENCES producers (producer_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE inventory (
            inventory_id TEXT PRIMARY KEY,
            warehouse_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            quantity_tons REAL NOT NULL,
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id),
            FOREIGN KEY (batch_id) REFERENCES batches (batch_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE routes (
            route_id TEXT PRIMARY KEY,
            origin_type TEXT NOT NULL,
            origin_id TEXT NOT NULL,
            destination_type TEXT NOT NULL,
            destination_id TEXT NOT NULL,
            standard_transit_days REAL NOT NULL,
            transport_mode TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE shipments (
            shipment_id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            route_id TEXT NOT NULL,
            order_id TEXT,
            quantity_tons REAL NOT NULL,
            departure_date TEXT NOT NULL,
            expected_arrival_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches (batch_id),
            FOREIGN KEY (route_id) REFERENCES routes (route_id)
        )
    """)

    shelf_life = {"Wheat": 180, "Barley": 180, "Rice": 365, "Corn": 120, "Soybeans": 150}
    cursor.executemany(
        "INSERT INTO products VALUES (?, ?, ?)",
        [(p, p, shelf_life[p]) for p in PRODUCTS],
    )

    random.seed(11)

    producers = []
    for i in range(n_producers):
        name = f"{random.choice(PRODUCER_NAME_PARTS)} {random.choice(PRODUCER_SUFFIXES)}"
        producers.append((
            f"PROD-{i:03d}", name, random.choice(REGIONS), random.choice(PRODUCTS),
            round(random.uniform(0.7, 0.99), 2), round(random.uniform(3, 20), 1),
        ))
    cursor.executemany("INSERT INTO producers VALUES (?, ?, ?, ?, ?, ?)", producers)

    warehouses = []
    wh_cities = (WAREHOUSE_CITIES * ((n_warehouses // len(WAREHOUSE_CITIES)) + 1))[:n_warehouses]
    for i, (city, region) in enumerate(wh_cities):
        warehouses.append((
            f"WH-{i:03d}", city, region, round(random.uniform(5000, 50000), 0),
        ))
    cursor.executemany("INSERT INTO warehouses VALUES (?, ?, ?, ?)", warehouses)

    batches = []
    for i in range(n_batches):
        producer = random.choice(producers)
        product = producer[3]
        harvest_days_ago = random.randint(1, 120)
        harvest_date = (datetime.now() - timedelta(days=harvest_days_ago)).strftime("%Y-%m-%d")
        batches.append((
            f"BATCH-{i:04d}", product, producer[0], harvest_date,
            round(random.uniform(50, 800), 1), random.choice(["Grade A", "Grade B", "Grade C"]),
        ))
    cursor.executemany("INSERT INTO batches VALUES (?, ?, ?, ?, ?, ?)", batches)

    inventory = []
    for i, batch in enumerate(batches):
        n_splits = random.randint(1, 2)
        remaining = batch[4]
        for s in range(n_splits):
            wh = random.choice(warehouses)
            qty = round(remaining / n_splits, 1)
            inventory.append((f"INV-{i:04d}-{s}", wh[0], batch[0], qty))
    cursor.executemany("INSERT INTO inventory VALUES (?, ?, ?, ?)", inventory)

    routes = []
    route_i = 0
    for producer in random.sample(producers, min(60, len(producers))):
        wh = random.choice(warehouses)
        routes.append((
            f"ROUTE-{route_i:04d}", "producer", producer[0], "warehouse", wh[0],
            round(random.uniform(2, 25), 1), random.choice(["Truck", "Rail", "Ship"]),
        ))
        route_i += 1
    for wh in warehouses:
        routes.append((
            f"ROUTE-{route_i:04d}", "warehouse", wh[0], "customer_region", wh[2],
            round(random.uniform(3, 45), 1), random.choice(["Truck", "Rail", "Ship", "Air"]),
        ))
        route_i += 1
    cursor.executemany("INSERT INTO routes VALUES (?, ?, ?, ?, ?, ?, ?)", routes)

    shipments = []
    wh_routes = [r for r in routes if r[1] == "producer"]
    for i in range(n_shipments):
        route = random.choice(wh_routes)
        candidate_batches = [b for b in batches if b[2] == route[2]]
        if not candidate_batches:
            continue
        batch = random.choice(candidate_batches)
        dep_days_ago = random.randint(0, 20)
        departure_date = (datetime.now() - timedelta(days=dep_days_ago)).strftime("%Y-%m-%d")
        expected_arrival = (datetime.now() - timedelta(days=dep_days_ago) + timedelta(days=route[5])).strftime("%Y-%m-%d")
        shipments.append((
            f"SHIP-{i:04d}", batch[0], route[0], None,
            round(random.uniform(50, 500), 1), departure_date, expected_arrival,
            random.choices(["In Transit", "Delivered", "Delayed"], weights=[40, 45, 15])[0],
        ))
    cursor.executemany("INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?, ?, ?)", shipments)

    conn.commit()

    print(f"Created {DB_PATH}")
    for table in ["products", "producers", "warehouses", "batches", "inventory", "routes", "shipments"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cursor.fetchone()[0]} rows")

    conn.close()


if __name__ == "__main__":
    create_and_populate()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("\n--- Sample: Wheat producers ---")
    cursor.execute("SELECT producer_id, producer_name, region, reliability_score FROM producers WHERE primary_product='Wheat' LIMIT 5")
    for row in cursor.fetchall():
        print(row)

    print("\n--- Sample: In-transit shipments ---")
    cursor.execute("SELECT shipment_id, batch_id, departure_date, expected_arrival_date, status FROM shipments WHERE status='In Transit' LIMIT 5")
    for row in cursor.fetchall():
        print(row)
    conn.close()
