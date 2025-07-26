#!/usr/bin/env python3
"""Test script to verify direct tool integration"""
import asyncio
import sys
sys.path.append('.')

from voice_agent_direct_tools import search_web, send_email, load_mcp_servers

async def test_tools():
    """Test the direct HTTP tools"""
    # Load MCP server configurations first
    await load_mcp_servers()
    
    print("🧪 Testing Direct HTTP Tools with Database Configuration")
    print("=" * 50)
    
    # Test web search
    print("\n1. Testing N8N Web Search Tool:")
    try:
        result = await search_web("test query")
        print(f"✅ Web search result: {result[:200]}...")
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