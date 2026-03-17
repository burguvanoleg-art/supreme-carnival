import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

def test_gemini():
    prompt = "Simplify this: Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods from carbon dioxide and water."
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    print(f"Calling Gemini API with key: {GEMINI_API_KEY[:5]}...")
    response = requests.post(GEMINI_URL, json=payload)
    print(f"Status Code: {response.status_code}")
    
    result = response.json()
    print("Full Response JSON:")
    print(result)
    
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        print(f"\nExtracted Text: {text}")
    except Exception as e:
        print(f"\nError extracting text: {e}")

if __name__ == "__main__":
    test_gemini()
