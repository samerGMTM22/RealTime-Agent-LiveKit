import logging
import os
import asyncio
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    Agent,
    AgentSession
)
from livekit.agents import mcp
from livekit.plugins import openai, deepgram, silero
import requests

logger = logging.getLogger("voice-agent")
load_dotenv()

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

async def load_mcp_servers_from_db(user_id: int = 1) -> List[mcp.MCPServer]:
    """Load and configure MCP servers from database using LiveKit native MCP support"""
    mcp_servers = []
    
    try:
        # Get MCP servers from Express API
        response = requests.get('http://localhost:5000/api/mcp/servers', timeout=5)
        if response.status_code == 200:
            servers_data = response.json()
            servers = servers_data if isinstance(servers_data, list) else servers_data.get('servers', [])
            
            for server in servers:
                if server.get('isActive', False):
                    server_url = server.get('url', '')
                    server_name = server.get('name', 'Unknown')
                    api_key = server.get('apiKey', '')
                    
                    if server_url:
                        try:
                            # Configure MCP server based on URL type following LiveKit patterns
                            if server_url.startswith('http'):
                                # HTTP/SSE transport for remote MCP servers
                                headers = {}
                                if api_key:
                                    headers["Authorization"] = f"Bearer {api_key}"
                                
                                mcp_server = mcp.MCPServer(
                                    url=server_url,
                                    transport="sse",
                                    name=server_name
                                )
                                
                                # Add headers if needed (check if LiveKit supports this)
                                if headers:
                                    # Store headers in server metadata for later use
                                    mcp_server._headers = headers
                                    
                            elif server_url.startswith('stdio:'):
                                # STDIO transport for local commands
                                command_str = server_url.replace('stdio:', '').strip()
                                command_parts = command_str.split()
                                
                                if len(command_parts) > 1:
                                    mcp_server = mcp.MCPServer(
                                        command=command_parts[0],
                                        args=command_parts[1:],
                                        transport="stdio",
                                        name=server_name
                                    )
                                else:
                                    mcp_server = mcp.MCPServer(
                                        command=command_str,
                                        transport="stdio",
                                        name=server_name
                                    )
                            else:
                                # Default to HTTP if no protocol specified
                                mcp_server = mcp.MCPServer(
                                    url=server_url,
                                    transport="sse",
                                    name=server_name
                                )
                            
                            mcp_servers.append(mcp_server)
                            logger.info(f"Configured MCP server: {server_name} -> {server_url}")
                            
                        except Exception as e:
                            logger.error(f"Failed to configure MCP server {server_name}: {e}")
                            continue
                    
        logger.info(f"Successfully loaded {len(mcp_servers)} MCP servers from database")
        
    except Exception as e:
        logger.error(f"Failed to load MCP servers from database: {e}")
    
    return mcp_servers

class MCPVoiceAgent(Agent):
    """Voice agent with native LiveKit MCP integration"""
    
    def __init__(self, config: Dict[str, Any], mcp_servers: List[mcp.MCPServer]):
        super().__init__(
            instructions=f"""
            {config['instructions']}
            
            You have access to external tools and services through MCP (Model Context Protocol) servers.
            
            Guidelines for tool usage:
            - When using tools, explain what you're doing clearly
            - Confirm important actions before executing them
            - If a tool fails, try alternative approaches
            - Always provide helpful context about results
            - Speak naturally and conversationally
            
            Available capabilities may include:
            - Web search and current information
            - Email and communication tools
            - File system operations
            - Database queries
            - Third-party service integrations
            
            Be proactive in offering assistance and ask clarifying questions when needed.
            """,
            mcp_servers=mcp_servers,
            allow_interruptions=True,
            min_endpointing_delay=0.5,
            max_endpointing_delay=2.0
        )

async def entrypoint(ctx: JobContext):
    """Main entry point using LiveKit native MCP integration"""
    
    # Connect to LiveKit room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Load agent configuration
    config = await load_agent_config()
    logger.info(f"Loaded agent config: {config['name']}")
    
    # Load MCP servers dynamically from database
    mcp_servers = await load_mcp_servers_from_db()
    logger.info(f"Configured {len(mcp_servers)} MCP servers")
    
    # Create voice agent with native MCP support
    agent = MCPVoiceAgent(config=config, mcp_servers=mcp_servers)
    
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
    logger.info("Starting voice agent session with native MCP integration...")
    await session.start(agent=agent, room=ctx.room)
    
    # Initial greeting
    await session.say(
        "Hello! I'm your voice assistant with access to various tools and services. "
        "I can help you with web searches, emails, and more. How can I assist you today?"
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))