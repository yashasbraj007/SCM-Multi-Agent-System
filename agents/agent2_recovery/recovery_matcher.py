"""
Agent 2 - Inventory & Recovery Planning
Rule-based warehouse/producer matching with delay-tolerance scoring.

Given a disrupted shipment (product + quantity + requested delivery time),
this searches a simulated network of warehouses/producers for candidates
that can cover the shortfall, and ranks them using a tolerance-aware score:
small delays past the requested time barely hurt the ranking, large delays
are heavily penalized.
"""
"""
Agent 2 - searches BOTH existing warehouse inventory AND producers
directly in scm.db
"""

import sqlite3
from dataclasses import dataclass

def tolerance_score(days_late: float) -> float:
    if days_late <= 0:
        return 0.0
    elif days_late <= 7:
        return days_late * 1.0
    elif days_late <= 20:
        return 7.0 + (days_late - 7) * 3.0
    else:
        return 7.0 + (13 * 3.0) + (days_late - 20) * 10.0


@dataclass
class RecoveryCandidate:
    source_type: str
    source_id: str
    available_quantity: float
    estimated_delivery_days: float
    days_late: float
    score: float


def search_warehouse_inventory(product, min_quantity, requested_delivery_days, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.warehouse_id, w.region, SUM(i.quantity_tons) as total_qty
        FROM inventory i
        JOIN batches b ON i.batch_id = b.batch_id
        JOIN warehouses w ON i.warehouse_id = w.warehouse_id
        WHERE b.product_id = ?
        GROUP BY w.warehouse_id
        HAVING total_qty >= ?
    """, (product, min_quantity))
    rows = cursor.fetchall()
    conn.close()

    candidates = []
    for warehouse_id, region, total_qty in rows:
        eta_days = 5.0
        days_late = eta_days - requested_delivery_days
        candidates.append(RecoveryCandidate("warehouse", warehouse_id, total_qty, eta_days, round(days_late, 1), round(tolerance_score(days_late), 2)))
    return candidates


def search_producers(product, min_quantity, requested_delivery_days, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT producer_id, producer_name, region, reliability_score, typical_lead_time_days
        FROM producers
        WHERE primary_product = ?
    """, (product,))
    rows = cursor.fetchall()
    conn.close()

    candidates = []
    for producer_id, name, region, reliability, lead_time in rows:
        effective_eta = lead_time * (2 - reliability)
        days_late = effective_eta - requested_delivery_days
        base_score = tolerance_score(days_late)
        reliability_penalty = (1 - reliability) * 5
        candidates.append(RecoveryCandidate(
            "producer", producer_id, min_quantity, round(effective_eta, 1),
            round(days_late, 1), round(base_score + reliability_penalty, 2)
        ))
    return candidates


def find_best_recovery_options(product, requested_quantity, requested_delivery_days, top_n=5, db_path="scm.db"):
    warehouse_candidates = search_warehouse_inventory(product, requested_quantity, requested_delivery_days, db_path)
    producer_candidates = search_producers(product, requested_quantity, requested_delivery_days, db_path)
    all_candidates = warehouse_candidates + producer_candidates
    all_candidates.sort(key=lambda c: c.score)
    return all_candidates[:top_n]