#!/usr/bin/env python3
"""
LiveKit Voice Agent with direct MCP integration
This uses the traditional voice pipeline (VAD + STT + LLM + TTS) for reliability
and connects directly to MCP servers without backend proxying.
"""

import os
import sys
import logging
import asyncio
import requests
from typing import List, Optional, Dict, Any, cast

# LiveKit imports
from livekit import rtc
from livekit.agents import (
    JobContext, WorkerOptions, cli, AutoSubscribe, 
    AgentSession, Agent
)
from livekit.plugins import openai, silero

# Add agents directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# MCP client imports
from mcp_client import MCPServerSse, MCPToolsIntegration

# Set up logging - reduce audio stream clutter
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING) 
logging.getLogger("openai").setLevel(logging.WARNING)
logger = logging.getLogger("voice-agent-mcp")

# MCP server configurations
MCP_SERVERS = {
    "internet_access": {
        "url": "https://n8n.srv755489.hstgr.cloud/mcp/43a3ec6f-728e-489b-9456-45f9d41750b7",
        "name": "Internet Access MCP"
    },
    "zapier": {
        "url": "https://mcp.zapier.com/api/mcp/s/MDRmNjkzMDUtYzI0NS00Y2FlLTgzODQtNzU5ZmRjMjViNDI1OmU3ZWQ4YWJjLTIxNDEtNDI5OC1iNTBiLWRlYWUxMjkxYWRkMw==",
        "name": "Zapier MCP"
    }
}

async def entrypoint(ctx: JobContext):
    """Main entry point with direct MCP integration"""
    
    # 1. Connect to LiveKit room
    logger.info(f"Connecting to room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # 2. Set up participant handlers
    participant_name = ""
    
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        nonlocal participant_name
        participant_name = participant.identity
        logger.info(f"Participant joined: {participant_name}")
    
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"Audio track published by {participant.identity}")
            publication.set_subscribed(True)
    
    # 3. Fetch configuration from database
    config = {
        "name": "MCP Voice Assistant",
        "systemPrompt": "You are a helpful AI voice assistant with access to web search and email capabilities.",
        "model": "gpt-4o",
        "voice": "alloy",
        "temperature": 0.7,
        "responseLength": "medium"
    }
    
    try:
        config_response = requests.get("http://localhost:5000/api/agent-configs/active", timeout=5)
        if config_response.status_code == 200:
            db_config = config_response.json()
            config.update(db_config)
            logger.info(f"Loaded config from database: {config['name']}")
    except Exception as e:
        logger.warning(f"Could not fetch config from database, using defaults: {e}")
    
    # 4. Extract configuration
    voice = config.get("voice", "alloy")
    temp_raw = float(config.get("temperature", 0.7))
    # Convert temperature from 0-100 range to 0-2 range for OpenAI API
    temp = min(2.0, max(0.0, temp_raw / 50.0)) if temp_raw > 2 else temp_raw
    
    # 5. Initialize MCP servers
    mcp_servers = []
    try:
        # Create MCP server instances
        for server_id, server_config in MCP_SERVERS.items():
            server = MCPServerSse(
                url=server_config["url"],
                name=server_config["name"]
            )
            mcp_servers.append(server)
            logger.info(f"Created MCP server: {server.name}")
    except Exception as e:
        logger.error(f"Failed to initialize MCP servers: {e}")
    
    # 6. Create MCP function tools
    mcp_tools = []
    if mcp_servers:
        try:
            mcp_tools = await MCPToolsIntegration.create_function_tools(mcp_servers)
            logger.info(f"✅ Created {len(mcp_tools)} MCP function tools")
        except Exception as e:
            logger.error(f"Failed to create MCP tools: {e}")
    
    # 7. Create enhanced system prompt
    base_prompt = config.get("systemPrompt", "You are a helpful AI assistant.")
    if mcp_tools:
        enhanced_prompt = f"""{base_prompt}

You have access to these tools:

🔍 Web Search: Use search_web(query) to find current information online
📧 Email: Use send_email(to, subject, body) to send emails

Use these tools naturally when users ask for searches or email sending. Keep responses conversational and helpful."""
    else:
        enhanced_prompt = f"""{base_prompt}

Note: External services (web search and email) are temporarily unavailable, but I can still help with questions and general assistance using my training data."""
    
    logger.info(f"Voice: {voice}, Temperature: {temp} (raw: {temp_raw}), MCP tools: {len(mcp_tools)}")
    
    # 8. Create agent with MCP tools
    agent = Agent(
        instructions=enhanced_prompt,
        tools=mcp_tools if mcp_tools else None,
    )
    
    # 9. Create AgentSession with traditional voice pipeline + VAD
    session = AgentSession(
        vad=silero.VAD.load(),  # VAD for streaming support
        stt=openai.STT(model="whisper-1"),  # OpenAI Whisper STT
        llm=openai.LLM(
            model="gpt-4o",
            temperature=temp,
        ),
        tts=openai.TTS(voice=voice),  # OpenAI TTS
        allow_interruptions=True,
        min_interruption_duration=0.5,
        min_endpointing_delay=0.3,
        max_endpointing_delay=2.0,
    )
    
    # 10. Start session
    try:
        await session.start(room=ctx.room, agent=agent)
        logger.info("Voice agent session started successfully with MCP integration!")
        
        # Generate a brief greeting
        greeting = "Hello! I'm your voice assistant. I can help with questions"
        if mcp_tools:
            greeting += ", web searches, and sending emails"
        greeting += ". How can I help you today?"
        
        await session.generate_reply(instructions=f"Greet the user with: {greeting}")
        
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise
    finally:
        # Cleanup MCP servers on exit
        for server in mcp_servers:
            try:
                await server.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up MCP server: {e}")

if __name__ == "__main__":
    # Set up environment
    os.environ['LD_LIBRARY_PATH'] = "/nix/store/gcc-unwrapped-13.3.0/lib:/nix/store/glibc-2.39-52/lib:" + os.environ.get('LD_LIBRARY_PATH', '')
    
    # Run the agent
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))