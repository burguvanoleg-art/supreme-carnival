from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="Maria's API", description="A simple FastAPI for health, users, weather, and pokemons")

# 1. CORS Middleware setup to allow communication from any origin (e.g., your frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

# 2. GET /health: A simple health check endpoint
@app.get("/health")
async def health():
    """Returns the current status of the server."""
    return {"status": "ok", "message": "Server is running"}

# 3. GET /user: Returns hardcoded user data
@app.get("/user")
async def get_user():
    """Simulates a database fetch by returning a hardcoded user profile."""
    return {
        "name": "Maria Popescu",
        "email": "maria@example.com",
        "age": 25,
        "city": "Chisinau"
    }

# 4. GET /weather: Fetches the current temperature for a given city
@app.get("/weather")
async def get_weather(city: str = Query(..., description="The name of the city to get weather for")):
    """
    1. Calls Open-Meteo geocoding API to find city coordinates.
    2. Calls Open-Meteo forecast API for the current temperature.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Geocoding - search for city to get latitude/longitude
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_response = await client.get(geo_url)
        
        if geo_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Error reaching geocoding service")
        
        geo_data = geo_response.json()
        if not geo_data.get("results"):
            raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        
        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        
        # Step 2: Weather Forecast - get current temperature at those coordinates
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_response = await client.get(weather_url)
        
        if weather_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Error reaching weather service")
        
        weather_data = weather_response.json()
        temp = weather_data["current_weather"]["temperature"]
        
        return {
            "city": location["name"],
            "country": location.get("country"),
            "temperature": f"{temp}°C"
        }

# 5. GET /pokemons: Returns a list of Pokemon names
@app.get("/pokemons")
async def get_pokemons(count: int = Query(5, description="Number of pokemons to retrieve", gt=0)):
    """Fetches a list of pokemon names from the PokeAPI."""
    async with httpx.AsyncClient() as client:
        poke_url = f"https://pokeapi.co/api/v2/pokemon?limit={count}"
        response = await client.get(poke_url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Error reaching PokeAPI")
        
        data = response.json()
        names = [poke["name"] for poke in data["results"]]
        
        return {
            "count": len(names),
            "pokemons": names
        }

# --- Entry point to run locally ---
if __name__ == "__main__":
    import uvicorn
    # To run: python main.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
