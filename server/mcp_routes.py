"""API routes for MCP server management"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
from .storage import storage, InsertMcpServer
from .mcp_manager import MCPManager
from pydantic import BaseModel

logger = logging.getLogger("mcp_routes")
router = APIRouter()

# Global MCP manager instance
mcp_manager = MCPManager(storage)

class McpServerCreate(BaseModel):
    name: str
    url: str
    description: str = ""
    apiKey: str = ""
    isActive: bool = True

class McpServerUpdate(BaseModel):
    name: str = None
    url: str = None
    description: str = None
    apiKey: str = None
    isActive: bool = None

@router.get("/api/mcp-servers")
async def get_mcp_servers(user_id: int = 1):
    """Get all MCP servers for a user"""
    try:
        servers = await storage.getMcpServersByUserId(user_id)
        return {"servers": servers}
    except Exception as e:
        logger.error(f"Failed to get MCP servers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve MCP servers")

@router.post("/api/mcp-servers")
async def create_mcp_server(server_data: McpServerCreate, user_id: int = 1):
    """Create a new MCP server"""
    try:
        insert_data = InsertMcpServer(
            userId=user_id,
            name=server_data.name,
            url=server_data.url,
            description=server_data.description,
            apiKey=server_data.apiKey,
            isActive=server_data.isActive
        )
        
        server = await storage.createMcpServer(insert_data)
        
        # Attempt to connect if active
        if server.isActive:
            await mcp_manager.connect_server(server)
        
        return {"server": server}
    except Exception as e:
        logger.error(f"Failed to create MCP server: {e}")
        raise HTTPException(status_code=500, detail="Failed to create MCP server")

@router.put("/api/mcp-servers/{server_id}")
async def update_mcp_server(server_id: int, server_data: McpServerUpdate):
    """Update an MCP server"""
    try:
        update_dict = {k: v for k, v in server_data.dict().items() if v is not None}
        
        server = await storage.updateMcpServer(server_id, update_dict)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        # Reconnect if the server was updated and is active
        if server.isActive:
            await mcp_manager.disconnect_server(server_id)
            await mcp_manager.connect_server(server)
        else:
            await mcp_manager.disconnect_server(server_id)
        
        return {"server": server}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update MCP server: {e}")
        raise HTTPException(status_code=500, detail="Failed to update MCP server")

@router.delete("/api/mcp-servers/{server_id}")
async def delete_mcp_server(server_id: int):
    """Delete an MCP server"""
    try:
        await mcp_manager.disconnect_server(server_id)
        success = await storage.deleteMcpServer(server_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        return {"message": "MCP server deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete MCP server: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete MCP server")

@router.post("/api/mcp-servers/{server_id}/test")
async def test_mcp_server(server_id: int):
    """Test connection to an MCP server"""
    try:
        servers = await storage.getMcpServersByUserId(1)  # Default user
        server = next((s for s in servers if s.id == server_id), None)
        
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        # Test connection
        success = await mcp_manager.connect_server(server)
        
        if success:
            tools = await mcp_manager.get_server_tools(server_id)
            return {
                "status": "connected",
                "tools_count": len(tools),
                "tools": tools
            }
        else:
            return {"status": "failed", "error": "Connection failed"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test MCP server: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/api/mcp-servers/{server_id}/tools")
async def get_server_tools(server_id: int):
    """Get available tools for an MCP server"""
    try:
        tools = await mcp_manager.get_server_tools(server_id)
        return {"tools": tools}
    except Exception as e:
        logger.error(f"Failed to get server tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve server tools")

@router.post("/api/mcp-servers/{server_id}/tools/{tool_name}/call")
async def call_mcp_tool(server_id: int, tool_name: str, params: Dict[str, Any]):
    """Call a tool on an MCP server"""
    try:
        result = await mcp_manager.call_tool(server_id, tool_name, params)
        return {"result": result}
    except Exception as e:
        logger.error(f"Failed to call MCP tool: {e}")
        raise HTTPException(status_code=500, detail=f"Tool call failed: {str(e)}")

@router.get("/api/mcp-status")
async def get_mcp_status():
    """Get overall MCP system status"""
    try:
        connected_count = len(mcp_manager.connected_servers)
        all_tools = await mcp_manager.get_all_tools()
        
        return {
            "status": "connected" if connected_count > 0 else "disconnected",
            "connected_servers": connected_count,
            "total_tools": len(all_tools),
            "servers": {
                server_id: {
                    "name": server.name,
                    "tools_count": len(await mcp_manager.get_server_tools(server_id))
                }
                for server_id, server in mcp_manager.connected_servers.items()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get MCP status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "connected_servers": 0,
            "total_tools": 0
        }