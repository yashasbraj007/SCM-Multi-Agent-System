import sqlite3
c = sqlite3.connect("data/crm.db").cursor()
c.execute("SELECT disruption_id, order_id, status, severity, delay_days FROM disruption_events")
for row in c.fetchall():
    print(row)
