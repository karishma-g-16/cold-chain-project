"""
MQTT PUBLISHER
==============
Sensor data को MQTT broker पर publish करता है.
Real weather data from OpenWeatherMap (fallback: wttr.in)
"""

import json
import uuid
import time
import os
import sys
import requests
from datetime import datetime
from typing import Optional
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Import fix - add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Sensor simulator (fallback ke liye)
from sensor.sensor_simulator import ColdChainSensor


class MQTTPublisher:
    """MQTT Publisher class"""

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        device_id: str = "DEVICE_001"
    ):
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.topic = f"coldchain/devices/{device_id}/readings"

        # MQTT Client - unique ID taaki multiple devices conflict na karen
        self.client = mqtt.Client(
            client_id=f"publisher_{device_id}_{uuid.uuid4().hex[:6]}",
            clean_session=True
        )

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish
        self.client.on_disconnect = self._on_disconnect

        # State
        self.is_connected = False
        self.publish_count = 0

        # Sensor (fallback ke liye)
        self.sensor = ColdChainSensor(device_id=device_id)

    def _on_connect(self, client, userdata, flags, rc):
        """Connection callback"""
        if rc == 0:
            self.is_connected = True
            print(f"✅ Connected to MQTT Broker at {self.broker}:{self.port}")
            print(f"📡 Publishing on topic: {self.topic}")
        else:
            self.is_connected = False
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            print(f"❌ Connection failed: {error_messages.get(rc, f'Unknown error ({rc})')}")

    def _on_publish(self, client, userdata, mid):
        """Publish callback"""
        print(f"✓ Message delivered (ID: {mid})")

    def _on_disconnect(self, client, userdata, rc):
        """Disconnect callback"""
        self.is_connected = False
        if rc != 0:
            print(f"⚠️  Unexpected disconnection. Attempting reconnect...")

    def _fetch_real_weather(self) -> dict:
        """OpenWeatherMap se real Delhi weather fetch karo (fallback: wttr.in)"""
        import random

        base_lat, base_lon = 28.7041, 77.1025

        # Primary: OpenWeatherMap
        try:
            api_key = os.getenv('OPENWEATHER_API_KEY',)
            url = f"https://api.openweathermap.org/data/2.5/weather?q=Delhi,IN&appid={api_key}&units=metric"
            response = requests.get(url, timeout=5)
            data = response.json()

            temp = round(data['main']['temp'], 2)
            humidity = round(float(data['main']['humidity']), 1)

            print(f"   🌐 Source: Live weather (OpenWeatherMap / Delhi)")

            return {
                "device_id": self.device_id,
                "temperature": temp,
                "humidity": humidity,
                "gps": {
                    "lat": round(base_lat + random.uniform(-0.02, 0.02), 6),
                    "lon": round(base_lon + random.uniform(-0.02, 0.02), 6)
                },
                "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            }

        except Exception as e:
            print(f"⚠️  OpenWeatherMap error: {e}. Trying wttr.in...")

        # Fallback 1: wttr.in
        try:
            url = "https://wttr.in/Delhi?format=j1"
            response = requests.get(url, timeout=5)
            data = response.json()
            current = data['current_condition'][0]
            temp = round(float(current['temp_C']), 2)
            humidity = round(float(current['humidity']), 1)

            print(f"   🌐 Source: Live weather (wttr.in / Delhi)")

            return {
                "device_id": self.device_id,
                "temperature": temp,
                "humidity": humidity,
                "gps": {
                    "lat": round(base_lat + random.uniform(-0.02, 0.02), 6),
                    "lon": round(base_lon + random.uniform(-0.02, 0.02), 6)
                },
                "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            }

        except Exception as e:
            print(f"⚠️  wttr.in also failed: {e}. Using simulator.")

        # Fallback 2: Simulator
        return self.sensor.read_sensors()

    def connect(self, retry: int = 5, retry_delay: int = 3) -> bool:
        """Connect to MQTT broker"""
        print(f"🔌 Connecting to MQTT Broker at {self.broker}:{self.port}...")

        for attempt in range(retry):
            try:
                self.client.connect(self.broker, self.port, keepalive=60)
                self.client.loop_start()

                # Wait for connection
                timeout = 5
                start_time = time.time()
                while not self.is_connected and (time.time() - start_time) < timeout:
                    time.sleep(0.1)

                if self.is_connected:
                    return True
                else:
                    print(f"⏳ Attempt {attempt + 1}/{retry} failed. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)

            except Exception as e:
                print(f"❌ Connection error: {e}")
                if attempt < retry - 1:
                    print(f"⏳ Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)

        return False

    def publish_reading(self) -> Optional[dict]:
        """Publish sensor reading"""
        if not self.is_connected:
            print("❌ Not connected to broker!")
            return None

        try:
            # Real weather data fetch karo
            reading = self._fetch_real_weather()

            # Convert to JSON
            payload = json.dumps(reading)

            # Publish
            result = self.client.publish(
                topic=self.topic,
                payload=payload,
                qos=1,
                retain=False
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.publish_count += 1

                # Display
                temp = reading['temperature']
                temp_status = "🟢" if 2 <= temp <= 8 else "🔴"

                print(f"\n📊 Reading #{self.publish_count}")
                print(f"   {temp_status} Temp: {temp}°C | Humidity: {reading['humidity']}%")
                print(f"   📍 GPS: ({reading['gps']['lat']}, {reading['gps']['lon']})")
                print(f"   🕐 Time: {reading['timestamp']}")

                return reading
            else:
                print(f"❌ Publish failed: Error code {result.rc}")
                return None

        except Exception as e:
            print(f"❌ Error publishing reading: {e}")
            return None

    def run(self, interval: int = 30):
        """Continuous publishing loop"""
        print(f"\n🌡️  Starting Cold Chain Monitor")
        print(f"📡 Device ID: {self.device_id}")
        print(f"⏱️  Reading interval: {interval}s")
        print(f"🌐 Data source: OpenWeatherMap (fallback: wttr.in → simulator)")
        print(f"Press Ctrl+C to stop\n")

        try:
            while True:
                self.publish_reading()
                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n🛑 Stopping...")
            print(f"📈 Total readings sent: {self.publish_count}")
            self.disconnect()

    def disconnect(self):
        """Disconnect from broker"""
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
            print("👋 Disconnected from MQTT Broker")


def main():
    """Main entry point"""

    # Load environment variables
    env_path = os.path.join(parent_dir, 'config', '.env')
    load_dotenv(env_path, override=False)  # Terminal variable ko priority do

    # Configuration
    BROKER = os.getenv('MQTT_BROKER', 'localhost')
    PORT = int(os.getenv('MQTT_PORT', 1993))
    DEVICE_ID = os.getenv('DEVICE_ID', 'DEVICE_001')
    INTERVAL = 30

    # Create publisher
    publisher = MQTTPublisher(
        broker=BROKER,
        port=PORT,
        device_id=DEVICE_ID
    )

    # Connect and run
    if publisher.connect():
        publisher.run(interval=INTERVAL)
    else:
        print("❌ Failed to connect to MQTT broker. Exiting.")
        sys.exit(1)


if __name__ == "__main__":
    main()