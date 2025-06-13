import logging
import asyncio
from typing import Annotated
from dotenv import load_dotenv

from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    AgentSession,
    Agent,
)
from livekit.plugins import openai
from livekit.agents.llm import function_tool
import requests

logger = logging.getLogger("voice-agent")
load_dotenv()

# Store MCP servers globally for function tools
mcp_servers_config = []

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
        "systemPrompt": "You are a helpful voice AI assistant that provides music guidance and advice. You help with music practice, techniques, and general music education. Use MCP tools for current information when needed.",
        "voiceModel": "alloy",
        "temperature": 80,
        "responseLength": "medium"
    }


async def get_mcp_servers():
    """Fetch MCP server configurations from the database."""
    try:
        response = requests.get('http://localhost:5000/api/mcp/servers', timeout=5)
        if response.status_code == 200:
            servers = response.json()
            logger.info(f"Fetched {len(servers)} MCP servers from database")
            
            # Filter for active/connected servers
            active_servers = [s for s in servers if s.get('status') == 'connected']
            logger.info(f"Found {len(active_servers)} active MCP servers")
            return active_servers
    except Exception as e:
        logger.error(f"Error fetching MCP servers: {e}")
    
    return []


@function_tool
async def get_general_info():
    """Provides general information about music and voice coaching services."""
    
    logger.info("Providing general music information")
    
    return """I'm a voice AI assistant that helps with music-related questions and guidance. I can provide:
    - Music practice tips and techniques
    - Singing and vocal coaching advice
    - Recording and performance guidance
    - General music education information
    
    For specific channel or video information, you can use MCP tools for web searches."""


@function_tool
async def get_music_tips(topic: Annotated[str, "The music topic to provide advice about"]):
    """Provides music-related advice and tips for various topics like singing, recording, instruments, performance, etc."""
    
    logger.info(f"Providing music tips for topic: {topic}")
    
    music_tips = {
        "singing": "Practice proper breathing techniques, warm up your voice before singing, stay hydrated, and record yourself to hear areas for improvement.",
        "recording": "Use a good quality microphone, record in a quiet space with minimal echo, and monitor your audio levels to avoid clipping.",
        "guitar": "Start with basic chords, practice regularly even if just for 15 minutes daily, and use a metronome to develop timing.",
        "performance": "Practice performing in front of others, connect with your audience through eye contact and emotion, and prepare thoroughly to build confidence.",
        "piano": "Focus on proper hand posture, start with scales and simple songs, and practice both hands separately before combining them.",
        "drums": "Start with basic beats, use a metronome to develop timing, and practice rudiments to build coordination."
    }
    
    tip = music_tips.get(topic.lower(), f"For {topic}, focus on consistent practice, proper technique, and listening to professionals in that area.")
    return f"Music tip for {topic}: {tip}"


@function_tool
async def suggest_learning_resources(interest: Annotated[str, "The user's musical interest or area they want to learn about"]):
    """Suggests learning resources and practice approaches for musical interests."""
    
    logger.info(f"Suggesting learning resources for interest: {interest}")
    
    suggestions = {
        "vocal": "Focus on breath control exercises, scales practice, and recording yourself to track progress. Consider working with a vocal coach.",
        "recording": "Start with basic home recording setups - a good USB microphone, audio interface, and DAW software like Reaper or Pro Tools.",
        "performance": "Practice performing for friends and family first, work on stage presence, and consider joining local open mic nights.",
        "songwriting": "Study song structures, practice writing lyrics daily, and analyze songs you admire to understand composition techniques.",
        "instruments": "Establish consistent daily practice routines, use metronomes for timing, and consider online tutorials or local teachers."
    }
    
    suggestion = suggestions.get(interest.lower(), f"For {interest}, focus on consistent practice, proper technique, and connecting with other musicians in your area.")
    return f"Learning suggestion: {suggestion}"


@function_tool
async def search_web(query: Annotated[str, "The search query to find current information"]):
    """Search the web for current information using MCP internet access tools."""
    
    logger.info(f"Searching web for: {query}")
    
    global mcp_servers_config
    
    if not mcp_servers_config:
        logger.warning("MCP servers not configured")
        return "I don't currently have access to web search capabilities. Please ensure MCP tools are properly configured."
    
    try:
        # Make API call to MCP tools for web search
        response = requests.post('http://localhost:5000/api/mcp/execute', 
                               json={'tool': 'web_search', 'query': query}, 
                               timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('results'):
                return f"Search results for '{query}': {data['results']}"
        
        logger.warning("MCP web search unavailable")
        return "I don't currently have access to web search capabilities. Please ensure MCP tools are properly configured."
        
    except Exception as e:
        logger.error(f"Error accessing MCP tools: {e}")
        return "I'm unable to perform web searches right now. The MCP integration may need to be configured."


class GiveMeTheMicAgent(Agent):
    def __init__(self, config: dict):
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        super().__init__(instructions=system_prompt)
        self.config = config

    async def on_enter(self):
        """Called when the agent enters the session - generates initial greeting"""
        logger.info("Agent entering session, generating initial greeting")
        await self.session.generate_reply(
            instructions="Greet the user warmly and introduce yourself as the Give Me the Mic assistant. Ask how you can help them with music today."
        )


async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent."""
    logger.info(f"Starting agent for room: {ctx.room.name}")
    
    # Get agent configuration from database
    config = await get_agent_config(ctx.room.name)
    logger.info(f"Using agent config: {config.get('name', 'Default')}")
    
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
    # Convert temperature from percentage (0-100) to decimal (0.6-1.2)
    temp_raw = config.get("temperature", 80)
    temperature = max(0.6, min(1.2, float(temp_raw) / 100.0))
    
    logger.info(f"Voice: {voice}, Temperature: {temperature}")

    # Initialize MCP servers
    global mcp_servers_config
    mcp_servers_config = await get_mcp_servers()
    
    if mcp_servers_config:
        logger.info(f"MCP servers ready for use: {len(mcp_servers_config)} servers")
    else:
        logger.info("Agent will run without MCP servers")

    # Connect to the room
    await ctx.connect()

    # Create agent session with proper configuration
    try:
        logger.info("Attempting OpenAI Realtime API connection")
        
        # Try OpenAI Realtime API first
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                voice=voice,
                temperature=temperature,
                model="gpt-4o-realtime-preview"
            ),
        )
        
        logger.info("OpenAI Realtime API session created")
        
        # Create agent with function tools
        agent = GiveMeTheMicAgent(config)
        
        await session.start(
            agent=agent,
            room=ctx.room,
        )
        
        logger.info("OpenAI Realtime API session started successfully")
        
    except Exception as e:
        logger.error(f"OpenAI Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline")
        
        # Fallback to STT-LLM-TTS pipeline
        try:
            session = AgentSession(
                stt=openai.STT(model="whisper-1"),
                llm=openai.LLM(
                    model="gpt-4o-mini",
                    temperature=temperature,
                ),
                tts=openai.TTS(voice=voice),
            )
            
            # Create agent with function tools
            agent = GiveMeTheMicAgent(config)
            
            await session.start(
                agent=agent,
                room=ctx.room,
            )
            
            logger.info("STT-LLM-TTS pipeline session started successfully")
            
        except Exception as fallback_e:
            logger.error(f"Fallback pipeline also failed: {fallback_e}")
            raise
    
    logger.info("Give Me the Mic agent is running and ready for voice interactions")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))