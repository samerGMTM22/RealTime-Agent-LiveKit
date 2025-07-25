"""Working LiveKit + OpenAI Realtime API Voice Agent with MCP Integration"""
import logging
import requests
import asyncio
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, AgentSession, Agent, function_tool
from livekit.plugins import openai

logger = logging.getLogger("realtime-voice-agent")
load_dotenv()

# Global MCP manager for function tools
_mcp_enabled = False

class VoiceAssistant(Agent):
    """Voice assistant agent with Realtime API and MCP integration."""
    
    def __init__(self, config: Dict):
        super().__init__(instructions=config.get("systemPrompt", "You are a helpful AI assistant."))
        self.config = config
        self.name = config.get('name', 'Voice Assistant')

async def get_agent_config(room_name: str) -> Dict:
    """Fetch agent configuration from database API."""
    try:
        # Use active config endpoint
        response = requests.get("http://localhost:5000/api/agent-configs/active", timeout=10)
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
    """Default configuration fallback."""
    return {
        "id": 1,
        "name": "Voice Assistant",
        "systemPrompt": "You are a helpful AI assistant that can search the web and help with various tasks.",
        "voiceModel": "coral",
        "temperature": 80,
        "responseLength": "medium"
    }

@function_tool
async def search_web(query: str) -> str:
    """Search the web using MCP integration with result polling."""
    global _mcp_enabled
    
    if not _mcp_enabled:
        return f"I searched for '{query}' but MCP services are currently unavailable. Let me know if you'd like me to help with something else!"
    
    try:
        logger.info(f"Executing web search: {query}")
        
        # Use enhanced MCP endpoint with polling for actual results
        response = requests.post(
            'http://localhost:5000/api/mcp/execute',
            json={
                "serverId": 9,  # Internal search server
                "tool": "execute_web_search", 
                "params": {"query": query}
            },
            timeout=45  # Extended timeout for polling
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                result = data.get("result", "")
                formatted_result = format_search_results(result, query)
                logger.info(f"Web search completed successfully for: {query}")
                return formatted_result
            else:
                error_msg = data.get("error", "Unknown error")
                logger.error(f"MCP search failed: {error_msg}")
                return f"I tried to search for '{query}' but encountered an issue: {error_msg}"
        else:
            logger.error(f"MCP API error: {response.status_code}")
            return f"I'm having trouble accessing search services right now. Status: {response.status_code}"
            
    except requests.exceptions.Timeout:
        logger.error(f"Search timeout for query: {query}")
        return f"The search for '{query}' is taking longer than expected. Please try again with a more specific query."
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return f"I encountered an error while searching for '{query}'. Please try rephrasing your request."

@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email using Zapier MCP integration."""
    global _mcp_enabled
    
    if not _mcp_enabled:
        return "Email services are currently unavailable. Please try again later."
    
    try:
        logger.info(f"Sending email to: {to}")
        
        # Use Zapier MCP server for email
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
            timeout=45  # Increased timeout for Zapier MCP
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                logger.info(f"Email sent successfully to: {to}")
                return f"✅ Email sent successfully to {to} with subject '{subject}'"
            else:
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Email send failed: {error_msg}")
                return f"Failed to send email: {error_msg}"
        else:
            logger.error(f"Email API error: {response.status_code}")
            return f"Email service temporarily unavailable. Status: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        return f"I encountered an error while sending the email: {str(e)}"

async def get_available_mcp_tools() -> List[Dict]:
    """Get available MCP servers and their capabilities."""
    try:
        response = requests.get("http://localhost:5000/api/mcp/servers", timeout=10)
        if response.status_code == 200:
            servers = response.json()
            return [server for server in servers if server.get("isActive", True)]
    except Exception as e:
        logger.error(f"Error fetching MCP servers: {e}")
    return []

def format_search_results(result: str, query: str) -> str:
    """Format search results for better voice output."""
    try:
        import json
        
        # Try to parse as JSON first
        if result.startswith('{') or result.startswith('['):
            try:
                data = json.loads(result)
                if isinstance(data, list) and len(data) > 0:
                    formatted = f"I found {len(data)} results for '{query}':\n\n"
                    for i, item in enumerate(data[:3], 1):  # Limit to top 3 for voice
                        if isinstance(item, dict):
                            title = item.get('title', item.get('name', ''))
                            snippet = item.get('snippet', item.get('description', ''))
                            if title:
                                formatted += f"{i}. {title}\n"
                                if snippet:
                                    # Truncate long snippets for voice readability
                                    clean_snippet = snippet.replace('\n', ' ').strip()
                                    if len(clean_snippet) > 120:
                                        clean_snippet = clean_snippet[:120] + "..."
                                    formatted += f"   {clean_snippet}\n\n"
                    return formatted
                elif isinstance(data, dict):
                    # Handle single result object
                    title = data.get('title', data.get('name', ''))
                    content = data.get('content', data.get('description', data.get('snippet', '')))
                    if title and content:
                        return f"I found information about '{query}':\n\n{title}\n{content[:200]}..."
            except json.JSONDecodeError:
                pass
        
        # Handle as text with intelligent formatting
        lines = result.split('\n')
        meaningful_lines = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
        
        if meaningful_lines:
            formatted = f"Here's what I found for '{query}':\n\n"
            for i, line in enumerate(meaningful_lines[:3], 1):
                # Clean up the line
                clean_line = line.replace('  ', ' ').strip()
                if len(clean_line) > 150:
                    clean_line = clean_line[:150] + "..."
                formatted += f"{i}. {clean_line}\n\n"
            return formatted
        else:
            # Fallback for simple text
            clean_result = result.replace('\n', ' ').strip()
            if len(clean_result) > 300:
                clean_result = clean_result[:300] + "..."
            return f"I found this information about '{query}': {clean_result}"
            
    except Exception as e:
        logger.error(f"Error formatting search results: {e}")
        # Simple fallback
        clean_result = str(result).replace('\n', ' ').strip()
        if len(clean_result) > 200:
            clean_result = clean_result[:200] + "..."
        return f"I found some information about '{query}': {clean_result}"

async def check_mcp_status() -> bool:
    """Check if MCP services are available."""
    try:
        response = requests.get("http://localhost:5000/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("mcp") == "connected"
    except Exception as e:
        logger.error(f"Error checking MCP status: {e}")
    return False

async def entrypoint(ctx: JobContext):
    """Main entry point - Working LiveKit + OpenAI Realtime API integration."""
    logger.info(f"Starting LiveKit Realtime API agent for room: {ctx.room.name}")
    
    # Check MCP availability
    global _mcp_enabled
    _mcp_enabled = await check_mcp_status()
    if _mcp_enabled:
        logger.info("MCP services are available - search functionality enabled")
    else:
        logger.warning("MCP services unavailable - running without search")
    
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
    
    # 4. Get configuration from database
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
    
    logger.info(f"Voice: {voice}, Temperature: {realtime_temp}, MCP: {'enabled' if _mcp_enabled else 'disabled'}")

    # 5. Create enhanced system prompt with MCP capabilities
    base_prompt = config.get("systemPrompt", "You are a helpful AI assistant.")
    if _mcp_enabled:
        enhanced_prompt = f"""{base_prompt}

You have access to powerful tools through MCP (Model Context Protocol) integration:

🔍 **Web Search** (search_web function):
- Use for current events, news, or recent developments
- Search for specific facts, statistics, or technical information  
- Find business information, product details, or reviews
- Get weather, sports scores, or real-time data
- Any question where fresh information would be valuable

📧 **Email Communication** (send_email function):
- Send emails through Zapier integration
- Format: send_email(to="email@example.com", subject="Subject", body="Message")
- Always confirm email details before sending

When users ask about searching the internet or sending emails, use these functions to provide real, actionable results. Always respond naturally and conversationally."""
    else:
        enhanced_prompt = f"""{base_prompt}

Note: MCP services (web search and email capabilities) are currently unavailable, but I can still help with general questions, explanations, and tasks that don't require real-time information."""

    # 6. Create AgentSession with OpenAI Realtime API
    logger.info("Starting OpenAI Realtime API session with LiveKit integration...")
    
    # Configure turn detection to be less aggressive
    from openai.types.beta.realtime.session import TurnDetection
    
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            voice=voice,
            temperature=realtime_temp,
            turn_detection=TurnDetection(
                type="server_vad",
                threshold=0.7,  # Higher = less sensitive (was 0.5)
                prefix_padding_ms=400,  # More padding before speech
                silence_duration_ms=1000,  # Wait longer before cutting off (was 500ms)
                create_response=True,
                interrupt_response=True,
            )
        ),
        allow_interruptions=True,
        min_interruption_duration=0.8,  # Increased from 0.5
        min_endpointing_delay=0.8,  # Increased from 0.5
        max_endpointing_delay=8.0,  # Increased from 6.0
    )

    # 7. Create function tools list based on MCP availability
    from typing import List, Union
    from livekit.agents import FunctionTool, RawFunctionTool
    
    available_tools: List[Union[FunctionTool, RawFunctionTool]] = []
    if _mcp_enabled:
        available_tools = [search_web, send_email]
        logger.info(f"Registered {len(available_tools)} MCP function tools")
    else:
        logger.info("No MCP tools registered - services unavailable")
    
    # 8. Create assistant with enhanced system prompt and tools
    enhanced_config = config.copy()
    enhanced_config["systemPrompt"] = enhanced_prompt
    assistant = VoiceAssistant(enhanced_config)
    
    # 9. Create Agent with function tools
    agent = Agent(
        instructions=enhanced_prompt,
        tools=available_tools,
    )
    
    # 10. Start session with proper LiveKit integration
    await session.start(room=ctx.room, agent=agent)
    
    # 11. Generate initial greeting - use chat_ctx to avoid system prompt confusion
    # Don't use generate_reply with instructions as it can confuse system/user prompts
    logger.info("Agent ready and waiting for user interaction")
    
    logger.info("LiveKit + OpenAI Realtime API session started successfully")

if __name__ == "__main__":
    # Set up proper environment for LiveKit
    import os
    os.environ['LD_LIBRARY_PATH'] = "/nix/store/gcc-unwrapped-13.3.0/lib:/nix/store/glibc-2.39-52/lib:" + os.environ.get('LD_LIBRARY_PATH', '')
    
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))