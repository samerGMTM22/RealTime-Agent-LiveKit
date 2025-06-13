"""MCP Client implementation for LiveKit voice agent"""
import asyncio
import json
import logging
import aiohttp
import websockets
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger("mcp_client")

class MCPServer(ABC):
    """Base class for MCP server connections"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.connected = False
        self.capabilities = []
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the MCP server"""
        pass
        
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the MCP server"""
        pass
        
    @abstractmethod
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server"""
        pass
        
    @abstractmethod
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        pass

class MCPServerHttp(MCPServer):
    """MCP server using HTTP/WebSocket protocol (for remote servers)"""
    
    def __init__(self, name: str, url: str, api_key: str = None, **kwargs):
        super().__init__(name, **kwargs)
        self.url = url
        self.api_key = api_key
        self.session = None
        self.websocket = None
        
    async def connect(self) -> bool:
        """Connect to HTTP-based MCP server"""
        try:
            # Create HTTP session
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            self.session = aiohttp.ClientSession(headers=headers)
            
            # Test connection with a simple health check
            async with self.session.get(f"{self.url}/health") as resp:
                if resp.status == 200:
                    self.connected = True
                    logger.info(f"Connected to HTTP MCP server: {self.name}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to connect to HTTP MCP server {self.name}: {e}")
            if self.session:
                await self.session.close()
                self.session = None
                
        return False
        
    async def disconnect(self):
        """Disconnect from HTTP MCP server"""
        if self.session:
            await self.session.close()
            self.session = None
        self.connected = False
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from HTTP MCP server"""
        if not self.connected or not self.session:
            return []
            
        try:
            async with self.session.get(f"{self.url}/tools") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("tools", [])
        except Exception as e:
            logger.error(f"Failed to list tools from {self.name}: {e}")
            
        return []
        
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on HTTP MCP server"""
        if not self.connected or not self.session:
            return {"error": "Server not connected"}
            
        try:
            payload = {
                "tool": tool_name,
                "parameters": params
            }
            
            async with self.session.post(f"{self.url}/call-tool", json=payload) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"error": f"HTTP {resp.status}: {await resp.text()}"}
                    
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {self.name}: {e}")
            return {"error": str(e)}

class MCPServerStdio(MCPServer):
    """MCP server using stdio protocol (for local servers)"""
    
    def __init__(self, name: str, command: str, **kwargs):
        super().__init__(name, **kwargs)
        self.command = command
        self.process = None
        self.message_id = 0
        
    async def connect(self) -> bool:
        """Connect to stdio-based MCP server"""
        try:
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_shell(
                self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send initialization message
            init_msg = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {}
                }
            }
            
            await self._send_message(init_msg)
            response = await self._receive_message()
            
            if response and response.get("result"):
                self.connected = True
                logger.info(f"Connected to stdio MCP server: {self.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to stdio MCP server {self.name}: {e}")
            if self.process:
                self.process.terminate()
                self.process = None
                
        return False
        
    async def disconnect(self):
        """Disconnect from stdio MCP server"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except:
                pass
            self.process = None
        self.connected = False
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from stdio MCP server"""
        if not self.connected or not self.process:
            return []
            
        try:
            msg = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list"
            }
            
            await self._send_message(msg)
            response = await self._receive_message()
            
            if response and response.get("result"):
                return response["result"].get("tools", [])
                
        except Exception as e:
            logger.error(f"Failed to list tools from {self.name}: {e}")
            
        return []
        
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on stdio MCP server"""
        if not self.connected or not self.process:
            return {"error": "Server not connected"}
            
        try:
            msg = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }
            
            await self._send_message(msg)
            response = await self._receive_message()
            
            if response:
                if "result" in response:
                    return response["result"]
                elif "error" in response:
                    return {"error": response["error"]}
                    
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} on {self.name}: {e}")
            return {"error": str(e)}
            
        return {"error": "No response from server"}
        
    def _next_id(self) -> int:
        """Get next message ID"""
        self.message_id += 1
        return self.message_id
        
    async def _send_message(self, message: Dict):
        """Send JSON-RPC message to stdio server"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Process not available")
            
        data = json.dumps(message) + '\n'
        self.process.stdin.write(data.encode())
        await self.process.stdin.drain()
        
    async def _receive_message(self) -> Optional[Dict]:
        """Receive JSON-RPC message from stdio server"""
        if not self.process or not self.process.stdout:
            return None
            
        try:
            line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=5.0
            )
            
            if line:
                return json.loads(line.decode().strip())
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response from {self.name}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {self.name}: {e}")
            
        return None