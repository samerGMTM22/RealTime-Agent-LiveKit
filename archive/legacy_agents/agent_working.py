"""Working LiveKit Voice Agent with MCP Job Polling Integration"""
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
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, llm, AgentSession
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero
import httpx

# Import enhanced MCP integration with job polling
from mcp_integration.storage import PostgreSQLStorage
from mcp_integration.universal_manager import UniversalMCPDispatcher

# Global MCP dispatcher for job polling
_mcp_dispatcher = None

logger = logging.getLogger("voice-agent")
load_dotenv()

@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP job polling architecture."""
    global _mcp_dispatcher
    
    logger.info(f"SEARCH INITIATED: {query}")
    
    if not _mcp_dispatcher:
        logger.warning("MCP dispatcher not initialized")
        return "Search system not initialized. Please wait a moment and try again."
    
    try:
        # Get available search tools
        available_tools = await _mcp_dispatcher.get_available_tools()
        search_tools = [t for t in available_tools if 'search' in t['name'].lower() or 'web' in t['name'].lower()]
        
        if not search_tools:
            logger.warning("No search tools available")
            return "No web search tools are currently available. Please check your MCP server configuration."
        
        # Use the first available search tool
        search_tool = search_tools[0]
        tool_name = search_tool['name']
        
        logger.info(f"Using search tool: {tool_name}")
        
        # Execute the search with job polling
        result = await _mcp_dispatcher.execute_tool(
            tool_name=tool_name,
            params={"query": query},
            timeout=35  # Extended timeout for polling
        )
        
        if result:
            # Format result for voice output
            formatted = str(result)
            if len(formatted) > 500:
                formatted = formatted[:500] + "... I can provide more details if needed."
            
            logger.info(f"SEARCH COMPLETED: {query}")
            return formatted
        else:
            return "I completed the search but didn't receive any results. The search might still be processing."
            
    except asyncio.TimeoutError:
        logger.error(f"Search timed out for query: {query}")
        return "The search is taking longer than expected. This might be due to high server load. Please try again in a moment."
    except Exception as e:
        logger.error(f"Search error for query '{query}': {e}")
        return f"I encountered an error while searching: {str(e)[:100]}. Please try rephrasing your query."

async def get_agent_config(room_name: str):
    """Fetch agent configuration from the database based on room name."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/api/agent-configs/active")
            if response.status_code == 200:
                config = response.json()
                logger.info(f"Fetched config from database: {config['name']}")
                return config
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
    
    # Fallback configuration
    return {
        "systemPrompt": "You are a helpful AI assistant with access to web search capabilities.",
        "voiceModel": "alloy",
        "temperature": 80,
        "responseLength": "medium"
    }

async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent with MCP job polling integration."""
    logger.info(f"Agent started for room: {ctx.room.name}")
    
    # Connect to room with audio-only subscription
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Ensure audio track subscription
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind == "audio":
            publication.set_subscribed(True)
            logger.info(f"Subscribed to audio track from {participant.identity}")
    
    # Wait for a participant to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")
    
    # Get agent configuration
    config = await get_agent_config(ctx.room.name)
    logger.info(f"Using agent config: {config.get('name', 'Default')}")
    
    # Map voice model names to OpenAI voice options
    voice_mapping = {
        "alloy": "alloy", "echo": "echo", "fable": "fable",
        "onyx": "onyx", "nova": "nova", "shimmer": "shimmer", "coral": "coral"
    }
    
    voice = voice_mapping.get(config.get("voiceModel", "alloy"), "alloy")
    temp_raw = config.get("temperature", 80)
    realtime_temp = max(0.6, min(1.2, 0.6 + (float(temp_raw) / 100.0) * 0.6))
    
    logger.info(f"Voice: {voice}, Temperature: {realtime_temp}")

    # Initialize global MCP dispatcher with job polling architecture
    global _mcp_dispatcher
    logger.info("Initializing MCP job polling system...")
    
    try:
        storage = PostgreSQLStorage()
        _mcp_dispatcher = UniversalMCPDispatcher(storage)
        await _mcp_dispatcher.initialize_tools(user_id=1)
        
        available_tools = await _mcp_dispatcher.get_available_tools()
        logger.info(f"MCP system ready with {len(available_tools)} tools available")
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP job polling system: {e}")
        _mcp_dispatcher = None

    try:
        logger.info("Starting STT-LLM-TTS pipeline with MCP integration")
        
        # Convert temperature for standard LLM
        llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
        
        # Create STT-LLM-TTS pipeline with MCP function tools
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(model="whisper-1"),
            llm=openai.LLM(model="gpt-4o", temperature=llm_temp),
            tts=openai.TTS(model="tts-1", voice=voice),
        )
        
        # The search_web function tool is automatically available due to @function_tool decorator

        await session.start(
            room=ctx.room,
        )
        
        logger.info("STT-LLM-TTS pipeline with MCP polling started successfully")

    except Exception as e:
        logger.error(f"Failed to start agent session: {e}")
        # Keep the connection alive even if session fails
        await asyncio.sleep(60)

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )