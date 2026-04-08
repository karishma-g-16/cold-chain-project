"""
WEATHER FETCHER
===============
Delhi का live weather data fetch करता है.
Primary: OpenWeatherMap API
Fallback: wttr.in API
"""

import requests
import json
import os
from typing import Optional, Dict
from datetime import datetime
from dotenv import load_dotenv

# Load env
load_dotenv()


class WeatherFetcher:
    """
    Real-time weather data fetcher for Delhi
    Primary: OpenWeatherMap | Fallback: wttr.in
    """

    def __init__(self, location: str = "Delhi"):
        """
        Args:
            location: City name (default: Delhi)
        """
        self.location = location
        self.api_key = os.getenv('OPENWEATHER_API_KEY',)
        self.owm_url = f"https://api.openweathermap.org/data/2.5/weather?q={location},IN&appid={self.api_key}&units=metric"
        self.wttr_url = f"https://wttr.in/{location}?format=j1"

    def get_current_weather(self) -> Optional[Dict]:
        """
        Current weather fetch करता है
        Primary: OpenWeatherMap | Fallback: wttr.in

        Returns:
            dict: Temperature, humidity, weather condition
        """

        # Primary: OpenWeatherMap
        try:
            response = requests.get(self.owm_url, timeout=5)

            if response.status_code == 200:
                data = response.json()

                return {
                    "ambient_temp_c": round(float(data['main']['temp']), 2),
                    "ambient_humidity": int(data['main']['humidity']),
                    "weather_desc": data['weather'][0]['description'].title(),
                    "feels_like_c": round(float(data['main']['feels_like']), 2),
                    "wind_speed_kmph": round(float(data['wind']['speed']) * 3.6, 1),  # m/s to km/h
                    "location": self.location,
                    "source": "OpenWeatherMap",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            else:
                print(f"⚠️  OpenWeatherMap error: {response.status_code}. Trying wttr.in...")

        except requests.exceptions.RequestException as e:
            print(f"⚠️  OpenWeatherMap network error: {e}. Trying wttr.in...")

        # Fallback: wttr.in
        try:
            response = requests.get(self.wttr_url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]

                return {
                    "ambient_temp_c": float(current['temp_C']),
                    "ambient_humidity": int(current['humidity']),
                    "weather_desc": current['weatherDesc'][0]['value'],
                    "feels_like_c": float(current['FeelsLikeC']),
                    "wind_speed_kmph": int(current['windspeedKmph']),
                    "location": self.location,
                    "source": "wttr.in",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            else:
                print(f"❌ wttr.in error: {response.status_code}")
                return None

        except (requests.exceptions.RequestException, KeyError, ValueError, json.JSONDecodeError) as e:
            print(f"❌ wttr.in also failed: {e}")
            return None

    def get_simple_format(self) -> Optional[str]:
        """
        Simple text format में weather

        Returns:
            str: "32.46°C, Scattered Clouds, 16% humidity"
        """
        weather = self.get_current_weather()
        if weather:
            return (
                f"{weather['ambient_temp_c']}°C, "
                f"{weather['weather_desc']}, "
                f"{weather['ambient_humidity']}% humidity "
                f"(via {weather['source']})"
            )
        return None


# Test code
if __name__ == "__main__":
    print("🌤️  Testing Weather Fetcher...")

    fetcher = WeatherFetcher("Delhi")

    # Get current weather
    weather = fetcher.get_current_weather()

    if weather:
        print(f"\n📍 Location: {weather['location']}")
        print(f"🌐 Source:   {weather['source']}")
        print(f"🌡️  Ambient Temperature: {weather['ambient_temp_c']}°C")
        print(f"💧 Humidity: {weather['ambient_humidity']}%")
        print(f"☁️  Conditions: {weather['weather_desc']}")
        print(f"🌡️  Feels Like: {weather['feels_like_c']}°C")
        print(f"💨 Wind Speed: {weather['wind_speed_kmph']} km/h")
        print(f"🕐 Time: {weather['timestamp']}")

        print(f"\n📝 Simple: {fetcher.get_simple_format()}")
    else:
        print("❌ Failed to fetch weather")