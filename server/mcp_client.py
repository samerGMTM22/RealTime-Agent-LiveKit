"""MCP Client implementation for LiveKit voice agent"""

import asyncio
import logging
import json
import subprocess
import websockets
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger("mcp_client")

class MCPServer:
    """Base class for MCP server connections"""
    
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params
        self.server = None
        self.tools = []
        self.connected = False
        
    async def connect(self) -> bool:
        """Connect to the MCP server"""
        raise NotImplementedError
        
    async def disconnect(self):
        """Disconnect from the MCP server"""
        self.connected = False
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server"""
        return self.tools
        
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        raise NotImplementedError

class MCPServerStdio(MCPServer):
    """MCP server using stdio protocol (for local servers)"""
    
    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.process = None
        
    async def connect(self) -> bool:
        try:
            cmd = self.params.get("cmd", "npx")
            args = self.params.get("args", [])
            
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                cmd, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize MCP session
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "livekit-agent",
                        "version": "1.0.0"
                    }
                }
            }
            
            await self._send_message(init_message)
            response = await self._receive_message()
            
            if response and "result" in response:
                # Get available tools
                tools_message = {
                    "jsonrpc": "2.0", 
                    "id": 2,
                    "method": "tools/list"
                }
                await self._send_message(tools_message)
                tools_response = await self._receive_message()
                
                if tools_response and "result" in tools_response:
                    self.tools = tools_response["result"].get("tools", [])
                
                self.connected = True
                logger.info(f"Connected to {self.name} via stdio, found {len(self.tools)} tools")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to {self.name}: {e}")
            await self.disconnect()
            
        return False
    
    async def disconnect(self):
        await super().disconnect()
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
            self.process = None
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.connected:
            raise Exception("Server not connected")
            
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params
            }
        }
        
        await self._send_message(message)
        response = await self._receive_message()
        
        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")
        else:
            raise Exception("Invalid response from MCP server")
    
    async def _send_message(self, message: Dict):
        if self.process and self.process.stdin:
            data = json.dumps(message) + "\n"
            self.process.stdin.write(data.encode())
            await self.process.stdin.drain()
    
    async def _receive_message(self) -> Optional[Dict]:
        if self.process and self.process.stdout:
            try:
                line = await asyncio.wait_for(self.process.stdout.readline(), timeout=10.0)
                if line:
                    return json.loads(line.decode().strip())
            except (asyncio.TimeoutError, json.JSONDecodeError) as e:
                logger.error(f"Error receiving message: {e}")
        return None

class MCPServerHttp(MCPServer):
    """MCP server using HTTP/WebSocket protocol (for remote servers)"""
    
    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.websocket = None
        
    async def connect(self) -> bool:
        try:
            url = self.params.get("url")
            headers = {}
            
            if self.params.get("api_key"):
                headers["Authorization"] = f"Bearer {self.params['api_key']}"
            
            # Connect via WebSocket
            self.websocket = await websockets.connect(
                url.replace("http", "ws"),
                extra_headers=headers
            )
            
            # Initialize MCP session
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "livekit-agent", "version": "1.0.0"}
                }
            }
            
            await self.websocket.send(json.dumps(init_message))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if "result" in response_data:
                # Get available tools
                tools_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
                await self.websocket.send(json.dumps(tools_message))
                tools_response = await self.websocket.recv()
                tools_data = json.loads(tools_response)
                
                if "result" in tools_data:
                    self.tools = tools_data["result"].get("tools", [])
                
                self.connected = True
                logger.info(f"Connected to {self.name} via WebSocket, found {len(self.tools)} tools")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to {self.name}: {e}")
            await self.disconnect()
            
        return False
    
    async def disconnect(self):
        super().disconnect()
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.connected or not self.websocket:
            raise Exception("Server not connected")
            
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": params}
        }
        
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        
        if "result" in response_data:
            return response_data["result"]
        elif "error" in response_data:
            raise Exception(f"Tool call failed: {response_data['error']}")
        else:
            raise Exception("Invalid response from MCP server")