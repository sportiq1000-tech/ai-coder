"""
Test what models are currently available
"""
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import asyncio
import httpx
from utils.config import settings

async def test_groq_models():
    print("\n=== GROQ MODELS ===")
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                print("Available Groq models:")
                for model in data.get("data", []):
                    print(f"  - {model['id']}")
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"Error: {e}")

async def test_cerebras_models():
    print("\n=== CEREBRAS MODELS ===")
    headers = {"Authorization": f"Bearer {settings.CEREBRAS_API_KEY}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.cerebras.ai/v1/models",
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                print("Available Cerebras models:")
                for model in data.get("data", []):
                    print(f"  - {model['id']}")
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"Error: {e}")

async def test_model_generation(provider, model_name, base_url, api_key):
    print(f"\n=== Testing {provider}: {model_name} ===")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            if response.status_code == 200:
                print(f"✅ {model_name} works!")
                data = response.json()
                print(f"   Response: {data['choices'][0]['message']['content']}")
            else:
                print(f"❌ {model_name} failed: {response.status_code}")
                print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ {model_name} error: {e}")

async def main():
    # List available models
    await test_groq_models()
    await test_cerebras_models()
    
    # Test specific models
    print("\n" + "="*50)
    print("TESTING SPECIFIC MODELS")
    print("="*50)
    
    # Test Groq models
    groq_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "mixtral-8x7b-32768",
    ]
    
    for model in groq_models:
        await test_model_generation(
            "Groq",
            model,
            "https://api.groq.com/openai/v1",
            settings.GROQ_API_KEY
        )
    
    # Test Cerebras models
    cerebras_models = [
        "llama-3.3-70b",
        "llama3.1-70b",
        "llama3.1-8b",
    ]
    
    for model in cerebras_models:
        await test_model_generation(
            "Cerebras",
            model,
            "https://api.cerebras.ai/v1",
            settings.CEREBRAS_API_KEY
        )

if __name__ == "__main__":
    asyncio.run(main())