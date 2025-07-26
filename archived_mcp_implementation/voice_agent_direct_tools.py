"""
LiveKit Voice Agent with Direct N8N and Zapier Tool Integration
Based on definitive solution architecture - uses HTTP webhooks instead of MCP protocol
"""
import asyncio
import logging
import requests
from typing import Any
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, AgentSession, Agent, function_tool
from livekit.plugins import openai, silero
from livekit.agents.llm import ChatContext
from dotenv import load_dotenv

# Import tool implementations
import os
import json
import aiohttp

# Configure logging with filters for audio data
import sys

class AudioDataFilter(logging.Filter):
    def filter(self, record):
        # Filter out binary audio data from logs
        msg = str(record.getMessage())
        if '\\x' in msg or len(msg) > 1000:
            return False
        return True

# Apply audio filter to all loggers
def setup_logging():
    """Setup logging with audio data filters"""
    audio_filter = AudioDataFilter()
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Apply filter to all common loggers
    for logger_name in ['voice-agent-direct-tools', 'livekit', 'livekit.agents', 'openai', 'httpx']:
        logger = logging.getLogger(logger_name)
        logger.addFilter(audio_filter)
        # Reduce verbosity for audio-heavy loggers
        if logger_name in ['httpx', 'openai']:
            logger.setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger("voice-agent-direct-tools")
load_dotenv()

# Test MCP backend connectivity
try:
    test_response = requests.get("http://localhost:5000/api/mcp/health", timeout=5)
    if test_response.status_code == 200:
        logger.info("✅ MCP backend is available")
    else:
        logger.warning("⚠️ MCP backend responded but may have issues")
except Exception as e:
    logger.error(f"❌ MCP backend not available: {e}")

# Global server configurations (loaded once on startup)
MCP_SERVERS = {}

async def load_mcp_servers():
    """Load MCP server configurations from database"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:5000/api/mcp/servers") as resp:
                if resp.status == 200:
                    servers = await resp.json()
                    for server in servers:
                        MCP_SERVERS[server['id']] = server
                    logger.info(f"✅ Loaded {len(MCP_SERVERS)} MCP servers from database")
                else:
                    logger.error(f"Failed to load MCP servers: HTTP {resp.status}")
    except Exception as e:
        logger.error(f"Error loading MCP servers: {e}")

# Add MCP Tool Executor class
class MCPToolExecutor:
    """Handles direct HTTP execution using database-configured URLs"""
    
    @staticmethod
    async def execute_tool(server_id: int, tool_name: str, params: dict) -> dict:
        """Execute tool via backend MCP proxy using database configuration"""
        try:
            # Use the backend MCP proxy which handles the actual execution
            payload = {
                "serverId": server_id,
                "tool": tool_name,
                "params": params
            }
            
            logger.info(f"🔧 Executing {tool_name} on server {server_id} via MCP proxy")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:5000/api/mcp/execute",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=35)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("success"):
                            result_content = data.get("result", "")
                            logger.info(f"✅ Tool {tool_name} succeeded")
                            return {"success": True, "content": result_content}
                        else:
                            error_msg = data.get("error", "Unknown error")
                            logger.error(f"❌ Tool {tool_name} failed: {error_msg}")
                            return {"success": False, "error": error_msg}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                        
        except Exception as e:
            logger.error(f"Tool execution exception: {e}")
            return {"success": False, "error": str(e)}

# Define function tools with database-driven configuration
@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information."""
    logger.info(f"🔍 Web search requested: {query}")
    
    # Find N8N server from loaded configurations
    n8n_server = next((s for s in MCP_SERVERS.values() if 'n8n' in s.get('name', '').lower() or 'n8n' in s.get('url', '')), None)
    
    if not n8n_server:
        logger.error("N8N server not found in database")
        return "I need to configure the N8N server first. Please set it up in the dashboard."
    
    result = await MCPToolExecutor.execute_tool(
        server_id=n8n_server['id'],
        tool_name="search",  # Using standard tool name
        params={"query": query}
    )
    
    if result["success"]:
        content = result.get("content", "")
        if content:
            return f"Here's what I found about '{query}':\n\n{content}"
        else:
            return f"I searched for '{query}' but didn't find specific results."
    else:
        return f"I couldn't search for '{query}' right now due to: {result.get('error', 'unknown error')}"

@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email using Zapier."""
    logger.info(f"📧 Email send requested to: {to}")
    
    # Find Zapier server from loaded configurations
    zapier_server = next((s for s in MCP_SERVERS.values() if 'zapier' in s.get('name', '').lower()), None)
    
    if not zapier_server:
        logger.error("Zapier server not found in database")
        return "I need to configure the Zapier server first. Please set it up in the dashboard."
    
    result = await MCPToolExecutor.execute_tool(
        server_id=zapier_server['id'],
        tool_name="send_email",
        params={"to": to, "subject": subject, "body": body}
    )
    
    if result["success"]:
        return f"✅ Email sent successfully to {to}!"
    else:
        return f"❌ Failed to send email to {to}: {result.get('error', 'unknown error')}"

async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent with direct tool integration."""
    
    # 0. Load MCP server configurations from database
    await load_mcp_servers()
    
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
    
    logger.info(f"✅ Direct HTTP tools configured for N8N and Zapier")
    logger.info(f"Voice: {config.get('voiceModel', 'alloy')}, Temperature: {temp} (raw: {temp_raw})")
    
    # 4. Create Agent with instructions and tools
    agent = Agent(
        instructions=config.get("systemPrompt", "You are a helpful voice assistant with web search and email capabilities."),
        tools=[search_web, send_email]  # Register our function tools directly
    )
    
    # 5. Create session with STT-LLM-TTS pipeline
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(language="en"),
        llm=openai.LLM(
            model="gpt-4o",
            temperature=temp,
        ),
        tts=openai.TTS(voice=config.get("voiceModel", "alloy")),
    )
    
    # 6. Start the session
    await session.start(agent=agent, room=ctx.room)
    
    logger.info("Voice agent session started successfully with direct tool integration!")
    
    # Initial greeting
    await session.generate_reply(instructions="Greet the user warmly and let them know you can search the web or send emails.")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))