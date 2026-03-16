import os
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions

# Load environment variables from .env
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=api_key)
# Switching to gemini-flash-latest as it has higher quota limits for free tier
model = genai.GenerativeModel('gemini-flash-latest')

app = FastAPI(title="City Activity Advisor")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper Functions ---

def get_coordinates(city_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves latitude and longitude for a given city name."""
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
    """Retrieves weather forecast for specific coordinates and date."""
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

def get_places(lat: float, lon: float, activity_tag: str) -> List[Dict[str, Any]]:
    """Finds real places using OpenStreetMap Overpass API."""
    try:
        if "=" in activity_tag:
            key, value = activity_tag.split("=")
            tag_filter = f'["{key}"="{value}"]'
        else:
            tag_filter = f'["amenity"="{activity_tag}"]'

        overpass_query = f"""
        [out:json];
        (
          node(around:5000,{lat},{lon}){tag_filter};
          way(around:5000,{lat},{lon}){tag_filter};
        );
        out center;
        """
        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data={"data": overpass_query}, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        places = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name", "Unnamed Place")
            address = tags.get("addr:street", "Address unknown")
            places.append({"name": name, "address": address})
        
        return places[:5]
    except Exception as e:
        print(f"Places API error: {e}")
        return []

def get_weather_forecast(lat: float, lon: float) -> Optional[List[Dict[str, Any]]]:
    """Retrieves a 7-day weather forecast."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
            f"&timezone=auto"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "daily" in data:
            daily = data["daily"]
            forecasts = []
            for i in range(len(daily["time"])):
                forecasts.append({
                    "date": daily["time"][i],
                    "max_temp": daily["temperature_2m_max"][i],
                    "min_temp": daily["temperature_2m_min"][i],
                    "rain_chance": daily["precipitation_probability_max"][i],
                    "code": daily["weather_code"][i]
                })
            return forecasts
        return None
    except Exception as e:
        print(f"Weather API error: {e}")
        return None

def get_popular_places(lat: float, lon: float) -> List[Dict[str, Any]]:
    """Finds popular places in a city."""
    try:
        overpass_query = f"""
        [out:json];
        (
          node(around:5000,{lat},{lon})["amenity"~"cafe|restaurant"];
          node(around:5000,{lat},{lon})["leisure"~"park|garden"];
          way(around:5000,{lat},{lon})["leisure"~"park|garden"];
        );
        out center;
        """
        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data={"data": overpass_query}, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        places = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            if not name: continue
            
            type_label = "Venue"
            if "amenity" in tags: type_label = tags["amenity"].capitalize()
            elif "leisure" in tags: type_label = tags["leisure"].capitalize()
            
            address = tags.get("addr:street", "Address unknown")
            places.append({"name": name, "address": address, "type": type_label})
            if len(places) >= 10: break
            
        return places
    except Exception as e:
        print(f"Places API error: {e}")
        return []

# --- Endpoints ---

@app.get("/")
async def root():
    """Serves the frontend index.html."""
    try:
        if os.path.exists("static/index.html"):
            return FileResponse("static/index.html")
        return {"status": "error", "data": "Frontend not found"}
    except Exception as e:
        return {"status": "error", "data": str(e)}

@app.get("/city-forecast")
async def get_city_forecast(city_name: str = Query(..., description="E.g., 'Chisinau'")) -> Dict[str, Any]:
    """Retrieves a 7-day forecast for a city."""
    try:
        location = get_coordinates(city_name)
        if not location:
            return {"status": "error", "data": f"City '{city_name}' not found"}
        
        forecast = get_weather_forecast(location["lat"], location["lon"])
        if not forecast:
            return {"status": "error", "data": "Forecast unavailable"}
            
        return {"status": "ok", "data": {"city": location["name"], "country": location["country"], "forecast": forecast}}
    except Exception as e:
        return {"status": "error", "data": str(e)}

@app.get("/popular-venues")
async def get_popular_venues(city_name: str = Query(..., description="E.g., 'Chisinau'")) -> Dict[str, Any]:
    """Retrieves popular venues for a city."""
    try:
        location = get_coordinates(city_name)
        if not location:
            return {"status": "error", "data": f"City '{city_name}' not found"}
            
        places = get_popular_places(location["lat"], location["lon"])
        return {"status": "ok", "data": places}
    except Exception as e:
        return {"status": "error", "data": str(e)}

@app.get("/wizard-advisor")
async def wizard_advisor(
    city: str = Query(...), 
    date: str = Query(...), 
    intent: str = Query(...),
    venue: str = Query(None)
) -> Dict[str, Any]:
    """Generates a final recommendation based on the wizard's collected data."""
    try:
        location = get_coordinates(city)
        if not location:
            return {"status": "error", "data": "City not found"}

        weather = get_weather(location["lat"], location["lon"], date)
        
        venue_ctx = f"The user noted interest in: {venue}." if venue else ""
        final_prompt = (
            f"Context: {location['name']}, {location['country']} on {date}.\n"
            f"Weather: Max {weather['max_temp']}°C, Min {weather['min_temp']}°C, {weather['rain_chance']}% rain.\n"
            f"User intent: {intent}. {venue_ctx}\n"
            "Task: Suggest where to go, what to do, and what to wear. Concise and friendly. No Markdown symbols."
        )
        
        synthesis_res = model.generate_content(final_prompt)
        recommendation = synthesis_res.text.replace("**", "").replace("*", "").replace("#", "").strip()
        
        return {
            "status": "ok",
            "data": {
                "weather": weather,
                "recommendation": recommendation
            }
        }
    except Exception as e:
        return {"status": "error", "data": str(e)}

# Mount static files directory
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
