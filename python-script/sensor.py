import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import requests
import json
import time
from datetime import datetime

MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
MQTT_TOPIC = "rios/embalses"

API_URL_CATALOGO = "https://aplicacions.aca.gencat.cat/sdim2/apirest/catalog?componentType=embassament"
API_URL_DATOS = "https://aplicacions.aca.gencat.cat/sdim2/apirest/data/EMBASSAMENT-EST"

# Diccionarios globales
MAPA_EMBALSES = {}   # sensor_id -> nombre del embalse
MAPA_TIPOS = {}      # sensor_id -> descripción del tipo de medida


def construir_mapas():
    """Consulta el catálogo y construye los mapas de nombres y tipos."""
    global MAPA_EMBALSES, MAPA_TIPOS
    print("Obteniendo catálogo de embalses...")
    try:
        response = requests.get(API_URL_CATALOGO, timeout=20)
        response.raise_for_status()
        catalogo = response.json()

        for provider in catalogo.get("providers", []):
            for sensor in provider.get("sensors", []):
                sensor_id = sensor.get("sensor")
                nombre = sensor.get("componentDesc")
                tipo = sensor.get("description", "Medición")
                if sensor_id:
                    if nombre:
                        MAPA_EMBALSES[sensor_id] = nombre
                    MAPA_TIPOS[sensor_id] = tipo
        print(f"Mapa construido con {len(MAPA_EMBALSES)} embalses.")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el catálogo: {e}")


def fetch_api_data():
    try:
        response = requests.get(API_URL_DATOS, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API de datos: {e}")
        return None


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("Conectado al broker MQTT correctamente")
    else:
        print(f"Error de conexión al broker MQTT. Código: {reason_code}")


def main():
    construir_mapas()

    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id="sensor-rios-01",
    )
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    print("Iniciando sensor virtual de ríos y embalses...")

    while True:
        print("Obteniendo datos de la API...")
        data = fetch_api_data()

        if data and "sensors" in data:
            contador = 0
            for item in data["sensors"]:
                sensor_id = item.get("sensor", "desconocido")
                nombre_embalse = MAPA_EMBALSES.get(sensor_id, sensor_id)
                tipo = MAPA_TIPOS.get(sensor_id, "Medición")

                for obs in item.get("observations", []):
                    try:
                        valor = float(obs.get("value"))
                    except (TypeError, ValueError):
                        continue

                    payload = {
                        "sensor": nombre_embalse,     # nombre legible
                        "sensor_id": sensor_id,        # código original
                        "tipo": tipo,                  # tipo de medida
                        "valor": valor,
                        "timestamp": obs.get("timestamp"),
                    }

                    client.publish(MQTT_TOPIC, json.dumps(payload))
                    contador += 1
                    print(f"Publicado: {nombre_embalse} | {tipo} | {valor}")

            print(f"Total publicado: {contador} observaciones")
        else:
            print("No se pudieron obtener datos de la API.")

        time.sleep(30)


if __name__ == "__main__":
    main()