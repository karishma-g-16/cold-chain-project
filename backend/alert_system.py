"""
ALERT SYSTEM
============
Temperature violation hone pe Telegram alerts bhejta hai.
"""

import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load env
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
env_path = os.path.join(parent_dir, 'config', '.env')
load_dotenv(env_path)


class TelegramAlertSystem:
    """Telegram Alert System for Cold Chain violations"""

    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        # Thresholds
        self.temp_min = float(os.getenv('TEMP_MIN', 2.0))
        self.temp_max = float(os.getenv('TEMP_MAX', 8.0))
        self.temp_warning_min = float(os.getenv('TEMP_WARNING_MIN', 1.0))
        self.temp_warning_max = float(os.getenv('TEMP_WARNING_MAX', 9.0))

        # Alert cooldown - same device ke liye baar baar alert na bhejo
        self.last_alert = {}  # device_id -> last alert timestamp
        self.cooldown_seconds = 300  # 5 minutes

    def send_message(self, message: str) -> bool:
        """Telegram pe message bhejo"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                return True
            else:
                print(f"❌ Telegram error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Telegram send error: {e}")
            return False

    def check_and_alert(self, reading: dict) -> bool:
        """
        Reading check karo aur zarurat par alert bhejo

        Returns:
            bool: True if alert sent
        """
        device_id = reading.get('device_id', 'UNKNOWN')
        temp = float(reading.get('temperature', 0))
        humidity = float(reading.get('humidity', 0))
        timestamp = reading.get('timestamp', datetime.utcnow().isoformat() + "Z")
        lat = reading.get('gps', {}).get('lat', 0)
        lon = reading.get('gps', {}).get('lon', 0)

        # Cooldown check
        now = datetime.utcnow().timestamp()
        last = self.last_alert.get(device_id, 0)
        if (now - last) < self.cooldown_seconds:
            return False

        # Violation type determine karo
        alert_message = None

        if temp > self.temp_max:
            alert_message = self._build_alert(
                level="🔴 CRITICAL",
                device_id=device_id,
                temp=temp,
                humidity=humidity,
                timestamp=timestamp,
                lat=lat,
                lon=lon,
                reason=f"Temperature too HIGH: {temp}°C (Max allowed: {self.temp_max}°C)"
            )
        elif temp < self.temp_min:
            alert_message = self._build_alert(
                level="🔴 CRITICAL",
                device_id=device_id,
                temp=temp,
                humidity=humidity,
                timestamp=timestamp,
                lat=lat,
                lon=lon,
                reason=f"Temperature too LOW: {temp}°C (Min allowed: {self.temp_min}°C)"
            )
        elif temp > self.temp_warning_max:
            alert_message = self._build_alert(
                level="🟡 WARNING",
                device_id=device_id,
                temp=temp,
                humidity=humidity,
                timestamp=timestamp,
                lat=lat,
                lon=lon,
                reason=f"Temperature WARNING HIGH: {temp}°C (Warning threshold: {self.temp_warning_max}°C)"
            )
        elif temp < self.temp_warning_min:
            alert_message = self._build_alert(
                level="🟡 WARNING",
                device_id=device_id,
                temp=temp,
                humidity=humidity,
                timestamp=timestamp,
                lat=lat,
                lon=lon,
                reason=f"Temperature WARNING LOW: {temp}°C (Warning threshold: {self.temp_warning_min}°C)"
            )

        if alert_message:
            if self.send_message(alert_message):
                self.last_alert[device_id] = now
                print(f"   📱 Telegram alert sent for {device_id}!")
                return True

        return False

    def _build_alert(self, level, device_id, temp, humidity,
                     timestamp, lat, lon, reason) -> str:
        """Alert message build karo"""
        return f"""🚨 <b>COLD CHAIN VIOLATION</b>

{level}
━━━━━━━━━━━━━━━━━━━━
🔧 <b>Device:</b> {device_id}
🌡️ <b>Temperature:</b> {temp}°C
💧 <b>Humidity:</b> {humidity}%
📍 <b>GPS:</b> {lat}, {lon}
🕐 <b>Time:</b> {timestamp}
━━━━━━━━━━━━━━━━━━━━
⚠️ <b>Reason:</b> {reason}

✅ Safe Range: {self.temp_min}°C - {self.temp_max}°C
"""

    def send_startup_message(self):
        """System start hone pe notification"""
        message = f"""✅ <b>Cold Chain Monitor Started</b>

🌡️ Safe Range: {self.temp_min}°C - {self.temp_max}°C
🕐 Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
📡 Monitoring all devices...

System is now active and monitoring! 🚀"""
        self.send_message(message)

    def send_test_alert(self):
        """Test alert bhejo"""
        message = """🧪 <b>Test Alert</b>

Cold Chain Alert System is working correctly!
✅ Telegram connection verified.

🌡️ This is a test message."""
        return self.send_message(message)


# Test code
if __name__ == "__main__":
    print("🧪 Testing Telegram Alert System...")

    alert = TelegramAlertSystem()

    # Test message bhejo
    print("📱 Sending test message...")
    if alert.send_test_alert():
        print("✅ Test alert sent successfully!")
    else:
        print("❌ Failed to send test alert")

    # Test violation alert
    print("\n📱 Sending violation alert...")
    test_reading = {
        "device_id": "DEVICE_001",
        "temperature": 32.5,
        "humidity": 45.0,
        "gps": {"lat": 28.7041, "lon": 77.1025},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if alert.check_and_alert(test_reading):
        print("✅ Violation alert sent!")
    else:
        print("⚠️  No alert sent (cooldown or no violation)")