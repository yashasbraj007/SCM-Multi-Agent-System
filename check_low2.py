import sqlite3
c = sqlite3.connect("data/crm.db").cursor()
c.execute("SELECT disruption_id, status FROM disruption_events WHERE disruption_id='DISR-0000'")
print(c.fetchall())
