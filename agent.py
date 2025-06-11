import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    RoomInputOptions,
)
from livekit.agents.llm import function_tool
from livekit.plugins import openai
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
            return config
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
    
    # Fallback configuration
    return {
        "systemPrompt": "You are a helpful voice AI assistant for the Give Me the Mic YouTube channel. You help viewers with channel information, video content, and general music-related questions.",
        "voiceModel": "alloy",
        "temperature": 80,
        "responseLength": "medium"
    }


class GiveMeTheMicAgent(Agent):
    def __init__(self, config: dict) -> None:
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        super().__init__(instructions=system_prompt)
        self.config = config

    async def on_enter(self):
        """Called when the agent enters the session - generates initial greeting"""
        logger.info("Agent entering session, generating initial greeting")
        await self.session.generate_reply(
            instructions="Greet the user warmly and introduce yourself as the Give Me the Mic assistant. Ask how you can help them with music today."
        )

    @function_tool
    async def get_channel_info(self):
        """Provides information about the Give Me the Mic YouTube channel including subscriber count, content type, and channel details."""
        
        logger.info("Providing Give Me the Mic channel information")
        
        return """The Give Me the Mic channel (@givemethemicmusic) is a music-focused YouTube channel with 484 subscribers and 249 videos. 
        The channel features content about singing, music performance, recording tips, and musical entertainment. 
        It's a great resource for aspiring musicians and singers looking to improve their craft."""

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
    async def suggest_content(self, interest: str):
        """Suggests Give Me the Mic channel content based on user's musical interests.
        
        Args:
            interest: The user's musical interest or area they want to learn about
        """
        
        logger.info(f"Suggesting content for interest: {interest}")
        
        suggestions = {
            "vocal": "Check out our vocal technique videos and singing tips series on the Give Me the Mic channel.",
            "recording": "Our home recording setup guides and audio production tips would be perfect for you.",
            "performance": "Look for our stage presence and performance confidence videos.",
            "songwriting": "We have songwriting tutorials and creative process breakdowns you'd enjoy.",
            "instruments": "Browse our instrument-specific tutorials and playing technique videos."
        }
        
        suggestion = suggestions.get(interest.lower(), f"For {interest}, I recommend exploring our general music education content on Give Me the Mic.")
        return f"Content suggestion: {suggestion} Don't forget to subscribe and hit the notification bell!"


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

    # Create session with hybrid voice pipeline approach
    try:
        # Try OpenAI Realtime API first
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                voice=voice,
                temperature=temperature,
                model="gpt-4o-realtime-preview"
            ),
        )
        logger.info("Attempting OpenAI Realtime API connection")
        
        await session.start(
            agent=GiveMeTheMicAgent(config),
            room=ctx.room,
            room_input_options=RoomInputOptions(),
        )
        logger.info("OpenAI Realtime API session started successfully")
        
    except Exception as e:
        logger.error(f"OpenAI Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline")
        
        # Fallback to STT-LLM-TTS pipeline for more reliable voice interaction
        session = AgentSession(
            stt=openai.STT(model="whisper-1"),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=openai.TTS(voice=voice),
        )
        
        await session.start(
            agent=GiveMeTheMicAgent(config),
            room=ctx.room,
            room_input_options=RoomInputOptions(),
        )
        logger.info("STT-LLM-TTS pipeline session started successfully")
    
    logger.info("Give Me the Mic agent is running and ready for voice interactions")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))