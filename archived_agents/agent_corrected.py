import logging
import os
import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
import requests

# Add the workspace root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, llm, AgentSession, Agent
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero

# Import simplified MCP integration 
from mcp_integration.simple_client import SimpleMCPManager

logger = logging.getLogger("voice-agent")
load_dotenv()

# Global MCP manager for module-level function tools
_mcp_manager = None

# Module-level function tools (expert's recommendation)
@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    logger.info(f"FUNCTION ACTUALLY EXECUTED: search_web({query})")
    execution_time = time.time()
    
    try:
        global _mcp_manager
        if _mcp_manager:
            # Try to execute via MCP manager
            for server_id, client in _mcp_manager.connected_servers.items():
                if "internet" in client.name.lower():
                    result = await _mcp_manager.call_tool(server_id, "search", {"query": query})
                    if "error" not in result:
                        logger.info(f"FUNCTION COMPLETED at {execution_time}: MCP search successful")
                        return result.get("content", "Search completed successfully")
        
        # Fallback to Express API
        logger.info(f"Making Express API call for search: {query}")
        response = requests.post('http://localhost:5000/api/mcp/execute', 
                               json={"tool": "search", "params": {"query": query}}, 
                               timeout=10)
        logger.info(f"Express API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Express API response data: {data}")
            if data.get("success"):
                logger.info(f"FUNCTION COMPLETED at {execution_time}: Express API successful")
                return data.get("result", "Search completed")
            else:
                return f"Search failed: {data.get('error', 'Unknown error')}"
        else:
            return "Search service unavailable"
            
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return f"Search failed: {str(e)}"

@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Zapier MCP integration."""
    logger.info(f"FUNCTION ACTUALLY EXECUTED: send_email(to={to}, subject={subject})")
    execution_time = time.time()
    
    try:
        global _mcp_manager
        if _mcp_manager:
            # Try to execute via MCP manager
            for server_id, client in _mcp_manager.connected_servers.items():
                if "zapier" in client.name.lower() or "email" in client.name.lower():
                    result = await _mcp_manager.call_tool(server_id, "send_email", 
                                                       {"to": to, "subject": subject, "body": body})
                    if "error" not in result:
                        logger.info(f"FUNCTION COMPLETED at {execution_time}: MCP email successful")
                        return "Email sent successfully via MCP"
        
        # Fallback to Express API
        logger.info(f"Making Express API call for email: {to}")
        response = requests.post('http://localhost:5000/api/mcp/execute', 
                               json={"tool": "send_email", "params": {"to": to, "subject": subject, "body": body}}, 
                               timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                logger.info(f"FUNCTION COMPLETED at {execution_time}: Express API email successful")
                return "Email sent successfully"
            else:
                return f"Email send failed: {data.get('error', 'Unknown error')}"
        else:
            return "Email service unavailable"
            
    except Exception as e:
        logger.error(f"Error in email send: {e}")
        return f"Email send failed: {str(e)}"

async def get_agent_config(room_name: str):
    """Fetch agent configuration from the database based on room name."""
    try:
        # Default to agent config ID 1 for now
        agent_config_id = 1
        
        response = requests.get(f'http://localhost:5000/api/agent-configs/{agent_config_id}')
        if response.status_code == 200:
            config = response.json()
            logger.info(f"Fetched config from database: {config.get('name', 'Unknown')}")
            return config
        else:
            logger.warning("Failed to fetch config from database, using defaults")
            return {
                "name": "Voice Assistant",
                "systemPrompt": "You are a professional customer service agent.",
                "voiceModel": "echo",
                "temperature": 102
            }
    except Exception as e:
        logger.error(f"Error loading agent config: {e}")
        return {
            "name": "Voice Assistant",
            "systemPrompt": "You are a professional customer service agent.",
            "voiceModel": "echo", 
            "temperature": 102
        }

class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        super().__init__(instructions=system_prompt)
        self.config = config

async def entrypoint(ctx: JobContext):
    """Main entry point following expert guidelines with module-level function tools."""
    
    await ctx.connect()
    
    # Get room name and fetch configuration
    room_name = ctx.room.name
    config = await get_agent_config(room_name)
    
    logger.info(f"Agent started for room: {room_name}")
    logger.info(f"Using agent config: {config.get('name', 'Unknown')}")
    logger.info(f"System prompt: {config.get('systemPrompt', 'Default')[:100]}...")
    logger.info(f"Voice: {config.get('voiceModel', 'echo')}, Temperature: {config.get('temperature', 102)/100}")

    # Initialize global MCP manager for module-level function tools
    global _mcp_manager
    logger.info("Initializing MCP integration...")
    _mcp_manager = SimpleMCPManager()
    
    try:
        mcp_servers = await _mcp_manager.initialize_user_servers(user_id=1)
        connected_count = len([s for s in mcp_servers if s.get("status") == "connected"])
        logger.info(f"Connected to {connected_count} MCP servers")
    except Exception as e:
        logger.error(f"Failed to initialize MCP servers: {e}")
        _mcp_manager = None

    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        logger.info(f"Track published: {publication.kind} from {participant.identity}")

    ctx.room.on("track_published", on_track_published)

    # Wait for participant to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    logger.info("Attempting OpenAI Realtime API")
    
    try:
        # Extract configuration values
        voice = config.get("voiceModel", "echo")
        realtime_temp = max(0.6, min(1.2, config.get("temperature", 102) / 100))
        
        # Create assistant
        assistant = Assistant(config)
        
        # Add module-level function tools to assistant
        assistant.add_function(search_web)
        assistant.add_function(send_email)
        logger.info("Module-level function tools added to assistant")
        
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                model="gpt-4o-realtime-preview",
                voice=voice,
                temperature=realtime_temp,
                instructions=config.get("systemPrompt", "You are a helpful assistant."),
            ),
            allow_interruptions=True,
            min_interruption_duration=0.5,
            min_endpointing_delay=0.5,
            max_endpointing_delay=6.0,
        )

        await session.start(
            room=ctx.room,
            agent=assistant,
        )
        
        await session.generate_reply(
            instructions="Greet the user warmly and offer your assistance."
        )
        
        logger.info("OpenAI Realtime API agent started successfully")
        
    except Exception as e:
        logger.error(f"OpenAI Realtime API failed: {e}")
        
        # Fallback to standard pipeline
        logger.info("Falling back to standard pipeline")
        
        assistant = Assistant(config)
        
        # Add module-level function tools to fallback assistant
        assistant.add_function(search_web)
        assistant.add_function(send_email)
        
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(),
            llm=openai.LLM(model="gpt-4o"),
            tts=openai.TTS(),
        )

        await session.start(agent=assistant, room=ctx.room)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))