import json
import random
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
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

# -------------------------------------------------------
# Configuración MQTT
# -------------------------------------------------------
client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER, 1883, 60)
client.subscribe(TOPIC_CONTROL, qos=1)
client.loop_start()

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
            # Necesita bajar (enfriar) — avanza vel grados hacia el target
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