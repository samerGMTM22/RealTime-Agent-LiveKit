#!/usr/bin/env python
"""
Enhanced LiveKit + OpenAI Realtime API Voice Agent with MCP Integration
Features:
- Improved turn detection to prevent voice cutting off
- Better error handling for MCP timeouts
- Clear separation of system prompts vs user inputs
- Fallback mode when MCP services are unavailable
"""
import asyncio
import os
import logging
import requests
from typing import Optional, Dict, Any, List, Union

# LiveKit imports with proper error handling
try:
    from livekit import rtc
    from livekit.agents import (
        JobContext, WorkerOptions, cli, AutoSubscribe, 
        AgentSession, Agent, function_tool,
        FunctionTool, RawFunctionTool
    )
    from livekit.plugins import openai
    from openai.types.beta.realtime.session import TurnDetection
except ImportError as e:
    print(f"Error importing LiveKit libraries: {e}")
    print("Make sure to install: pip install livekit-agents[openai]")
    exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("realtime-voice-agent")

# Global flag for MCP availability
_mcp_enabled = False
_mcp_test_mode = os.getenv("MCP_TEST_MODE", "false").lower() == "true"

# Test configuration
if _mcp_test_mode:
    logger.info("Running in MCP test mode - simulating responses")

class VoiceAssistant(Agent):
    """Custom agent class for voice interactions"""
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config

# Function tools with better error handling
@function_tool
async def search_web(query: str) -> str:
    """Search the web using MCP integration with improved error handling."""
    global _mcp_enabled, _mcp_test_mode
    
    # Test mode - return simulated results
    if _mcp_test_mode:
        logger.info(f"[TEST MODE] Simulating web search for: {query}")
        return f"[Test Mode] Search results for '{query}': This is a simulated response showing that the search function is working correctly. In production, this would return real search results."
    
    if not _mcp_enabled:
        return f"I understand you want to search for '{query}', but web search is currently unavailable. I can still help answer questions based on my knowledge."
    
    try:
        logger.info(f"Executing web search: {query}")
        
        # Use enhanced MCP endpoint with better timeout handling
        response = requests.post(
            'http://localhost:5000/api/mcp/execute',
            json={
                "serverId": 9,  # Internal search server
                "tool": "execute_web_search", 
                "params": {"query": query}
            },
            timeout=45  # Extended timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                result = data.get("result", "")
                logger.info(f"Web search completed successfully")
                return format_search_results(result, query)
            else:
                error_msg = data.get("error", "Unknown error")
                logger.error(f"MCP search failed: {error_msg}")
                
                # Provide helpful fallback response
                if "timeout" in error_msg.lower():
                    return f"The search is taking longer than expected. Let me share what I know about '{query}' from my existing knowledge instead."
                else:
                    return f"I couldn't complete the web search right now, but I can still help answer questions about '{query}' based on my knowledge."
        else:
            logger.error(f"MCP API error: {response.status_code}")
            return f"I'm having trouble accessing search services (error {response.status_code}). I'll do my best to help with what I know."
            
    except requests.exceptions.Timeout:
        logger.error(f"Search timeout for query: {query}")
        return f"The search is taking too long. Let me share what I know about '{query}' instead of waiting for search results."
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error during search")
        return f"I can't connect to search services right now. Let me help you with '{query}' using my existing knowledge."
    except Exception as e:
        logger.error(f"Unexpected search error: {str(e)}")
        return f"I encountered an issue while searching. Let me help you with '{query}' using my available knowledge instead."

@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email using Zapier MCP integration with improved error handling."""
    global _mcp_enabled, _mcp_test_mode
    
    # Test mode - simulate email sending
    if _mcp_test_mode:
        logger.info(f"[TEST MODE] Simulating email to: {to}")
        return f"[Test Mode] ✅ Email simulated successfully!\nTo: {to}\nSubject: {subject}\nBody preview: {body[:100]}..."
    
    if not _mcp_enabled:
        return "Email services are currently unavailable. Please try again later or use an alternative method."
    
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
            timeout=45  # Extended timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                logger.info(f"Email sent successfully to: {to}")
                return f"✅ Email sent successfully to {to}! The message with subject '{subject}' has been delivered."
            else:
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Email send failed: {error_msg}")
                
                if "timeout" in error_msg.lower():
                    return f"The email service is taking longer than expected. The email to {to} may still be sent in the background."
                else:
                    return f"I couldn't send the email right now. Error: {error_msg}. Please try again later."
        else:
            logger.error(f"Email API error: {response.status_code}")
            return f"Email service returned an error (code {response.status_code}). Please try again later."
            
    except requests.exceptions.Timeout:
        logger.error(f"Email timeout")
        return f"The email service is taking too long to respond. Your email to {to} might still be processing."
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error during email send")
        return f"I can't connect to the email service right now. Please try sending your email to {to} later."
    except Exception as e:
        logger.error(f"Unexpected email error: {str(e)}")
        return f"An unexpected error occurred while sending the email: {str(e)}"

def format_search_results(result: str, query: str) -> str:
    """Format search results for voice output"""
    if not result or result == "No results found":
        return f"I searched for '{query}' but didn't find any specific results. Would you like me to search for something related?"
    
    # Format for voice-friendly output
    formatted = f"Here's what I found about {query}:\n\n{result}"
    
    # Truncate if too long for voice
    if len(formatted) > 500:
        formatted = formatted[:497] + "..."
        formatted += "\n\nThere's more information available. Would you like me to continue or search for something specific?"
    
    return formatted

async def check_mcp_availability() -> bool:
    """Check if MCP services are available with timeout"""
    try:
        response = requests.get("http://localhost:5000/api/mcp/servers", timeout=5)
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
    """Main entry point for the voice agent"""
    global _mcp_enabled
    
    # 1. Check MCP availability
    _mcp_enabled = await check_mcp_availability()
    if _mcp_enabled:
        logger.info("MCP services are available - full functionality enabled")
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
            # Ensure we subscribe to audio tracks
            publication.set_subscribed(True)
    
    # 4. Fetch configuration from database
    config = {
        "name": "Voice Assistant",
        "systemPrompt": "You are a helpful and friendly AI voice assistant. Speak naturally and conversationally.",
        "model": "gpt-4o-realtime-preview",
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
    realtime_temp = float(config.get("temperature", 0.7))
    
    # 6. Create enhanced system prompt
    base_prompt = config.get("systemPrompt", "You are a helpful AI assistant.")
    if _mcp_test_mode:
        enhanced_prompt = f"""{base_prompt}

You are currently running in test mode. Function tools are available but will return simulated results.
You have access to search_web and send_email functions - use them to demonstrate functionality."""
    elif _mcp_enabled:
        enhanced_prompt = f"""{base_prompt}

You have access to powerful tools:

🔍 **Web Search** (search_web function):
- Search for current information, news, facts, and real-time data
- Example: "Search for the latest news about AI"

📧 **Email** (send_email function):
- Send emails through our integration
- Example: "Send an email to john@example.com about our meeting"

Use these tools naturally when users ask for searches or email sending."""
    else:
        enhanced_prompt = f"""{base_prompt}

Note: External services (web search and email) are temporarily unavailable, but I can still help with questions and general assistance."""

    logger.info(f"Voice: {voice}, Temperature: {realtime_temp}, MCP: {'enabled' if _mcp_enabled else 'disabled'}")

    # 7. Create AgentSession with improved turn detection
    logger.info("Creating OpenAI Realtime API session with optimized settings...")
    
    try:
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                model="gpt-4o-realtime-preview",
                voice=voice,
                temperature=realtime_temp,
                turn_detection=TurnDetection(
                    type="server_vad",
                    threshold=0.7,  # Less sensitive
                    prefix_padding_ms=400,  # More padding
                    silence_duration_ms=1000,  # Wait longer
                    create_response=True,
                    interrupt_response=True,
                )
            ),
            allow_interruptions=True,
            min_interruption_duration=0.8,
            min_endpointing_delay=0.8,
            max_endpointing_delay=8.0,
        )
    except Exception as e:
        logger.error(f"Failed to create Realtime session: {e}")
        # Fallback to standard model if Realtime fails
        logger.info("Falling back to standard OpenAI model")
        session = AgentSession(
            llm=openai.LLM(model="gpt-4o-mini"),
            stt=openai.STT(),
            tts=openai.TTS(voice=voice),
        )
    
    # 8. Create function tools list
    available_tools: List[Union[FunctionTool, RawFunctionTool]] = []
    if _mcp_enabled or _mcp_test_mode:
        available_tools = [search_web, send_email]
        logger.info(f"Registered {len(available_tools)} function tools")
    
    # 9. Create agent with tools
    agent = Agent(
        instructions=enhanced_prompt,
        tools=available_tools if available_tools else None,
    )
    
    # 10. Start session
    try:
        await session.start(room=ctx.room, agent=agent)
        logger.info("Voice agent session started successfully!")
        
        # Log ready state without automatic greeting
        logger.info("Agent is ready and listening for user input")
        
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise

if __name__ == "__main__":
    # Set up environment
    os.environ['LD_LIBRARY_PATH'] = "/nix/store/gcc-unwrapped-13.3.0/lib:/nix/store/glibc-2.39-52/lib:" + os.environ.get('LD_LIBRARY_PATH', '')
    
    # Run the agent
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))