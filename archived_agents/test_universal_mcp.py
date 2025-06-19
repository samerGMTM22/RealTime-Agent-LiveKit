"""Test Universal MCP Integration System"""

import asyncio
import logging
from mcp_integration.universal_manager import UniversalMCPDispatcher
from mcp_integration.storage import PostgreSQLStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_universal_mcp_system():
    """Test the universal MCP integration system end-to-end"""
    
    storage = PostgreSQLStorage()
    await storage.connect()
    
    dispatcher = UniversalMCPDispatcher(storage)
    
    try:
        # Test 1: Initialize tools from database
        logger.info("=== Test 1: Initialize Universal MCP Tools ===")
        dynamic_tools = await dispatcher.initialize_tools(user_id=1)
        
        logger.info(f"Discovered {len(dynamic_tools)} dynamic tools")
        logger.info(f"Connected to {len(dispatcher.connected_servers)} servers")
        
        # Test 2: Get tool manifest
        logger.info("=== Test 2: Get Tool Manifest ===")
        manifest = await dispatcher.get_tool_manifest()
        
        logger.info(f"Tool Manifest Summary:")
        logger.info(f"- Provider: {manifest['provider_name']}")
        logger.info(f"- Total Servers: {manifest['total_servers']}")
        logger.info(f"- Total Tools: {manifest['total_tools']}")
        
        for server in manifest['servers']:
            logger.info(f"  Server: {server['name']} (Protocol: {server['protocol']})")
        
        for tool in manifest['tools']:
            logger.info(f"  Tool: {tool['tool_name']} - {tool['description']}")
        
        # Test 3: Health check all servers
        logger.info("=== Test 3: Health Check All Servers ===")
        health_status = await dispatcher.health_check_all()
        
        for server_id, status in health_status.items():
            health_indicator = "✅" if status['healthy'] else "❌"
            logger.info(f"{health_indicator} {status['name']} ({status['protocol']}) - {status.get('url', 'No URL')}")
            if 'error' in status:
                logger.error(f"   Error: {status['error']}")
        
        # Test 4: Execute tool if available
        if dispatcher.tool_registry:
            logger.info("=== Test 4: Execute MCP Tool ===")
            
            # Find a search tool to test
            search_tool = None
            for tool_name in dispatcher.tool_registry.keys():
                if 'search' in tool_name.lower():
                    search_tool = tool_name
                    break
            
            if search_tool:
                logger.info(f"Testing tool: {search_tool}")
                result = await dispatcher.execute_tool(search_tool, {"query": "universal MCP integration test"})
                logger.info(f"Tool execution result: {result[:200]}...")
            else:
                logger.info("No search tool found for testing")
                # Test first available tool
                first_tool = list(dispatcher.tool_registry.keys())[0]
                logger.info(f"Testing first available tool: {first_tool}")
                result = await dispatcher.execute_tool(first_tool, {})
                logger.info(f"Tool execution result: {result[:200]}...")
        
        else:
            logger.warning("No tools available for testing")
        
        # Test 5: Protocol handler verification
        logger.info("=== Test 5: Protocol Handler Verification ===")
        for protocol, handler in dispatcher.protocol_handlers.items():
            logger.info(f"Protocol: {protocol} -> Handler: {handler.__class__.__name__}")
        
        logger.info("=== Universal MCP Integration Test Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await dispatcher.cleanup()
        await storage.cleanup()

if __name__ == "__main__":
    asyncio.run(test_universal_mcp_system())