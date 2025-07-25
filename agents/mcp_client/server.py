"""MCP server implementations using official MCP client libraries."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
import os
from contextlib import AsyncExitStack
# from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from mcp import types

logger = logging.getLogger("mcp-server")

class MCPServer:
    """Base class for MCP servers."""
    
    async def connect(self):
        """Connect to the server."""
        raise NotImplementedError

    @property
    def name(self) -> str:
        """A readable name for the server."""
        raise NotImplementedError

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List the tools available on the server."""
        raise NotImplementedError

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke a tool on the server."""
        raise NotImplementedError

    async def cleanup(self):
        """Cleanup the server."""
        raise NotImplementedError


class MCPServerSse(MCPServer):
    """Official MCP server implementation using SSE transport."""
    
    def __init__(self, params: Dict[str, Any], cache_tools_list: bool = True, name: Optional[str] = None):
        self.params = params
        self.url = params.get("url", "")
        self._name = name or f"MCP Server ({self.url})"
        self.cache_tools_list = cache_tools_list
        self.session: Optional[ClientSession] = None
        self.exit_stack: AsyncExitStack = AsyncExitStack()
        self.connected = False
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_dirty = True
        
    @property
    def name(self) -> str:
        return self._name
        
    async def connect(self):
        """Skip SSE connection - use HTTP proxy directly for N8N/Zapier compatibility."""
        if self.connected:
            return
            
        try:
            logger.info(f"Configuring HTTP proxy mode for: {self.url}")
            
            # These endpoints are N8N/Zapier HTTP APIs, not standard MCP SSE
            # Skip the SSE connection entirely and use HTTP proxy
            self.session = None  # No SSE session needed
            self.connected = True  # Mark as "connected" for HTTP mode
            logger.info(f"Configured HTTP proxy mode for: {self.name}")
        except Exception as e:
            logger.error(f"Configuration error for {self.name}: {e}")
            self.connected = False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server."""
        if not self.session:
            raise RuntimeError("Server not initialized. Call connect() first.")

        # Return from cache if available and not dirty
        if self.cache_tools_list and not self._cache_dirty and self._tools_cache:
            return self._tools_cache

        self._cache_dirty = False
        
        try:
            # Use official MCP protocol to list tools
            result = await self.session.list_tools()
            
            # Convert MCP tools to our format
            self._tools_cache = []
            for tool in result.tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema or {}
                }
                self._tools_cache.append(tool_dict)
            
            logger.info(f"Listed {len(self._tools_cache)} tools from {self.name}")
            return self._tools_cache
        except Exception as e:
            logger.error(f"Error listing tools from {self.name}: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call tool using HTTP proxy (N8N/Zapier endpoints aren't standard MCP SSE)."""
        arguments = arguments or {}
        
        try:
            logger.info(f"Calling tool {tool_name} via HTTP proxy on {self.name}")
            
            import aiohttp
            # import asyncio  # Already imported at module level
            
            # Determine server ID based on name
            server_id = 9 if "internet" in self.name.lower() else 18
            
            payload = {
                "serverId": server_id,
                "tool": tool_name,
                "params": arguments
            }
            
            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(
                    "http://localhost:5000/api/mcp/execute",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("success"):
                            result_content = data.get("result", "")
                            logger.info(f"Tool {tool_name} succeeded: {len(str(result_content))} chars")
                            return {"content": result_content}
                        else:
                            error_msg = data.get("error", "Unknown error")
                            logger.error(f"Tool {tool_name} failed: {error_msg}")
                            return {"error": error_msg}
                    else:
                        error_text = await response.text()
                        logger.error(f"HTTP {response.status}: {error_text}")
                        return {"error": f"HTTP call failed: {error_text}"}
                        
        except asyncio.TimeoutError:
            logger.warning(f"Tool {tool_name} timed out after 30s")
            return {"error": "The request is taking too long. Let me help with what I know instead."}
        except Exception as e:
            logger.error(f"Tool {tool_name} exception: {e}")
            return {"error": f"I encountered an issue: {str(e)}"}
    
    async def cleanup(self):
        """Cleanup the server connection."""
        try:
            await self.exit_stack.aclose()
            self.session = None
            self.connected = False
            logger.info(f"Cleaned up MCP server: {self.name}")
        except Exception as e:
            logger.error(f"Error cleaning up {self.name}: {e}")
    
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()