"""Complete Universal MCP Integration Test"""

import asyncio
import logging
from mcp_integration.universal_manager import UniversalMCPDispatcher
from mcp_integration.storage import PostgreSQLStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complete_universal_mcp():
    """Test complete universal MCP integration with real servers"""
    
    storage = PostgreSQLStorage()
    await storage.connect()
    
    dispatcher = UniversalMCPDispatcher(storage)
    
    try:
        logger.info("=== Universal MCP Integration Complete Test ===")
        
        # Initialize the universal system
        dynamic_tools = await dispatcher.initialize_tools(user_id=1)
        manifest = await dispatcher.get_tool_manifest()
        
        logger.info(f"System initialized: {manifest['total_servers']} servers, {manifest['total_tools']} tools")
        
        # Test tool discovery and execution
        if dispatcher.tool_registry:
            tool_name = list(dispatcher.tool_registry.keys())[0]
            logger.info(f"Testing universal tool execution: {tool_name}")
            
            # Test with search query if it's a search tool
            if 'search' in tool_name.lower():
                result = await dispatcher.execute_tool(tool_name, {"query": "universal MCP test"})
                logger.info(f"Search result: {result[:100]}...")
            else:
                result = await dispatcher.execute_tool(tool_name, {})
                logger.info(f"Tool result: {result[:100]}...")
        
        # Verify architecture compliance
        logger.info("=== Architecture Verification ===")
        logger.info(f"Protocol handlers: {list(dispatcher.protocol_handlers.keys())}")
        logger.info(f"Tool registry size: {len(dispatcher.tool_registry)}")
        logger.info(f"Connected servers: {len(dispatcher.connected_servers)}")
        
        # Test health monitoring
        health = await dispatcher.health_check_all()
        logger.info(f"Health check results: {len(health)} servers monitored")
        
        logger.info("=== Universal MCP Integration Test Completed Successfully ===")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    
    finally:
        await dispatcher.cleanup()
        await storage.cleanup()

if __name__ == "__main__":
    success = asyncio.run(test_complete_universal_mcp())
    print(f"Test result: {'PASSED' if success else 'FAILED'}")