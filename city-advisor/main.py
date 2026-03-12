import os
import requests
from typing import Dict, Any, Optional
from fastapi import FastAPI, Query
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI(title="City Activity Advisor")

def get_coordinates(city_name: str) -> Optional[Dict[str, Any]]:
    """
    Get latitude and longitude for a city using Open-Meteo Geocoding API.
    """
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "lat": result["latitude"],
                "lon": result["longitude"],
                "name": result["name"],
                "country": result.get("country", "Unknown")
            }
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None

def get_weather(lat: float, lon: float, date_str: str) -> Optional[Dict[str, Any]]:
    """
    Get weather forecast for a specific date (YYYY-MM-DD) using Open-Meteo API.
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&timezone=auto&start_date={date_str}&end_date={date_str}"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "daily" in data:
            daily = data["daily"]
            return {
                "max_temp": daily["temperature_2m_max"][0],
                "min_temp": daily["temperature_2m_min"][0],
                "rain_chance": daily["precipitation_probability_max"][0]
            }
        return None
    except Exception as e:
        print(f"Weather API error: {e}")
        return None

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint for health check."""
    try:
        return {"status": "ok", "data": "City Activity Advisor API is running"}
    except Exception as e:
        return {"status": "error", "data": str(e)}

@app.get("/test-weather")
async def test_weather(
    city: str = Query(..., description="City name"),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
) -> Dict[str, Any]:
    """
    Endpoint to test geocoding and weather integration.
    """
    try:
        # 1. Geocode
        location = get_coordinates(city)
        if not location:
            return {"status": "error", "data": f"City '{city}' not found"}

        # 2. Weather
        weather = get_weather(location["lat"], location["lon"], date)
        if not weather:
            return {"status": "error", "data": "Could not fetch weather data"}

        return {
            "status": "ok",
            "data": {
                "location": location,
                "weather": weather
            }
        }
    except Exception as e:
        return {"status": "error", "data": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
