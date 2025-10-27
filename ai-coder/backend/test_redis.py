"""
Test Redis cache functionality
"""
import asyncio
from utils.cache import get_cache
from utils.logger import logger


async def test_redis_cache():
    """Test Redis cache operations"""
    print("\n" + "="*60)
    print("TESTING REDIS CACHE")
    print("="*60)
    
    cache = get_cache()
    
    # Wait for Redis initialization
    await asyncio.sleep(2)
    
    # Test 1: Connection Status
    print("\n1. Cache Status:")
    stats = await cache.get_stats()
    print(f"   Type: {stats['type']}")
    print(f"   Enabled: {stats['enabled']}")
    print(f"   Redis Connected: {stats['redis_connected']}")
    if stats['type'] == 'redis':
        print(f"   ✅ Using Redis Cache!")
    else:
        print(f"   ⚠️  Using Memory Cache (Redis not available)")
    
    # Test 2: Set/Get
    print("\n2. Testing SET operation:")
    test_data = {
        "message": "Hello from Redis!",
        "number": 42,
        "list": [1, 2, 3]
    }
    success = await cache.set("test_key", test_data, ttl=300)
    print(f"   Set operation: {'✅ Success' if success else '❌ Failed'}")
    
    # Test 3: Get
    print("\n3. Testing GET operation:")
    retrieved = await cache.get("test_key")
    print(f"   Retrieved: {retrieved}")
    if retrieved == test_data:
        print("   ✅ Data matches!")
    else:
        print("   ❌ Data mismatch!")
    
    # Test 4: Delete
    print("\n4. Testing DELETE operation:")
    await cache.delete("test_key")
    retrieved_after_delete = await cache.get("test_key")
    if retrieved_after_delete is None:
        print("   ✅ Delete successful!")
    else:
        print("   ❌ Delete failed!")
    
    # Test 5: Cache key generation
    print("\n5. Testing cache key generation:")
    key1 = cache.generate_key("code", "python", check_style=True)
    key2 = cache.generate_key("code", "python", check_style=True)
    key3 = cache.generate_key("different", "python", check_style=True)
    print(f"   Key 1: {key1}")
    print(f"   Key 2: {key2}")
    print(f"   Keys 1&2 match: {'✅ Yes' if key1 == key2 else '❌ No'}")
    print(f"   Key 3 different: {'✅ Yes' if key3 != key1 else '❌ No'}")
    
    # Test 6: TTL expiration (quick test)
    print("\n6. Testing TTL (2 second expiration):")
    await cache.set("expire_test", "will expire", ttl=2)
    print("   Set with 2s TTL")
    print("   Waiting 3 seconds...")
    await asyncio.sleep(3)
    expired = await cache.get("expire_test")
    if expired is None:
        print("   ✅ TTL expiration working!")
    else:
        print("   ⚠️  Still in cache (might be memory cache)")
    
    # Test 7: Stats
    print("\n7. Detailed Cache Stats:")
    final_stats = await cache.get_stats()
    for key, value in final_stats.items():
        print(f"   {key}: {value}")
    
    # Cleanup
    await cache.close()
    
    print("\n" + "="*60)
    print("✅ REDIS CACHE TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_redis_cache())