import json
import random
import time
import paho.mqtt.client as mqtt

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

TOPIC         = "pesquera/congelador"
TOPIC_CONTROL = "pesquera/congelador/+/control"

# -------------------------------------------------------
# Estado actual de cada congelador
# temp_actual: valor que se publica y cambia gradualmente
# setpoint:    objetivo marcado desde Node-RED
# velocidad:   qué tan rápido responde (°C por ciclo)
# -------------------------------------------------------
congeladores = {
    "A": {"especie": "trucha",  "temp_actual": -18.0, "setpoint": -18.0, "velocidad": 0.3},
    "B": {"especie": "tilapia", "temp_actual": -18.0, "setpoint": -18.0, "velocidad": 0.3},
    "C": {"especie": "bagre",   "temp_actual": -18.0, "setpoint": -18.0, "velocidad": 0.3},
}

# -------------------------------------------------------
# Callback: llega comando desde Node-RED (slider)
# -------------------------------------------------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        modo = "HiveMQ Cloud ☁" if USAR_NUBE else "Mosquitto Local 🖥"
        print(f"✅ Simulador conectado a {modo}")
        client.subscribe(TOPIC_CONTROL, qos=1)
    else:
        print(f"❌ Error de conexión: {rc}")

def on_message(client, userdata, msg):
    try:
        data     = json.loads(msg.payload.decode())
        cong     = data.get("congelador")
        setpoint = data.get("setpoint")

        if cong not in congeladores or setpoint is None:
            return

        congeladores[cong]["setpoint"] = float(setpoint)
        temp_act  = congeladores[cong]["temp_actual"]
        direccion = "🔽 bajando" if setpoint < temp_act else "🔼 subiendo"
        print(f"🎛  Congelador {cong}: setpoint → {setpoint}°C  "
              f"(temp actual: {temp_act:.2f}°C  {direccion})")

    except Exception as e:
        print(f"⚠️  Error en comando de control: {e}")

def on_disconnect(client, userdata, rc, properties=None):
    print("🔴 Desconectado. Reconectando...")
    try:
        client.reconnect()
    except Exception as e:
        print(f"❌ Error al reconectar: {e}")

# -------------------------------------------------------
# Configuración MQTT
# -------------------------------------------------------
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
client.loop_start()

time.sleep(2)  # Espera a que conecte
print("🚀 Simulador iniciado. Publicando cada 3 segundos...\n")

# -------------------------------------------------------
# Bucle principal
# -------------------------------------------------------
while True:
    for cong, cfg in congeladores.items():
        temp   = cfg["temp_actual"]
        target = cfg["setpoint"]
        vel    = cfg["velocidad"]

        # --- Movimiento gradual hacia el setpoint ---
        diferencia = target - temp

        if abs(diferencia) < vel:
            # Ya llegó: oscila ligeramente alrededor del setpoint (ruido de sensor)
            nueva_temp = target + random.uniform(-0.2, 0.2)
        elif diferencia < 0:
            # Necesita bajar (enfriar)
            nueva_temp = temp - vel + random.uniform(-0.1, 0.05)
        else:
            # Necesita subir (calentar)
            nueva_temp = temp + vel + random.uniform(-0.05, 0.1)

        # Limitar a rango físico razonable
        nueva_temp = round(max(-45.0, min(-1.0, nueva_temp)), 2)
        cfg["temp_actual"] = nueva_temp

        data = {
            "congelador":            cong,
            "temperatura":           nueva_temp,
            "humedad":               round(random.uniform(50, 80), 2),
            "especie":               cfg["especie"],
            "tiempo_almacenamiento": random.randint(1, 72),
            "setpoint":              target,
        }

        client.publish(TOPIC, json.dumps(data))
        print(f"📤 {cong}: {nueva_temp}°C  (setpoint: {target}°C)")

    print()
    time.sleep(3)