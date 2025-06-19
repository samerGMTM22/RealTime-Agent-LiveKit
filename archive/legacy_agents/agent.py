import logging
import os
import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv

# Add the workspace root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, llm, AgentSession
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero
import requests
import time
import httpx

# Import enhanced MCP integration with job polling
from mcp_integration.storage import PostgreSQLStorage
from mcp_integration.universal_manager import UniversalMCPDispatcher

# Global MCP dispatcher for job polling
_mcp_dispatcher = None

logger = logging.getLogger("voice-agent")
load_dotenv()

def format_search_results(result: str) -> str:
    """Format search results for better voice output."""
    try:
        # If result is JSON-like, parse it
        import json
        if result.startswith('{') or result.startswith('['):
            data = json.loads(result)
            if isinstance(data, list):
                formatted = "Here's what I found:\n\n"
                for i, item in enumerate(data[:3], 1):  # Limit to top 3 for voice
                    if isinstance(item, dict):
                        title = item.get('title', item.get('name', ''))
                        snippet = item.get('snippet', item.get('description', ''))
                        if title:
                            formatted += f"{i}. {title}\n"
                            if snippet:
                                formatted += f"   {snippet[:80]}...\n\n"
                return formatted
            elif isinstance(data, dict):
                title = data.get('title', 'Result')
                content = data.get('content', data.get('snippet', str(data)))
                return f"{title}: {content[:200]}..."
        
        # If not JSON, format as text
        lines = result.split('\n')
        formatted = "Here's what I found: "
        for i, line in enumerate(lines[:3], 1):
            if line.strip():
                formatted += f"{i}. {line.strip()[:100]}... "
        
        return formatted
        
    except:
        # If formatting fails, return truncated original
        return result[:300] + "..." if len(result) > 300 else result

# Enhanced MCP function tools with job polling architecture
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
            formatted_result = format_search_results(result)
            logger.info(f"SEARCH COMPLETED: {query}")
            return formatted_result
        else:
            return "I completed the search but didn't receive any results. The search might still be processing."
            
    except asyncio.TimeoutError:
        logger.error(f"Search timed out for query: {query}")
        return "The search is taking longer than expected. This might be due to high server load. Please try again in a moment."
    except Exception as e:
        logger.error(f"Search error for query '{query}': {e}")
        return f"I encountered an error while searching: {str(e)[:100]}. Please try rephrasing your query."

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


class Assistant:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.name = config.get('name', 'AI Assistant')
    
    @llm.ai_callable()
    async def get_general_info(self) -> str:
        """Provides general information about the assistant."""
        return f"I'm {self.name} and I'm here to help you with any questions you have."






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

    # Initialize global MCP dispatcher with job polling architecture
    global _mcp_dispatcher
    logger.info("Initializing MCP job polling system...")
    
    try:
        storage = PostgreSQLStorage()
        _mcp_dispatcher = UniversalMCPDispatcher(storage)
        await _mcp_dispatcher.initialize_tools(user_id=1)
        
        available_tools = await _mcp_dispatcher.get_available_tools()
        logger.info(f"MCP system ready with {len(available_tools)} tools available")
        
        # Run health checks
        health_status = await _mcp_dispatcher.health_check_all_servers()
        connected_count = len([s for s in health_status.values() if s])
        logger.info(f"Connected to {connected_count} MCP servers")
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP job polling system: {e}")
        _mcp_dispatcher = None

    try:
        logger.info("Attempting OpenAI Realtime API")
        
        # Create assistant
        assistant = Assistant(config=config)
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