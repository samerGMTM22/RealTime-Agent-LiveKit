"""
LiveKit Voice Agent with Direct N8N and Zapier Tool Integration
Based on definitive solution architecture - uses HTTP webhooks instead of MCP protocol
"""
import asyncio
import logging
import requests
from typing import Any
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero
from livekit.agents.llm import ChatContext

# Import our direct tool adapters
from n8n_tool import N8NTools
from zapier_tool import ZapierTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent-direct-tools")

async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent with direct tool integration."""
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"Connecting to room: {ctx.room.name}")
    
    # 1. Fetch agent configuration from database
    try:
        response = requests.get("http://localhost:5000/api/agent-configs/active", timeout=10)
        response.raise_for_status()
        config = response.json()
        logger.info(f"Loaded config from database: {config['name']}")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        config = {
            "name": "Voice Assistant",
            "systemPrompt": "You are a helpful voice assistant with access to web search and email capabilities.",
            "voiceModel": "alloy",
            "temperature": 70.0
        }
    
    # 2. Convert temperature from 0-100 range to 0-2 range for OpenAI API
    temp_raw = float(config.get("temperature", 70.0))
    temp = min(2.0, max(0.0, temp_raw / 50.0)) if temp_raw > 2 else temp_raw
    
    # 3. Instantiate the direct tool adapters
    n8n_tools = N8NTools()
    zapier_tools = ZapierTools()
    
    logger.info(f"✅ Created direct tool adapters for N8N and Zapier")
    logger.info(f"Voice: {config.get('voiceModel', 'alloy')}, Temperature: {temp} (raw: {temp_raw})")
    
    # 4. Create the voice assistant with tools
    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(
            model="gpt-4o",
            temperature=temp,
        ),
        tts=openai.TTS(voice=config.get("voiceModel", "alloy")),
        chat_ctx=[
            {"role": "system", "content": config.get("systemPrompt", "You are a helpful voice assistant.")}
        ],
        tools=[n8n_tools, zapier_tools]  # Register our direct tool adapters
    )
    
    # 5. Start the assistant
    assistant.start(ctx.room)
    
    logger.info("Voice agent session started successfully with direct tool integration!")
    
    # 6. Keep the session running
    await assistant.aclose()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))