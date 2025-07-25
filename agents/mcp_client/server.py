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
        """Connect to the MCP server with detailed error handling."""
        if self.connected:
            return
            
        try:
            logger.info(f"Attempting SSE connection to: {self.url}")
            
            # Test if this is a compatible MCP SSE endpoint
            import aiohttp
            async with aiohttp.ClientSession() as test_session:
                try:
                    # Test basic connectivity first
                    async with test_session.get(self.url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        logger.info(f"Endpoint response: {response.status}")
                except Exception as test_error:
                    logger.error(f"Basic connectivity test failed: {test_error}")
                    raise ConnectionError(f"Cannot reach endpoint: {test_error}")
            
            # Try official MCP SSE client
            transport = await self.exit_stack.enter_async_context(
                sse_client(self.url)
            )
            read, write = transport
            
            # Create session
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            
            self.session = session
            self.connected = True
            logger.info(f"Successfully connected to MCP server: {self.name}")
        except Exception as e:
            logger.error(f"Detailed connection error for {self.name}: {type(e).__name__}: {e}")
            logger.error(f"URL: {self.url}")
            await self.cleanup()
            # Don't re-raise - allow tools to be created anyway
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
        """Call a tool with fallback to HTTP if MCP SSE failed."""
        arguments = arguments or {}
        
        # If we have a working MCP session, use it
        if self.session and self.connected:
            try:
                logger.info(f"Calling tool {tool_name} via MCP protocol on {self.name}")
                
                result = await self.session.call_tool(tool_name, arguments)
                
                # Handle the result - MCP CallToolResult structure
                if not result or not hasattr(result, 'content'):
                    return {"error": "Invalid tool response"}
                
                # Extract content from MCP result
                content = ""
                if result.content:
                    for item in result.content:
                        # Handle different content types
                        if hasattr(item, 'type'):
                            if item.type == 'text' and hasattr(item, 'text'):
                                content += item.text
                            elif hasattr(item, 'data'):
                                content += str(item.data)
                        else:
                            # Fallback - convert to string
                            content += str(item)
                
                return {"content": content or "Tool executed successfully"}
                
            except Exception as e:
                logger.error(f"MCP protocol call failed for {tool_name}: {e}")
                # Fall through to HTTP fallback
        
        # Fallback to HTTP API (our working backend proxy)
        try:
            logger.info(f"Using HTTP fallback for tool {tool_name} on {self.name}")
            
            import aiohttp
            import asyncio
            
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
                            return {"content": data.get("result", "")}
                        else:
                            return {"error": data.get("error", "Unknown error")}
                    else:
                        error_text = await response.text()
                        return {"error": f"HTTP call failed: {error_text}"}
                        
        except asyncio.TimeoutError:
            return {"error": "The request is taking too long. Let me help with what I know instead."}
        except Exception as e:
            logger.error(f"HTTP fallback failed for {tool_name}: {e}")
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