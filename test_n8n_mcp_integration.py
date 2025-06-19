#!/usr/bin/env python3
"""
Test N8N MCP Integration with exact tool names from Gemini's research
"""

import asyncio
import requests
import json

async def test_n8n_mcp_direct():
    """Test N8N MCP integration directly via Express API"""
    
    # Test the MCP execution endpoint with exact N8N tool names
    n8n_tool_names = [
        'execute_web_search',    # Primary from Gemini research
        'web_search',           # Alternative name
        'search',               # Simple name
        'internet_search',      # Descriptive name
        'mcp_search'            # MCP-specific name
    ]
    
    test_query = "latest AI developments"
    
    print("Testing N8N MCP Integration with exact tool names...")
    print(f"Test query: {test_query}")
    print("-" * 50)
    
    for tool_name in n8n_tool_names:
        print(f"\nTesting tool name: '{tool_name}'")
        
        try:
            # Call the MCP execution endpoint
            response = requests.post(
                'http://localhost:5000/api/mcp/execute',
                json={
                    'tool': 'search',
                    'params': {'query': test_query},
                    'tool_name': tool_name  # Add for debugging
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ SUCCESS with '{tool_name}'")
                    print(f"Result: {result.get('result', 'No result')[:200]}...")
                    print(f"Server: {result.get('server', 'Unknown')}")
                    break
                else:
                    print(f"❌ FAILED with '{tool_name}': {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP {response.status_code} with '{tool_name}': {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ EXCEPTION with '{tool_name}': {str(e)}")
    
    print("\n" + "=" * 50)
    print("Test completed")

if __name__ == "__main__":
    asyncio.run(test_n8n_mcp_direct())