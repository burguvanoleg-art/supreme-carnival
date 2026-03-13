import os
import requests
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Study-Buddy API")

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={GEMINI_API_KEY}"

# Pydantic Models
class StudyText(BaseModel):
    text: str

class FollowUpRequest(BaseModel):
    context_text: str
    question: str

# Helper Functions
def call_gemini(prompt: str) -> str:
    """
    Helper function to call Google Gemini API via requests.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment")

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    response = requests.post(GEMINI_URL, json=payload)
    response.raise_for_status()
    
    result = response.json()
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise ValueError("Invalid response structure from Gemini API")

# Endpoints
@app.post("/simplify")
async def simplify_text(request: StudyText) -> Dict[str, Any]:
    """
    Takes complex text and returns a simplified explanation.
    """
    try:
        prompt = f"Simplify the following text so a 10-year-old can understand it:\n\n{request.text}"
        simplified = call_gemini(prompt)
        return {"status": "ok", "data": simplified}
    except Exception as e:
        return {"status": "error", "data": str(e)}

@app.post("/quiz")
async def generate_quiz(request: StudyText) -> Dict[str, Any]:
    """
    Generates 3-5 quiz questions based on the provided text.
    """
    try:
        prompt = f"Based on the following text, generate 3-5 quiz questions to test comprehension. Provide answers at the end:\n\n{request.text}"
        quiz = call_gemini(prompt)
        return {"status": "ok", "data": quiz}
    except Exception as e:
        return {"status": "error", "data": str(e)}

@app.post("/follow-up")
async def answer_follow_up(request: FollowUpRequest) -> Dict[str, Any]:
    """
    Answers a follow-up question based on the provided context text.
    """
    try:
        prompt = f"Context: {request.context_text}\n\nQuestion: {request.question}\n\nAnswer the question based ONLY on the context provided."
        answer = call_gemini(prompt)
        return {"status": "ok", "data": answer}
    except Exception as e:
        return {"status": "error", "data": str(e)}

@app.get("/weather")
async def get_weather(lat: float = 40.7128, lon: float = -74.0060) -> Dict[str, Any]:
    """
    Fetches current weather for given coordinates using Open-Meteo API.
    """
    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(weather_url)
        response.raise_for_status()
        data = response.json()
        return {"status": "ok", "data": data.get("current_weather", {})}
    except Exception as e:
        return {"status": "error", "data": f"Weather API failure: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
