"""
TEST SENSOR
===========
sensor_simulator.py ke functions test karta hai.
Run: pytest tests/test_sensor.py -v
"""

import sys
import os
import pytest

# Path fix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensor.sensor_simulator import ColdChainSensor


# ─────────────────────────────────────────
# FIXTURES — reusable test setup
# ─────────────────────────────────────────

@pytest.fixture
def sensor():
    """Har test ke liye fresh sensor object"""
    return ColdChainSensor(device_id="TEST_DEVICE_001")


# ─────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────

class TestColdChainSensor:
    """ColdChainSensor class ke tests"""

    def test_sensor_creates_successfully(self, sensor):
        """Sensor object sahi banta hai"""
        assert sensor is not None
        assert sensor.device_id == "TEST_DEVICE_001"

    def test_reading_has_all_required_fields(self, sensor):
        """Reading mein sab zaruri fields hain"""
        reading = sensor.read_sensors()

        assert 'device_id' in reading, "device_id missing"
        assert 'temperature' in reading, "temperature missing"
        assert 'humidity' in reading, "humidity missing"
        assert 'gps' in reading, "gps missing"
        assert 'timestamp' in reading, "timestamp missing"

    def test_temperature_is_number(self, sensor):
        """Temperature ek valid number hai"""
        reading = sensor.read_sensors()
        temp = reading['temperature']

        assert isinstance(temp, (int, float)), "Temperature number nahi hai"
        assert not (temp != temp), "Temperature NaN nahi hona chahiye"

    def test_humidity_is_valid(self, sensor):
        """Humidity 0-100 ke beech hai"""
        reading = sensor.read_sensors()
        humidity = reading['humidity']

        assert isinstance(humidity, (int, float))
        assert 0 <= humidity <= 100, f"Humidity {humidity} out of range (0-100)"

    def test_gps_has_lat_lon(self, sensor):
        """GPS mein lat aur lon dono hain"""
        reading = sensor.read_sensors()
        gps = reading['gps']

        assert 'lat' in gps, "GPS lat missing"
        assert 'lon' in gps, "GPS lon missing"

    def test_gps_coordinates_are_valid(self, sensor):
        """GPS coordinates valid range mein hain"""
        reading = sensor.read_sensors()
        lat = reading['gps']['lat']
        lon = reading['gps']['lon']

        assert -90 <= lat <= 90, f"Latitude {lat} invalid"
        assert -180 <= lon <= 180, f"Longitude {lon} invalid"

    def test_device_id_in_reading(self, sensor):
        """Reading mein device_id sahi hai"""
        reading = sensor.read_sensors()
        assert reading['device_id'] == "TEST_DEVICE_001"

    def test_timestamp_format(self, sensor):
        """Timestamp valid string hai"""
        reading = sensor.read_sensors()
        timestamp = reading['timestamp']

        assert isinstance(timestamp, str), "Timestamp string hona chahiye"
        assert len(timestamp) > 0, "Timestamp empty nahi hona chahiye"
        assert 'Z' in timestamp or '+' in timestamp, "Timestamp UTC format mein hona chahiye"

    def test_multiple_readings_are_different(self, sensor):
        """Har reading alag hoti hai (random data)"""
        readings = [sensor.read_sensors() for _ in range(5)]
        temperatures = [r['temperature'] for r in readings]

        # Saari readings same nahi honi chahiye
        assert len(set(temperatures)) > 1, "Saari readings same hain — random nahi hai"

    def test_different_device_ids(self):
        """Alag device ID se alag sensor"""
        sensor1 = ColdChainSensor(device_id="DEVICE_001")
        sensor2 = ColdChainSensor(device_id="DEVICE_002")

        reading1 = sensor1.read_sensors()
        reading2 = sensor2.read_sensors()

        assert reading1['device_id'] == "DEVICE_001"
        assert reading2['device_id'] == "DEVICE_002"
        assert reading1['device_id'] != reading2['device_id']


class TestTemperatureRange:
    """Temperature range specific tests"""

    def test_simulated_temp_is_cold_chain_range(self):
        """Simulated temperature cold chain range mein hai (2-8 C)"""
        sensor = ColdChainSensor(device_id="RANGE_TEST")

        # 20 readings lo aur check karo
        for i in range(20):
            reading = sensor.read_sensors()
            temp = reading['temperature']
            assert 0 <= temp <= 15, f"Reading #{i+1}: Temp {temp} bahut zyada out of range hai"

    def test_violation_detection_high_temp(self):
        """High temperature violation correctly detect hoti hai"""
        temp_min = 2.0
        temp_max = 8.0

        test_temp = 27.05  # Delhi ka actual weather
        violation = temp_test(test_temp, temp_min, temp_max)

        assert violation is not None, "27.05 C pe violation detect honi chahiye"
        assert "HIGH" in violation, "HIGH temperature violation honi chahiye"

    def test_violation_detection_normal_temp(self):
        """Normal temperature pe koi violation nahi"""
        temp_min = 2.0
        temp_max = 8.0

        test_temp = 5.0  # safe range
        violation = temp_test(test_temp, temp_min, temp_max)

        assert violation is None, "5 C pe koi violation nahi honi chahiye"

    def test_violation_detection_low_temp(self):
        """Low temperature violation correctly detect hoti hai"""
        temp_min = 2.0
        temp_max = 8.0

        test_temp = 0.5  # too low
        violation = temp_test(test_temp, temp_min, temp_max)

        assert violation is not None, "0.5 C pe violation detect honi chahiye"
        assert "LOW" in violation, "LOW temperature violation honi chahiye"


# Helper function
def temp_test(temp, temp_min, temp_max):
    """Temperature violation check helper"""
    if temp < temp_min:
        return f"CRITICAL: Temperature too LOW ({temp}C < {temp_min}C)"
    elif temp > temp_max:
        return f"CRITICAL: Temperature too HIGH ({temp}C > {temp_max}C)"
    return None


# Direct run ke liye
if __name__ == "__main__":
    pytest.main([__file__, "-v"])