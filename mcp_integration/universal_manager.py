"""Universal MCP Dispatcher - Implements Gemini's universal architecture"""

import logging
from typing import Dict, List, Optional, Any, Callable  
from .protocols import (
    BaseProtocolHandler, 
    HTTPProtocolHandler, 
    SSEProtocolHandler, 
    WebSocketProtocolHandler, 
    StdioProtocolHandler
)
from .storage import PostgreSQLStorage

logger = logging.getLogger(__name__)

class UniversalMCPDispatcher:
    """Universal MCP dispatcher that works with any MCP server protocol"""
    
    def __init__(self, storage: PostgreSQLStorage):
        self.storage = storage
        self.tool_registry: Dict[str, Dict] = {}  # Maps tool_name to server_config and handler
        self.protocol_handlers: Dict[str, BaseProtocolHandler] = {
            "http": HTTPProtocolHandler(),
            "http_post": HTTPProtocolHandler(),
            "sse": SSEProtocolHandler(),
            "websocket": WebSocketProtocolHandler(),
            "stdio": StdioProtocolHandler(),
        }
        self.connected_servers: Dict[int, Dict] = {}
    
    async def initialize_tools(self, user_id: int = 1) -> List[Callable]:
        """Discover and prepare all tools from all MCP servers for a user"""
        try:
            # Get all active MCP servers for the user
            servers_config = await self.storage.getMcpServersByUserId(user_id)
            
            # Clear existing registry
            self.tool_registry.clear()
            self.connected_servers.clear()
            
            # Process each server
            for server_config in servers_config:
                if not server_config.get('is_active', True):
                    continue
                
                await self._process_server(server_config)
            
            # Generate dynamic function tools
            dynamic_tools = self._generate_function_tools()
            
            logger.info(f"Initialized {len(self.tool_registry)} tools from {len(self.connected_servers)} servers")
            return dynamic_tools
            
        except Exception as e:
            logger.error(f"Failed to initialize tools: {e}")
            return []
    
    async def _process_server(self, server_config: Dict):
        """Process a single MCP server: connect, discover tools, register"""
        try:
            server_id = server_config['id']
            protocol_type = server_config.get('protocol_type', 'sse')  # Default to SSE for existing servers
            
            # Get the appropriate protocol handler
            handler = self.protocol_handlers.get(protocol_type)
            if not handler:
                logger.error(f"Unknown protocol type: {protocol_type}")
                return
            
            # Check server health
            if not await handler.health_check(server_config):
                logger.warning(f"Server {server_config['name']} health check failed")
                # Continue anyway - server might be functional for tools
            
            # Discover available tools
            manifest = await handler.discover_tools(server_config)
            tools = manifest.get('tools', [])
            
            if not tools:
                logger.warning(f"No tools discovered for server {server_config['name']}")
                return
            
            # Register tools in the registry
            for tool in tools:
                tool_name = tool.get('tool_name')
                if not tool_name:
                    continue
                
                # Handle tool name conflicts by prefixing with server name
                original_tool_name = tool_name
                if tool_name in self.tool_registry:
                    tool_name = f"{server_config['name'].lower().replace(' ', '_')}_{tool_name}"
                    logger.info(f"Tool name conflict resolved: {original_tool_name} -> {tool_name}")
                
                # Register the tool
                self.tool_registry[tool_name] = {
                    'server_config': server_config,
                    'handler': handler,
                    'tool_info': tool,
                    'server_id': server_id,
                    'original_tool_name': original_tool_name
                }
            
            # Mark server as connected
            self.connected_servers[server_id] = server_config
            logger.info(f"Registered {len(tools)} tools from server {server_config['name']}")
            
        except Exception as e:
            logger.error(f"Failed to process server {server_config.get('name', 'unknown')}: {e}")
    
    def _generate_function_tools(self) -> List[Callable]:
        """Generate LiveKit function tools from registered MCP tools"""
        function_tools = []
        
        for tool_name, tool_data in self.tool_registry.items():
            tool_info = tool_data['tool_info']
            
            # Create a wrapper function for each tool
            def create_tool_wrapper(name: str, data: Dict):
                async def tool_wrapper(**kwargs) -> str:
                    """Dynamically created MCP tool wrapper"""
                    return await self.execute_tool(name, kwargs)
                
                # Set function metadata
                tool_wrapper.__name__ = name
                tool_wrapper.__doc__ = tool_info.get('description', f'Execute {name} via MCP')
                
                return tool_wrapper
            
            wrapper = create_tool_wrapper(tool_name, tool_data)
            function_tools.append(wrapper)
        
        return function_tools
    
    async def execute_tool(self, tool_name: str, params: Dict) -> str:
        """Execute a tool via the universal dispatcher"""
        try:
            # Look up the tool in the registry
            if tool_name not in self.tool_registry:
                return f"Error: Tool '{tool_name}' not found in registry"
            
            tool_data = self.tool_registry[tool_name]
            server_config = tool_data['server_config']
            handler = tool_data['handler']
            original_tool_name = tool_data.get('original_tool_name', tool_name)
            
            logger.info(f"Executing tool '{tool_name}' (original: '{original_tool_name}') on server '{server_config['name']}'")
            
            # Execute the tool via the appropriate protocol handler using original tool name
            result = await handler.execute_tool(server_config, original_tool_name, params)
            
            # Normalize the response to a string
            if result.get('status') == 'success':
                content = result.get('content', 'Tool executed successfully')
                return str(content)
            else:
                error_msg = result.get('content', 'Unknown error occurred')
                logger.error(f"Tool execution failed: {error_msg}")
                return f"Error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {e}")
            return f"Error: Tool execution failed - {str(e)}"
    
    async def get_tool_manifest(self) -> Dict:
        """Get a complete manifest of all available tools"""
        manifest = {
            "provider_name": "Universal MCP Dispatcher",
            "total_servers": len(self.connected_servers),
            "total_tools": len(self.tool_registry),
            "servers": [],
            "tools": []
        }
        
        # Add server information
        for server_id, server_config in self.connected_servers.items():
            manifest["servers"].append({
                "id": server_id,
                "name": server_config["name"],
                "protocol": server_config.get("protocol_type", "unknown"),
                "url": server_config.get("url", ""),
                "active": True
            })
        
        # Add tool information
        for tool_name, tool_data in self.tool_registry.items():
            tool_info = tool_data['tool_info']
            manifest["tools"].append({
                "tool_name": tool_name,
                "original_tool_name": tool_data.get('original_tool_name', tool_name),
                "description": tool_info.get('description', ''),
                "server_name": tool_data['server_config']['name'],
                "server_id": tool_data['server_id'],
                "schema": tool_info.get('input_schema', {})
            })
        
        return manifest
    
    async def health_check_all(self) -> Dict:
        """Check health of all connected servers"""
        health_status = {}
        
        for server_id, server_config in self.connected_servers.items():
            protocol_type = server_config.get('protocol_type', 'sse')
            handler = self.protocol_handlers.get(protocol_type)
            
            if handler:
                try:
                    is_healthy = await handler.health_check(server_config)
                    health_status[server_id] = {
                        "name": server_config["name"],
                        "healthy": is_healthy,
                        "protocol": protocol_type,
                        "url": server_config.get("url", "")
                    }
                except Exception as e:
                    health_status[server_id] = {
                        "name": server_config["name"],
                        "healthy": False,
                        "error": str(e),
                        "protocol": protocol_type,
                        "url": server_config.get("url", "")
                    }
        
        return health_status
    
    async def cleanup(self):
        """Cleanup all protocol handlers and connections"""
        try:
            for handler in self.protocol_handlers.values():
                if hasattr(handler, 'cleanup'):
                    await handler.cleanup()
            
            self.tool_registry.clear()
            self.connected_servers.clear()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")