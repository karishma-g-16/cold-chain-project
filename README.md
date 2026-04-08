<!-- # Cold Chain Compliance Logger

Automated temperature monitoring system for pharmaceutical/vaccine transportation.

## Tech Stack
- **IoT**: Python, MQTT (Mosquitto)
- **Backend**: FastAPI, Python
- **Database**: InfluxDB (time-series)
- **Alerts**: Telegram Bot
- **Reports**: ReportLab (PDF)

## Setup
```bash
conda activate coldchain
pip install -r sensor/requirements.txt
pip install -r backend/requirements.txt
```

## Run
```bash
# Terminal 1: MQTT Broker
sudo mosquitto -c config/mosquitto.conf -v

# Terminal 2: Sensor
python sensor/mqtt_publisher.py

# Terminal 3: Backend
uvicorn backend.main:app --reload -->



# ❄️ Automated Cold Chain Compliance Logger

A real-time IoT cold chain monitoring system that tracks temperature and humidity using MQTT, stores data in InfluxDB, and sends instant Telegram alerts on violations.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-purple?logo=eclipse-mosquitto)](https://mosquitto.org)
[![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-orange?logo=influxdb)](https://influxdata.com)
[![Telegram](https://img.shields.io/badge/Alerts-Telegram-blue?logo=telegram)](https://telegram.org)

---

## 🏗️ Architecture

```
OpenWeatherMap API
        │
        ▼
MQTT Publisher (sensor/mqtt_publisher.py)
        │  [MQTT QoS 1]
        ▼
Mosquitto Broker (localhost:1993)
        │
        ▼
MQTT Subscriber (backend/mqtt_subscriber.py)
        │
   ┌────┴────┐
   ▼         ▼
InfluxDB   Telegram
(Storage)  (Alerts)
   │
   ▼
FastAPI REST API
(backend/main.py)
```

---

## ✨ Features

- **Real-time monitoring** — Live Delhi weather data via OpenWeatherMap API
- **MQTT pipeline** — QoS 1 guaranteed delivery with Mosquitto broker
- **Time-series storage** — InfluxDB 2.7 for efficient sensor data storage
- **Instant alerts** — Telegram bot notifications on temperature violations
- **REST API** — FastAPI endpoints for readings, violations, and devices
- **PDF reports** — Auto-generated compliance reports with ReportLab
- **Fallback chain** — OpenWeatherMap → wttr.in → Simulator

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| API Framework | FastAPI + Uvicorn |
| Message Broker | MQTT (Mosquitto) |
| IoT Protocol | paho-mqtt (QoS 1) |
| Time-series DB | InfluxDB 2.7 (Docker) |
| Weather Data | OpenWeatherMap API |
| Alerts | Telegram Bot API |
| PDF Reports | ReportLab |
| Config | python-dotenv |

---

## 📁 Project Structure

```
cold-chain-project/
├── sensor/
│   ├── mqtt_publisher.py       # MQTT publisher (real weather data)
│   ├── sensor_simulator.py     # Fallback sensor simulator
│   └── weather_fetcher.py      # OpenWeatherMap + wttr.in fetcher
├── backend/
│   ├── main.py                 # FastAPI REST API
│   ├── mqtt_subscriber.py      # MQTT subscriber + InfluxDB writer
│   ├── database.py             # InfluxDB handler
│   ├── alert_system.py         # Telegram alert system
│   └── pdf_generator.py        # Compliance PDF report generator
├── config/
│   ├── .env                    # Environment variables
│   └── mosquitto.conf          # Mosquitto broker config
├── data/                       # Generated PDF reports
├── tests/                      # Test files
└── README.md
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+
- Docker
- Mosquitto MQTT Broker
- Telegram Bot Token

### 1. Clone the repository

```bash
git clone https://github.com/karishma-g-16/cold-chain-project.git
cd cold-chain-project
```

### 2. Create conda environment

```bash
conda create -n coldchain python=3.11
conda activate coldchain
pip install -r backend/requirements.txt
```

### 3. Start InfluxDB

```bash
docker run -d \
  --name influxdb \
  --publish 8086:8086 \
  -v influxdb2-data:/var/lib/influxdb2 \
  influxdb:2.7.0

# Setup InfluxDB
docker exec influxdb influx setup \
  --username admin \
  --password admin123456 \
  --org coldchain-org \
  --bucket coldchain \
  --retention 0 \
  --force

# Get token
docker exec influxdb influx auth list
```

### 4. Configure environment

```bash
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

```dotenv
MQTT_BROKER=localhost
MQTT_PORT=1993
DEVICE_ID=DEVICE_001
OPENWEATHER_API_KEY=your_api_key
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your_influxdb_token
INFLUX_ORG=coldchain-org
INFLUX_BUCKET=coldchain
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TEMP_MIN=2.0
TEMP_MAX=8.0
```

### 5. Start Mosquitto Broker

```bash
sudo mosquitto -c config/mosquitto.conf -d
```

---

## ▶️ Running the System

Open 3 terminals:

**Terminal 1 — MQTT Publisher**
```bash
conda activate coldchain
python sensor/mqtt_publisher.py
```

**Terminal 2 — MQTT Subscriber**
```bash
conda activate coldchain
python backend/mqtt_subscriber.py
```

**Terminal 3 — FastAPI**
```bash
conda activate coldchain
cd backend && uvicorn main:app --reload --port 8000
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | API health check |
| GET | `/readings` | All device readings (last 60 min) |
| GET | `/readings/{device_id}` | Specific device readings |
| GET | `/violations` | Temperature violations |
| GET | `/devices` | Active devices list |
| POST | `/test-alert` | Send test Telegram alert |
| POST | `/readings/manual` | Manual reading entry |

**Swagger UI:** `http://localhost:8000/docs`

---

## 📊 Sample API Response

```json
{
  "status": "ok",
  "count": 2,
  "violations": [
    {
      "device_id": "DEVICE_001",
      "temperature": 27.05,
      "humidity": 36,
      "violation_reason": "Temperature too HIGH: 27.05°C (Safe range: 2.0°C - 8.0°C)"
    }
  ]
}
```

---

## 📱 Telegram Alerts

The system sends instant Telegram alerts when:
- Temperature exceeds **8°C** (Critical High)
- Temperature drops below **2°C** (Critical Low)
- Warning thresholds breached (1°C - 9°C)

Alerts include device ID, temperature, humidity, GPS coordinates, and timestamp.

---

## 📄 PDF Compliance Reports

Generate compliance reports:

```bash
python backend/pdf_generator.py
```

Reports are saved in the `data/` directory with timestamp.

---

## 👩‍💻 Author

**Karishma** — IoT Backend Engineer  
[GitHub](https://github.com/karishma-g-16)

---

## 📝 License

MIT License