
import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    stt,
    tts,
    vad,
)
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero
import requests

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
            
            # Also fetch MCP servers for this agent
            try:
                mcp_response = requests.get(f'http://localhost:5000/api/mcp/servers', timeout=5)
                if mcp_response.status_code == 200:
                    mcp_servers = mcp_response.json()
                    config['mcp_servers'] = mcp_servers
                    logger.info(f"Loaded {len(mcp_servers)} MCP servers for agent")
                else:
                    config['mcp_servers'] = []
            except Exception as mcp_error:
                logger.warning(f"Could not load MCP servers: {mcp_error}")
                config['mcp_servers'] = []
                
            return config
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
    
    # Fallback configuration
    return {
        "systemPrompt": "You are a helpful voice AI assistant that provides music guidance and advice. You help with music practice, techniques, and general music education.",
        "voiceModel": "alloy",
        "temperature": 80,
        "responseLength": "medium",
        "mcp_servers": []
    }


class GiveMeTheMicAgent(Agent):
    def __init__(self, config: dict) -> None:
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        super().__init__(instructions=system_prompt)
        self.config = config

    async def on_enter(self):
        """Called when the agent enters the session - generates initial greeting"""
        logger.info("Agent entering session, generating initial greeting")
        # Generate initial greeting with proper session context
        greeting = "Hello! I'm your Give Me the Mic assistant. I'm here to help you with music, singing, recording, and all things related to your musical journey. How can I assist you today?"
        
        # Use the session's say method to ensure audio output
        await self.session.say(greeting, allow_interruptions=True)

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
        logger.info(f"Performing web search for: {query}")
        
        # Get MCP servers from config
        mcp_servers = self.config.get('mcp_servers', [])
        
        # Check if we have any MCP servers configured
        if not mcp_servers:
            return "No MCP servers are currently configured. Please add MCP servers in the configuration to enable web search and other external tools."
        
        # Find internet access MCP server
        internet_server = None
        for server in mcp_servers:
            server_name = server.get('name', '').lower()
            if 'internet' in server_name or 'web' in server_name:
                internet_server = server
                break
        
        if not internet_server:
            available_servers = [s.get('name', 'Unknown') for s in mcp_servers]
            return f"No internet-capable MCP server found. Available servers: {', '.join(available_servers)}. Please configure an internet access MCP server."
        
        try:
            # Make API call to MCP tools for web search
            response = requests.post('http://localhost:5000/api/mcp/execute', 
                                   json={
                                       'server_id': internet_server.get('id'),
                                       'tool': 'web_search', 
                                       'query': query
                                   }, 
                                   timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('results'):
                    return f"Search results for '{query}': {data['results']}"
                else:
                    return f"Web search completed but no results found for '{query}'. The MCP server '{internet_server.get('name')}' may need configuration."
            
            logger.warning(f"MCP web search failed with status {response.status_code}")
            return f"Web search failed through MCP server '{internet_server.get('name')}'. Please check the server configuration and connection."
            
        except Exception as e:
            logger.error(f"Error accessing MCP tools: {e}")
            return f"I'm unable to perform web searches right now. Error connecting to MCP server '{internet_server.get('name', 'Unknown')}'."


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

    # Connect to the room first
    await ctx.connect()

    # Initialize agent instance
    agent = GiveMeTheMicAgent(config)
    
    # Create session with proper VAD and streaming configuration
    try:
        # Try OpenAI Realtime API first (without ServerVAD which doesn't exist)
        try:
            realtime_model = openai.realtime.RealtimeModel(
                voice=voice,
                temperature=temperature,
                instructions=config.get("systemPrompt", "You are a helpful voice AI assistant."),
            )
            
            session = AgentSession(
                llm=realtime_model,
            )
            logger.info("Attempting OpenAI Realtime API connection")
            
            # Start session with proper agent and room configuration
            await session.start(
                agent=agent,
                room=ctx.room,
            )
            logger.info("OpenAI Realtime API session started successfully")
            
        except Exception as realtime_error:
            logger.error(f"OpenAI Realtime API failed: {realtime_error}")
            raise realtime_error
            
    except Exception as e:
        logger.error(f"OpenAI Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline with VAD")
        
        # Fallback to STT-LLM-TTS pipeline with proper VAD configuration
        session = AgentSession(
            # Add Silero VAD for voice activity detection
            vad=silero.VAD.load(
                min_silence_duration=0.5,  # 500ms of silence to stop
                min_speaking_duration=0.3,  # 300ms to start speaking
            ),
            # Use streaming STT with adapter
            stt=stt.StreamAdapter(
                stt=openai.STT(model="whisper-1"),
                vad=silero.VAD.load(),
            ),
            llm=openai.LLM(
                model="gpt-4o-mini",
                temperature=temperature,
            ),
            tts=openai.TTS(voice=voice),
        )
        
        await session.start(
            agent=agent,
            room=ctx.room,
        )
        logger.info("STT-LLM-TTS pipeline session started successfully with VAD")
    
    logger.info("Give Me the Mic agent is running and ready for voice interactions")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
