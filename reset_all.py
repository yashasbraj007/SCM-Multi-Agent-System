import sqlite3
c = sqlite3.connect("data/crm.db")
c.execute("UPDATE disruption_events SET status='Open'")
c.commit()
c.close()
print("done - all reset")
