import logging
import os
import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Add the workspace root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, llm, AgentSession, Agent
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero
import requests
import time

# Import simplified MCP integration 
from mcp_integration.simple_client import SimpleMCPManager

# Global MCP manager to be accessible by function tools
_mcp_manager = None

logger = logging.getLogger("voice-agent")
load_dotenv()

# Define function tools at module level (expert's recommendation)
@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    logger.info(f"FUNCTION ACTUALLY EXECUTED: search_web({query})")
    execution_time = time.time()
    
    try:
        # Use Express API with enhanced polling mechanism for actual results
        logger.info(f"Making Express API call for search: {query}")
        response = requests.post('http://localhost:5000/api/mcp/execute', 
                               json={"tool": "search", "params": {"query": query}}, 
                               timeout=30)  # Extended timeout for polling mechanism
        logger.info(f"Express API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Express API response data: {data}")
            if data.get("success"):
                result = data.get("result", "")
                
                # Check if we got actual results or just acknowledgment
                if "accepted" in result.lower() and len(result) < 100:
                    logger.warning("Received acknowledgment but no actual search results")
                    return f"I've initiated a web search for '{query}'. The search service processed the request but results may take longer to retrieve."
                else:
                    # We got actual results from polling mechanism
                    logger.info(f"FUNCTION COMPLETED at {execution_time}: Got actual search results")
                    return result
            else:
                error_msg = data.get('error', 'Unknown error')
                if "timeout" in error_msg.lower():
                    return f"Search for '{query}' is taking longer than expected. The search was initiated but results may be available shortly."
                else:
                    return f"Search failed: {error_msg}"
        else:
            return "Search service unavailable"
            
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return f"Search failed: {str(e)}"

# Email function temporarily disabled to prevent SSE connection loops
# @function_tool
async def send_email_disabled(to: str, subject: str, body: str) -> str:
    """Send an email via Zapier MCP integration - TEMPORARILY DISABLED."""
    logger.info(f"Email function called but disabled to prevent agent blocking")
    return "Email functionality is temporarily disabled while resolving connection issues. Your request has been noted."


async def get_agent_config(room_name: str):
    """Fetch agent configuration from the database based on room name."""
    try:
        # Default to agent config ID 1 for now
        agent_config_id = 1
        
        # Make request to get agent configuration
        response = requests.get(f'http://localhost:5000/api/agent-configs/{agent_config_id}', timeout=5)
        if response.status_code == 200:
            config = response.json()
            logger.info(f"Fetched config from database: {config['name']}")
            return config
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
    
    # Fallback configuration
    return {
        "systemPrompt": "You are a helpful AI assistant.",
        "voiceModel": "alloy",
        "temperature": 80,
        "responseLength": "medium"
    }


class Assistant(Agent):
    def __init__(self, config: dict, tools: list = None) -> None:
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        # Pass tools to parent Agent constructor
        super().__init__(
            instructions=system_prompt,
            tools=tools if tools is not None else []  # Pass the tools here!
        )
        self.config = config






async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent following expert guidelines."""
    logger.info(f"Agent started for room: {ctx.room.name}")
    
    # Connect to room with audio-only subscription
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Ensure audio track subscription as recommended by expert
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind == "audio":
            publication.set_subscribed(True)
            logger.info(f"Subscribed to audio track from {participant.identity}")
    
    # Wait for a participant to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")
    
    # Get agent configuration from REST API
    try:
        config = await get_agent_config(ctx.room.name)
        logger.info(f"Using agent config: {config.get('name', 'Default')}")
        logger.info(f"System prompt: {config.get('systemPrompt', 'Default')[:100]}...")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        config = {
            "systemPrompt": "You are a helpful AI assistant.",
            "voiceModel": "alloy",
            "temperature": 80,
            "responseLength": "medium"
        }
    
    # Map voice model names to OpenAI voice options
    voice_mapping = {
        "alloy": "alloy",
        "echo": "echo", 
        "fable": "fable",
        "onyx": "onyx",
        "nova": "nova",
        "shimmer": "shimmer",
        "coral": "coral"
    }
    
    voice = voice_mapping.get(config.get("voiceModel", "alloy"), "alloy")
    temp_raw = config.get("temperature", 80)
    realtime_temp = max(0.6, min(1.2, 0.6 + (float(temp_raw) / 100.0) * 0.6))
    
    logger.info(f"Voice: {voice}, Temperature: {realtime_temp}")

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

    try:
        logger.info("Attempting OpenAI Realtime API")
        
        # Create assistant with function tools passed to constructor
        assistant = Assistant(
            config=config, 
            tools=[search_web]  # Only include working search function
        )
        logger.info("Assistant created with module-level function tools")
        
        # Create AgentSession with Realtime API
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                model="gpt-4o-realtime-preview",
                voice=voice,
                temperature=realtime_temp,
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
        
        # Generate initial greeting
        await session.generate_reply(
            instructions="Greet the user warmly and offer your assistance."
        )
        
        logger.info("OpenAI Realtime API agent started successfully")
        
    except Exception as e:
        logger.error(f"Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline")
        
        # Convert temperature for standard LLM
        llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
        
        # Create assistant for fallback with function tools
        assistant = Assistant(
            config=config,
            tools=[search_web]
        )
        
        # Create STT-LLM-TTS pipeline as fallback
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(model="whisper-1"),
            llm=openai.LLM(model="gpt-4o", temperature=llm_temp),
            tts=openai.TTS(model="tts-1", voice=voice),
        )

        await session.start(
            room=ctx.room, 
            agent=assistant
        )
        
        logger.info("STT-LLM-TTS pipeline started successfully")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))