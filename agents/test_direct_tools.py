#!/usr/bin/env python3
"""Test script to verify direct tool integration"""
import asyncio
import sys
sys.path.append('.')

from voice_agent_direct_tools import execute_web_search, send_email

async def test_tools():
    """Test the direct HTTP tools"""
    print("🧪 Testing Direct HTTP Tools")
    print("=" * 50)
    
    # Test web search
    print("\n1. Testing N8N Web Search Tool:")
    try:
        result = await execute_web_search("test query")
        print(f"✅ Web search result: {result[:100]}...")
    except Exception as e:
        print(f"❌ Web search error: {e}")
    
    # Test email
    print("\n2. Testing Zapier Email Tool:")
    try:
        result = await send_email("test@example.com", "Test Subject", "Test Body")
        print(f"✅ Email result: {result}")
    except Exception as e:
        print(f"❌ Email error: {e}")
    
    print("\n" + "=" * 50)
    print("Tool testing complete!")

if __name__ == "__main__":
    asyncio.run(test_tools())