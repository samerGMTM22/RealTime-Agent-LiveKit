"""MCP Manager for handling server connections and lifecycle"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from mcp_client import MCPServer, MCPServerStdio, MCPServerHttp
from storage import IStorage, McpServer

logger = logging.getLogger("mcp_manager")

class MCPManager:
    """Manages MCP server connections and lifecycle"""
    
    def __init__(self, storage: IStorage):
        self.storage = storage
        self.connected_servers: Dict[int, MCPServer] = {}
        self.server_capabilities: Dict[int, List[str]] = {}
        self.health_check_task = None
        
    async def initialize_user_servers(self, user_id: int) -> List[McpServer]:
        """Load and connect all active MCP servers for a user"""
        servers = await self.storage.getMcpServersByUserId(user_id)
        active_servers = [s for s in servers if s.isActive]
        
        connected = []
        for server_config in active_servers:
            if await self.connect_server(server_config):
                connected.append(server_config)
                
        # Start health monitoring
        if connected and not self.health_check_task:
            self.health_check_task = asyncio.create_task(
                self._health_check_loop()
            )
            
        logger.info(f"Initialized {len(connected)} MCP servers for user {user_id}")
        return connected
    
    async def connect_server(self, server_config: McpServer) -> bool:
        """Connect to a single MCP server"""
        try:
            # Update status to connecting
            await self.storage.updateMcpServer(
                server_config.id,
                {"connectionStatus": "connecting"}
            )
            
            # Create appropriate server type
            if server_config.url.startswith(("http://", "https://", "ws://", "wss://")):
                server = MCPServerHttp(
                    name=server_config.name,
                    params={
                        "url": server_config.url,
                        "api_key": server_config.apiKey
                    }
                )
            else:
                # Local server via stdio
                args = server_config.url.split()[1:] if " " in server_config.url else [server_config.url]
                server = MCPServerStdio(
                    name=server_config.name,
                    params={
                        "cmd": "npx",
                        "args": args
                    }
                )
            
            # Connect
            if await server.connect():
                self.connected_servers[server_config.id] = server
                self.server_capabilities[server_config.id] = [
                    tool["name"] for tool in server.tools
                ]
                
                # Update database
                await self.storage.updateMcpServer(
                    server_config.id,
                    {
                        "connectionStatus": "connected",
                        "lastConnected": datetime.now(),
                        "metadata": {
                            "capabilities": self.server_capabilities[server_config.id],
                            "tool_count": len(server.tools)
                        }
                    }
                )
                
                logger.info(f"Connected to MCP server {server_config.name} with {len(server.tools)} tools")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to {server_config.name}: {e}")
            await self.storage.updateMcpServer(
                server_config.id,
                {
                    "connectionStatus": "error",
                    "metadata": {"error": str(e)}
                }
            )
            
        return False
    
    async def disconnect_server(self, server_id: int):
        """Disconnect a specific MCP server"""
        if server_id in self.connected_servers:
            server = self.connected_servers[server_id]
            await server.disconnect()
            
            del self.connected_servers[server_id]
            if server_id in self.server_capabilities:
                del self.server_capabilities[server_id]
            
            await self.storage.updateMcpServer(
                server_id,
                {"connectionStatus": "disconnected"}
            )
            
            logger.info(f"Disconnected MCP server {server_id}")
    
    async def add_server(self, server_config: McpServer) -> bool:
        """Add and connect a new MCP server"""
        if await self.connect_server(server_config):
            return True
        return False
    
    async def remove_server(self, server_id: int) -> bool:
        """Remove and disconnect an MCP server"""
        await self.disconnect_server(server_id)
        return await self.storage.deleteMcpServer(server_id)
    
    async def get_server_tools(self, server_id: int) -> List[Dict]:
        """Get available tools for a specific server"""
        if server_id in self.connected_servers:
            server = self.connected_servers[server_id]
            return await server.list_tools()
        return []
    
    async def call_tool(self, server_id: int, tool_name: str, params: Dict) -> Dict:
        """Call a tool on a specific MCP server"""
        if server_id not in self.connected_servers:
            raise Exception(f"MCP server {server_id} not connected")
            
        server = self.connected_servers[server_id]
        return await server.call_tool(tool_name, params)
    
    async def get_all_tools(self) -> Dict[str, Dict]:
        """Get all available tools from all connected servers"""
        all_tools = {}
        
        for server_id, server in self.connected_servers.items():
            tools = await server.list_tools()
            for tool in tools:
                # Prefix tool name with server name to avoid conflicts
                tool_key = f"{server.name}_{tool['name']}"
                all_tools[tool_key] = {
                    "server_id": server_id,
                    "server_name": server.name,
                    "tool": tool
                }
                
        return all_tools
    
    async def _health_check_loop(self):
        """Continuous health monitoring of connected servers"""
        while self.connected_servers:
            try:
                for server_id, server in list(self.connected_servers.items()):
                    try:
                        # Simple health check - list tools
                        await asyncio.wait_for(server.list_tools(), timeout=5.0)
                        
                        # Update last connected time
                        await self.storage.updateMcpServer(
                            server_id,
                            {"lastConnected": datetime.now()}
                        )
                        
                    except Exception as e:
                        logger.warning(f"Health check failed for server {server_id}: {e}")
                        
                        # Mark as error but don't disconnect yet
                        await self.storage.updateMcpServer(
                            server_id,
                            {
                                "connectionStatus": "error",
                                "metadata": {"health_check_error": str(e)}
                            }
                        )
                
                # Health check every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)
    
    async def shutdown(self):
        """Shutdown all MCP connections"""
        if self.health_check_task:
            self.health_check_task.cancel()
            
        for server_id in list(self.connected_servers.keys()):
            await self.disconnect_server(server_id)
            
        logger.info("MCP Manager shutdown complete")