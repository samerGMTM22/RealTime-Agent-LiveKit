# LiveKit OpenAI Realtime API Voice Agent - Expert Consultation

## Context & Objective

We're building a voice agent using LiveKit Agents framework with the OpenAI Realtime API. The agent should allow users to have real-time voice conversations, but we're experiencing critical connection and response issues.

**Goal:** Use exclusively the OpenAI Realtime API (not STT-LLM-TTS pipeline) for a working voice conversation agent.

## Current Technical Stack

- **LiveKit Agents**: v1.0.23
- **LiveKit RTC**: v1.0.8  
- **OpenAI Plugin**: livekit-plugins-openai (installed)
- **Python**: 3.11
- **OpenAI Model**: gpt-4o-realtime-preview
- **Environment**: Replit with proper OPENAI_API_KEY configured

## Agent Implementation

```python
async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the LiveKit agent."""
    # Configuration from database
    voice = "coral"  # OpenAI voice
    temperature = 1.02  # Range 0.6-1.2 for Realtime API
    
    # Server VAD turn detection
    turn_detection = TurnDetection(
        type="server_vad",
        threshold=0.5,
        prefix_padding_ms=300,
        silence_duration_ms=500,
        create_response=True,
        interrupt_response=True,
    )

    # Pure OpenAI Realtime API session
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            voice=voice,
            temperature=temperature,
            turn_detection=turn_detection,
        ),
        allow_interruptions=True,
        min_interruption_duration=0.5,
        min_endpointing_delay=0.5,
        max_endpointing_delay=6.0,
    )

    await session.start(room=ctx.room, agent=Assistant(config))
    await ctx.connect()
    await session.generate_reply(instructions="Greet the user and offer your assistance.")
```

## Critical Issues Observed

### 1. Connection Timeouts
**Error Pattern:**
```
livekit.agents.llm.realtime.RealtimeError: generate_reply timed out.
Error in _realtime_reply_task
generation_ev = await self._rt_session.generate_reply(...)
```

**Frequency:** Occurs immediately when trying to generate any response

### 2. Agent Startup Success But No Audio Response
**Symptoms:**
- Agent successfully connects to LiveKit room
- Database configuration fetched correctly
- User's audio is detected and published
- Agent shows "OpenAI Realtime API agent is running"
- **BUT:** No audio response from agent, user hears nothing

### 3. LiveKit Connection Flow (Working)
```
✓ LiveKit token generation: SUCCESS
✓ Room creation: SUCCESS  
✓ Agent registration: SUCCESS
✓ User audio publishing: SUCCESS
✓ Agent participant connection: SUCCESS
```

### 4. OpenAI API Status
- API key is valid (confirmed via `/api/status` endpoint)
- Returns: `{"openai":"connected"}` 
- No authentication errors in logs

## Detailed Questions for Expert

### A. OpenAI Realtime API Configuration
1. **API Access**: Does the OpenAI Realtime API require special access/waitlist approval beyond having a valid API key? Could this cause silent connection failures?

2. **Model Availability**: Is `gpt-4o-realtime-preview` the correct model identifier? Are there regional restrictions or specific requirements?

3. **Temperature Range**: Is the temperature range 0.6-1.2 correct for the Realtime API? Documentation mentions this but want to confirm.

### B. Turn Detection Configuration
4. **Server VAD Settings**: Are these TurnDetection parameters optimal for the OpenAI Realtime API?
   ```python
   TurnDetection(
       type="server_vad",
       threshold=0.5,
       prefix_padding_ms=300,
       silence_duration_ms=500,
       create_response=True,
       interrupt_response=True,
   )
   ```

5. **VAD vs Client Detection**: Should we use `type="server_vad"` or a different detection method? What's the recommended approach?

### C. Session Configuration Issues
6. **Missing Components**: In our pure Realtime API setup, do we need to specify STT, TTS, or VAD components, or should they be omitted entirely when using RealtimeModel?

7. **Session Parameters**: Are these AgentSession parameters correct for Realtime API usage?
   ```python
   allow_interruptions=True,
   min_interruption_duration=0.5,
   min_endpointing_delay=0.5,
   max_endpointing_delay=6.0,
   ```

### D. Connection & Network Issues
8. **WebSocket Configuration**: Could there be WebSocket configuration issues between LiveKit and OpenAI? Do we need specific network settings or headers?

9. **Timeout Configuration**: The `generate_reply` timeout suggests the OpenAI connection isn't establishing properly. What's the typical connection flow and where might it be failing?

10. **Regional Issues**: Could there be regional restrictions or latency issues affecting the OpenAI Realtime API connection from our environment?

### E. Implementation Patterns
11. **Initialization Sequence**: Is this the correct sequence for starting a Realtime API agent?
    ```python
    session = AgentSession(llm=openai.realtime.RealtimeModel(...))
    await session.start(room=ctx.room, agent=Assistant(config))
    await ctx.connect()
    await session.generate_reply(...)
    ```

12. **Error Handling**: Should we implement specific error handling for Realtime API connection failures? What are the common failure modes?

### F. Debugging Approach
13. **Logging**: What specific logging or debugging steps can help identify where the OpenAI Realtime API connection is failing?

14. **Alternative Testing**: Is there a way to test the OpenAI Realtime API connection independently of the full LiveKit agent setup?

15. **Minimal Example**: Could you provide a minimal working example of LiveKit + OpenAI Realtime API integration that we can compare against?

## Current Logs for Reference

**Agent Startup (Success):**
```
INFO livekit.agents - registered worker
INFO voice-agent - Starting agent for room: voice_agent_session_xxx
INFO voice-agent - Using agent config: My YouTube Agent  
INFO voice-agent - Voice: coral, Temperature: 1.02
INFO voice-agent - OpenAI Realtime API agent is running
```

**User Audio (Detected):**
```
publishing track {"source":"microphone","kind":"audio"}
silence detected on local audio track
```

**Critical Error (Repeating):**
```
ERROR livekit.agents - generate_reply timed out.
ERROR livekit.agents - Error in _realtime_reply_task
```

## Request to Expert

Please provide specific guidance on:
1. Which of these issues is most likely the root cause
2. Step-by-step debugging approach to isolate the problem
3. Correct configuration patterns for OpenAI Realtime API with LiveKit
4. Any missing setup steps or common pitfalls
5. Working code example if our implementation has fundamental issues

The agent successfully connects to LiveKit and detects user audio, but completely fails to establish OpenAI Realtime API communication for generating responses.