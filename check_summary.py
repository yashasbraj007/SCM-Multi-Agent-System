import sqlite3
c = sqlite3.connect("data/crm.db").cursor()
c.execute("SELECT status, COUNT(*) FROM disruption_events GROUP BY status")
print(c.fetchall())
