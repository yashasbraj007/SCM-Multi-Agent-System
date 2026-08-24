import sqlite3

c = sqlite3.connect("data/crm.db")
result = c.execute(
    "SELECT disruption_id, status, delay_days FROM disruption_events WHERE disruption_id=?",
    ("DISR-0019",)
).fetchall()
print(result)
c.close()