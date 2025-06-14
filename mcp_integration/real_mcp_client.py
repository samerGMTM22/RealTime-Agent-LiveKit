"""Real MCP Client implementation using JSON-RPC 2.0 over stdio"""
import asyncio
import json
import subprocess
import uuid
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPServer:
    """MCP server configuration"""
    id: str
    name: str
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    
class MCPClient:
    """Handles communication with a single MCP server via stdio"""
    
    def __init__(self, server: MCPServer):
        self.server = server
        self.process = None
        self.pending_requests = {}
        self.capabilities = {}
        self.tools = {}
        self._read_task = None
        
    async def connect(self):
        """Connect to MCP server via stdio"""
        try:
            # Prepare command
            cmd = [self.server.command] + (self.server.args or [])
            env = {**os.environ, **(self.server.env or {})}
            
            logger.info(f"Starting MCP server: {' '.join(cmd)}")
            
            # Start MCP server process
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Start message reader
            self._read_task = asyncio.create_task(self._read_messages())
            
            # Initialize MCP connection
            await self._initialize()
            
            logger.info(f"Successfully connected to MCP server: {self.server.name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.server.name}: {e}")
            raise
            
    async def _read_messages(self):
        """Read JSON-RPC messages from stdout"""
        buffer = ""
        while self.process and self.process.returncode is None:
            try:
                data = await self.process.stdout.read(1024)
                if not data:
                    break
                    
                buffer += data.decode('utf-8')
                
                # Process complete messages (newline-delimited JSON)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            message = json.loads(line)
                            await self._handle_message(message)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON from {self.server.name}: {line}")
                            
            except Exception as e:
                logger.error(f"Error reading messages from {self.server.name}: {e}")
                break
                
    async def _handle_message(self, message: Dict):
        """Handle incoming JSON-RPC message"""
        if "id" in message:
            # Response to our request
            request_id = message["id"]
            if request_id in self.pending_requests:
                future = self.pending_requests.pop(request_id)
                if "error" in message:
                    future.set_exception(Exception(message["error"]["message"]))
                else:
                    future.set_result(message.get("result"))
                    
    async def _send_request(self, method: str, params: Dict = None) -> Any:
        """Send JSON-RPC request and wait for response"""
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode('utf-8'))
        await self.process.stdin.drain()
        
        logger.debug(f"Sent MCP request: {request}")
        
        # Wait for response with timeout
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            logger.debug(f"Received MCP response: {result}")
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise Exception(f"Request timeout for {method}")
            
    async def _initialize(self):
        """Initialize MCP connection"""
        # Send initialize request
        result = await self._send_request("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {
                "tools": {"listChanged": True}
            },
            "clientInfo": {
                "name": "livekit-mcp-client",
                "version": "1.0.0"
            }
        })
        
        self.capabilities = result.get("capabilities", {})
        logger.info(f"MCP server {self.server.name} capabilities: {self.capabilities}")
        
        # Send initialized notification
        await self._send_notification("notifications/initialized")
        
        # List available tools
        if self.capabilities.get("tools"):
            tools_result = await self._send_request("tools/list")
            self.tools = {tool["name"]: tool for tool in tools_result.get("tools", [])}
            logger.info(f"Available tools for {self.server.name}: {list(self.tools.keys())}")
            
    async def _send_notification(self, method: str, params: Dict = None):
        """Send JSON-RPC notification (no response expected)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json.encode('utf-8'))
        await self.process.stdin.drain()
        
    async def execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool on this MCP server"""
        if tool_name not in self.tools:
            # Try alternative tool names
            alternatives = {
                "search": "brave_web_search",
                "web_search": "brave_web_search",
                "search_web": "brave_web_search",
                "send_email": "send_email",
                "create_draft": "create_draft_email"
            }
            mapped_name = alternatives.get(tool_name, tool_name)
            
            if mapped_name not in self.tools:
                available_tools = list(self.tools.keys())
                logger.warning(f"Tool {tool_name} not found. Available: {available_tools}")
                raise ValueError(f"Tool {tool_name} not found. Available: {available_tools}")
            
            tool_name = mapped_name
                
        result = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        return result
        
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()


class RealMCPManager:
    """Manages multiple MCP server connections for LiveKit agent"""
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        
    async def initialize_user_servers(self, user_id: int) -> List[Dict]:
        """Initialize MCP servers for user"""
        # Define MCP server configurations based on environment
        servers = []
        
        # Brave Search MCP server
        brave_api_key = os.environ.get("BRAVE_API_KEY")
        if brave_api_key:
            servers.append(MCPServer(
                id="brave-search",
                name="internet access",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-brave-search"],
                env={"BRAVE_API_KEY": brave_api_key}
            ))
        
        # Zapier MCP server
        zapier_api_key = os.environ.get("ZAPIER_API_KEY")
        if zapier_api_key:
            servers.append(MCPServer(
                id="zapier",
                name="Zapier send draft email",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-zapier"],
                env={"ZAPIER_API_KEY": zapier_api_key}
            ))
        
        if not servers:
            logger.warning("No MCP servers configured. Set BRAVE_API_KEY and/or ZAPIER_API_KEY environment variables.")
            return []
        
        results = []
        for server in servers:
            try:
                client = MCPClient(server)
                await client.connect()
                self.clients[server.name] = client
                
                results.append({
                    "status": "connected",
                    "name": server.name,
                    "tools": list(client.tools.keys())
                })
                
            except Exception as e:
                logger.error(f"Failed to connect to {server.name}: {e}")
                results.append({
                    "status": "failed",
                    "name": server.name,
                    "error": str(e)
                })
                
        return results
        
    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Dict:
        """Execute tool on MCP server and format response"""
        if server_name not in self.clients:
            raise ValueError(f"Server {server_name} not connected")
            
        client = self.clients[server_name]
        
        try:
            result = await client.execute_tool(tool_name, arguments)
            
            # Format response based on server type
            if server_name == "internet access":
                return self._format_search_results(result)
            elif "email" in server_name.lower():
                return self._format_email_result(result)
            else:
                return {"content": json.dumps(result), "success": True}
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"error": str(e), "success": False}
            
    def _format_search_results(self, result: Dict) -> Dict:
        """Format Brave search results for voice response"""
        try:
            # Handle different result formats from Brave search
            if isinstance(result, list):
                # Array of content blocks
                formatted_results = []
                for idx, item in enumerate(result[:5], 1):
                    if isinstance(item, dict):
                        if "text" in item:
                            formatted_results.append(f"{idx}. {item['text']}")
                        elif "title" in item and "snippet" in item:
                            formatted_results.append(f"{idx}. {item['title']}: {item['snippet']}")
                        else:
                            formatted_results.append(f"{idx}. {str(item)}")
                    else:
                        formatted_results.append(f"{idx}. {str(item)}")
                
                return {
                    "content": "\n\n".join(formatted_results) if formatted_results else "No results found",
                    "success": True
                }
            elif isinstance(result, dict):
                if "content" in result:
                    return {"content": result["content"], "success": True}
                else:
                    return {"content": str(result), "success": True}
            else:
                return {"content": str(result), "success": True}
                
        except Exception as e:
            logger.error(f"Error formatting search results: {e}")
            return {"content": "Search completed", "success": True}
            
    def _format_email_result(self, result: Dict) -> Dict:
        """Format email send result"""
        if isinstance(result, dict):
            if result.get("success") or "id" in result:
                return {"content": "Email sent successfully", "success": True}
            elif "error" in result:
                return {"content": f"Email error: {result['error']}", "success": False}
            else:
                return {"content": "Email draft created", "success": True}
        else:
            return {"content": "Email processed", "success": True}
            
    async def disconnect_all(self):
        """Disconnect all MCP servers"""
        for client in self.clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client: {e}")
        self.clients.clear()
        logger.info("Disconnected all MCP servers")