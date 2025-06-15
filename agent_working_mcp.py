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
from livekit.plugins import openai
import requests
import json

logger = logging.getLogger("voice-agent")
load_dotenv()

# Global MCP manager for function tools
_working_mcp_manager = None

class WorkingMCPManager:
    """Working MCP manager that properly integrates with database configuration"""
    
    def __init__(self):
        self.connected_servers: Dict[int, Dict] = {}
        self.server_capabilities: Dict[int, List[str]] = {}
        
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
                        
                        # Map server capabilities based on name
                        capabilities = []
                        name_lower = server_name.lower()
                        if any(keyword in name_lower for keyword in ['internet', 'web', 'search']):
                            capabilities.extend(['search', 'web_search'])
                        if any(keyword in name_lower for keyword in ['email', 'zapier', 'mail']):
                            capabilities.extend(['send_email', 'email'])
                        if any(keyword in name_lower for keyword in ['file', 'filesystem']):
                            capabilities.extend(['read_file', 'write_file'])
                        
                        self.server_capabilities[server_id] = capabilities
                        connected_count += 1
                        logger.info(f"Registered MCP server: {server_name} (ID: {server_id}) with capabilities: {capabilities}")
                
                logger.info(f"Successfully initialized {connected_count} MCP servers from database")
                return connected_count > 0
                
        except Exception as e:
            logger.error(f"Failed to initialize MCP servers from database: {e}")
            return False
        
        return False
    
    async def execute_tool_via_api(self, server_id: int, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via the Express API MCP proxy"""
        try:
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
                        "server": result.get('server', 'Unknown')
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get('error', 'Unknown error'),
                        "server": result.get('server', 'Unknown')
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "server": f"Server {server_id}"
                }
                
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name} on server {server_id}: {e}")
            return {"success": False, "error": str(e), "server": f"Server {server_id}"}
    
    def find_server_for_tool(self, tool_name: str) -> Optional[int]:
        """Find the best server for a given tool"""
        for server_id, capabilities in self.server_capabilities.items():
            if tool_name in capabilities:
                return server_id
        return None
    
    def get_connected_servers(self) -> List[Dict]:
        """Get list of connected servers"""
        return list(self.connected_servers.values())
    
    def get_tool_name_for_server(self, server_id: int, function_type: str) -> str:
        """Get the actual N8N tool name for a server and function type"""
        if server_id in self.connected_servers:
            server = self.connected_servers[server_id]
            
            # Check if the server has tool mappings in metadata
            metadata = server.get('metadata', {})
            tool_mappings = metadata.get('tool_mappings', {})
            
            if function_type in tool_mappings:
                return tool_mappings[function_type]
            
            # Check if the server has tools array with actual N8N names
            tools = server.get('tools', [])
            if tools:
                # Try to find a tool that matches the function type
                for tool in tools:
                    if isinstance(tool, dict):
                        tool_name = tool.get('name', '')
                        if function_type in tool_name.lower() or 'search' in tool_name.lower():
                            return tool_name
                    elif isinstance(tool, str):
                        if function_type in tool.lower() or 'search' in tool.lower():
                            return tool
        
        # Fallback to common N8N tool names based on Gemini's research
        fallback_names = {
            'search': 'execute_web_search',
            'email': 'send_email', 
            'web_search': 'execute_web_search',
            'internet_search': 'execute_web_search'
        }
        
        return fallback_names.get(function_type, function_type)
    


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

# Working function tools that properly use the MCP manager
@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    global _working_mcp_manager
    logger.info(f"Function called: search_web(query='{query}')")
    
    if not _working_mcp_manager:
        return "MCP integration not available. Please try again later."
    
    # Find server that can handle search
    server_id = _working_mcp_manager.find_server_for_tool('search')
    if not server_id:
        return "No web search service available. Please configure an internet access MCP server."
    
    # Use the best available tool name for N8N search functionality
    tool_name = "execute_web_search"  # Primary N8N tool name from Gemini's research
    
    logger.info(f"Using MCP server ID {server_id} to call tool '{tool_name}'")
    result = await _working_mcp_manager.execute_tool_via_api(
        server_id=server_id,
        tool_name=tool_name,
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

@function_tool  
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Zapier MCP integration."""
    global _working_mcp_manager
    logger.info(f"Function called: send_email(to='{to}', subject='{subject}')")
    
    if not _working_mcp_manager:
        return "Email service not available. Please try again later."
    
    # Find server that can handle email
    server_id = _working_mcp_manager.find_server_for_tool('send_email')
    if not server_id:
        return "No email service available. Please configure an email MCP server."
    
    logger.info(f"Using MCP server ID {server_id} for email")
    result = await _working_mcp_manager.execute_tool_via_api(
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

@function_tool
async def get_mcp_status() -> str:
    """Get status of available MCP tools and capabilities."""
    global _working_mcp_manager
    logger.info("Function called: get_mcp_status()")
    
    if not _working_mcp_manager:
        return "MCP integration not available."
    
    servers = _working_mcp_manager.get_connected_servers()
    if not servers:
        return "No MCP servers currently connected."
    
    status_lines = ["Available MCP capabilities:"]
    for server in servers:
        server_id = server['id']
        capabilities = _working_mcp_manager.server_capabilities.get(server_id, [])
        status_lines.append(f"• {server['name']}: {', '.join(capabilities) if capabilities else 'No specific capabilities'}")
    
    return "\n".join(status_lines)

class WorkingMCPAgent(Agent):
    """Agent with working dynamic MCP integration loaded from database"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(
            instructions=f"""
            {config['instructions']}
            
            You have access to external tools and services through MCP (Model Context Protocol) servers 
            that are dynamically loaded from the database configuration.
            
            Available function tools:
            - search_web(query): Search the internet for current information
            - send_email(to, subject, body): Send emails via configured email services
            - get_mcp_status(): Check available MCP services and capabilities
            
            Guidelines for tool usage:
            - When using tools, explain what you're doing clearly
            - Confirm important actions before executing them
            - If a tool fails, acknowledge the issue and suggest alternatives
            - Always provide helpful context about results
            - Speak naturally and conversationally
            
            Be proactive in offering assistance and ask clarifying questions when needed.
            """,
            functions=[search_web, send_email, get_mcp_status]
        )

async def entrypoint(ctx: JobContext):
    """Main entry point with working dynamic MCP integration from database"""
    
    # Connect to LiveKit room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Initialize global MCP manager
    global _working_mcp_manager
    _working_mcp_manager = WorkingMCPManager()
    
    # Load MCP servers from database
    mcp_initialized = await _working_mcp_manager.initialize_from_database()
    if mcp_initialized:
        servers = _working_mcp_manager.get_connected_servers()
        logger.info(f"MCP integration ready with {len(servers)} servers")
        for server in servers:
            logger.info(f"  - {server['name']}: {server['url']}")
    else:
        logger.warning("MCP integration failed to initialize")
    
    # Load agent configuration
    config = await load_agent_config()
    logger.info(f"Loaded agent config: {config['name']}")
    
    # Create working MCP agent
    agent = WorkingMCPAgent(config=config)
    
    # Configure session components
    session = AgentSession(
        # Large Language Model
        llm=openai.LLM(
            model="gpt-4o",
            temperature=config.get("temperature", 0.8)
        ),
        
        # Text-to-Speech  
        tts=openai.TTS(
            voice=config.get("voice", "nova"),
            speed=1.0
        )
    )
    
    # Start the session
    logger.info("Starting voice agent session with working MCP integration...")
    await session.start(agent=agent, room=ctx.room)
    
    # Initial greeting
    await session.say(
        "Hello! I'm your voice assistant with access to various tools and services. "
        "I can help you with web searches, emails, and more. How can I assist you today?"
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))