"""
Orchestrator - fully connected to real business data.

Instead of fake DisruptionEvent objects, this pulls real active orders from
the CRM database, runs them through Agent 1's severity classifier, queries
the real warehouse database for recovery options via Agent 2's logic, and
writes the result back into the CRM - closing the full loop with real data.

Orchestrator - fully connected across BOTH databases.
"""

import sys
import os
import sqlite3

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agents", "agent1_logistics"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "agents", "agent2_recovery"))

from severity_classifier import DisruptionEvent, classify_severity, Severity
from recovery_matcher import find_best_recovery_options

CRM_DB = os.path.join(os.path.dirname(__file__), "..", "data", "crm.db")
SCM_DB = os.path.join(os.path.dirname(__file__), "..", "data", "scm.db")

PRODUCT_SHELF_LIFE_DAYS = {"Wheat": 180, "Barley": 180, "Rice": 365, "Corn": 120, "Soybeans": 150}


def get_open_disruptions(limit=5):
    conn = sqlite3.connect(CRM_DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.disruption_id, d.order_id, d.shipment_id, d.event_type, d.delay_days,
               c.company_name, c.contact_name
        FROM disruption_events d
        JOIN orders o ON d.order_id = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE d.status = 'Open'
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def resolve_shipment_details(shipment_id):
    conn = sqlite3.connect(SCM_DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.shipment_id, s.quantity_tons, b.product_id, b.batch_id
        FROM shipments s
        JOIN batches b ON s.batch_id = b.batch_id
        WHERE s.shipment_id = ?
    """, (shipment_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_order_requested_days(order_id):
    conn = sqlite3.connect(CRM_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT requested_delivery_days_from_order FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 14


def write_results(disruption_id, order_id, severity, options):
    conn = sqlite3.connect(CRM_DB)
    cursor = conn.cursor()

    cursor.execute("UPDATE disruption_events SET severity = ?, status = 'Resolved' WHERE disruption_id = ?",
                   (severity, disruption_id))
    cursor.execute("UPDATE orders SET severity = ? WHERE order_id = ?", (severity, order_id))

    if options:
        plan_id = f"PLAN-{disruption_id.split('-')[1]}"
        cursor.execute("SELECT recovery_plan_id FROM recovery_plans WHERE disruption_id = ?", (disruption_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute(
                "INSERT INTO recovery_plans (recovery_plan_id, disruption_id, created_date, selected_option_id, status) "
                "VALUES (?, ?, date('now'), ?, 'Selected')",
                (plan_id, disruption_id, f"{plan_id}-OPT-0"),
            )
        else:
            plan_id = existing[0]
            cursor.execute("UPDATE recovery_plans SET selected_option_id = ?, status = 'Selected' WHERE recovery_plan_id = ?",
                           (f"{plan_id}-OPT-0", plan_id))

        for i, opt in enumerate(options):
            cursor.execute(
                "INSERT OR REPLACE INTO recovery_options "
                "(recovery_option_id, recovery_plan_id, source_type, source_id, estimated_delivery_days, score) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (f"{plan_id}-OPT-{i}", plan_id, opt.source_type, opt.source_id, opt.estimated_delivery_days, opt.score),
            )

    conn.commit()
    conn.close()


def handle_disruption(disruption_row):
    disruption_id, order_id, shipment_id, event_type, delay_days, company_name, contact_name = disruption_row

    print(f"\n{'='*75}")
    print(f"{disruption_id} | Order {order_id} | {company_name} (contact: {contact_name})")
    print(f"Event: {event_type} | Shipment: {shipment_id} | Delay: {delay_days} days")
    print(f"{'='*75}")

    shipment = resolve_shipment_details(shipment_id)
    if not shipment:
        print(f"[Error] Shipment {shipment_id} not found in scm.db - skipping.")
        return

    _, quantity, product, batch_id = shipment
    requested_days = get_order_requested_days(order_id)
    shelf_life = PRODUCT_SHELF_LIFE_DAYS.get(product, 180)

    event = DisruptionEvent(
        shipment_id=shipment_id, product=product, delay_days=delay_days,
        remaining_shelf_life_days=shelf_life, requested_delivery_days_from_now=requested_days,
    )
    result = classify_severity(event)
    print(f"\n[Agent 1] Product: {product} (batch {batch_id}) | Qty: {quantity}")
    print(f"[Agent 1] Severity: {result.severity.value} | Buffer: {result.buffer_days} days")
    print(f"[Agent 1] {result.explanation}")

    if result.severity == Severity.LOW:
        write_results(disruption_id, order_id, result.severity.value, [])
        print(f"\n[System] No recovery needed. Disruption marked resolved, CRM updated.")
        return

    print(f"\n[System] Severity {result.severity.value} - searching scm.db (warehouses + producers)...")
    options = find_best_recovery_options(product, quantity, requested_days, top_n=3, db_path=SCM_DB)

    if not options:
        write_results(disruption_id, order_id, result.severity.value, [])
        print(f"[Agent 2] No viable recovery options found.")
        return

    print(f"\n[Agent 2] Top recovery options:")
    for opt in options:
        print(f"  - [{opt.source_type}] {opt.source_id}: qty~{opt.available_quantity:.0f}, "
              f"ETA {opt.estimated_delivery_days:.1f}d, score={opt.score}")

    write_results(disruption_id, order_id, result.severity.value, options)
    print(f"\n[System] CRM updated: recovery plan written with {len(options)} scored options "
          f"(best: [{options[0].source_type}] {options[0].source_id}).")


if __name__ == "__main__":
    disruptions = get_open_disruptions(limit=5)
    for row in disruptions:
        handle_disruption(row)