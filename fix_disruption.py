import sqlite3
c = sqlite3.connect('data/crm.db')
c.execute("UPDATE disruption_events SET delay_days=200, status='Open' WHERE disruption_id='DISR-0019'")
c.commit()
print('done')
