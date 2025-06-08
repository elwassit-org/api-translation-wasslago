#!/usr/bin/env python3
"""
Test script to measure translation performance and identify bottlenecks
"""
import asyncio
import time
from services.translation import TextTranslator

async def test_translation_performance():
    """Test translation performance with different chunk sizes"""
    
    # Test data
    test_text = """
    This is a test document for translation performance analysis.
    It contains multiple sentences to test chunking and concurrent translation.
    The goal is to identify where the bottleneck occurs in our translation pipeline.
    We want to measure API call times, concurrency efficiency, and overall throughput.
    This text should be long enough to create multiple chunks for testing.
    """
    
    print("🧪 Translation Performance Test")
    print("=" * 50)
    
    translator = TextTranslator()
    
    # Test 1: Small chunks (high concurrency)
    print("\n📊 Test 1: Small chunks (500 chars)")
    chunks_small = translator.chunk_text(test_text, max_chars=500)
    start_time = time.time()
    result1 = await translator.translate_text(chunks_small, "English", "Spanish")
    test1_time = time.time() - start_time
    print(f"Result length: {len(result1)} chars in {test1_time:.3f}s")
    
    # Test 2: Medium chunks
    print("\n📊 Test 2: Medium chunks (1000 chars)")
    chunks_medium = translator.chunk_text(test_text, max_chars=1000)
    start_time = time.time()
    result2 = await translator.translate_text(chunks_medium, "English", "Spanish")
    test2_time = time.time() - start_time
    print(f"Result length: {len(result2)} chars in {test2_time:.3f}s")
    
    # Test 3: Large chunks (low concurrency)
    print("\n📊 Test 3: Large chunks (2000 chars)")
    chunks_large = translator.chunk_text(test_text, max_chars=2000)
    start_time = time.time()
    result3 = await translator.translate_text(chunks_large, "English", "Spanish")
    test3_time = time.time() - start_time
    print(f"Result length: {len(result3)} chars in {test3_time:.3f}s")
    
    print("\n🏆 Performance Comparison:")
    print(f"Small chunks ({len(chunks_small)} chunks): {test1_time:.3f}s")
    print(f"Medium chunks ({len(chunks_medium)} chunks): {test2_time:.3f}s") 
    print(f"Large chunks ({len(chunks_large)} chunks): {test3_time:.3f}s")
    
    # Determine optimal chunk size
    efficiency_small = len(test_text) / test1_time if test1_time > 0 else 0
    efficiency_medium = len(test_text) / test2_time if test2_time > 0 else 0
    efficiency_large = len(test_text) / test3_time if test3_time > 0 else 0
    
    print(f"\n⚡ Efficiency (chars/sec):")
    print(f"Small: {efficiency_small:.0f}")
    print(f"Medium: {efficiency_medium:.0f}")
    print(f"Large: {efficiency_large:.0f}")
    
    best = max(efficiency_small, efficiency_medium, efficiency_large)
    if best == efficiency_small:
        print("💡 Small chunks are most efficient")
    elif best == efficiency_medium:
        print("💡 Medium chunks are most efficient") 
    else:
        print("💡 Large chunks are most efficient")

if __name__ == "__main__":
    asyncio.run(test_translation_performance())
