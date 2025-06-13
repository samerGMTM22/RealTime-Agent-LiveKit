# LiveKit OpenAI Realtime API Voice Agent - Complete Implementation Guide

## Overview

This document serves as a comprehensive reference for implementing a working voice agent using LiveKit Agents framework with OpenAI's Realtime API. It documents the specific issues we encountered and the exact solutions that resulted in a functional voice conversation system.

## Critical Success Factors

### 1. OpenAI Realtime API Access Requirements

**Issue:** The primary blocker was OpenAI Realtime API access limitations.

**Solution:** Confirmed that:
- OpenAI API key must have Realtime API access (requires Tier 5 usage or special approval)
- Model `gpt-4o-realtime-preview` requires explicit access beyond standard API access
- Silent failures occur when access is unavailable

**Verification Method:**
```python
# Test Realtime API access before implementation
import asyncio
import websockets
import json
import os

async def test_realtime_access():
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "OpenAI-Beta": "realtime=v1"
    }
    try:
        async with websockets.connect(
            "wss://api.openai.com/v1/realtime",
            additional_headers=headers,
            timeout=10
        ) as websocket:
            # Send test session update
            await websocket.send(json.dumps({
                "type": "session.update",
                "session": {"model": "gpt-4o-realtime-preview"}
            }))
            response = await websocket.recv()
            return "session.updated" in response
    except Exception:
        return False
```

### 2. Correct LiveKit Agent Architecture

**Issue:** Initial attempts used incorrect LiveKit patterns and missing components.

**Working Solution:** Use `AgentSession` with proper participant handling and audio subscription.

**Key Implementation:**
```python
from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, AgentSession, Agent
from livekit.plugins import openai, silero

async def entrypoint(ctx: JobContext):
    """Correct implementation pattern"""
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
    
    # 4. Create AgentSession with Realtime API
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            voice="coral",
            temperature=1.02,  # Range: 0.6-1.2 for Realtime API
        ),
        allow_interruptions=True,
        min_interruption_duration=0.5,
        min_endpointing_delay=0.5,
        max_endpointing_delay=6.0,
    )

    # 5. Start session with custom agent
    await session.start(room=ctx.room, agent=Assistant(config))
    
    # 6. Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and offer your assistance."
    )
```

### 3. Database Configuration Integration

**Issue:** Agent needed to fetch configuration from existing database system.

**Working Solution:**
```python
async def get_agent_config(room_name: str):
    """Fetch agent configuration from database based on room name."""
    try:
        # Extract config ID from room name pattern
        if 'voice_agent_session_' in room_name:
            config_id = 1  # Default to first config
        
        # Fetch from API endpoint
        response = requests.get(f"http://localhost:5000/api/agent-configs/{config_id}")
        if response.status_code == 200:
            config = response.json()
            logger.info(f"Fetched config from database: {config.get('name', 'Unknown')}")
            return config
        else:
            logger.warning(f"Failed to fetch config: {response.status_code}")
            return get_default_config()
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
        return get_default_config()

def get_default_config():
    """Default configuration fallback"""
    return {
        "id": 1,
        "name": "Default Agent",
        "systemPrompt": "You are a helpful AI assistant.",
        "voiceModel": "coral",
        "temperature": 80,
        "responseLength": "medium"
    }
```

### 4. Voice Model and Temperature Configuration

**Critical Settings:**
- **Temperature Range:** OpenAI Realtime API requires 0.6-1.2 range
- **Voice Models:** alloy, echo, fable, onyx, nova, shimmer, coral
- **Conversion Logic:** Convert percentage (0-100) to valid range

```python
# Voice model mapping
voice_mapping = {
    "alloy": "alloy", "echo": "echo", "fable": "fable",
    "onyx": "onyx", "nova": "nova", "shimmer": "shimmer", "coral": "coral"
}

# Temperature conversion for Realtime API
temp_raw = config.get("temperature", 80)  # Percentage value
realtime_temp = max(0.6, min(1.2, 0.6 + (float(temp_raw) / 100.0) * 0.6))
```

### 5. Fallback Implementation (STT-LLM-TTS)

**Issue:** Needed robust fallback when Realtime API fails.

**Working Fallback:**
```python
try:
    # Primary: Realtime API implementation
    session = AgentSession(llm=openai.realtime.RealtimeModel(...))
    # ... realtime setup
    
except Exception as e:
    logger.error(f"Realtime API failed: {e}")
    
    # Fallback: STT-LLM-TTS pipeline
    llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)  # Different range for LLM
    
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
    
    await session.start(room=ctx.room, agent=Assistant(config))
```

## Common Issues and Solutions

### Issue 1: "generate_reply timed out" Error

**Symptoms:**
```
livekit.agents.llm.realtime.RealtimeError: generate_reply timed out.
Error in _realtime_reply_task
```

**Root Causes:**
1. No OpenAI Realtime API access
2. Invalid API key for Realtime features
3. Network connectivity issues

**Solution:**
- Verify Realtime API access with test script
- Check OpenAI account tier and permissions
- Implement fallback to STT-LLM-TTS

### Issue 2: Agent Connects But No Audio Response

**Symptoms:**
- Agent shows "started successfully"
- User audio is detected
- No audio response from agent

**Root Causes:**
1. Missing audio track subscription
2. Incorrect participant handling
3. Missing initial greeting generation

**Solution:**
```python
# Ensure proper audio subscription
@ctx.room.on("track_published")
def on_track_published(publication, participant):
    if publication.kind == "audio":
        publication.set_subscribed(True)

# Wait for participant before starting
participant = await ctx.wait_for_participant()

# Generate initial response
await session.generate_reply(instructions="Greet the user warmly")
```

### Issue 3: Incorrect Import Usage

**Failed Approaches:**
```python
# These don't work in our LiveKit version:
from livekit.agents.multimodal import MultimodalAgent  # Not available
from livekit.agents import VoiceAssistant  # Wrong class
```

**Working Imports:**
```python
from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, AgentSession, Agent
from livekit.plugins import openai, silero
```

## Environment Setup

### Required Dependencies
```bash
pip install livekit-agents livekit-plugins-openai livekit-plugins-silero python-dotenv
```

### Environment Variables
```bash
OPENAI_API_KEY=your-openai-api-key  # Must have Realtime API access
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
```

## Complete Working Implementation

### agent.py (Full Working Code)
```python
import logging
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, AgentSession, Agent
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero
import requests
import os

logger = logging.getLogger("voice-agent")
load_dotenv()

async def get_agent_config(room_name: str):
    """Fetch agent configuration from database based on room name."""
    try:
        config_id = 1  # Default config ID
        response = requests.get(f"http://localhost:5000/api/agent-configs/{config_id}")
        if response.status_code == 200:
            config = response.json()
            logger.info(f"Fetched config from database: {config.get('name', 'Unknown')}")
            return config
        else:
            return get_default_config()
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
        return get_default_config()

def get_default_config():
    return {
        "id": 1, "name": "Default Agent", "systemPrompt": "You are a helpful AI assistant.",
        "voiceModel": "coral", "temperature": 80, "responseLength": "medium"
    }

class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config

    @function_tool
    async def get_general_info(self):
        """Provides general information about services."""
        return f"I'm {self.config.get('name', 'your AI assistant')} and I'm here to help you with any questions you have."

async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent."""
    logger.info(f"Agent started for room: {ctx.room.name}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind == "audio":
            publication.set_subscribed(True)
            logger.info(f"Subscribed to audio track from {participant.identity}")
    
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")
    
    config = await get_agent_config(ctx.room.name)
    logger.info(f"Using agent config: {config.get('name', 'Default')}")
    
    voice_mapping = {
        "alloy": "alloy", "echo": "echo", "fable": "fable",
        "onyx": "onyx", "nova": "nova", "shimmer": "shimmer", "coral": "coral"
    }
    
    voice = voice_mapping.get(config.get("voiceModel", "alloy"), "alloy")
    temp_raw = config.get("temperature", 80)
    realtime_temp = max(0.6, min(1.2, 0.6 + (float(temp_raw) / 100.0) * 0.6))
    
    logger.info(f"Voice: {voice}, Temperature: {realtime_temp}")

    try:
        logger.info("Attempting OpenAI Realtime API")
        
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

        await session.start(room=ctx.room, agent=Assistant(config))
        
        await session.generate_reply(
            instructions="Greet the user warmly and offer your assistance."
        )
        
        logger.info("OpenAI Realtime API agent started successfully")
        
    except Exception as e:
        logger.error(f"Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline")
        
        llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
        
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

        await session.start(room=ctx.room, agent=Assistant(config))
        logger.info("STT-LLM-TTS pipeline agent started successfully")

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
```

## Testing and Verification

### 1. Agent Startup Verification
Look for these log messages:
```
INFO voice-agent - Agent started for room: voice_agent_session_xxx
INFO voice-agent - Participant joined: user
INFO voice-agent - Using agent config: My YouTube Agent
INFO voice-agent - Voice: coral, Temperature: 1.02
INFO voice-agent - Attempting OpenAI Realtime API
INFO voice-agent - OpenAI Realtime API agent started successfully
```

### 2. Audio Flow Verification
- User audio should be detected and published
- Agent should subscribe to audio tracks
- Agent should generate audio responses
- User should hear agent voice clearly

### 3. Fallback Testing
If Realtime API fails, should see:
```
ERROR voice-agent - Realtime API failed: [error details]
INFO voice-agent - Falling back to STT-LLM-TTS pipeline
INFO voice-agent - STT-LLM-TTS pipeline agent started successfully
```

## Troubleshooting Checklist

1. **Verify OpenAI Realtime API Access**
   - Run the test script
   - Check OpenAI account tier
   - Confirm API key permissions

2. **Check LiveKit Connection**
   - Verify LiveKit credentials
   - Confirm room creation
   - Check participant connection

3. **Audio Issues**
   - Ensure proper audio track subscription
   - Check browser audio permissions
   - Verify microphone access

4. **Configuration Issues**
   - Confirm database connectivity
   - Verify agent configuration loading
   - Check voice model and temperature values

## Key Learnings

1. **OpenAI Realtime API requires explicit access** - This was the primary blocker
2. **Proper audio subscription is critical** - Without it, agent won't hear user
3. **Participant waiting is essential** - Agent must wait for user before starting
4. **Temperature ranges differ** - Realtime API (0.6-1.2) vs LLM (0.0-2.0)
5. **Fallback implementation is crucial** - Ensures system reliability
6. **Initial greeting generation** - Necessary for agent to produce first audio

This guide provides a complete reference for maintaining and troubleshooting the LiveKit OpenAI Realtime API voice agent implementation.