"""
Test if .env is being loaded
"""
from dotenv import load_dotenv
import os
from pathlib import Path

# Check .env file
env_path = Path('.env')
print(f"Looking for .env at: {env_path.absolute()}")
print(f".env exists: {env_path.exists()}")
print(f".env size: {env_path.stat().st_size if env_path.exists() else 'N/A'} bytes")

# Try to load it
print("\nAttempting to load .env...")
load_dotenv(env_path)

# Check if keys are loaded
keys = ['GROQ_API_KEY', 'CEREBRAS_API_KEY', 'BYTEZ_API_KEY', 'AZURE_AI_KEY']
print("\nEnvironment variables status:")
for key in keys:
    value = os.getenv(key)
    if value:
        print(f"✅ {key}: {value[:10]}... (loaded)")
    else:
        print(f"❌ {key}: NOT FOUND")

# Now try pydantic
print("\n" + "="*50)
print("Testing Pydantic Settings...")
print("="*50)

try:
    from utils.config import settings
    print(f"✅ Settings loaded successfully!")
    print(f"   GROQ_API_KEY: {settings.GROQ_API_KEY[:10] if settings.GROQ_API_KEY else 'None'}...")
    print(f"   CEREBRAS_API_KEY: {settings.CEREBRAS_API_KEY[:10] if settings.CEREBRAS_API_KEY else 'None'}...")
except Exception as e:
    print(f"❌ Settings failed: {e}")