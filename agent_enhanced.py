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

# Enhanced search function with result polling
@function_tool
async def search_web(query: str) -> str:
    """Search the web with real-time progress updates and actual results."""
    logger.info(f"FUNCTION EXECUTED: search_web({query})")
    
    try:
        # Make request with enhanced MCP proxy that polls for results
        logger.info(f"Making enhanced Express API call for search: {query}")
        
        response = requests.post(
            'http://localhost:5000/api/mcp/execute',
            json={
                "serverId": 2,  # N8N server ID from your database
                "tool": "execute_web_search",
                "params": {"query": query}
            },
            timeout=35  # Longer timeout to allow for polling
        )
        
        logger.info(f"Express API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Express API response data: {data}")
            
            if data.get("success"):
                result = data.get("result", "")
                
                # Format results nicely for voice output
                if isinstance(result, str) and len(result) > 100:
                    # Parse and format search results
                    formatted_result = format_search_results(result)
                    logger.info(f"Returning formatted search results")
                    return formatted_result
                else:
                    return result
            else:
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"Search failed: {error_msg}")
                return f"I couldn't complete the search. Error: {error_msg}"
        else:
            logger.error(f"HTTP error {response.status_code}")
            return "The search service is currently unavailable. Please try again later."
            
    except requests.Timeout:
        logger.error("Search request timed out")
        return "The search is taking longer than expected. This might be due to network issues. Please try again."
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"I encountered an error while searching: {str(e)}"

def format_search_results(result: str) -> str:
    """Format search results for better voice output."""
    try:
        # If result is JSON-like, parse it
        import json
        if result.startswith('{') or result.startswith('['):
            data = json.loads(result)
            if isinstance(data, list):
                formatted = "Here's what I found:\n\n"
                for i, item in enumerate(data[:5], 1):  # Limit to top 5
                    if isinstance(item, dict):
                        title = item.get('title', item.get('name', ''))
                        snippet = item.get('snippet', item.get('description', ''))
                        if title:
                            formatted += f"{i}. {title}\n"
                            if snippet:
                                formatted += f"   {snippet[:100]}...\n\n"
                return formatted
            elif isinstance(data, dict):
                # Handle single result
                title = data.get('title', 'Result')
                content = data.get('content', data.get('snippet', str(data)))
                return f"{title}:\n{content}"
        
        # If not JSON, try to format as text
        lines = result.split('\n')
        formatted = "Here's what I found:\n\n"
        for i, line in enumerate(lines[:5], 1):
            if line.strip():
                formatted += f"{i}. {line.strip()}\n\n"
        
        return formatted
        
    except:
        # If formatting fails, return original
        return result

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
        "systemPrompt": "You are a helpful AI assistant with web search capabilities.",
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
            tools=tools if tools is not None else []
        )
        self.config = config


async def entrypoint(ctx: JobContext):
    """Main entry point for the enhanced LiveKit agent with MCP result retrieval."""
    logger.info(f"Enhanced agent started for room: {ctx.room.name}")
    
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
    
    # Get agent configuration from REST API
    try:
        config = await get_agent_config(ctx.room.name)
        logger.info(f"Using agent config: {config.get('name', 'Default')}")
        logger.info(f"System prompt: {config.get('systemPrompt', 'Default')[:100]}...")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        config = {
            "systemPrompt": "You are a helpful AI assistant with web search capabilities.",
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

    # Initialize global MCP manager
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
        logger.info("Starting enhanced OpenAI Realtime API with MCP result retrieval")
        
        # Create assistant with enhanced search function
        assistant = Assistant(
            config=config, 
            tools=[search_web]  # Enhanced search with result polling
        )
        logger.info("Assistant created with enhanced function tools")
        
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
            instructions="Greet the user warmly and mention that you can search the web for current information."
        )
        
        logger.info("Enhanced OpenAI Realtime API agent started successfully")
        
    except Exception as e:
        logger.error(f"Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline")
        
        # Convert temperature for standard LLM
        llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
        
        # Create assistant for fallback with enhanced function tools
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
        
        logger.info("STT-LLM-TTS pipeline started successfully with enhanced MCP")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))