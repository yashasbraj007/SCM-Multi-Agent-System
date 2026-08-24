import sqlite3
c = sqlite3.connect("data/scm.db").cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
for row in c.fetchall():
    print(row)
