#!/usr/bin/env python
"""
Reliable LiveKit Voice Agent with Traditional Voice Pipeline
- Uses STT-LLM-TTS instead of Realtime API to avoid function tool bugs
- Shorter MCP timeouts to prevent connection issues  
- Robust error handling for MCP timeouts
- Based on official LiveKit documentation patterns
"""
import asyncio
import os
import logging
import requests
from typing import Optional, Dict, Any

# LiveKit imports
from livekit import rtc
from livekit.agents import (
    JobContext, WorkerOptions, cli, AutoSubscribe, 
    AgentSession, Agent, function_tool
)
from livekit.plugins import openai

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("reliable-voice-agent")

# Global flag for MCP availability
_mcp_enabled = False
_mcp_test_mode = os.getenv("MCP_TEST_MODE", "false").lower() == "true"

@function_tool
async def search_web(query: str) -> str:
    """Search the web using MCP integration with reduced timeout."""
    global _mcp_enabled, _mcp_test_mode
    
    # Test mode - return simulated results
    if _mcp_test_mode:
        logger.info(f"[TEST MODE] Simulating web search for: {query}")
        return f"[Test Mode] Here's what I found about '{query}': This is a simulated search result showing the function is working correctly."
    
    if not _mcp_enabled:
        return f"I understand you want to search for '{query}', but web search is temporarily unavailable. Let me help with what I know instead."
    
    try:
        logger.info(f"Executing web search: {query}")
        
        # Reduced timeout to prevent WebSocket disconnection
        response = requests.post(
            'http://localhost:5000/api/mcp/execute',
            json={
                "serverId": 9,  # Internal search server
                "tool": "execute_web_search", 
                "params": {"query": query}
            },
            timeout=15  # Reduced from 45 to 15 seconds
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                result = data.get("result", "")
                logger.info(f"Web search completed successfully")
                return format_search_results(result, query)
            else:
                error_msg = data.get("error", "Unknown error")
                logger.warning(f"MCP search failed: {error_msg}")
                
                # Quick fallback response
                return f"I couldn't complete the web search for '{query}' right now. Let me share what I know from my training data instead. What specific aspect of {query} would you like to know about?"
        else:
            logger.warning(f"MCP API error: {response.status_code}")
            return f"Web search is experiencing issues. I can still help answer questions about '{query}' using my existing knowledge."
            
    except requests.exceptions.Timeout:
        logger.warning(f"Search timeout for query: {query}")
        return f"The search for '{query}' is taking too long. Let me help with what I know about this topic instead."
    except requests.exceptions.ConnectionError:
        logger.warning(f"Connection error during search")
        return f"I can't connect to search services right now. I'll answer your question about '{query}' using my available knowledge."
    except Exception as e:
        logger.warning(f"Search error: {str(e)}")
        return f"I encountered an issue while searching. Let me help you with '{query}' using my training data instead."

@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email using Zapier MCP integration with reduced timeout."""
    global _mcp_enabled, _mcp_test_mode
    
    # Test mode - simulate email sending
    if _mcp_test_mode:
        logger.info(f"[TEST MODE] Simulating email to: {to}")
        return f"[Test Mode] Email simulated successfully! To: {to}, Subject: {subject}"
    
    if not _mcp_enabled:
        return "Email services are currently unavailable. Please try again later."
    
    try:
        logger.info(f"Sending email to: {to}")
        
        # Validate email format
        if "@" not in to or "." not in to.split("@")[-1]:
            return f"The email address '{to}' doesn't appear to be valid. Please check and try again."
        
        response = requests.post(
            'http://localhost:5000/api/mcp/execute',
            json={
                "serverId": 15,  # Zapier MCP server
                "tool": "send_email",
                "params": {
                    "to": to,
                    "subject": subject,
                    "body": body
                }
            },
            timeout=15  # Reduced from 45 to 15 seconds
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                logger.info(f"Email sent successfully to: {to}")
                return f"Email sent successfully to {to}! The message with subject '{subject}' has been delivered."
            else:
                error_msg = data.get("error", "Unknown error")
                logger.warning(f"Email send failed: {error_msg}")
                return f"I couldn't send the email right now. Error: {error_msg}. Please try again in a moment."
        else:
            logger.warning(f"Email API error: {response.status_code}")
            return f"Email service returned an error. Please try again later."
            
    except requests.exceptions.Timeout:
        logger.warning(f"Email timeout")
        return f"The email service is taking too long to respond. Please try sending the email to {to} again."
    except Exception as e:
        logger.warning(f"Email error: {str(e)}")
        return f"An error occurred while sending the email: {str(e)}"

def format_search_results(result: str, query: str) -> str:
    """Format search results for voice output"""
    if not result or result == "No results found":
        return f"I searched for '{query}' but didn't find specific results. Would you like me to search for something related?"
    
    # Format for voice-friendly output
    formatted = f"Here's what I found about {query}: {result}"
    
    # Truncate if too long for voice
    if len(formatted) > 400:
        formatted = formatted[:397] + "..."
        formatted += " There's more information available if you'd like me to continue."
    
    return formatted

async def check_mcp_availability() -> bool:
    """Check if MCP services are available with short timeout"""
    try:
        response = requests.get("http://localhost:5000/api/mcp/servers", timeout=3)
        if response.status_code == 200:
            servers = response.json()
            active_servers = [s for s in servers if s.get("isActive", True)]
            if active_servers:
                logger.info(f"Found {len(active_servers)} active MCP servers")
                return True
    except Exception as e:
        logger.warning(f"MCP availability check failed: {e}")
    return False

async def entrypoint(ctx: JobContext):
    """Main entry point using traditional voice pipeline for reliability"""
    global _mcp_enabled
    
    # 1. Check MCP availability
    _mcp_enabled = await check_mcp_availability()
    if _mcp_enabled:
        logger.info("MCP services available - full functionality enabled")
    elif _mcp_test_mode:
        logger.info("Running in MCP test mode - simulated responses enabled")
    else:
        logger.warning("MCP services unavailable - running in limited mode")
    
    # 2. Connect to LiveKit room
    logger.info(f"Connecting to room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # 3. Set up participant handlers
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
    
    # 4. Fetch configuration from database
    config = {
        "name": "Reliable Voice Assistant",
        "systemPrompt": "You are a helpful and friendly AI voice assistant. Speak naturally and conversationally.",
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
    
    # 5. Extract configuration
    voice = config.get("voice", "alloy")
    temp = float(config.get("temperature", 0.7))
    
    # 6. Create enhanced system prompt
    base_prompt = config.get("systemPrompt", "You are a helpful AI assistant.")
    if _mcp_test_mode:
        enhanced_prompt = f"""{base_prompt}

You are running in test mode. You have access to search_web and send_email functions that will return simulated results to demonstrate functionality."""
    elif _mcp_enabled:
        enhanced_prompt = f"""{base_prompt}

You have access to these tools:

🔍 Web Search: Use search_web(query) to find current information online
📧 Email: Use send_email(to, subject, body) to send emails

Use these tools naturally when users ask for searches or email sending. Keep responses conversational and helpful."""
    else:
        enhanced_prompt = f"""{base_prompt}

Note: External services (web search and email) are temporarily unavailable, but I can still help with questions and general assistance using my training data."""

    logger.info(f"Voice: {voice}, Temperature: {temp}, MCP: {'enabled' if _mcp_enabled else 'disabled'}")

    # 7. Create traditional voice pipeline (STT-LLM-TTS) for reliability
    logger.info("Creating reliable voice pipeline with function tools...")
    
    # Function tools list
    available_tools = []
    if _mcp_enabled or _mcp_test_mode:
        available_tools = [search_web, send_email]
        logger.info(f"Registered {len(available_tools)} function tools")
    
    # 8. Create agent with tools
    agent = Agent(
        instructions=enhanced_prompt,
        tools=available_tools if available_tools else None,
    )
    
    # 9. Create AgentSession with traditional voice pipeline
    session = AgentSession(
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
        logger.info("Reliable voice agent session started successfully!")
        
        # Generate a brief greeting
        greeting = "Hello! I'm your voice assistant. I can help with questions"
        if _mcp_enabled:
            greeting += ", web searches, and sending emails"
        greeting += ". How can I help you today?"
        
        await session.generate_reply(instructions=f"Greet the user with: {greeting}")
        
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise

if __name__ == "__main__":
    # Set up environment
    os.environ['LD_LIBRARY_PATH'] = "/nix/store/gcc-unwrapped-13.3.0/lib:/nix/store/glibc-2.39-52/lib:" + os.environ.get('LD_LIBRARY_PATH', '')
    
    # Run the agent
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))