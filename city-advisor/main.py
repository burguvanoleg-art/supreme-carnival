import os
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
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
model = genai.GenerativeModel('gemini-pro-latest')

app = FastAPI(title="City Activity Advisor")

# --- Helper Functions ---

def get_coordinates(city_name: str) -> Optional[Dict[str, Any]]:
    """Get latitude and longitude for a city using Open-Meteo Geocoding API."""
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
    """Get weather forecast for a specific date using Open-Meteo API."""
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
    """Find real places using OpenStreetMap Overpass API."""
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

# --- Endpoints ---

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root health check endpoint."""
    try:
        return {"status": "ok", "data": "City Activity Advisor API is running"}
    except Exception as e:
        return {"status": "error", "data": str(e)}

@app.get("/recommend")
async def recommend(query: str = Query(..., description="E.g., 'I want to play billiards tomorrow in Chisinau'")) -> Dict[str, Any]:
    """
    Main endpoint: 
    1. Extracts metadata via AI
    2. Fetches real weather and places
    3. Synthesizes a personalized recommendation via AI
    """
    try:
        # Step A: Metadata Extraction
        today = datetime.now().strftime("%Y-%m-%d")
        extraction_prompt = (
            f"Current date is {today}. From the query: '{query}', extract JSON:\n"
            "1. city: City name\n"
            "2. date: Date in YYYY-MM-DD (calculate relative dates like 'tomorrow')\n"
            "3. activity: OSM tag (e.g., 'leisure=billiards', 'amenity=restaurant', 'leisure=park')\n"
            "Return ONLY JSON."
        )
        
        extraction_res = model.generate_content(extraction_prompt)
        metadata = json.loads(extraction_res.text.strip().replace("```json", "").replace("```", ""))
        
        city = metadata.get("city")
        date = metadata.get("date", today)
        activity_tag = metadata.get("activity", "amenity=cafe")

        # Step B: Data Fetching
        location = get_coordinates(city)
        if not location:
            return {"status": "error", "data": f"City '{city}' not found"}

        weather = get_weather(location["lat"], location["lon"], date)
        if not weather:
            return {"status": "error", "data": "Weather data unavailable"}

        places = get_places(location["lat"], location["lon"], activity_tag)
        places_str = ", ".join([p['name'] for p in places]) if places else "No specific venues found."

        # Step C: Final Synthesis
        final_prompt = (
            f"Context: {location['name']}, {location['country']} on {date}.\n"
            f"Weather: Max {weather['max_temp']}°C, Min {weather['min_temp']}°C, {weather['rain_chance']}% rain.\n"
            f"Venues found: {places_str}.\n"
            f"User intent: {query}.\n"
            "Task: Suggest where to go (from the list if possible), what to do, and what to wear. Concise and friendly."
        )
        
        synthesis_res = model.generate_content(final_prompt)
        
        return {
            "status": "ok",
            "data": {
                "metadata": metadata,
                "weather": weather,
                "places_found": places,
                "recommendation": synthesis_res.text
            }
        }
    except Exception as e:
        return {"status": "error", "data": f"Failed to generate recommendation: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
