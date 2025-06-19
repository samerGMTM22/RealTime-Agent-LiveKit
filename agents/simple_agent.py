"""Simple LiveKit Voice Agent - Minimal Implementation"""
import logging
import asyncio
import httpx
from typing import Dict
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe
from livekit.plugins import openai, silero

logger = logging.getLogger("voice-agent")
load_dotenv()

async def get_agent_config(room_name: str) -> Dict:
    """Fetch agent configuration from database."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/api/agent-configs/active")
            if response.status_code == 200:
                config = response.json()
                logger.info(f"Using config: {config.get('name', 'Default')}")
                return config
    except Exception as e:
        logger.error(f"Config fetch error: {e}")
    
    return {
        "systemPrompt": "You are a helpful AI assistant.",
        "voiceModel": "alloy",
        "temperature": 80
    }

async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent."""
    logger.info(f"Agent starting for room: {ctx.room.name}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind == "audio":
            publication.set_subscribed(True)
            logger.info(f"Audio subscribed from {participant.identity}")
    
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")
    
    config = await get_agent_config(ctx.room.name)
    
    voice = config.get("voiceModel", "alloy")
    temp_raw = config.get("temperature", 80)
    llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
    
    logger.info(f"Voice: {voice}, Temperature: {llm_temp}")
    
    # Use standard STT-LLM-TTS pipeline
    agent = agents.VoiceAgent(
        vad=silero.VAD.load(),
        stt=openai.STT(model="whisper-1"),
        llm=openai.LLM(
            model="gpt-4o",
            temperature=llm_temp,
        ),
        tts=openai.TTS(model="tts-1", voice=voice),
    )

    await agent.start(ctx.room, participant)
    logger.info("Voice agent started successfully")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))