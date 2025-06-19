import logging
import os
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from dotenv import load_dotenv

from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    Agent,
    AgentSession,
    function_tool
)
from livekit.plugins import openai, deepgram, silero
import requests
import json

logger = logging.getLogger("voice-agent")
load_dotenv()

# Global MCP manager for function tools
_dynamic_mcp_manager = None

class DynamicMCPManager:
    """Manager for dynamic MCP server connections loaded from database"""
    
    def __init__(self):
        self.connected_servers: Dict[int, Dict] = {}
        self.tools_registry: Dict[str, Callable] = {}
        
    async def initialize_from_database(self, user_id: int = 1) -> bool:
        """Load and connect to MCP servers from database"""
        try:
            # Get MCP servers from Express API
            response = requests.get('http://localhost:5000/api/mcp/servers', timeout=5)
            if response.status_code == 200:
                servers_data = response.json()
                servers = servers_data if isinstance(servers_data, list) else servers_data.get('servers', [])
                
                connected_count = 0
                for server in servers:
                    if server.get('isActive', False):
                        server_id = server['id']
                        server_name = server['name']
                        server_url = server.get('url', '')
                        api_key = server.get('apiKey', '')
                        
                        # Store server connection info
                        server_config = {
                            'id': server_id,
                            'name': server_name,
                            'url': server_url,
                            'api_key': api_key,
                            'status': 'connected'
                        }
                        
                        self.connected_servers[server_id] = server_config
                        connected_count += 1
                        logger.info(f"Registered MCP server: {server_name} (ID: {server_id})")
                
                logger.info(f"Successfully initialized {connected_count} MCP servers")
                return connected_count > 0
                
        except Exception as e:
            logger.error(f"Failed to initialize MCP servers from database: {e}")
            return False
        
        return False
    
    async def call_mcp_tool(self, server_id: int, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on a specific MCP server"""
        if server_id not in self.connected_servers:
            return {"error": f"Server {server_id} not connected"}
        
        server = self.connected_servers[server_id]
        
        try:
            # Use Express API as MCP proxy
            mcp_request = {
                "server_id": server_id,
                "tool_name": tool_name, 
                "params": params
            }
            
            response = requests.post(
                'http://localhost:5000/api/mcp/call-tool',
                json=mcp_request,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return {
                        "success": True,
                        "content": result.get('result', 'Operation completed'),
                        "server": server['name']
                    }
                else:
                    return {
                        "error": result.get('error', 'Unknown error'),
                        "server": server['name']
                    }
            else:
                return {
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "server": server['name']
                }
                
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name} on server {server_id}: {e}")
            return {"error": str(e), "server": server['name']}
    
    def get_connected_servers(self) -> List[Dict]:
        """Get list of connected servers"""
        return list(self.connected_servers.values())

async def load_agent_config(user_id: int = 1) -> Dict[str, Any]:
    """Load agent configuration from database"""
    try:
        response = requests.get(f'http://localhost:5000/api/agent-configs/active', timeout=5)
        if response.status_code == 200:
            config_data = response.json()
            return {
                "name": config_data.get("name", "Voice Assistant"),
                "instructions": config_data.get("instructions", "You are a helpful voice assistant with access to external tools and services."),
                "voice": config_data.get("voice", "nova"),
                "temperature": config_data.get("temperature", 0.8)
            }
    except Exception as e:
        logger.error(f"Failed to load agent config: {e}")
    
    return {
        "name": "Voice Assistant", 
        "instructions": "You are a helpful voice assistant with access to external tools and services.",
        "voice": "nova",
        "temperature": 0.8
    }

# Dynamic function tools that use the MCP manager
@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    global _dynamic_mcp_manager
    logger.info(f"Function called: search_web(query='{query}')")
    
    if not _dynamic_mcp_manager:
        return "MCP integration not available. Please try again later."
    
    # Find internet/search server
    for server_id, server in _dynamic_mcp_manager.connected_servers.items():
        if any(keyword in server['name'].lower() for keyword in ['internet', 'search', 'web']):
            logger.info(f"Using MCP server '{server['name']}' for web search")
            result = await _dynamic_mcp_manager.call_mcp_tool(
                server_id=server_id,
                tool_name="search",
                params={"query": query}
            )
            
            if result.get("success"):
                content = result.get("content", "Search completed")
                logger.info(f"Web search successful: {content[:100]}...")
                return content
            else:
                error = result.get("error", "Search failed")
                logger.error(f"Web search failed: {error}")
                return f"Search failed: {error}"
    
    return "No web search service available. Please configure an internet access MCP server."

@function_tool  
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Zapier MCP integration."""
    global _dynamic_mcp_manager
    logger.info(f"Function called: send_email(to='{to}', subject='{subject}')")
    
    if not _dynamic_mcp_manager:
        return "Email service not available. Please try again later."
    
    # Find email/zapier server
    for server_id, server in _dynamic_mcp_manager.connected_servers.items():
        if any(keyword in server['name'].lower() for keyword in ['email', 'zapier', 'mail']):
            logger.info(f"Using MCP server '{server['name']}' for email")
            result = await _dynamic_mcp_manager.call_mcp_tool(
                server_id=server_id,
                tool_name="send_email",
                params={"to": to, "subject": subject, "body": body}
            )
            
            if result.get("success"):
                logger.info("Email sent successfully via MCP")
                return "Email sent successfully"
            else:
                error = result.get("error", "Email send failed")
                logger.error(f"Email send failed: {error}")
                return f"Email send failed: {error}"
    
    return "No email service available. Please configure an email MCP server."

@function_tool
async def get_mcp_capabilities() -> str:
    """List available MCP tools and capabilities."""
    global _dynamic_mcp_manager
    logger.info("Function called: get_mcp_capabilities()")
    
    if not _dynamic_mcp_manager:
        return "MCP integration not available."
    
    servers = _dynamic_mcp_manager.get_connected_servers()
    if not servers:
        return "No MCP servers currently connected."
    
    capabilities = []
    for server in servers:
        capabilities.append(f"• {server['name']}: Available for tool calls")
    
    return f"Available MCP capabilities:\n" + "\n".join(capabilities)

class DynamicMCPAgent(Agent):
    """Agent with dynamic MCP integration loaded from database"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(
            instructions=f"""
            {config['instructions']}
            
            You have access to external tools and services through MCP (Model Context Protocol) servers 
            that are dynamically loaded from the database configuration.
            
            Available function tools:
            - search_web(query): Search the internet for current information
            - send_email(to, subject, body): Send emails via configured email services
            - get_mcp_capabilities(): List available MCP services and tools
            
            Guidelines for tool usage:
            - When using tools, explain what you're doing clearly
            - Confirm important actions before executing them
            - If a tool fails, acknowledge the issue and suggest alternatives
            - Always provide helpful context about results
            - Speak naturally and conversationally
            
            Be proactive in offering assistance and ask clarifying questions when needed.
            """,
            functions=[search_web, send_email, get_mcp_capabilities]
        )

async def entrypoint(ctx: JobContext):
    """Main entry point with dynamic MCP integration from database"""
    
    # Connect to LiveKit room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Initialize global MCP manager
    global _dynamic_mcp_manager
    _dynamic_mcp_manager = DynamicMCPManager()
    
    # Load MCP servers from database
    mcp_initialized = await _dynamic_mcp_manager.initialize_from_database()
    if mcp_initialized:
        servers = _dynamic_mcp_manager.get_connected_servers()
        logger.info(f"MCP integration ready with {len(servers)} servers")
    else:
        logger.warning("MCP integration failed to initialize")
    
    # Load agent configuration
    config = await load_agent_config()
    logger.info(f"Loaded agent config: {config['name']}")
    
    # Create dynamic MCP agent
    agent = DynamicMCPAgent(config=config)
    
    # Configure session components
    session = AgentSession(
        # Speech-to-Text
        stt=deepgram.STT(
            model="nova-2",
            language="en-US",
            smart_format=True
        ),
        
        # Large Language Model
        llm=openai.LLM(
            model="gpt-4o",
            temperature=config.get("temperature", 0.8)
        ),
        
        # Text-to-Speech  
        tts=openai.TTS(
            voice=config.get("voice", "nova"),
            speed=1.0
        ),
        
        # Voice Activity Detection
        vad=silero.VAD.load(
            min_silence_duration=0.5,
            min_speaking_duration=0.3
        )
    )
    
    # Start the session
    logger.info("Starting voice agent session with dynamic MCP integration...")
    await session.start(agent=agent, room=ctx.room)
    
    # Initial greeting
    await session.say(
        "Hello! I'm your voice assistant with access to various tools and services. "
        "I can help you with web searches, emails, and more. How can I assist you today?"
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))