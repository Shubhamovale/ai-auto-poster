import os
from google import genai

def generate_post_content():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    
    print("📋 Available models:")
    for model in client.models.list():
        print(f"  - {model.name}")
    
    return None
