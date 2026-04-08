"""
FASTAPI MAIN
============
Cold Chain Logger REST API
Endpoints:
- GET /health          -> API health check
- GET /devices         -> All devices list
- GET /readings        -> Recent readings (all devices)
- GET /readings/{device_id} -> Specific device readings
- GET /violations      -> Recent violations
- POST /test-alert     -> Test Telegram alert
"""

import os
import sys
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import fix
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from backend.database import InfluxDBHandler
from backend.alert_system import TelegramAlertSystem

# Load env
env_path = os.path.join(parent_dir, 'config', '.env')
load_dotenv(env_path)

# FastAPI app
app = FastAPI(
    title="Cold Chain Logger API",
    description="Real-time cold chain monitoring system with MQTT, InfluxDB & Telegram alerts",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB aur Alert instances
db = InfluxDBHandler()
alert = TelegramAlertSystem()

# Startup mein InfluxDB connect karo
@app.on_event("startup")
async def startup_event():
    if db.connect():
        print("✅ InfluxDB connected on startup")
    else:
        print("❌ InfluxDB connection failed on startup")


@app.on_event("shutdown")
async def shutdown_event():
    db.disconnect()
    print("👋 API shutdown")


# ─────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """API health check"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "Cold Chain Logger API",
        "version": "1.0.0"
    }


@app.get("/readings", tags=["Readings"])
async def get_all_readings(
    minutes: int = Query(default=60, description="Last N minutes ka data")
):
    """Saare devices ki recent readings"""
    readings = db.get_recent_readings(minutes=minutes)

    if not readings:
        return {
            "status": "ok",
            "count": 0,
            "readings": [],
            "message": f"No readings found in last {minutes} minutes"
        }

    return {
        "status": "ok",
        "count": len(readings),
        "minutes": minutes,
        "readings": readings
    }


@app.get("/readings/{device_id}", tags=["Readings"])
async def get_device_readings(
    device_id: str,
    minutes: int = Query(default=60, description="Last N minutes ka data")
):
    """Specific device ki readings"""
    readings = db.get_recent_readings(device_id=device_id, minutes=minutes)

    if not readings:
        return {
            "status": "ok",
            "device_id": device_id,
            "count": 0,
            "readings": [],
            "message": f"No readings found for {device_id} in last {minutes} minutes"
        }

    return {
        "status": "ok",
        "device_id": device_id,
        "count": len(readings),
        "minutes": minutes,
        "readings": readings
    }


@app.get("/violations", tags=["Violations"])
async def get_violations(
    minutes: int = Query(default=60, description="Last N minutes ka data")
):
    """Temperature violations dhundho"""
    readings = db.get_recent_readings(minutes=minutes)

    temp_min = float(os.getenv('TEMP_MIN', 2.0))
    temp_max = float(os.getenv('TEMP_MAX', 8.0))

    violations = []
    for r in readings:
        temp = r.get('temperature')
        if temp is not None:
            if temp < temp_min or temp > temp_max:
                r['violation_reason'] = (
                    f"Temperature {'too LOW' if temp < temp_min else 'too HIGH'}: "
                    f"{temp}°C (Safe range: {temp_min}°C - {temp_max}°C)"
                )
                violations.append(r)

    return {
        "status": "ok",
        "count": len(violations),
        "minutes": minutes,
        "safe_range": {"min": temp_min, "max": temp_max},
        "violations": violations
    }


@app.get("/devices", tags=["Devices"])
async def get_devices(
    minutes: int = Query(default=60, description="Last N minutes active devices")
):
    """Active devices list"""
    readings = db.get_recent_readings(minutes=minutes)

    # Unique devices
    devices = {}
    for r in readings:
        device_id = r.get('device_id')
        if device_id and device_id not in devices:
            devices[device_id] = {
                "device_id": device_id,
                "last_seen": r.get('time'),
                "last_temperature": r.get('temperature'),
                "last_humidity": r.get('humidity'),
            }

    return {
        "status": "ok",
        "count": len(devices),
        "devices": list(devices.values())
    }


@app.post("/test-alert", tags=["Alerts"])
async def send_test_alert():
    """Telegram test alert bhejo"""
    success = alert.send_test_alert()

    if success:
        return {"status": "ok", "message": "Test alert sent to Telegram!"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send Telegram alert")


@app.post("/readings/manual", tags=["Readings"])
async def manual_reading(reading: dict):
    """Manual reading store karo aur violation check karo"""
    # Store in InfluxDB
    stored = db.write_reading(reading)

    if not stored:
        raise HTTPException(status_code=500, detail="Failed to store reading")

    # Violation check
    violation = db.check_temperature_violation(reading)
    alert_sent = False

    if violation:
        alert_sent = alert.check_and_alert(reading)

    return {
        "status": "ok",
        "stored": stored,
        "violation": violation,
        "alert_sent": alert_sent
    }


# Run karo
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )