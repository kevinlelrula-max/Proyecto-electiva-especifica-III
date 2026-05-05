import psycopg2

DATABASE_URL = "postgresql://climalink:rTzY0aKIvu9f1MHUQVT0ZXo3t0xoXBhj@dpg-d7rqlv7avr4c73a43k70-a.oregon-postgres.render.com/climalink"

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute(
    "UPDATE usuarios SET email_alerta = %s WHERE username = %s",
    ('pruebanotificaciones31@gmail.com', 'admin')
)
conn.commit()

cursor.execute("SELECT username, email_alerta FROM usuarios WHERE username = 'admin'")
row = cursor.fetchone()
print(f"✅ Actualizado: usuario={row[0]}, email={row[1]}")

cursor.close()
conn.close()
