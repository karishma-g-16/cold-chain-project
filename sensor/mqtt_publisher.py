"""
MQTT PUBLISHER
==============
Sensor data ko MQTT broker par publish karta hai.
Real weather data from OpenWeatherMap (fallback: wttr.in)
"""

import json
import uuid
import time
import os
import sys
import requests
from datetime import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sensor.sensor_simulator import ColdChainSensor

env_path = os.path.join(parent_dir, "config", ".env")
load_dotenv(env_path, override=False)


class MQTTPublisher:

    def __init__(self, broker, port, device_id):
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.topic = f"coldchain/devices/{device_id}/readings"
        self.publish_count = 0
        self.sensor = ColdChainSensor(device_id=device_id)

    def _fetch_real_weather(self):
        import random

        base_lat, base_lon = 28.7041, 77.1025

        try:
            api_key = os.getenv("OPENWEATHER_API_KEY", "")
            url = f"https://api.openweathermap.org/data/2.5/weather?q=Delhi,IN&appid={api_key}&units=metric"
            response = requests.get(url, timeout=5)
            data = response.json()
            temp = round(data["main"]["temp"], 2)
            humidity = round(float(data["main"]["humidity"]), 1)
            print(f"   🌐 Source: OpenWeatherMap")
            return {
                "device_id": self.device_id,
                "temperature": temp,
                "humidity": humidity,
                "gps": {
                    "lat": round(base_lat + random.uniform(-0.02, 0.02), 6),
                    "lon": round(base_lon + random.uniform(-0.02, 0.02), 6),
                },
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }
        except Exception as e:
            print(f"⚠️  OpenWeatherMap failed. Trying wttr.in...")

        try:
            url = "https://wttr.in/Delhi?format=j1"
            response = requests.get(url, timeout=5)
            data = response.json()
            current = data["current_condition"][0]
            temp = round(float(current["temp_C"]), 2)
            humidity = round(float(current["humidity"]), 1)
            print(f"   🌐 Source: wttr.in")
            return {
                "device_id": self.device_id,
                "temperature": temp,
                "humidity": humidity,
                "gps": {
                    "lat": round(base_lat + random.uniform(-0.02, 0.02), 6),
                    "lon": round(base_lon + random.uniform(-0.02, 0.02), 6),
                },
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }
        except Exception as e:
            print(f"⚠️  wttr.in failed. Using simulator.")

        return self.sensor.read_sensors()

    def run(self, interval=30):
        print(f"\n🌡️  Starting Cold Chain Monitor")
        print(f"📡 Device ID: {self.device_id}")
        print(f"⏱️  Interval: {interval}s")
        print(f"Press Ctrl+C to stop\n")

        # Simple MQTT client — loop_forever se publish karo
        client = mqtt.Client(
            client_id=f"publisher_{self.device_id}_{uuid.uuid4().hex[:6]}",
            clean_session=True,
        )

        connected = []

        def on_connect(c, userdata, flags, rc):
            if rc == 0:
                connected.append(True)
                print(f"✅ Connected to MQTT Broker at {self.broker}:{self.port}")
                print(f"📡 Topic: {self.topic}")

        def on_publish(c, userdata, mid):
            print(f"✓ Delivered (ID: {mid})")

        client.on_connect = on_connect
        client.on_publish = on_publish

        client.connect(self.broker, self.port, keepalive=60)

        # Background mein loop chalao
        import threading

        def mqtt_loop():
            client.loop_forever()

        t = threading.Thread(target=mqtt_loop, daemon=True)
        t.start()

        # Connection ka wait karo
        timeout = 10
        start = time.time()
        while not connected and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not connected:
            print("❌ Failed to connect to broker!")
            return

        try:
            while True:
                reading = self._fetch_real_weather()
                payload = json.dumps(reading)

                client.publish(topic=self.topic, payload=payload, qos=1, retain=False)

                self.publish_count += 1
                temp = reading["temperature"]
                temp_status = "🟢" if 2 <= temp <= 8 else "🔴"
                print(f"\n📊 Reading #{self.publish_count}")
                print(
                    f"   {temp_status} Temp: {temp}°C | Humidity: {reading['humidity']}%"
                )
                print(f"   📍 GPS: ({reading['gps']['lat']}, {reading['gps']['lon']})")
                print(f"   🕐 Time: {reading['timestamp']}")

                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n🛑 Stopping...")
            print(f"📈 Total readings: {self.publish_count}")
            client.disconnect()
            print("👋 Disconnected")


def main():
    BROKER = os.getenv("MQTT_BROKER", "localhost")
    PORT = int(os.getenv("MQTT_PORT", 1993))
    DEVICE_ID = os.getenv("DEVICE_ID", "DEVICE_001")

    publisher = MQTTPublisher(broker=BROKER, port=PORT, device_id=DEVICE_ID)
    publisher.run(interval=30)


if __name__ == "__main__":
    main()
