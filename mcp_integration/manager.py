import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from .client import MCPServerHttp, MCPServerStdio
from .storage import PostgreSQLStorage

logger = logging.getLogger("mcp_manager")

class MCPManager:
    """Manages MCP server lifecycle and connections"""
    
    def __init__(self, storage: PostgreSQLStorage):
        self.storage = storage
        self.connected_servers: Dict[int, any] = {}
        self.server_capabilities: Dict[int, List[str]] = {}
        
    async def initialize_user_servers(self, user_id: int) -> List[Dict]:
        """Load and connect MCP servers for user"""
        try:
            servers = await self.storage.getMcpServersByUserId(user_id)
            active_servers = [s for s in servers if s["is_active"]]
            
            connected = []
            for server_config in active_servers:
                if await self.connect_server(server_config):
                    connected.append(server_config)
                    
            return connected
            
        except Exception as e:
            logger.error(f"Failed to initialize servers: {e}")
            return []
    
    async def connect_server(self, server_config: Dict) -> bool:
        """Connect to a single MCP server"""
        try:
            # Update status
            await self.storage.updateMcpServer(
                server_config["id"],
                {"connectionStatus": "connecting"}
            )
            
            # Create appropriate server type
            if server_config["url"].startswith("http"):
                server = MCPServerHttp(
                    name=server_config["name"],
                    url=server_config["url"],
                    api_key=server_config.get("api_key")
                )
            else:
                # Local stdio server
                server = MCPServerStdio(
                    name=server_config["name"],
                    command=server_config["url"]
                )
            
            # Connect
            if await server.connect():
                self.connected_servers[server_config["id"]] = server
                
                # Get capabilities
                tools = await server.list_tools()
                self.server_capabilities[server_config["id"]] = [
                    tool["name"] for tool in tools
                ]
                
                # Update database
                await self.storage.updateMcpServer(
                    server_config["id"],
                    {
                        "connectionStatus": "connected",
                        "lastConnected": datetime.now().isoformat(),
                        "metadata": {"capabilities": self.server_capabilities[server_config["id"]]}
                    }
                )
                
                logger.info(f"Connected to MCP server: {server_config['name']}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to {server_config['name']}: {e}")
            await self.storage.updateMcpServer(
                server_config["id"],
                {
                    "connectionStatus": "error",
                    "metadata": {"error": str(e)}
                }
            )
            
        return False
    
    async def get_all_tools(self) -> List[Dict]:
        """Get all available tools from connected servers"""
        all_tools = []
        
        for server_id, server in self.connected_servers.items():
            try:
                tools = await server.list_tools()
                for tool in tools:
                    tool["server_id"] = server_id
                    tool["server_name"] = server.name
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"Failed to get tools from server {server_id}: {e}")
                
        return all_tools
    
    async def call_tool(self, server_id: int, tool_name: str, params: Dict) -> Dict:
        """Call a tool on a specific MCP server"""
        if server_id not in self.connected_servers:
            return {"error": f"Server {server_id} not connected"}
            
        server = self.connected_servers[server_id]
        return await server.call_tool(tool_name, params)
    
    async def cleanup(self):
        """Disconnect all servers and cleanup"""
        for server_id, server in self.connected_servers.items():
            try:
                await server.disconnect()
                await self.storage.updateMcpServer(
                    server_id,
                    {"connectionStatus": "disconnected"}
                )
            except Exception as e:
                logger.error(f"Error disconnecting server {server_id}: {e}")
        
        self.connected_servers.clear()
        await self.storage.cleanup()