"""MCP server implementations for different transport protocols."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
import aiohttp
import json

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
    """MCP server implementation using SSE (Server-Sent Events) transport."""
    
    def __init__(self, url: str, name: Optional[str] = None):
        self.url = url
        self._name = name or f"MCP Server ({url})"
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        
    @property
    def name(self) -> str:
        return self._name
        
    async def connect(self):
        """Connect to the MCP server."""
        if self.connected:
            return
            
        try:
            self.session = aiohttp.ClientSession()
            # Test connection by listing tools
            await self.list_tools()
            self.connected = True
            logger.info(f"Connected to MCP server: {self.name}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.name}: {e}")
            if self.session:
                await self.session.close()
                self.session = None
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server."""
        if self._tools_cache is not None:
            return self._tools_cache
            
        if not self.session:
            await self.connect()
            
        try:
            # For now, return hardcoded tools that match our MCP servers
            if "internet" in self.name.lower():
                self._tools_cache = [{
                    "name": "execute_web_search",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }]
            elif "zapier" in self.name.lower():
                self._tools_cache = [{
                    "name": "send_email",
                    "description": "Send an email",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email body"}
                        },
                        "required": ["to", "subject", "body"]
                    }
                }]
            else:
                self._tools_cache = []
            
            return self._tools_cache
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server using the backend proxy."""
        arguments = arguments or {}
        
        try:
            # Use the backend MCP proxy endpoint
            payload = {
                "serverId": 9 if "internet" in self.name.lower() else 15,  # Map to server IDs
                "tool": tool_name,
                "params": arguments
            }
            
            if not self.session:
                await self.connect()
            
            if not self.session:
                raise RuntimeError("Session not initialized")
                
            async with self.session.post(
                "http://localhost:5000/api/mcp/execute", 
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20)  # 20 second timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        return {"content": data.get("result", "")}
                    else:
                        return {"error": data.get("error", "Unknown error")}
                else:
                    error_text = await response.text()
                    logger.error(f"Tool call failed: {response.status} - {error_text}")
                    return {"error": f"Tool call failed: {error_text}"}
        except asyncio.TimeoutError:
            logger.error(f"Tool call timed out after 20 seconds: {tool_name}")
            return {"error": "The search is taking too long. Let me help with what I know instead."}
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": f"I encountered an issue: {str(e)}"}
    
    async def cleanup(self):
        """Cleanup the server connection."""
        if self.session:
            await self.session.close()
            self.session = None
        self.connected = False
        logger.info(f"Cleaned up MCP server: {self.name}")
    
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()