import json
import sqlite3
import threading
import time
import paho.mqtt.client as mqtt
import blynklib

# ---------------- CONFIG ----------------
BROKER = "localhost"
TOPIC = "pesquera/congelador"

BLYNK_AUTH = "TU_TOKEN_AQUI"

# ---------------- BLYNK ----------------
blynk = blynklib.Blynk(BLYNK_AUTH)

def run_blynk():
    while True:
        blynk.run()
        time.sleep(0.05)

threading.Thread(target=run_blynk, daemon=True).start()

# ---------------- BASE DE DATOS ----------------
conn = sqlite3.connect("datos.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    congelador TEXT,
    temperatura REAL,
    humedad REAL,
    especie TEXT,
    tiempo INTEGER,
    estado TEXT,
    fecha TEXT
)
""")

conn.commit()

# ---------------- REGLAS ----------------
condiciones = {
    "tilapia": {"temp": -18, "max_horas": 48},
    "bagre": {"temp": -18, "max_horas": 60},
    "trucha": {"temp": -20, "max_horas": 36}
}

def evaluar_estado(temp, tiempo, especie):
    ref = condiciones.get(especie, {"temp": -18, "max_horas": 999})

    if temp > ref["temp"] or tiempo > ref["max_horas"]:
        return "RIESGO"
    return "OPTIMO"

# ---------------- CONTROL INTELIGENTE ----------------
last_temp = {}
last_state = {}
last_save_time = {}

def should_save(congelador, temp, estado):
    """
    Reglas inteligentes:
    - guarda si es primera vez
    - guarda si cambia estado
    - guarda si cambia temperatura significativamente
    """
    if congelador not in last_temp:
        return True

    if last_state.get(congelador) != estado:
        return True

    if abs(last_temp[congelador] - temp) >= 0.3:
        return True

    return False

# ---------------- MQTT ----------------
def on_message(client, userdata, msg):
    global last_temp, last_state, last_save_time

    try:
        data = json.loads(msg.payload.decode())

        congelador = data["congelador"]
        temp = float(data["temperatura"])
        hum = float(data["humedad"])
        especie = data["especie"]
        tiempo = int(data["tiempo_almacenamiento"])

        estado = evaluar_estado(temp, tiempo, especie)
        now = time.time()

        # 🔥 límite de frecuencia por congelador (5 segundos)
        if congelador in last_save_time:
            if now - last_save_time[congelador] < 5:
                return

        # 🔥 lógica inteligente de guardado
        if not should_save(congelador, temp, estado):
            return

        last_temp[congelador] = temp
        last_state[congelador] = estado
        last_save_time[congelador] = now

        print(f"📥 {congelador} | {especie} | {temp}°C | {estado}")

        # ALERTA
        if estado == "RIESGO":
            print("⚠ ALERTA: Producto en riesgo")
            blynk.virtual_write(1, "⚠ RIESGO")

        # GUARDAR BD
        cursor.execute("""
            INSERT INTO registros 
            (congelador, temperatura, humedad, especie, tiempo, estado, fecha)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (congelador, temp, hum, especie, tiempo, estado))

        conn.commit()

        # BLYNK
        blynk.virtual_write(0, temp)
        blynk.virtual_write(1, hum)
        blynk.virtual_write(2, especie)
        blynk.virtual_write(3, estado)

    except Exception as e:
        print("❌ Error MQTT:", e)

# ---------------- MQTT SETUP ----------------
client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.subscribe(TOPIC)
client.on_message = on_message

print("🟢 Backend activo...")
client.loop_forever()