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
        
        logger.info("Fetching YouTube channel information from API")
        
        try:
            # Make API call to get real-time channel info
            response = requests.get('http://localhost:5000/api/youtube/channel/@givemethemicmusic', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('channel'):
                    channel = data['channel']
                    return f"""Give Me the Mic Channel Information:
                    - Channel: {channel.get('title', 'Give Me the Mic')}
                    - Subscribers: {channel.get('subscriberCount', 'N/A')}
                    - Videos: {channel.get('videoCount', 'N/A')} 
                    - Total Views: {channel.get('viewCount', 'N/A')}
                    - Description: {channel.get('description', 'Music-focused YouTube channel')}
                    
                    This channel focuses on music education, performance tips, and giving aspiring musicians a platform."""
            
            logger.warning("YouTube API unavailable, using fallback information")
            return "I don't currently have access to real-time YouTube data. Please ensure the YouTube API is properly configured for the most up-to-date channel statistics."
            
        except Exception as e:
            logger.error(f"Error fetching YouTube data: {e}")
            return "I'm unable to access YouTube channel data right now. The YouTube API integration may need to be configured."

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

    @function_tool
    async def get_latest_videos(self, channel_handle: str = "@givemethemicmusic"):
        """Gets the latest videos from the specified YouTube channel.
        
        Args:
            channel_handle: The YouTube channel handle (default: @givemethemicmusic)
        """
        
        logger.info(f"Fetching latest videos for: {channel_handle}")
        
        try:
            # Make API call to get channel videos
            response = requests.get(f'http://localhost:5000/api/youtube/channel/{channel_handle}/videos', timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('videos') and len(data['videos']) > 0:
                    videos = data['videos'][:5]  # Get top 5 latest videos
                    video_list = []
                    for video in videos:
                        video_list.append(f"- {video.get('title', 'Untitled')} ({video.get('publishedAt', 'Unknown date')})")
                    
                    return f"Latest videos from {channel_handle}:\n" + "\n".join(video_list)
            
            logger.warning("YouTube video API unavailable")
            return "I don't currently have access to YouTube video data. Please ensure the YouTube API is properly configured."
            
        except Exception as e:
            logger.error(f"Error fetching YouTube videos: {e}")
            return "I'm unable to access YouTube video data right now. The YouTube API integration may need to be configured."


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