"""
Full CRM / operational database - expands beyond customers + orders to
include order line items, customer communications, disruption events,
shipment tracking events, temperature events, and recovery plans/options.

This is what Agent 1 and Agent 2 actually read from and write to during
a disruption 

Full CRM / operational database, LINKED to real scm.db shipments/batches.

"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

CRM_DB_PATH = os.path.join(os.path.dirname(__file__), "crm.db")
SCM_DB_PATH = os.path.join(os.path.dirname(__file__), "scm.db")

CUSTOMERS = [
    ("CUST-001", "Nordic Mills AB", "Flour Milling", "Sweden", "Strategic", "Lena Berg", "Procurement Manager", "lena.berg@nordicmills.se"),
    ("CUST-002", "Rheinland Baeckerei GmbH", "Bakery Chain", "Germany", "Standard", "Markus Weber", "Supply Chain Lead", "m.weber@rheinland-baeckerei.de"),
    ("CUST-003", "Golden Grain Foods Ltd", "Food Distributor", "United Kingdom", "Strategic", "Emily Clarke", "Head of Procurement", "e.clarke@goldengrain.co.uk"),
    ("CUST-004", "Atlas Grain Trading Co", "Commodity Trader", "Egypt", "Strategic", "Youssef Nasser", "Trading Director", "y.nasser@atlasgrain.eg"),
    ("CUST-005", "Pacific Rim Foods Inc", "Food Distributor", "Japan", "Standard", "Kenji Sato", "Purchasing Manager", "k.sato@pacificrim.jp"),
    ("CUST-006", "Andean Harvest S.A.", "Grain Cooperative", "Argentina", "Standard", "Sofia Martinez", "Operations Manager", "s.martinez@andeanharvest.ar"),
    ("CUST-007", "Prairie Milling Corp", "Flour Milling", "Canada", "Strategic", "James Whitfield", "VP Procurement", "j.whitfield@prairiemilling.ca"),
    ("CUST-008", "Baltic Bakeries Group", "Bakery Chain", "Poland", "Standard", "Anna Kowalska", "Supply Chain Manager", "a.kowalska@balticbakeries.pl"),
    ("CUST-009", "Sahara Foods Trading", "Food Distributor", "Morocco", "Standard", "Karim El Amrani", "Purchasing Lead", "k.elamrani@saharafoods.ma"),
    ("CUST-010", "Danube Grain Partners", "Commodity Trader", "Austria", "Strategic", "Julia Hofer", "Trading Manager", "j.hofer@danubegrain.at"),
    ("CUST-011", "Anatolia Flour Mills", "Flour Milling", "Turkey", "Standard", "Emre Yildiz", "Procurement Officer", "e.yildiz@anatoliaflour.tr"),
    ("CUST-012", "Nile Valley Distributors", "Food Distributor", "Egypt", "Standard", "Fatima Hassan", "Purchasing Manager", "f.hassan@nilevalley.eg"),
    ("CUST-013", "Rocky Mountain Bakeries", "Bakery Chain", "USA", "Strategic", "Sarah Johnson", "Supply Chain Director", "s.johnson@rmbakeries.com"),
    ("CUST-014", "Iberia Grain Co-op", "Grain Cooperative", "Spain", "Standard", "Carlos Ruiz", "Operations Lead", "c.ruiz@iberiagrain.es"),
    ("CUST-015", "Nordsee Fisch & Foods", "Food Distributor", "Denmark", "Standard", "Mette Larsen", "Procurement Manager", "m.larsen@nordseefoods.dk"),
    ("CUST-016", "Great Lakes Milling", "Flour Milling", "USA", "Strategic", "Robert Chen", "VP Supply Chain", "r.chen@greatlakesmilling.com"),
    ("CUST-017", "Mekong Rice Traders", "Commodity Trader", "Vietnam", "Standard", "Linh Nguyen", "Trading Manager", "l.nguyen@mekongrice.vn"),
    ("CUST-018", "Alpine Bakery Collective", "Bakery Chain", "Switzerland", "Standard", "Peter Zimmermann", "Head of Procurement", "p.zimmermann@alpinebakery.ch"),
    ("CUST-019", "Levant Food Distribution", "Food Distributor", "Lebanon", "Standard", "Nadia Khalil", "Purchasing Director", "n.khalil@levantfood.lb"),
    ("CUST-020", "Highland Grain Traders", "Commodity Trader", "Scotland", "Standard", "Fiona MacLeod", "Trading Lead", "f.macleod@highlandgrain.uk"),
]

ORDER_STATUSES = ["Fulfilled", "Active", "Delayed", "Cancelled"]
COMM_CHANNELS = ["Email", "Phone Call", "Portal Message"]


def get_real_shipments_from_scm():
    conn = sqlite3.connect(SCM_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.shipment_id, s.batch_id, s.quantity_tons, s.departure_date,
               s.expected_arrival_date, s.status, b.product_id, b.producer_id
        FROM shipments s
        JOIN batches b ON s.batch_id = b.batch_id
    """)
    results = cursor.fetchall()
    conn.close()
    return results


def create_and_populate(n_orders=60, n_disruptions=20):
    if not os.path.exists(SCM_DB_PATH):
        raise FileNotFoundError("scm.db not found - run setup_scm_db.py first.")

    real_shipments = get_real_shipments_from_scm()
    if not real_shipments:
        raise ValueError("No shipments found in scm.db.")

    conn = sqlite3.connect(CRM_DB_PATH)
    cursor = conn.cursor()

    tables = [
        "customers", "orders", "order_items", "customer_communications",
        "disruption_events", "shipment_tracking_events", "temperature_events",
        "recovery_plans", "recovery_options",
    ]
    for t in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {t}")

    cursor.execute("""CREATE TABLE customers (
        customer_id TEXT PRIMARY KEY, company_name TEXT NOT NULL, industry TEXT NOT NULL,
        country TEXT NOT NULL, account_tier TEXT NOT NULL, contact_name TEXT NOT NULL,
        contact_role TEXT NOT NULL, contact_email TEXT NOT NULL)""")

    cursor.execute("""CREATE TABLE orders (
        order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, order_date TEXT NOT NULL,
        requested_delivery_days_from_order INTEGER NOT NULL, status TEXT NOT NULL,
        severity TEXT, notes TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id))""")

    cursor.execute("""CREATE TABLE order_items (
        order_item_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, product TEXT NOT NULL,
        quantity_tons REAL NOT NULL, shipment_id TEXT,
        FOREIGN KEY (order_id) REFERENCES orders (order_id))""")

    cursor.execute("""CREATE TABLE customer_communications (
        comm_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, customer_id TEXT NOT NULL,
        comm_type TEXT NOT NULL, channel TEXT NOT NULL, sent_date TEXT NOT NULL,
        message_summary TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id),
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id))""")

    cursor.execute("""CREATE TABLE disruption_events (
        disruption_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, shipment_id TEXT,
        event_type TEXT NOT NULL, detected_date TEXT NOT NULL, delay_days REAL,
        description TEXT NOT NULL, severity TEXT, status TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id))""")

    cursor.execute("""CREATE TABLE shipment_tracking_events (
        tracking_event_id TEXT PRIMARY KEY, shipment_id TEXT NOT NULL, event_date TEXT NOT NULL,
        location TEXT NOT NULL, event_description TEXT NOT NULL)""")

    cursor.execute("""CREATE TABLE temperature_events (
        temp_event_id TEXT PRIMARY KEY, shipment_id TEXT NOT NULL, recorded_date TEXT NOT NULL,
        temperature_celsius REAL NOT NULL, within_tolerance INTEGER NOT NULL)""")

    cursor.execute("""CREATE TABLE recovery_plans (
        recovery_plan_id TEXT PRIMARY KEY, disruption_id TEXT NOT NULL, created_date TEXT NOT NULL,
        selected_option_id TEXT, status TEXT NOT NULL,
        FOREIGN KEY (disruption_id) REFERENCES disruption_events (disruption_id))""")

    cursor.execute("""CREATE TABLE recovery_options (
        recovery_option_id TEXT PRIMARY KEY, recovery_plan_id TEXT NOT NULL, source_type TEXT NOT NULL,
        source_id TEXT NOT NULL, estimated_delivery_days REAL NOT NULL, score REAL NOT NULL,
        FOREIGN KEY (recovery_plan_id) REFERENCES recovery_plans (recovery_plan_id))""")

    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?)", CUSTOMERS)

    random.seed(21)

    sampled_shipments = random.choices(real_shipments, k=n_orders) if len(real_shipments) < n_orders else random.sample(real_shipments, n_orders)

    orders = []
    order_items = []
    communications = []
    order_to_shipment = {}

    for i, shipment in enumerate(sampled_shipments):
        ship_id, batch_id, qty, dep_date, exp_arrival, ship_status, product, producer_id = shipment
        customer_id = random.choice(CUSTOMERS)[0]
        order_id = f"ORD-{i:04d}"
        order_date = dep_date
        requested_delivery_days = (datetime.strptime(exp_arrival, "%Y-%m-%d") - datetime.strptime(dep_date, "%Y-%m-%d")).days
        status = "Delayed" if ship_status == "Delayed" else random.choices(ORDER_STATUSES, weights=[45, 40, 10, 5])[0]

        orders.append((order_id, customer_id, order_date, requested_delivery_days, status, None, None))
        order_items.append((f"{order_id}-ITEM-0", order_id, product, qty, ship_id))
        order_to_shipment[order_id] = (ship_id, product, qty, requested_delivery_days, producer_id)

        communications.append((
            f"COMM-{i:04d}", order_id, customer_id, "Order Confirmation", random.choice(COMM_CHANNELS),
            order_date, f"Order {order_id} confirmed, linked to shipment {ship_id}.",
        ))

    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", orders)
    cursor.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", order_items)
    cursor.executemany("INSERT INTO customer_communications VALUES (?, ?, ?, ?, ?, ?, ?)", communications)

    delayed_orders = [(oid, *vals) for oid, vals in order_to_shipment.items()
                       if any(o[0] == oid and o[4] == "Delayed" for o in orders)]
    other_orders = [(oid, *vals) for oid, vals in order_to_shipment.items() if oid not in [d[0] for d in delayed_orders]]
    random.shuffle(other_orders)

    disruption_source_orders = (delayed_orders + other_orders)[:n_disruptions]

    disruptions, tracking_events, temp_events, recovery_plans = [], [], [], []

    for i, (order_id, ship_id, product, qty, requested_days, producer_id) in enumerate(disruption_source_orders):
        disruption_id = f"DISR-{i:04d}"
        delay_days = round(random.uniform(1, 60), 1)
        detected_date = datetime.now().strftime("%Y-%m-%d")
        event_type = random.choice(["Transit Delay", "Quality Flag", "Weather Disruption"])
        disruptions.append((
            disruption_id, order_id, ship_id, event_type, detected_date, delay_days,
            f"{event_type} detected on shipment {ship_id} (order {order_id}), {delay_days} day delay.",
            None, "Open",
        ))

        for k in range(random.randint(1, 3)):
            ev_date = (datetime.now() - timedelta(days=random.randint(0, 10))).strftime("%Y-%m-%d")
            tracking_events.append((
                f"TRACK-{i:04d}-{k}", ship_id, ev_date,
                random.choice(["Origin Port", "In Transit", "Customs", "Destination Port"]),
                "Routine tracking update.",
            ))

        for k in range(random.randint(2, 4)):
            temp_date = (datetime.now() - timedelta(days=random.randint(0, 10))).strftime("%Y-%m-%d")
            temp = round(random.uniform(-2, 8), 1)
            temp_events.append((f"TEMP-{i:04d}-{k}", ship_id, temp_date, temp, 1 if -1 <= temp <= 6 else 0))

        plan_id = f"PLAN-{i:04d}"
        recovery_plans.append((plan_id, disruption_id, detected_date, None, "Pending"))

    cursor.executemany("INSERT INTO disruption_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", disruptions)
    cursor.executemany("INSERT INTO shipment_tracking_events VALUES (?, ?, ?, ?, ?)", tracking_events)
    cursor.executemany("INSERT INTO temperature_events VALUES (?, ?, ?, ?, ?)", temp_events)
    cursor.executemany("INSERT INTO recovery_plans VALUES (?, ?, ?, ?, ?)", recovery_plans)

    conn.commit()

    print(f"Created {CRM_DB_PATH} (linked to real scm.db shipments)")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {cursor.fetchone()[0]} rows")

    conn.close()


if __name__ == "__main__":
    create_and_populate()

    conn = sqlite3.connect(CRM_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT disruption_id, order_id, shipment_id, event_type, delay_days FROM disruption_events LIMIT 5")
    disruption_rows = cursor.fetchall()
    conn.close()

    print("\n--- Verifying shipment_id linkage against scm.db ---")
    scm_conn = sqlite3.connect(SCM_DB_PATH)
    scm_cursor = scm_conn.cursor()
    for row in disruption_rows:
        disruption_id, order_id, shipment_id, event_type, delay_days = row
        scm_cursor.execute("SELECT shipment_id, batch_id, status FROM shipments WHERE shipment_id = ?", (shipment_id,))
        match = scm_cursor.fetchone()
        print(f"{disruption_id} -> shipment {shipment_id}: {'FOUND in scm.db -> ' + str(match) if match else 'NOT FOUND (bug!)'}")
    scm_conn.close()