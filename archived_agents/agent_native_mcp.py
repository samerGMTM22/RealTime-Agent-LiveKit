import logging
import os
import asyncio
import time
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    llm,
    mcp
)
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import openai
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

async def load_mcp_servers(user_id: int = 1) -> List[mcp.MCPServer]:
    """Load and configure MCP servers from database"""
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
                        # Configure MCP server based on URL type
                        if server_url.startswith('http'):
                            # HTTP/SSE transport
                            headers = {}
                            if api_key:
                                headers["Authorization"] = f"Bearer {api_key}"
                            
                            mcp_server = mcp.MCPServer(
                                url=server_url,
                                transport="sse",
                                name=server_name,
                                headers=headers if headers else None
                            )
                        else:
                            # Assume stdio transport for local commands
                            command_parts = server_url.split()
                            if len(command_parts) > 1:
                                mcp_server = mcp.MCPServer(
                                    command=command_parts[0],
                                    args=command_parts[1:],
                                    transport="stdio",
                                    name=server_name
                                )
                            else:
                                mcp_server = mcp.MCPServer(
                                    command=server_url,
                                    transport="stdio",
                                    name=server_name
                                )
                        
                        mcp_servers.append(mcp_server)
                        logger.info(f"Configured MCP server: {server_name} ({server_url})")
                    
        logger.info(f"Loaded {len(mcp_servers)} MCP servers")
        
    except Exception as e:
        logger.error(f"Failed to load MCP servers: {e}")
        # Add fallback servers if database is unavailable
        fallback_servers = [
            mcp.MCPServer(
                url="https://api.zapier.com/v1/mcp",
                transport="sse",
                name="Zapier",
                headers={"Authorization": f"Bearer {os.environ.get('ZAPIER_API_KEY', '')}"}
            ),
            mcp.MCPServer(
                url="https://mcp-server-internet.example.com/sse",
                transport="sse", 
                name="InternetAccess"
            )
        ]
        mcp_servers.extend(fallback_servers)
        logger.info(f"Using {len(fallback_servers)} fallback MCP servers")
    
    return mcp_servers

async def entrypoint(ctx: JobContext):
    """Main entry point with proper MultimodalAgent setup following expert guidelines."""
    
    # Connect to LiveKit room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Load agent configuration
    config = await load_agent_config()
    logger.info(f"Loaded agent config: {config['name']}")
    
    # Load MCP servers dynamically from database
    mcp_servers = await load_mcp_servers()
    logger.info(f"Configured {len(mcp_servers)} MCP servers")
    
    # Create multimodal agent with native MCP support
    agent = MultimodalAgent(
        model=openai.realtime.RealtimeModel(
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
            voice=config.get("voice", "nova"),
            temperature=config.get("temperature", 0.8),
            modalities=["text", "audio"],
            turn_detection=openai.realtime.ServerVAD(
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=500
            )
        ),
        mcp_servers=mcp_servers
    )
    
    # Add event handlers for function calls
    @agent.on("function_calls")
    def on_function_calls(fnc_call_infos: List[llm.FunctionCallInfo]):
        """Handle function call events"""
        for fnc_call in fnc_call_infos:
            logger.info(f"Function called: {fnc_call.function_info.name} with args: {fnc_call.arguments}")
    
    @agent.on("function_calls_finished") 
    def on_function_calls_finished(called_fncs: List[llm.CalledFunction]):
        """Handle function call completion events"""
        for called_fnc in called_fncs:
            logger.info(f"Function completed: {called_fnc.function_info.name}")
            if called_fnc.result:
                logger.info(f"Function result: {str(called_fnc.result)[:200]}...")
    
    # Start the agent
    logger.info("Starting MultimodalAgent with native MCP integration...")
    agent.start(ctx.room)
    
    # Send initial greeting
    await asyncio.sleep(1)  # Brief delay to ensure connection is stable
    await agent.say("Hello! I'm your voice assistant with access to various tools and services. How can I help you today?")
    
    # Keep the agent running
    await agent.aclose()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))