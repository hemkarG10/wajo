import os
import time
from google import genai
from google.genai import types
from pydantic import BaseModel

class DummyOutput(BaseModel):
    ok: bool

def test_rate_limit():
    key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=key)
    
    start = time.time()
    success = 0
    errors = 0
    
    print("Testing rate limit...")
    for i in range(30):
        try:
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=f"Say hello {i}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DummyOutput,
                    temperature=0.0,
                ),
            )
            success += 1
            print(f"{i}: Success")
        except Exception as e:
            errors += 1
            print(f"{i}: Error: {e}")
            break
            
    print(f"Finished in {time.time() - start:.2f}s. Success: {success}, Errors: {errors}")

if __name__ == "__main__":
    test_rate_limit()
