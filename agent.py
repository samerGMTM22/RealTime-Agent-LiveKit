import logging
import os
import asyncio
from dotenv import load_dotenv

from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    VoiceAssistant,
)
from livekit.plugins import openai
from livekit.agents.llm import function_tool
import requests

logger = logging.getLogger("voice-agent")
load_dotenv()

# Store MCP client globally for function tools
mcp_client = None

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


async def initialize_mcp_client(server_configs):
    """Initialize MCP client with server configurations."""
    global mcp_client
    
    if not server_configs:
        logger.info("No MCP server configurations found")
        return None
    
    try:
        # Import MCP functionality
        from livekit.agents.mcp import MCPClient
        
        # Create MCP client instance
        mcp_client = MCPClient()
        
        # Add server configurations
        for server_config in server_configs:
            server_name = server_config.get('name', 'Unknown')
            server_url = server_config.get('url', '')
            
            if not server_url:
                logger.warning(f"No URL provided for MCP server: {server_name}")
                continue
            
            # Add server to client
            await mcp_client.add_server(server_name, server_url)
            logger.info(f"Added MCP server: {server_name}")
        
        # Initialize the client
        await mcp_client.initialize()
        logger.info("MCP client initialized successfully")
        return mcp_client
        
    except ImportError:
        logger.warning("MCP package not available - MCP features disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        return None


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
async def get_music_tips(topic: str):
    """Provides music-related advice and tips for various topics like singing, recording, instruments, performance, etc.
    
    Args:
        topic: The music topic to provide advice about (e.g., singing, recording, guitar, performance)
    """
    
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
async def suggest_learning_resources(interest: str):
    """Suggests learning resources and practice approaches for musical interests.
    
    Args:
        interest: The user's musical interest or area they want to learn about
    """
    
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
async def search_web(query: str):
    """Search the web for current information using MCP internet access tools.
    
    Args:
        query: The search query to find current information
    """
    
    logger.info(f"Searching web for: {query}")
    
    global mcp_client
    
    if not mcp_client:
        logger.warning("MCP client not available")
        return "I don't currently have access to web search capabilities. Please ensure MCP tools are properly configured."
    
    try:
        # Use MCP client to perform web search
        result = await mcp_client.call_tool("web_search", {"query": query})
        
        if result and result.get('success'):
            return f"Search results for '{query}': {result.get('content', 'No results found')}"
        else:
            return f"Unable to search for '{query}' at this time."
            
    except Exception as e:
        logger.error(f"Error using MCP web search: {e}")
        return "I'm unable to perform web searches right now. The MCP integration may need to be configured."


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

    # Initialize MCP client
    mcp_servers_config = await get_mcp_servers()
    mcp_client_instance = await initialize_mcp_client(mcp_servers_config)
    
    if mcp_client_instance:
        logger.info("MCP client ready for use")
    else:
        logger.info("Agent will run without MCP servers")

    # Connect to the room
    await ctx.connect()

    # Create voice assistant with proper configuration
    try:
        # Try OpenAI Realtime API first
        logger.info("Attempting OpenAI Realtime API connection")
        
        assistant = VoiceAssistant(
            vad=ctx.proc.userdata.get("vad", openai.realtime.RealtimeVAD()),
            stt=openai.realtime.RealtimeSTT(),
            llm=openai.realtime.RealtimeLLM(
                model="gpt-4o-realtime-preview",
                voice=voice,
                temperature=temperature,
                instructions=config.get("systemPrompt", "You are a helpful voice AI assistant."),
            ),
            tts=openai.realtime.RealtimeTTS(),
            fnc_ctx=openai.realtime.FunctionContext(),
        )
        
        # Add function tools
        assistant.llm.register_function(get_general_info)
        assistant.llm.register_function(get_music_tips)
        assistant.llm.register_function(suggest_learning_resources)
        assistant.llm.register_function(search_web)
        
        # Start the assistant
        assistant.start(ctx.room)
        logger.info("OpenAI Realtime API session started successfully")
        
        # Generate initial greeting
        await assistant.say("Hello! I'm your Give Me the Mic voice assistant. I'm here to help you with music practice, techniques, and guidance. How can I assist you with your musical journey today?")
        
    except Exception as e:
        logger.error(f"OpenAI Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline")
        
        # Fallback to STT-LLM-TTS pipeline
        assistant = VoiceAssistant(
            vad=openai.VAD(),
            stt=openai.STT(model="whisper-1"),
            llm=openai.LLM(
                model="gpt-4o-mini",
                temperature=temperature,
            ),
            tts=openai.TTS(voice=voice),
        )
        
        # Add function tools
        assistant.llm.register_function(get_general_info)
        assistant.llm.register_function(get_music_tips)
        assistant.llm.register_function(suggest_learning_resources)
        assistant.llm.register_function(search_web)
        
        # Start the assistant
        assistant.start(ctx.room)
        logger.info("STT-LLM-TTS pipeline session started successfully")
        
        # Generate initial greeting
        await assistant.say("Hello! I'm your Give Me the Mic voice assistant. I'm here to help you with music practice, techniques, and guidance. How can I assist you with your musical journey today?")
    
    logger.info("Give Me the Mic agent is running and ready for voice interactions")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))