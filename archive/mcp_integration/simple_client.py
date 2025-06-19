"""Simplified MCP Client for LiveKit voice agent"""
import logging
import asyncio
import requests
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SimpleMCPClient:
    """Simplified MCP client that uses requests for HTTP calls"""
    
    def __init__(self, name: str, url: str, api_key: str = None):
        self.name = name
        self.url = url
        self.api_key = api_key
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to MCP server using synchronous requests"""
        try:
            # For MCP servers, we assume they're available if configured
            self.connected = True
            logger.info(f"MCP server {self.name} marked as available")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.name}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MCP server"""
        self.connected = False
        logger.info(f"Disconnected from MCP server {self.name}")
    
    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server using actual HTTP requests"""
        if not self.connected:
            return {"error": "Server not connected"}
            
        try:
            # Handle SSE-based MCP servers (like N8N)
            if '/sse' in self.url:
                return self._handle_sse_mcp_call(tool_name, params)
            
            # Prepare MCP JSON-RPC request for standard servers
            mcp_request = {
                "jsonrpc": "2.0",
                "id": f"req_{hash(f'{tool_name}_{params}')}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            logger.info(f"Making MCP call to {self.url} with tool {tool_name}")
            logger.info(f"MCP request: {mcp_request}")
            
            # Make actual HTTP request to MCP server
            response = requests.post(
                self.url, 
                json=mcp_request, 
                headers=headers, 
                timeout=10
            )
            
            logger.info(f"MCP server response status: {response.status_code}")
            logger.info(f"MCP server response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle MCP JSON-RPC response format
                if "result" in result:
                    mcp_result = result["result"]
                    if isinstance(mcp_result, dict) and "content" in mcp_result:
                        return {
                            "content": mcp_result["content"],
                            "status": "success"
                        }
                    elif isinstance(mcp_result, list) and len(mcp_result) > 0:
                        # Handle array of content blocks
                        content_parts = []
                        for item in mcp_result:
                            if isinstance(item, dict) and "text" in item:
                                content_parts.append(item["text"])
                            elif isinstance(item, str):
                                content_parts.append(item)
                        return {
                            "content": "\n".join(content_parts) if content_parts else str(mcp_result),
                            "status": "success"
                        }
                    else:
                        return {
                            "content": str(mcp_result),
                            "status": "success"
                        }
                elif "error" in result:
                    return {
                        "error": result["error"].get("message", "MCP server error"),
                        "status": "error"
                    }
                else:
                    return {
                        "content": str(result),
                        "status": "success"
                    }
            else:
                return {
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "status": "error"
                }
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {self.name}: {e}")
            return {"error": str(e)}
    
    def _handle_sse_mcp_call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SSE-based MCP server calls (like N8N) with concurrent session management"""
        import threading
        import queue
        import time
        
        try:
            # Use a queue to communicate between threads
            result_queue = queue.Queue()
            messages_url = None
            sse_response = None
            
            def sse_reader():
                nonlocal messages_url, sse_response
                try:
                    # Establish SSE connection
                    sse_headers = {
                        "Accept": "text/event-stream",
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive"
                    }
                    
                    if self.api_key:
                        sse_headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    logger.info(f"Establishing SSE connection to {self.url}")
                    
                    sse_response = requests.get(
                        self.url,
                        headers=sse_headers,
                        stream=True,
                        timeout=30
                    )
                    
                    if sse_response.status_code == 200:
                        # Read SSE stream to find session endpoint
                        for line in sse_response.iter_lines(decode_unicode=True):
                            if line and line.startswith('data: ') and '/messages?sessionId=' in line:
                                endpoint_path = line[6:].strip()
                                from urllib.parse import urljoin
                                messages_url = urljoin(self.url, endpoint_path)
                                result_queue.put(("endpoint_found", messages_url))
                                break
                            elif line and line.startswith('data: ') and line != 'data: ':
                                # Log other SSE data for debugging
                                logger.info(f"SSE data: {line}")
                        
                        # Keep connection alive for a short time
                        time.sleep(2)
                    else:
                        result_queue.put(("error", f"SSE connection failed: {sse_response.status_code}"))
                        
                except Exception as e:
                    result_queue.put(("error", str(e)))
                finally:
                    if sse_response:
                        sse_response.close()
            
            # Start SSE reader in background thread
            sse_thread = threading.Thread(target=sse_reader, daemon=True)
            sse_thread.start()
            
            # Wait for endpoint or error
            try:
                event_type, event_data = result_queue.get(timeout=10)
                
                if event_type == "endpoint_found":
                    messages_url = event_data
                    logger.info(f"Got session endpoint: {messages_url}")
                    
                    # Make the MCP JSON-RPC call immediately while session is active
                    mcp_request = {
                        "jsonrpc": "2.0",
                        "id": f"req_{hash(f'{tool_name}_{params}')}",
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": params
                        }
                    }
                    
                    mcp_headers = {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    if self.api_key:
                        mcp_headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    logger.info(f"Making MCP call to session endpoint: {messages_url}")
                    logger.info(f"MCP request: {mcp_request}")
                    
                    mcp_response = requests.post(
                        messages_url,
                        json=mcp_request,
                        headers=mcp_headers,
                        timeout=8
                    )
                    
                    logger.info(f"MCP session response status: {mcp_response.status_code}")
                    logger.info(f"MCP session response: {mcp_response.text[:500]}")
                    
                    if mcp_response.status_code == 200:
                        try:
                            result = mcp_response.json()
                            if "result" in result:
                                mcp_result = result["result"]
                                if isinstance(mcp_result, dict) and "content" in mcp_result:
                                    return {
                                        "content": mcp_result["content"],
                                        "status": "success"
                                    }
                                elif isinstance(mcp_result, list):
                                    content_parts = []
                                    for item in mcp_result:
                                        if isinstance(item, dict) and "text" in item:
                                            content_parts.append(item["text"])
                                        elif isinstance(item, str):
                                            content_parts.append(item)
                                    return {
                                        "content": "\n".join(content_parts) if content_parts else str(mcp_result),
                                        "status": "success"
                                    }
                                else:
                                    return {
                                        "content": str(mcp_result),
                                        "status": "success"
                                    }
                            else:
                                return {
                                    "error": "No result in MCP response",
                                    "status": "error"
                                }
                        except Exception as parse_error:
                            logger.error(f"Failed to parse MCP response: {parse_error}")
                            return {
                                "error": f"Invalid JSON response: {mcp_response.text[:200]}",
                                "status": "error"
                            }
                    else:
                        return {
                            "error": f"MCP session call failed: {mcp_response.status_code} {mcp_response.text}",
                            "status": "error"
                        }
                elif event_type == "error":
                    return {
                        "error": event_data,
                        "status": "error"
                    }
                else:
                    return {
                        "error": "Unknown SSE event type",
                        "status": "error"
                    }
                    
            except queue.Empty:
                return {
                    "error": "SSE connection timeout - no session endpoint received",
                    "status": "error"
                }
                
        except Exception as e:
            logger.error(f"Error in SSE MCP call for {tool_name}: {e}")
            return {"error": str(e)}


class SimpleMCPManager:
    """Simplified MCP manager for the voice agent"""
    
    def __init__(self):
        self.connected_servers: Dict[int, SimpleMCPClient] = {}
        
    async def initialize_user_servers(self, user_id: int) -> List[Dict]:
        """Initialize MCP servers for user using the Express API"""
        try:
            # Get servers from Express API
            response = requests.get('http://localhost:5000/api/mcp/servers', timeout=5)
            if response.status_code == 200:
                servers_data = response.json()
                servers = servers_data if isinstance(servers_data, list) else servers_data.get('servers', [])
                
                connected_count = 0
                for server in servers:
                    if server.get('isActive', False):
                        client = SimpleMCPClient(
                            name=server['name'],
                            url=server.get('url', ''),
                            api_key=server.get('apiKey')
                        )
                        
                        if client.connect():
                            self.connected_servers[server['id']] = client
                            connected_count += 1
                            logger.info(f"Connected to MCP server: {server['name']}")
                
                logger.info(f"Initialized {connected_count} MCP servers")
                return servers
            else:
                logger.warning(f"Failed to fetch MCP servers: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error initializing MCP servers: {e}")
            
        return []
    
    async def call_tool(self, server_id: int, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on a specific MCP server"""
        if server_id not in self.connected_servers:
            return {"error": "Server not found"}
            
        client = self.connected_servers[server_id]
        return client.call_tool(tool_name, params)
    
    async def get_all_tools(self) -> List[Dict]:
        """Get all available tools from connected servers"""
        tools = []
        for server_id, client in self.connected_servers.items():
            if client.connected:
                # Add common tools based on server name
                if "internet" in client.name.lower():
                    tools.append({
                        "name": "search",
                        "description": "Search the web for information",
                        "server_id": server_id,
                        "server_name": client.name
                    })
                elif "zapier" in client.name.lower():
                    tools.append({
                        "name": "send_email", 
                        "description": "Send email via Zapier",
                        "server_id": server_id,
                        "server_name": client.name
                    })
        return tools
    
    async def cleanup(self):
        """Cleanup all server connections"""
        for client in self.connected_servers.values():
            client.disconnect()
        self.connected_servers.clear()
        logger.info("Cleaned up all MCP connections")