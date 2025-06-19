"""PostgreSQL storage for MCP integration"""
import asyncio
import asyncpg
import os
from typing import Dict, List, Optional, Any
import json

class PostgreSQLStorage:
    def __init__(self):
        self.pool = None
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

    async def initialize(self):
        """Initialize the connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url)

    async def get_active_mcp_servers(self, user_id: int = 1) -> List[Dict[str, Any]]:
        """Get all active MCP servers for a user"""
        await self.initialize()
        
        query = """
            SELECT 
                id, name, url, protocol_type, discovery_endpoint, 
                result_endpoint, poll_interval, api_key, tools, 
                connection_status, capabilities, metadata
            FROM mcp_servers 
            WHERE user_id = $1 AND is_active = true
        """
        
        if self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, user_id)
                return [dict(row) for row in rows]
        return []

    async def update_server_status(self, server_id: int, status: str, last_connected: Optional[str] = None):
        """Update server connection status"""
        await self.initialize()
        
        query = """
            UPDATE mcp_servers 
            SET connection_status = $2, last_connected = COALESCE($3, last_connected), updated_at = NOW()
            WHERE id = $1
        """
        
        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(query, server_id, status, last_connected)

    async def update_server_tools(self, server_id: int, tools: List[Dict], capabilities: List[Dict]):
        """Update server tools and capabilities"""
        await self.initialize()
        
        query = """
            UPDATE mcp_servers 
            SET tools = $2, capabilities = $3, updated_at = NOW()
            WHERE id = $1
        """
        
        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(query, server_id, json.dumps(tools), json.dumps(capabilities))

    async def get_server_by_id(self, server_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific MCP server by ID"""
        await self.initialize()
        
        query = """
            SELECT 
                id, name, url, protocol_type, discovery_endpoint, 
                result_endpoint, poll_interval, api_key, tools, 
                connection_status, capabilities, metadata
            FROM mcp_servers 
            WHERE id = $1
        """
        
        if self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, server_id)
                return dict(row) if row else None
        return None

    async def cleanup(self):
        """Cleanup database connections"""
        if self.pool:
            await self.pool.close()