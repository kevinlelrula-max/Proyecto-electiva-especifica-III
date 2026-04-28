import sqlite3

conn = sqlite3.connect("datos.db")

cursor = conn.cursor()

cursor.execute("PRAGMA table_info(registros);")
print(cursor.fetchall())

conn.close()