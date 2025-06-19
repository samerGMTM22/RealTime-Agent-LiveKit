"""Pure OpenAI Realtime API Voice Agent - No STT-LLM-TTS Fallback"""
import logging
import httpx
from typing import Dict
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, AgentSession, Agent
from livekit.plugins import openai

logger = logging.getLogger("realtime-agent")
load_dotenv()

class RealtimeAssistant(Agent):
    """Voice assistant agent with pure Realtime API integration."""
    
    def __init__(self, config: Dict):
        super().__init__()
        self.config = config
        self.name = config.get('name', 'Realtime Assistant')

async def get_agent_config(room_name: str) -> Dict:
    """Fetch agent configuration from database."""
    try:
        config_id = 1  # Default to first config
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:5000/api/agent-configs/{config_id}")
            if response.status_code == 200:
                config = response.json()
                logger.info(f"Fetched config: {config.get('name', 'Unknown')}")
                return config
            else:
                logger.warning(f"Failed to fetch config: {response.status_code}")
                return get_default_config()
    except Exception as e:
        logger.error(f"Config fetch error: {e}")
        return get_default_config()

def get_default_config():
    """Default configuration for Realtime API."""
    return {
        "id": 1,
        "name": "Realtime Assistant",
        "systemPrompt": "You are a helpful AI assistant that can have natural voice conversations.",
        "voiceModel": "coral",
        "temperature": 80,
        "responseLength": "medium"
    }

async def entrypoint(ctx: JobContext):
    """Main entry point - Pure OpenAI Realtime API implementation."""
    logger.info(f"Starting Realtime API agent for room: {ctx.room.name}")
    
    # 1. Connect with audio-only subscription
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # 2. Ensure audio track subscription (critical for audio flow)
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind == "audio":
            publication.set_subscribed(True)
            logger.info(f"Subscribed to audio track from {participant.identity}")
    
    # 3. Wait for participant before starting agent
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")
    
    # 4. Get configuration
    config = await get_agent_config(ctx.room.name)
    
    # Voice model mapping for Realtime API
    voice_mapping = {
        "alloy": "alloy", "echo": "echo", "fable": "fable",
        "onyx": "onyx", "nova": "nova", "shimmer": "shimmer", "coral": "coral"
    }
    
    voice = voice_mapping.get(config.get("voiceModel", "coral"), "coral")
    temp_raw = config.get("temperature", 80)
    
    # Convert temperature: 0-100% to 0.6-1.2 range for Realtime API
    realtime_temp = max(0.6, min(1.2, 0.6 + (float(temp_raw) / 100.0) * 0.6))
    
    logger.info(f"Voice: {voice}, Temperature: {realtime_temp}")

    # 5. Create AgentSession with OpenAI Realtime API ONLY
    logger.info("Starting pure OpenAI Realtime API session...")
    
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            voice=voice,
            temperature=realtime_temp,
            instructions=config.get("systemPrompt", "You are a helpful AI assistant."),
        ),
        allow_interruptions=True,
        min_interruption_duration=0.5,
        min_endpointing_delay=0.5,
        max_endpointing_delay=6.0,
    )

    # 6. Start session with custom agent
    assistant = RealtimeAssistant(config)
    await session.start(room=ctx.room, agent=assistant)
    
    # 7. Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and offer your assistance."
    )
    
    logger.info("OpenAI Realtime API session started successfully")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))