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

# Import MCP integration as a package
from mcp_integration.manager import MCPManager
from mcp_integration.tools import MCPToolsIntegration
from mcp_integration.storage import PostgreSQLStorage

logger = logging.getLogger("voice-agent")
load_dotenv()


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


class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        super().__init__(instructions=system_prompt)
        self.config = config
        self.mcp_manager = None
        self.mcp_tools_integration = None

    async def initialize_mcp(self, user_id: int = 1):
        """Initialize MCP servers with error handling and graceful degradation"""
        try:
            logger.info("Initializing MCP integration...")
            
            # Create storage interface
            storage = PostgreSQLStorage()
            self.mcp_manager = MCPManager(storage)
            
            # Load and connect MCP servers for user
            mcp_servers = await self.mcp_manager.initialize_user_servers(user_id)
            
            if mcp_servers:
                # Build tools from MCP servers
                tools = await MCPToolsIntegration.build_livekit_tools(
                    self.mcp_manager.connected_servers
                )
                
                if tools:
                    # Add MCP tools to agent (tools are already decorated function_tool objects)
                    for tool in tools:
                        self.register_tool(tool)
                    logger.info(f"Added {len(tools)} MCP tools to agent")
                else:
                    logger.info("No MCP tools available")
            else:
                logger.info("No MCP servers connected")
            
            return mcp_servers
            
        except Exception as e:
            logger.error(f"MCP initialization failed: {e}")
            # Agent continues without MCP tools - this is graceful degradation
            return []

    @function_tool
    async def get_general_info(self):
        """Provides general information about music and voice coaching services."""
        
        logger.info("Providing general music information")
        
        return """I'm a voice AI assistant that helps with music-related questions and guidance. I can provide:
        - Music practice tips and techniques
        - Singing and vocal coaching advice
        - Recording and performance guidance
        - General music education information
        
        For specific channel or video information, you can use MCP tools for web searches."""

    @function_tool
    async def get_music_tips(self, topic: str):
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
    async def suggest_learning_resources(self, interest: str):
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
    async def search_web(self, query: str):
        """Search the web for current information using MCP internet access tools.
        
        Args:
            query: The search query to find current information
        """
        
        logger.info(f"Searching web for: {query}")
        
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
    temp_raw = config.get("temperature", 80)
    realtime_temp = max(0.6, min(1.2, 0.6 + (float(temp_raw) / 100.0) * 0.6))
    
    logger.info(f"Voice: {voice}, Temperature: {realtime_temp}")

    try:
        logger.info("Attempting OpenAI Realtime API")
        
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

        # Create assistant and start MCP initialization asynchronously
        assistant = Assistant(config)
        
        # Start MCP initialization in background (non-blocking)
        mcp_task = asyncio.create_task(assistant.initialize_mcp(user_id=1))
        
        await session.start(
            room=ctx.room,
            agent=assistant,
        )
        
        # Generate initial greeting
        await session.generate_reply(
            instructions="Greet the user warmly and offer your assistance."
        )
        
        # Wait for MCP initialization with timeout
        try:
            mcp_servers = await asyncio.wait_for(mcp_task, timeout=10.0)
            if mcp_servers:
                logger.info(f"MCP servers loaded: {len(mcp_servers)}")
                await session.generate_reply(
                    instructions=f"Inform the user that {len(mcp_servers)} external tools are now available for enhanced assistance."
                )
        except asyncio.TimeoutError:
            logger.warning("MCP initialization timed out, continuing with voice-only functionality")
        
        logger.info("OpenAI Realtime API agent started successfully")
        
    except Exception as e:
        logger.error(f"Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline")
        
        # Convert temperature for standard LLM
        llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
        
        # Create STT-LLM-TTS pipeline as fallback
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(model="whisper-1"),
            llm=openai.LLM(model="gpt-4o-mini", temperature=llm_temp),
            tts=openai.TTS(voice=voice),
            allow_interruptions=True,
            min_interruption_duration=0.5,
            min_endpointing_delay=0.5,
            max_endpointing_delay=6.0,
        )

        await session.start(
            room=ctx.room,
            agent=Assistant(config),
        )
        
        logger.info("STT-LLM-TTS pipeline agent started successfully")


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))