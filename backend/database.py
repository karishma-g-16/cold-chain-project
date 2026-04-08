"""
DATABASE
========
InfluxDB 2.0 ke saath connection aur data storage handle karta hai.
Cold chain sensor readings ko time-series data ke roop mein store karta hai.
"""

import os
from datetime import datetime
from typing import Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

# Load env
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
env_path = os.path.join(parent_dir, 'config', '.env')
load_dotenv(env_path)


class InfluxDBHandler:
    """
    InfluxDB 2.0 handler for cold chain data storage
    """

    def __init__(self):
        self.url = os.getenv('INFLUX_URL', 'http://localhost:8086')
        self.token = os.getenv('INFLUX_TOKEN', '')
        self.org = os.getenv('INFLUX_ORG', 'coldchain-org')
        self.bucket = os.getenv('INFLUX_BUCKET', 'coldchain')

        self.client = None
        self.write_api = None
        self.query_api = None

    def connect(self) -> bool:
        """InfluxDB se connect karo"""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )

            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()

            # Connection test
            health = self.client.health()
            if health.status == "pass":
                print(f"✅ InfluxDB connected at {self.url}")
                return True
            else:
                print(f"❌ InfluxDB health check failed: {health.status}")
                return False

        except Exception as e:
            print(f"❌ InfluxDB connection error: {e}")
            return False

    def write_reading(self, reading: dict) -> bool:
        """
        Sensor reading InfluxDB mein store karo

        Args:
            reading: MQTT se aaya sensor data dict

        Returns:
            bool: True if success
        """
        try:
            point = (
                Point("sensor_reading")
                .tag("device_id", reading.get("device_id", "UNKNOWN"))
                .field("temperature", float(reading.get("temperature", 0)))
                .field("humidity", float(reading.get("humidity", 0)))
                .field("lat", float(reading.get("gps", {}).get("lat", 0)))
                .field("lon", float(reading.get("gps", {}).get("lon", 0)))
                .time(reading.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                      WritePrecision.NS)
            )

            # Weather fields (agar available ho)
            if "weather_condition" in reading:
                point = point.tag("weather_condition", reading["weather_condition"])
            if "feels_like" in reading:
                point = point.field("feels_like", float(reading["feels_like"]))
            if "wind_speed" in reading:
                point = point.field("wind_speed", float(reading["wind_speed"]))

            self.write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=point
            )

            print(f"💾 Stored: Device={reading.get('device_id')} "
                  f"Temp={reading.get('temperature')}°C "
                  f"Humidity={reading.get('humidity')}%")
            return True

        except Exception as e:
            print(f"❌ Error writing to InfluxDB: {e}")
            return False

    def get_recent_readings(self, device_id: str = None, minutes: int = 60) -> list:
        """
        Recent readings fetch karo

        Args:
            device_id: Filter by device (None = all devices)
            minutes: Last N minutes ka data

        Returns:
            list: Readings list
        """
        try:
            device_filter = f'|> filter(fn: (r) => r["device_id"] == "{device_id}")' if device_id else ""

            query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -{minutes}m)
                |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
                {device_filter}
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 100)
            '''

            tables = self.query_api.query(query, org=self.org)
            readings = []

            for table in tables:
                for record in table.records:
                    readings.append({
                        "time": str(record.get_time()),
                        "device_id": record.values.get("device_id"),
                        "temperature": record.values.get("temperature"),
                        "humidity": record.values.get("humidity"),
                        "lat": record.values.get("lat"),
                        "lon": record.values.get("lon"),
                    })

            return readings

        except Exception as e:
            print(f"❌ Error querying InfluxDB: {e}")
            return []

    def check_temperature_violation(self, reading: dict) -> Optional[str]:
        """
        Temperature violation check karo

        Returns:
            str: Violation type or None
        """
        temp = float(reading.get("temperature", 0))
        temp_min = float(os.getenv("TEMP_MIN", 2.0))
        temp_max = float(os.getenv("TEMP_MAX", 8.0))

        if temp < temp_min:
            return f"CRITICAL: Temperature too LOW ({temp}°C < {temp_min}°C)"
        elif temp > temp_max:
            return f"CRITICAL: Temperature too HIGH ({temp}°C > {temp_max}°C)"
        return None

    def disconnect(self):
        """InfluxDB disconnect karo"""
        if self.client:
            self.client.close()
            print("👋 InfluxDB disconnected")


# Test code
if __name__ == "__main__":
    print("🧪 Testing InfluxDB Connection...")

    db = InfluxDBHandler()

    if db.connect():
        # Test write
        test_reading = {
            "device_id": "TEST_DEVICE",
            "temperature": 32.5,
            "humidity": 45.0,
            "gps": {"lat": 28.7041, "lon": 77.1025},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        print("\n📝 Writing test reading...")
        if db.write_reading(test_reading):
            print("✅ Write successful!")

        # Test violation check
        violation = db.check_temperature_violation(test_reading)
        if violation:
            print(f"🚨 {violation}")

        db.disconnect()
    else:
        print("❌ Connection failed!")