import sqlite3
c = sqlite3.connect("data/crm.db")
c.execute("UPDATE disruption_events SET status='Open' WHERE disruption_id='DISR-0000'")
c.commit()
c.close()
print("done")
