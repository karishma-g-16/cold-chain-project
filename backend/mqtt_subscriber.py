"""
MQTT SUBSCRIBER
===============
MQTT broker se sensor data receive karta hai,
InfluxDB mein store karta hai,
aur Telegram alerts bhejta hai.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from backend.database import InfluxDBHandler
from backend.alert_system import TelegramAlertSystem

env_path = os.path.join(parent_dir, "config", ".env")
load_dotenv(env_path)


class MQTTSubscriber:

    def __init__(self):
        self.broker = os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", 1993))
        self.topic = os.getenv("MQTT_TOPIC", "coldchain/devices/+/readings")

        self.client = mqtt.Client(
            client_id=f"subscriber_{uuid.uuid4().hex[:6]}", clean_session=True
        )

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self.is_connected = False
        self.message_count = 0
        self.violation_count = 0

        self.db = InfluxDBHandler()
        self.alert = TelegramAlertSystem()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            print(f"✅ Connected to MQTT Broker at {self.broker}:{self.port}")
            client.subscribe(self.topic, qos=1)
            print(f"📡 Subscribed to: {self.topic}")
        else:
            print(f"❌ Connection failed: RC={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.message_count += 1

            device_id = payload.get("device_id", "UNKNOWN")
            temp = payload.get("temperature", 0)
            humidity = payload.get("humidity", 0)
            timestamp = payload.get("timestamp", datetime.utcnow().isoformat() + "Z")

            temp_status = "🟢" if 2 <= temp <= 8 else "🔴"

            print(f"\n📨 Message #{self.message_count} received")
            print(f"   📡 Topic: {msg.topic}")
            print(f"   🔧 Device: {device_id}")
            print(f"   {temp_status} Temp: {temp}°C | Humidity: {humidity}%")
            print(f"   🕐 Time: {timestamp}")

            if self.db.write_reading(payload):
                print(f"   💾 Stored in InfluxDB ✅")
            else:
                print(f"   ❌ Failed to store in InfluxDB")

            violation = self.db.check_temperature_violation(payload)
            if violation:
                self.violation_count += 1
                print(f"   🚨 VIOLATION #{self.violation_count}: {violation}")
                self.alert.check_and_alert(payload)

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON payload: {e}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            print(f"⚠️  Unexpected disconnection. RC={rc}")

    def run(self):
        print(f"🔌 Connecting to MQTT Broker at {self.broker}:{self.port}...")
        print(f"\n🎧 Cold Chain Subscriber Started")
        print(f"📡 Listening on: {self.topic}")
        print(f"💾 Storing to InfluxDB: {self.db.bucket}")
        print(f"📱 Telegram alerts: Active")
        print(f"Press Ctrl+C to stop\n")

        self.alert.send_startup_message()

        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            print(f"\n\n🛑 Stopping subscriber...")
            print(f"📈 Total messages: {self.message_count}")
            print(f"🚨 Total violations: {self.violation_count}")
            self.client.disconnect()
            self.db.disconnect()
            print("👋 Subscriber stopped")

    def disconnect(self):
        self.client.disconnect()
        self.db.disconnect()
        print("👋 Subscriber stopped")


def main():
    subscriber = MQTTSubscriber()

    if not subscriber.db.connect():
        print("❌ Failed to connect to InfluxDB. Exiting.")
        sys.exit(1)

    subscriber.run()


if __name__ == "__main__":
    main()
