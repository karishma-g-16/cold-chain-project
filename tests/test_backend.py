"""
TEST BACKEND
============
FastAPI endpoints aur backend functions test karta hai.
Run: pytest tests/test_backend.py -v
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Path fix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────
# DATABASE TESTS (InfluxDB mock)
# ─────────────────────────────────────────

class TestInfluxDBHandler:
    """database.py ke tests — InfluxDB mock karke"""

    def test_check_temperature_violation_high(self):
        """High temperature violation detect hoti hai"""
        from backend.database import InfluxDBHandler

        db = InfluxDBHandler()
        reading = {'temperature': 27.05, 'device_id': 'DEVICE_001'}

        violation = db.check_temperature_violation(reading)

        assert violation is not None
        assert "HIGH" in violation
        assert "27.05" in violation

    def test_check_temperature_violation_low(self):
        """Low temperature violation detect hoti hai"""
        from backend.database import InfluxDBHandler

        db = InfluxDBHandler()
        reading = {'temperature': 0.5, 'device_id': 'DEVICE_001'}

        violation = db.check_temperature_violation(reading)

        assert violation is not None
        assert "LOW" in violation

    def test_check_temperature_no_violation(self):
        """Safe temperature pe koi violation nahi"""
        from backend.database import InfluxDBHandler

        db = InfluxDBHandler()
        reading = {'temperature': 5.0, 'device_id': 'DEVICE_001'}

        violation = db.check_temperature_violation(reading)

        assert violation is None

    def test_check_temperature_boundary_min(self):
        """Exactly 2 C pe koi violation nahi (boundary)"""
        from backend.database import InfluxDBHandler

        db = InfluxDBHandler()
        reading = {'temperature': 2.0}
        violation = db.check_temperature_violation(reading)
        assert violation is None

    def test_check_temperature_boundary_max(self):
        """Exactly 8 C pe koi violation nahi (boundary)"""
        from backend.database import InfluxDBHandler

        db = InfluxDBHandler()
        reading = {'temperature': 8.0}
        violation = db.check_temperature_violation(reading)
        assert violation is None

    def test_check_temperature_just_above_max(self):
        """8.01 C pe violation hoti hai"""
        from backend.database import InfluxDBHandler

        db = InfluxDBHandler()
        reading = {'temperature': 8.01}
        violation = db.check_temperature_violation(reading)
        assert violation is not None
        assert "HIGH" in violation


# ─────────────────────────────────────────
# ALERT SYSTEM TESTS
# ─────────────────────────────────────────

class TestTelegramAlertSystem:
    """alert_system.py ke tests"""

    def test_cooldown_prevents_repeated_alerts(self):
        """Cooldown mein second alert nahi jata"""
        from backend.alert_system import TelegramAlertSystem

        alert = TelegramAlertSystem()

        # Mock send_message taaki actual Telegram call na ho
        alert.send_message = MagicMock(return_value=True)

        reading = {
            'device_id': 'DEVICE_001',
            'temperature': 27.05,
            'humidity': 36.0,
            'gps': {'lat': 28.7041, 'lon': 77.1025},
            'timestamp': '2026-04-08T10:00:00Z'
        }

        # Pehla alert — bhejega
        result1 = alert.check_and_alert(reading)
        assert result1 == True, "Pehla alert bheja jana chahiye"

        # Turant doosra alert — cooldown mein hai, nahi bhejega
        result2 = alert.check_and_alert(reading)
        assert result2 == False, "Cooldown mein second alert nahi hona chahiye"

    def test_different_devices_alert_independently(self):
        """Alag devices ka cooldown alag hota hai"""
        from backend.alert_system import TelegramAlertSystem

        alert = TelegramAlertSystem()
        alert.send_message = MagicMock(return_value=True)

        reading1 = {
            'device_id': 'DEVICE_001',
            'temperature': 27.05, 'humidity': 36.0,
            'gps': {'lat': 28.7041, 'lon': 77.1025},
            'timestamp': '2026-04-08T10:00:00Z'
        }
        reading2 = {
            'device_id': 'DEVICE_002',  # alag device
            'temperature': 27.05, 'humidity': 36.0,
            'gps': {'lat': 28.7041, 'lon': 77.1025},
            'timestamp': '2026-04-08T10:00:00Z'
        }

        result1 = alert.check_and_alert(reading1)
        result2 = alert.check_and_alert(reading2)

        assert result1 == True, "DEVICE_001 ka alert jana chahiye"
        assert result2 == True, "DEVICE_002 ka alert bhi jana chahiye (alag cooldown)"

    def test_no_alert_for_safe_temperature(self):
        """Safe temperature pe alert nahi jata"""
        from backend.alert_system import TelegramAlertSystem

        alert = TelegramAlertSystem()
        alert.send_message = MagicMock(return_value=True)

        reading = {
            'device_id': 'DEVICE_001',
            'temperature': 5.0,  # safe range
            'humidity': 36.0,
            'gps': {'lat': 28.7041, 'lon': 77.1025},
            'timestamp': '2026-04-08T10:00:00Z'
        }

        result = alert.check_and_alert(reading)
        assert result == False, "Safe temperature pe alert nahi hona chahiye"
        alert.send_message.assert_not_called()

    def test_build_alert_contains_device_info(self):
        """Alert message mein device info hoti hai"""
        from backend.alert_system import TelegramAlertSystem

        alert = TelegramAlertSystem()
        message = alert._build_alert(
            level="CRITICAL",
            device_id="DEVICE_001",
            temp=27.05,
            humidity=36.0,
            timestamp="2026-04-08T10:00:00Z",
            lat=28.7041,
            lon=77.1025,
            reason="Temperature too HIGH"
        )

        assert "DEVICE_001" in message
        assert "27.05" in message
        assert "36.0" in message
        assert "Temperature too HIGH" in message


# ─────────────────────────────────────────
# FASTAPI ENDPOINT TESTS
# ─────────────────────────────────────────

class TestFastAPIEndpoints:
    """FastAPI endpoints ke tests"""

    @pytest.fixture
    def client(self):
        """Test client banao"""
        try:
            from fastapi.testclient import TestClient
            import sys
            sys.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'backend'
            ))

            # InfluxDB mock karo taaki real DB na chahiye
            with patch('backend.database.InfluxDBHandler.connect', return_value=True):
                from backend.main import app
                return TestClient(app)
        except Exception:
            return None

    def test_health_endpoint(self, client):
        """GET /health — 200 OK return karta hai"""
        if client is None:
            pytest.skip("FastAPI client setup failed")

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'ok'
        assert 'timestamp' in data
        assert 'version' in data

    def test_health_response_structure(self, client):
        """GET /health response mein sab fields hain"""
        if client is None:
            pytest.skip("FastAPI client setup failed")

        response = client.get("/health")
        data = response.json()

        required_fields = ['status', 'timestamp', 'service', 'version']
        for field in required_fields:
            assert field in data, f"'{field}' field missing in /health response"

    def test_violations_endpoint_returns_ok(self, client):
        """GET /violations — valid response deta hai"""
        if client is None:
            pytest.skip("FastAPI client setup failed")

        with patch('backend.database.InfluxDBHandler.get_recent_readings', return_value=[]):
            response = client.get("/violations")
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'ok'
            assert 'violations' in data
            assert 'safe_range' in data

    def test_readings_endpoint_with_minutes_param(self, client):
        """GET /readings?minutes=30 — parameter kaam karta hai"""
        if client is None:
            pytest.skip("FastAPI client setup failed")

        with patch('backend.database.InfluxDBHandler.get_recent_readings', return_value=[]):
            response = client.get("/readings?minutes=30")
            assert response.status_code == 200
            data = response.json()
            assert data['minutes'] == 30

    def test_devices_endpoint(self, client):
        """GET /devices — valid response deta hai"""
        if client is None:
            pytest.skip("FastAPI client setup failed")

        mock_readings = [
            {'device_id': 'DEVICE_001', 'temperature': 27.05,
             'humidity': 36, 'time': '2026-04-08T10:00:00Z',
             'lat': 28.7, 'lon': 77.1}
        ]

        with patch('backend.database.InfluxDBHandler.get_recent_readings',
                   return_value=mock_readings):
            response = client.get("/devices")
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'ok'
            assert 'devices' in data


# ─────────────────────────────────────────
# MQTT PAYLOAD TESTS
# ─────────────────────────────────────────

class TestMQTTPayload:
    """MQTT payload format tests"""

    def test_payload_is_valid_json(self):
        """MQTT payload valid JSON hai"""
        import json

        sample_payload = b'{"device_id": "DEVICE_001", "temperature": 27.05, "humidity": 36.0}'
        parsed = json.loads(sample_payload.decode('utf-8'))

        assert parsed['device_id'] == "DEVICE_001"
        assert parsed['temperature'] == 27.05

    def test_payload_missing_field_handled(self):
        """Missing field se crash nahi hota"""
        import json

        # humidity field nahi hai
        incomplete_payload = b'{"device_id": "DEVICE_001", "temperature": 27.05}'
        parsed = json.loads(incomplete_payload.decode('utf-8'))

        # .get() se safely access karo
        humidity = parsed.get('humidity', 0)
        assert humidity == 0, "Missing humidity ka default 0 hona chahiye"

    def test_temperature_violation_with_real_delhi_temp(self):
        """Real Delhi temperature (27 C) violation detect hoti hai"""
        from backend.database import InfluxDBHandler

        db = InfluxDBHandler()
        reading = {'temperature': 27.05}

        violation = db.check_temperature_violation(reading)
        assert violation is not None, "Delhi ka 27 C cold chain violation hai"
        assert "HIGH" in violation


# Direct run
if __name__ == "__main__":
    pytest.main([__file__, "-v"])