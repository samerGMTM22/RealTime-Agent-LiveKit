"""Universal MCP Protocol Handlers - Implements Gemini's universal architecture"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import httpx
from httpx_sse import aconnect_sse

logger = logging.getLogger(__name__)

class BaseProtocolHandler(ABC):
    """Base class for all MCP protocol handlers"""
    
    @abstractmethod
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        """Execute a tool on the MCP server"""
        pass

    @abstractmethod
    async def discover_tools(self, server_config: Dict) -> Dict:
        """Discover available tools from the MCP server"""
        pass

    @abstractmethod
    async def health_check(self, server_config: Dict) -> bool:
        """Check if the MCP server is healthy and responsive"""
        pass
    
    async def cleanup(self):
        """Cleanup protocol handler resources - implemented by subclasses as needed"""
        pass

class HTTPProtocolHandler(BaseProtocolHandler):
    """Handler for HTTP-based MCP servers"""
    
    def __init__(self):
        self.client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client
    
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        """Execute tool via HTTP POST"""
        try:
            client = await self._get_client()
            base_url = server_config.get('base_url') or server_config.get('url', '')
            url = f"{base_url.rstrip('/')}/execute"
            
            payload = {
                "tool_name": tool_name,
                "params": params
            }
            
            headers = {"Content-Type": "application/json"}
            if server_config.get('api_key'):
                headers["Authorization"] = f"Bearer {server_config['api_key']}"
            
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {
                "status": "success",
                "content": response.text,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
            }
            
        except Exception as e:
            logger.error(f"HTTP tool execution failed: {e}")
            return {
                "status": "error",
                "content": f"Tool execution failed: {str(e)}"
            }
    
    async def discover_tools(self, server_config: Dict) -> Dict:
        """Discover tools via HTTP GET"""
        try:
            client = await self._get_client()
            base_url = server_config.get('base_url') or server_config.get('url', '')
            discovery_url = f"{base_url.rstrip('/')}{server_config.get('discovery_endpoint', '/.well-known/mcp.json')}"
            
            headers = {}
            if server_config.get('api_key'):
                headers["Authorization"] = f"Bearer {server_config['api_key']}"
            
            response = await client.get(discovery_url, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"HTTP tool discovery failed: {e}")
            return {"tools": []}
    
    async def health_check(self, server_config: Dict) -> bool:
        """Check HTTP server health"""
        try:
            client = await self._get_client()
            base_url = server_config.get('base_url') or server_config.get('url', '')
            health_url = f"{base_url.rstrip('/')}/health"
            
            response = await client.get(health_url, timeout=5.0)
            return response.status_code == 200
            
        except Exception:
            return False
    
    async def cleanup(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None

class SSEProtocolHandler(BaseProtocolHandler):
    """Handler for Server-Sent Events (SSE) based MCP servers like N8N"""
    
    def __init__(self):
        self.connections = {}  # server_id -> connection info
    
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        """Execute tool via SSE connection"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                base_url = server_config.get('base_url') or server_config.get('url', '')
                url = f"{base_url.rstrip('/')}/webhook"
                
                # Prepare headers
                headers = {
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
                
                if server_config.get('api_key'):
                    headers["Authorization"] = f"Bearer {server_config['api_key']}"
                
                # Prepare payload based on server type
                if 'n8n' in server_config.get('name', '').lower():
                    # N8N specific payload format
                    payload = {
                        "action": tool_name,
                        **params
                    }
                else:
                    # Generic payload format
                    payload = {
                        "tool_name": tool_name,
                        "params": params
                    }
                
                # Execute via SSE
                async with aconnect_sse(client, "POST", url, json=payload, headers=headers) as event_source:
                    result_content = ""
                    
                    async for sse in event_source.aiter_sse():
                        if sse.event == "data":
                            try:
                                data = json.loads(sse.data)
                                if data.get("type") == "result":
                                    result_content = data.get("content", "")
                                    break
                                elif data.get("type") == "error":
                                    return {
                                        "status": "error",
                                        "content": data.get("message", "Unknown error")
                                    }
                            except json.JSONDecodeError:
                                # Handle plain text responses
                                result_content += sse.data
                        
                        elif sse.event == "end" or sse.event == "done":
                            break
                    
                    return {
                        "status": "success",
                        "content": result_content or "Tool executed successfully"
                    }
                    
        except Exception as e:
            logger.error(f"SSE tool execution failed: {e}")
            return {
                "status": "error",
                "content": f"Tool execution failed: {str(e)}"
            }
    
    async def discover_tools(self, server_config: Dict) -> Dict:
        """Discover tools via SSE server's discovery endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                base_url = server_config.get('base_url') or server_config.get('url', '')
                discovery_url = f"{base_url.rstrip('/')}{server_config.get('discovery_endpoint', '/.well-known/mcp.json')}"
                
                headers = {}
                if server_config.get('api_key'):
                    headers["Authorization"] = f"Bearer {server_config['api_key']}"
                
                response = await client.get(discovery_url, headers=headers)
                
                if response.status_code == 404:
                    # Fallback: return default tools based on server type
                    return self._get_default_tools(server_config)
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"SSE tool discovery failed: {e}")
            return self._get_default_tools(server_config)
    
    def _get_default_tools(self, server_config: Dict) -> Dict:
        """Provide default tool manifest for known server types"""
        server_name = server_config.get('name', '').lower()
        
        if 'n8n' in server_name and 'search' in server_name:
            return {
                "provider_name": server_config.get('name', 'N8N Server'),
                "protocol": "sse",
                "tools": [
                    {
                        "tool_name": "execute_web_search",
                        "description": "Search the web for current information using N8N workflow",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query to find current information"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        
        return {"tools": []}
    
    async def health_check(self, server_config: Dict) -> bool:
        """Check SSE server health"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try to connect briefly to test connectivity
                base_url = server_config.get('base_url') or server_config.get('url', '')
                response = await client.get(base_url)
                return response.status_code in [200, 404]  # 404 is OK for webhook endpoints
                
        except Exception:
            return False

class WebSocketProtocolHandler(BaseProtocolHandler):
    """Handler for WebSocket-based MCP servers"""
    
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        """Execute tool via WebSocket"""
        # Implementation for WebSocket MCP servers
        return {
            "status": "error",
            "content": "WebSocket protocol handler not yet implemented"
        }
    
    async def discover_tools(self, server_config: Dict) -> Dict:
        """Discover tools via WebSocket"""
        return {"tools": []}
    
    async def health_check(self, server_config: Dict) -> bool:
        """Check WebSocket server health"""
        return False

class StdioProtocolHandler(BaseProtocolHandler):
    """Handler for stdio-based MCP servers (local processes)"""
    
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        """Execute tool via stdio process"""
        # Implementation for stdio MCP servers
        return {
            "status": "error", 
            "content": "Stdio protocol handler not yet implemented"
        }
    
    async def discover_tools(self, server_config: Dict) -> Dict:
        """Discover tools from stdio process"""
        return {"tools": []}
    
    async def health_check(self, server_config: Dict) -> bool:
        """Check stdio process health"""
        return False