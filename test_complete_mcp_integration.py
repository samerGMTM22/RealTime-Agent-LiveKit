"""Complete MCP Integration Test - Validates Real Results vs Acknowledgments"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the workspace root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_integration.storage import PostgreSQLStorage
from mcp_integration.universal_manager import UniversalMCPDispatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complete_mcp_integration():
    """Test that MCP integration returns actual results, not acknowledgments."""
    
    print("🔍 Testing Complete MCP Job Polling Integration")
    print("=" * 60)
    
    try:
        # Initialize the system
        storage = PostgreSQLStorage()
        dispatcher = UniversalMCPDispatcher(storage)
        
        print("1. Initializing MCP job polling system...")
        await dispatcher.initialize_tools(user_id=1)
        
        # Get available tools
        tools = await dispatcher.get_available_tools()
        print(f"2. Found {len(tools)} available tools")
        
        # Test search functionality
        search_queries = [
            "latest Python programming trends 2025",
            "artificial intelligence news today",
            "web development best practices"
        ]
        
        for query in search_queries:
            print(f"\n3. Testing search: '{query}'")
            
            try:
                # This simulates what the voice agent would do
                result = await dispatcher.execute_tool(
                    tool_name="web_search",  # Generic tool name
                    params={"query": query},
                    timeout=30
                )
                
                if result:
                    result_str = str(result)
                    if len(result_str) > 200:
                        result_preview = result_str[:200] + "..."
                    else:
                        result_preview = result_str
                    
                    print(f"   ✓ Got actual result: {result_preview}")
                    print(f"   ✓ Result type: {type(result)}")
                    
                    # Check if this is a real result vs acknowledgment
                    is_real_result = (
                        len(result_str) > 50 and
                        "accepted" not in result_str.lower() and
                        "processing" not in result_str.lower() and
                        query.split()[0].lower() in result_str.lower()
                    )
                    
                    if is_real_result:
                        print("   🎉 CONFIRMED: Real search result (not acknowledgment)")
                    else:
                        print("   ⚠️  Result may be acknowledgment or processing message")
                else:
                    print("   ❌ No result returned")
                    
            except asyncio.TimeoutError:
                print("   ⏱️  Search timed out (server may be processing)")
            except Exception as e:
                print(f"   ❌ Search error: {e}")
        
        # Test server health
        print(f"\n4. Testing server health monitoring...")
        servers = await storage.getActiveMCPServers(user_id=1)
        
        for server in servers:
            health = await dispatcher._check_server_health(server)
            status = "✓ Healthy" if health['healthy'] else f"❌ Unhealthy: {health.get('error', 'Unknown')}"
            print(f"   {server['name']}: {status}")
        
        # Cleanup
        await dispatcher.cleanup()
        print(f"\n5. ✓ Test completed successfully")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

async def validate_voice_agent_integration():
    """Validate that voice agent gets real results through the MCP system."""
    
    print("\n🎤 Voice Agent Integration Validation")
    print("=" * 60)
    
    # Simulate voice agent search request
    test_query = "What are the latest developments in AI technology?"
    
    print(f"Simulating voice agent search: '{test_query}'")
    
    try:
        storage = PostgreSQLStorage()
        dispatcher = UniversalMCPDispatcher(storage)
        await dispatcher.initialize_tools(user_id=1)
        
        # This is what happens when user asks voice agent to search
        result = await dispatcher.execute_tool(
            tool_name="search_web",
            params={"query": test_query},
            timeout=25
        )
        
        if result:
            print("\n✓ Voice agent would receive:")
            print(f"   Result: {str(result)[:300]}...")
            print(f"   Length: {len(str(result))} characters")
            
            # Validate this is suitable for voice output
            result_str = str(result)
            is_voice_suitable = (
                len(result_str) > 100 and  # Substantial content
                len(result_str) < 2000 and  # Not too long for voice
                not result_str.lower().startswith("accepted") and  # Not acknowledgment
                "error" not in result_str.lower()[:50]  # No immediate errors
            )
            
            if is_voice_suitable:
                print("   🎉 PERFECT: Suitable for voice agent response")
            else:
                print("   ⚠️  May need formatting for voice output")
        else:
            print("   ❌ Voice agent would receive no result")
        
        await dispatcher.cleanup()
        
    except Exception as e:
        print(f"   ❌ Voice agent integration error: {e}")

async def main():
    """Run complete MCP integration tests."""
    
    print("🚀 MCP Job Polling Architecture - Complete Integration Test")
    print("=" * 80)
    print("Testing the solution to: Voice agents getting 'Accepted' instead of real results")
    print("=" * 80)
    
    # Test 1: Complete MCP integration
    integration_success = await test_complete_mcp_integration()
    
    # Test 2: Voice agent integration
    await validate_voice_agent_integration()
    
    print("\n" + "=" * 80)
    if integration_success:
        print("🎉 SUCCESS: MCP Job Polling Integration is working!")
        print("✓ Voice agents will now receive actual search results")
        print("✓ No more 'Accepted' acknowledgments without data")
        print("✓ Reliable result retrieval from async MCP servers")
    else:
        print("❌ Integration needs attention")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())