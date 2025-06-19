"""Final Working LiveKit Voice Agent with MCP Job Polling Integration"""
import asyncio
import logging
import os
import sys
import httpx
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Add the workspace root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, llm, AgentSession
from livekit.plugins import openai, silero

# Import MCP integration
from mcp_integration.storage import PostgreSQLStorage
from mcp_integration.universal_manager import UniversalMCPDispatcher

logger = logging.getLogger("voice-agent")
load_dotenv()

# Global MCP dispatcher
_mcp_dispatcher = None

def format_search_results(result: str) -> str:
    """Format search results for better voice output."""
    try:
        import json
        if result.startswith('{') or result.startswith('['):
            data = json.loads(result)
            if isinstance(data, list):
                formatted = "Here's what I found: "
                for i, item in enumerate(data[:3], 1):  # Limit to top 3 for voice
                    if isinstance(item, dict):
                        title = item.get('title', item.get('name', ''))
                        snippet = item.get('snippet', item.get('description', ''))
                        if title:
                            formatted += f"{i}. {title}. "
                            if snippet:
                                formatted += f"{snippet[:100]}... "
                return formatted
        
        # Format as text with line limits
        lines = result.split('\n')
        formatted = "Here's what I found: "
        for i, line in enumerate(lines[:3], 1):
            if line.strip():
                formatted += f"{i}. {line.strip()[:100]}... "
        return formatted
    except:
        return result[:300] + "..." if len(result) > 300 else result

@llm.ai_callable()
async def search_web(query: str) -> str:
    """Search the web for current information using MCP job polling architecture."""
    global _mcp_dispatcher
    
    logger.info(f"SEARCH INITIATED: {query}")
    
    # Fallback to direct API call if MCP dispatcher not available
    if not _mcp_dispatcher:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'http://localhost:5000/api/mcp/execute',
                    json={"serverId": 2, "tool": "execute_web_search", "params": {"query": query}},
                    timeout=35
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        result = data.get("result", "")
                        return format_search_results(result)
                
                return "Search completed but no results were returned. The system might be processing your request."
        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"I encountered an error while searching: {str(e)[:100]}. Please try again."
    
    # Use MCP dispatcher for job polling
    try:
        tools = await _mcp_dispatcher.get_available_tools()
        search_tools = [t for t in tools if 'search' in t['name'].lower()]
        
        if search_tools:
            tool_name = search_tools[0]['name']
            result = await _mcp_dispatcher.execute_tool(
                tool_name=tool_name,
                params={"query": query},
                timeout=35
            )
            
            if result:
                formatted = format_search_results(str(result))
                logger.info(f"SEARCH COMPLETED: {query}")
                return formatted
        
        return "Search tools are not currently available. Please try again in a moment."
        
    except Exception as e:
        logger.error(f"MCP search error: {e}")
        return f"Search encountered an issue: {str(e)[:100]}. Please try rephrasing your query."

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
        "systemPrompt": "You are a helpful AI assistant with access to web search capabilities. You can search for current information to help answer questions.",
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

    # Initialize global MCP dispatcher
    global _mcp_dispatcher
    logger.info("Initializing MCP job polling system...")
    
    try:
        storage = PostgreSQLStorage()
        _mcp_dispatcher = UniversalMCPDispatcher(storage)
        await _mcp_dispatcher.initialize_tools(user_id=1)
        
        available_tools = await _mcp_dispatcher.get_available_tools()
        logger.info(f"MCP system ready with {len(available_tools)} tools available")
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP system: {e}")
        _mcp_dispatcher = None

    # STT-LLM-TTS pipeline with MCP function tools
    try:
        logger.info("Starting STT-LLM-TTS pipeline with MCP integration...")
        
        # Convert temperature for standard LLM
        llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
        
        # Create agent session with proper configuration
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(model="whisper-1"),
            llm=openai.LLM(
                model="gpt-4o",
                temperature=llm_temp,
            ),
            tts=openai.TTS(model="tts-1", voice=voice),
        )

        # Start the session (search_web function automatically available via @llm.ai_callable decorator)
        await session.start(ctx.room)
        logger.info("STT-LLM-TTS pipeline with MCP integration started successfully")
        
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