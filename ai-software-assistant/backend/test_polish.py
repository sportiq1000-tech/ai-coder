"""
Test polishing features
"""
import asyncio
from utils.cache import get_cache
from utils.validators import CodeValidator, RequestValidator
from utils.parsers import ResponseParser
from utils.metrics import get_metrics

async def test_cache():
    print("\n=== Testing Cache ===")
    cache = get_cache()
    
    # Test set/get
    await cache.set("test_key", {"data": "test_value"}, ttl=60)
    result = await cache.get("test_key")
    print(f"Cache test: {result}")
    assert result == {"data": "test_value"}, "Cache failed"
    print("✅ Cache working")

def test_validators():
    print("\n=== Testing Validators ===")
    
    # Test language detection
    python_code = "def hello():\n    print('Hello')"
    detected = CodeValidator.detect_language(python_code)
    print(f"Detected language: {detected}")
    assert detected == "python", "Language detection failed"
    
    # Test security check
    safe_code = "def add(a, b):\n    return a + b"
    is_safe, issues = CodeValidator.check_security_issues(safe_code)
    print(f"Security check: safe={is_safe}, issues={len(issues)}")
    
    print("✅ Validators working")

def test_parsers():
    print("\n=== Testing Parsers ===")
    
    # Test JSON extraction
    response = '```json\n{"code": "def test(): pass"}\n```'
    parsed = ResponseParser.extract_json(response)
    print(f"Parsed JSON: {parsed}")
    assert parsed is not None, "JSON extraction failed"
    
    # Test code extraction
    code_response = "```python\ndef hello():\n    print('hi')\n```"
    code = ResponseParser.extract_code(code_response, "python")
    print(f"Extracted code: {code[:30]}...")
    
    print("✅ Parsers working")

def test_metrics():
    print("\n=== Testing Metrics ===")
    metrics = get_metrics()
    
    # Log a test request
    metrics.log_request(
        endpoint="/api/review",
        task_type="code_review",
        model_used="llama-3.3-70b",
        provider="groq",
        tokens_used=150,
        processing_time_ms=2500,
        status="success"
    )
    
    # Get stats
    stats = metrics.get_stats(last_n=10)
    print(f"Stats: {stats}")
    print("✅ Metrics working")

async def main():
    await test_cache()
    test_validators()
    test_parsers()
    test_metrics()
    print("\n" + "="*50)
    print("✅ ALL POLISH FEATURES WORKING!")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())