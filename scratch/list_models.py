import os
from google import genai

def list_models():
    key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=key)
    
    for m in client.models.list():
        print(m.name)

if __name__ == "__main__":
    list_models()
