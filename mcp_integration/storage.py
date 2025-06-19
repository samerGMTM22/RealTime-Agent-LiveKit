import os
import asyncio
import asyncpg
from typing import List, Dict, Optional
from datetime import datetime

class PostgreSQLStorage:
    """Python database interface matching TypeScript storage interface"""
    
    def __init__(self):
        self.pool = None
        
    async def connect(self):
        """Create connection pool"""
        if not self.pool:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable not set")
                
            self.pool = await asyncpg.create_pool(
                database_url,
                min_size=1,
                max_size=10
            )
    
    async def getAgentConfigByUserId(self, user_id: int) -> Optional[Dict]:
        """Get agent configuration for user"""
        await self.connect()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, system_prompt, voice_model, temperature, personality, response_length
                FROM agent_configs
                WHERE user_id = $1 AND is_active = true
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id
            )
            
            if row:
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "systemPrompt": row["system_prompt"],
                    "voiceModel": row["voice_model"],
                    "temperature": row["temperature"],
                    "personality": row["personality"],
                    "responseLength": row["response_length"]
                }
            return None
    
    async def getMcpServersByUserId(self, user_id: int) -> List[Dict]:
        """Get all MCP servers for a user"""
        await self.connect()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, url, description, api_key, is_active,
                       connection_status, last_connected, metadata
                FROM mcp_servers
                WHERE user_id = $1 AND is_active = true
                ORDER BY created_at DESC
                """,
                user_id
            )
            
            return [dict(row) for row in rows]
    
    async def updateMcpServer(self, server_id: int, updates: Dict) -> Optional[Dict]:
        """Update MCP server status"""
        await self.connect()
        
        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        for i, (key, value) in enumerate(updates.items(), 1):
            # Convert camelCase to snake_case
            db_key = ''.join(['_'+c.lower() if c.isupper() else c for c in key]).lstrip('_')
            set_clauses.append(f"{db_key} = ${i}")
            values.append(value)
        
        values.append(server_id)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE mcp_servers
                SET {', '.join(set_clauses)}, updated_at = NOW()
                WHERE id = ${len(values)}
                RETURNING *
                """,
                *values
            )
            
            return dict(row) if row else None
    
    async def cleanup(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()