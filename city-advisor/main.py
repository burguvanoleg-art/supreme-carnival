import os
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Query
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

# --- Helper Functions ---

def get_coordinates(city_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves latitude and longitude for a given city name using the Open-Meteo Geocoding API.

    Args:
        city_name (str): The name of the city to geocode.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing 'lat', 'lon', 'name', and 'country'
                                  if the city is found; otherwise, None.
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
    Retrieves the weather forecast for specific coordinates and date using the Open-Meteo API.

    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.
        date_str (str): The date in 'YYYY-MM-DD' format.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing 'max_temp', 'min_temp', and 'rain_chance'
                                  if weather data is available; otherwise, None.
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

def get_places(lat: float, lon: float, activity_tag: str) -> List[Dict[str, Any]]:
    """
    Finds real places using the OpenStreetMap Overpass API based on coordinates and an activity tag.

    Args:
        lat (float): Latitude of the central point for the search.
        lon (float): Longitude of the central point for the search.
        activity_tag (str): An OpenStreetMap tag (e.g., 'leisure=billiards', 'amenity=restaurant').

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing 'name' and 'address' of a place.
                              Returns an empty list if no places are found or an error occurs.
    """
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

@app.get("/weather")
async def get_weather_endpoint(city_name: str = Query(..., description="E.g., 'Chisinau'"),
                                 date: str = Query(..., description="Date in YYYY-MM-DD format, e.g., '2026-03-15'")) -> Dict[str, Any]:
    """
    Retrieves weather forecast for a specific city and date.

    Args:
        city_name (str): The name of the city.
        date (str): The date for the weather forecast (YYYY-MM-DD).

    Returns:
        Dict[str, Any]: A JSON object with weather details or an error message.
    """
    try:
        location = get_coordinates(city_name)
        if not location:
            return {"status": "error", "data": f"City '{city_name}' not found"}

        weather = get_weather(location["lat"], location["lon"], date)
        if not weather:
            return {"status": "error", "data": "Weather data unavailable for the specified date."}
        
        return {"status": "ok", "data": weather}
    except Exception as e:
        return {"status": "error", "data": f"Failed to retrieve weather: {str(e)}"}

@app.get("/places")
async def get_places_endpoint(city_name: str = Query(..., description="E.g., 'Chisinau'"),
                                activity_tag: str = Query(..., description="OSM tag, e.g., 'leisure=billiards' or 'restaurant' for amenity=restaurant")) -> Dict[str, Any]:
    """
    Finds places for a specific city and activity tag.

    Args:
        city_name (str): The name of the city.
        activity_tag (str): An OpenStreetMap tag (e.g., 'leisure=billiards', 'amenity=restaurant').

    Returns:
        Dict[str, Any]: A JSON object with place details or an error message.
    """
    try:
        location = get_coordinates(city_name)
        if not location:
            return {"status": "error", "data": f"City '{city_name}' not found"}

        places = get_places(location["lat"], location["lon"], activity_tag)
        
        return {"status": "ok", "data": places}
    except Exception as e:
        return {"status": "error", "data": f"Failed to retrieve places: {str(e)}"}

@app.get("/advisor")
async def advisor(query: str = Query(..., description="E.g., 'I want to play billiards tomorrow in Chisinau'")) -> Dict[str, Any]:
    """
    Generates a personalized activity recommendation based on a natural language query.

    The process involves:
    1. AI-driven extraction of city, date, and activity from the query.
    2. Fetching real-time weather data for the specified location and date.
    3. Discovering relevant places/venues using OpenStreetMap data.
    4. AI-driven synthesis of a comprehensive recommendation, considering weather and places.

    Args:
        query (str): The user's request, e.g., 'I want to play billiards tomorrow in Chisinau'.

    Returns:
        Dict[str, Any]: A JSON object with the following structure:
                        - "status": "ok" or "error"
                        - "data":
                            - "metadata": Extracted city, date, activity.
                            - "weather": Max/min temperature, rain chance.
                            - "places_found": List of recommended places.
                            - "recommendation": AI-generated text recommendation.
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
    except exceptions.ResourceExhausted:
        return {"status": "error", "data": "AI quota exceeded. Gemini API free tier limits have been reached. Please try again in a few minutes."}
    except json.JSONDecodeError:
        return {"status": "error", "data": "Failed to parse metadata from AI. Invalid JSON response."}
    except Exception as e:
        return {"status": "error", "data": f"Failed to generate recommendation: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
