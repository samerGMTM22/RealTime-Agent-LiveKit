"""Protocol handlers for MCP integration with job polling support"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import httpx
import asyncio

class BaseProtocolHandler(ABC):
    @abstractmethod
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        """Execute a tool and return job_id for polling"""
        pass

    @abstractmethod
    async def get_result(self, server_config: Dict, job_id: str) -> Dict:
        """Poll for result using job_id"""
        pass

    @abstractmethod
    async def discover_tools(self, server_config: Dict) -> Dict:
        """Discover available tools from server"""
        pass
    
    @abstractmethod
    async def health_check(self, server_config: Dict) -> bool:
        """Check if server is healthy"""
        pass

class HTTPProtocolHandler(BaseProtocolHandler):
    def __init__(self):
        self.timeout = 30.0

    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        """Execute tool via HTTP POST and return job info"""
        url = f"{server_config['url']}/mcp/execute/{tool_name}"
        headers = self._get_headers(server_config)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=params, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_result(self, server_config: Dict, job_id: str) -> Dict:
        """Get result via HTTP GET using job_id"""
        result_endpoint = server_config.get('result_endpoint', '/mcp/results')
        url = f"{server_config['url']}{result_endpoint}/{job_id}"
        headers = self._get_headers(server_config)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def discover_tools(self, server_config: Dict) -> Dict:
        """Discover tools via HTTP GET"""
        discovery_endpoint = server_config.get('discovery_endpoint', '/.well-known/mcp.json')
        url = f"{server_config['url']}{discovery_endpoint}"
        headers = self._get_headers(server_config)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Tool discovery failed for {server_config['name']}: {e}")
            return {"tools": []}
    
    async def health_check(self, server_config: Dict) -> bool:
        """Check server health via HTTP GET"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(server_config['url'])
                return 200 <= response.status_code < 300
        except Exception:
            return False

    def _get_headers(self, server_config: Dict) -> Dict[str, str]:
        """Get HTTP headers including auth if available"""
        headers = {"Content-Type": "application/json"}
        api_key = server_config.get('api_key')
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

class SSEProtocolHandler(HTTPProtocolHandler):
    """SSE Protocol Handler - inherits HTTP polling for now"""
    
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        """For SSE, we still use HTTP for job submission"""
        return await super().execute_tool(server_config, tool_name, params)
    
    async def get_result(self, server_config: Dict, job_id: str) -> Dict:
        """For SSE, we use HTTP polling since connection closes"""
        return await super().get_result(server_config, job_id)

class WebSocketProtocolHandler(BaseProtocolHandler):
    """WebSocket Protocol Handler - placeholder for future implementation"""
    
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        raise NotImplementedError("WebSocket protocol not yet implemented")
    
    async def get_result(self, server_config: Dict, job_id: str) -> Dict:
        raise NotImplementedError("WebSocket protocol not yet implemented")
    
    async def discover_tools(self, server_config: Dict) -> Dict:
        raise NotImplementedError("WebSocket protocol not yet implemented")
    
    async def health_check(self, server_config: Dict) -> bool:
        return False

class StdioProtocolHandler(BaseProtocolHandler):
    """Stdio Protocol Handler - placeholder for future implementation"""
    
    async def execute_tool(self, server_config: Dict, tool_name: str, params: Dict) -> Dict:
        raise NotImplementedError("Stdio protocol not yet implemented")
    
    async def get_result(self, server_config: Dict, job_id: str) -> Dict:
        raise NotImplementedError("Stdio protocol not yet implemented")
    
    async def discover_tools(self, server_config: Dict) -> Dict:
        raise NotImplementedError("Stdio protocol not yet implemented")
    
    async def health_check(self, server_config: Dict) -> bool:
        return False