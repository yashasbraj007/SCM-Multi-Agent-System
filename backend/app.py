import sys, os, sqlite3
from flask import Flask, jsonify

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "orchestrator"))
from orchestrator import get_open_disruptions, handle_disruption, CRM_DB

app = Flask(__name__)

def fetch_order_summary(order_id):
    conn = sqlite3.connect(CRM_DB)
    cur = conn.cursor()
    cur.execute("SELECT order_id, severity FROM orders WHERE order_id = ?", (order_id,))
    order = cur.fetchone()
    cur.execute("""SELECT message_summary FROM customer_communications
                   WHERE order_id = ? ORDER BY sent_date DESC LIMIT 1""", (order_id,))
    comm = cur.fetchone()
    conn.close()
    return {
        "order_id": order[0] if order else order_id,
        "severity": order[1] if order else None,
        "explanation": comm[0] if comm else None,
    }

@app.route("/disruptions", methods=["GET"])
def list_disruptions():
    rows = get_open_disruptions(limit=20)
    return jsonify([
        {
            "disruption_id": r[0],
            "order_id": r[1],
            "shipment_id": r[2],
            "event_type": r[3],
            "delay_days": r[4],
            "company": r[5],
            "contact_name": r[6],
        }
        for r in rows
    ])

@app.route("/disruptions/process", methods=["POST"])
def process_disruptions():
    rows = get_open_disruptions(limit=10)
    results = []
    for row in rows:
        handle_disruption(row)
        results.append(fetch_order_summary(row[1]))
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=False, port=5000, use_reloader=False)
