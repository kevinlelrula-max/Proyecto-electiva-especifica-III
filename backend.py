import json
import sqlite3
import threading
import time
import paho.mqtt.client as mqtt
from datetime import datetime

# ============================================================
#  CONFIGURACIÓN — Cambia USAR_NUBE según el entorno
#  True  → HiveMQ Cloud (cualquier red)
#  False → Mosquitto local (misma PC)
# ============================================================
USAR_NUBE = True

if USAR_NUBE:
    BROKER    = "0b158edb9649430e9bf6c29ac988da7f.s1.eu.hivemq.cloud"
    PORT      = 8883
    MQTT_USER = "pesquera"
    MQTT_PASS = "Pesquera2026!"
else:
    BROKER    = "localhost"
    PORT      = 1883
    MQTT_USER = None
    MQTT_PASS = None

TOPIC = "pesquera/congelador"

# ---------------- BASE DE DATOS ----------------
conn = sqlite3.connect("datos.db", check_same_thread=False)
cursor = conn.cursor()
db_lock = threading.Lock()

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    reset_token TEXT,
    activo INTEGER DEFAULT 1
)
""")
conn.commit()

# ---------------- REGLAS ----------------
condiciones = {
    "tilapia": {"temp": -18, "max_horas": 48},
    "bagre":   {"temp": -18, "max_horas": 60},
    "trucha":  {"temp": -20, "max_horas": 36}
}

def evaluar_estado(temp, tiempo, especie):
    ref = condiciones.get(especie, {"temp": -18, "max_horas": 999})
    if temp > ref["temp"] or tiempo > ref["max_horas"]:
        return "RIESGO"
    return "OPTIMO"

# ---------------- CONTROL INTELIGENTE DE GUARDADO ----------------
last_temp       = {}
last_state      = {}
last_save_time  = {}

def should_save(congelador, temp, estado):
    """
    Guarda solo si:
    - Es la primera vez que se recibe ese congelador
    - Cambia el estado (OPTIMO ↔ RIESGO)
    - La temperatura varía más de 0.3°C
    """
    if congelador not in last_temp:
        return True
    if last_state.get(congelador) != estado:
        return True
    if abs(last_temp[congelador] - temp) >= 0.3:
        return True
    return False

# ---------------- MQTT ----------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        modo = "HiveMQ Cloud ☁" if USAR_NUBE else "Mosquitto Local 🖥"
        print(f"✅ Conectado a {modo}")
        client.subscribe(TOPIC)
    else:
        print(f"❌ Error de conexión: {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())

        congelador = data.get("congelador")
        temp       = float(data.get("temperatura"))
        hum        = float(data.get("humedad"))
        especie    = data.get("especie")
        tiempo     = int(data.get("tiempo_almacenamiento"))

        estado = evaluar_estado(temp, tiempo, especie)
        now    = time.time()

        # Límite de frecuencia — máximo 1 guardado cada 5 segundos por congelador
        if congelador in last_save_time:
            if now - last_save_time[congelador] < 5:
                return

        # Lógica inteligente — solo guarda si hay cambio relevante
        if not should_save(congelador, temp, estado):
            return

        last_temp[congelador]      = temp
        last_state[congelador]     = estado
        last_save_time[congelador] = now

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"📥 {congelador} | {especie} | {temp}°C | {estado}")

        if estado == "RIESGO":
            print(f"⚠ ALERTA: {congelador} en riesgo")

        with db_lock:
            cursor.execute("""
                INSERT INTO registros
                (congelador, temperatura, humedad, especie, tiempo, estado, fecha)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (congelador, temp, hum, especie, tiempo, estado, fecha))
            conn.commit()

    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")

def on_disconnect(client, userdata, rc, properties=None):
    print("🔴 Desconectado. Reconectando...")
    try:
        client.reconnect()
    except Exception as e:
        print(f"❌ Error al reconectar: {e}")

# ---------------- CONEXIÓN ----------------
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

if USAR_NUBE:
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()

client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect

modo = "HiveMQ Cloud ☁" if USAR_NUBE else "Mosquitto Local 🖥"
print(f"🔌 Conectando a {modo}...")
client.connect(BROKER, PORT, 60)
print("🟢 Backend activo...")
client.loop_forever()