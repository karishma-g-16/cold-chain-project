"""
MQTT PUBLISHER WITH OPENWEATHERMAP
===================================
Real Delhi weather से temperature/humidity data publish करता है
"""

import json
import uuid
import time
import os
import sys
from datetime import datetime
from typing import Optional
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sensor.weather_fetcher import WeatherFetcher
from sensor.sensor_simulator import ColdChainSensor


class MQTTPublisherOpenWeather:
    """MQTT Publisher with OpenWeatherMap integration"""
    
    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1993,
        device_id: str = "DEVICE_001",
        location: str = "Delhi"
    ):
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.topic = f"coldchain/devices/{device_id}/readings"
        
        # MQTT Client - unique ID
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
        
        # Weather fetcher
        self.weather = WeatherFetcher(location=location)
        
        # Fallback sensor
        self.sensor = ColdChainSensor(device_id=device_id)
        
        # GPS base (Delhi)
        self.base_lat = 28.7041
        self.base_lon = 77.1025
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            print(f"✅ Connected to MQTT Broker at {self.broker}:{self.port}")
            print(f"📡 Publishing on topic: {self.topic}")
        else:
            self.is_connected = False
            print(f"❌ Connection failed: RC={rc}")
    
    def _on_publish(self, client, userdata, mid):
        print(f"✓ Message delivered (ID: {mid})")
    
    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            print(f"⚠️  Disconnected. RC={rc}")
    
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        print(f"🔌 Connecting to MQTT Broker at {self.broker}:{self.port}...")
        
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            timeout = 5
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            return self.is_connected
                    
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def _get_reading(self) -> dict:
        """Get reading from OpenWeatherMap"""
        import random
        
        # Fetch real weather
        weather = self.weather.get_current_weather()
        
        if weather:
            # Use real weather data
            print(f"   🌐 Source: {weather['source']}")
            
            return {
                "device_id": self.device_id,
                "temperature": weather['ambient_temp_c'],
                "humidity": weather['ambient_humidity'],
                "weather_condition": weather['weather_desc'],
                "feels_like": weather['feels_like_c'],
                "wind_speed": weather['wind_speed_kmph'],
                "gps": {
                    "lat": round(self.base_lat + random.uniform(-0.02, 0.02), 6),
                    "lon": round(self.base_lon + random.uniform(-0.02, 0.02), 6)
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "reading_number": self.publish_count + 1
            }
        else:
            # Fallback to simulator
            print(f"   ⚠️  Weather API failed. Using simulator.")
            return self.sensor.read_sensors()
    
    def publish_reading(self) -> bool:
        """Publish reading"""
        if not self.is_connected:
            print("❌ Not connected!")
            return False
        
        try:
            # Get reading
            reading = self._get_reading()
            
            # Publish
            payload = json.dumps(reading)
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
                
                if 'weather_condition' in reading:
                    print(f"   ☁️  Weather: {reading['weather_condition']}")
                
                print(f"   📍 GPS: ({reading['gps']['lat']}, {reading['gps']['lon']})")
                print(f"   🕐 {reading['timestamp']}")
                
                return True
            else:
                print(f"❌ Publish failed")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def run(self, interval: int = 30):
        """Main loop"""
        print(f"\n🌡️  Cold Chain Monitor - OpenWeatherMap Edition")
        print(f"📡 Device: {self.device_id}")
        print(f"🌐 Source: OpenWeatherMap API (Delhi)")
        print(f"⏱️  Interval: {interval}s")
        print(f"Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.publish_reading()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Stopping...")
            print(f"📈 Total readings: {self.publish_count}")
            self.disconnect()
    
    def disconnect(self):
        """Disconnect"""
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
            print("👋 Disconnected")


def main():
    # Load config
    env_path = os.path.join(parent_dir, 'config', '.env')
    load_dotenv(env_path)
    
    BROKER = os.getenv('MQTT_BROKER', 'localhost')
    PORT = int(os.getenv('MQTT_PORT', 1993))
    DEVICE_ID = os.getenv('DEVICE_ID', 'DEVICE_001')
    LOCATION = os.getenv('LOCATION', 'Delhi')
    
    publisher = MQTTPublisherOpenWeather(
        broker=BROKER,
        port=PORT,
        device_id=DEVICE_ID,
        location=LOCATION
    )
    
    if publisher.connect():
        publisher.run(interval=30)
    else:
        print("❌ Failed to connect")
        sys.exit(1)


if __name__ == "__main__":
    main()
