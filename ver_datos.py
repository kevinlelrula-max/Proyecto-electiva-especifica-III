import sqlite3

conn = sqlite3.connect("datos.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM registros")
datos = cursor.fetchall()

print("📊 Datos guardados:")
for fila in datos:
    print(fila)