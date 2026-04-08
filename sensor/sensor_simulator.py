# Complete working file बनाओ
"""
SENSOR SIMULATOR
================
Real hardware sensor की जगह fake data generate करता है.
Production में इसकी जगह DHT22/BME280 sensor से data आएगा.
"""

import random
import time
from datetime import datetime
from typing import Dict


class ColdChainSensor:
    """
    Temperature और Humidity sensor को simulate करता है
    """
    
    def __init__(self, device_id: str, target_temp: float = 5.0):
        """
        Args:
            device_id: Unique device identifier (e.g., "DEVICE_001")
            target_temp: Target temperature around which to fluctuate
        """
        self.device_id = device_id
        self.target_temp = target_temp
        self.reading_count = 0
        
        # GPS coordinates (Delhi area simulate)
        self.base_lat = 28.7041
        self.base_lon = 77.1025
    
    def read_sensors(self) -> Dict:
        """
        Sensor से reading लेता है (simulated)
        
        Returns:
            dict: Temperature, humidity, GPS, timestamp
        """
        self.reading_count += 1
        
        # Temperature: Target के around ±3°C fluctuation
        temperature = self.target_temp + random.uniform(-3, 3)
        
        # Humidity: 30-60% range
        humidity = random.uniform(30, 60)
        
        # GPS: Vehicle movement simulate
        gps_lat = self.base_lat + random.uniform(-0.01, 0.01)
        gps_lon = self.base_lon + random.uniform(-0.01, 0.01)
        
        # Current timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        return {
            "device_id": self.device_id,
            "temperature": round(temperature, 2),
            "humidity": round(humidity, 1),
            "gps": {
                "lat": round(gps_lat, 6),
                "lon": round(gps_lon, 6)
            },
            "timestamp": timestamp,
            "reading_number": self.reading_count
        }
    
    def get_status(self) -> str:
        """Device status return करता है"""
        return f"Device {self.device_id}: {self.reading_count} readings sent"


# Test code
if __name__ == "__main__":
    print("🌡️  Testing Sensor Simulator...")
    
    sensor = ColdChainSensor("TEST_DEVICE_001")
    
    for i in range(5):
        reading = sensor.read_sensors()
        print(f"\n📊 Reading #{i+1}:")
        print(f"   Temperature: {reading['temperature']}°C")
        print(f"   Humidity: {reading['humidity']}%")
        print(f"   GPS: {reading['gps']}")
        print(f"   Time: {reading['timestamp']}")
        
        time.sleep(2)
    
    print(f"\n✅ {sensor.get_status()}")
