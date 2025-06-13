import logging
import os
import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Add the workspace root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, llm, AgentSession, Agent
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero
import requests
import time

# Import simplified MCP integration 
from mcp_integration.simple_client import SimpleMCPManager

# Global MCP manager to be accessible by function tools
_mcp_manager = None

logger = logging.getLogger("voice-agent")
load_dotenv()

# Define function tools at module level (expert's recommendation)
@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    logger.info(f"FUNCTION ACTUALLY EXECUTED: search_web({query})")
    execution_time = time.time()
    
    try:
        global _mcp_manager
        if _mcp_manager:
            # Try to execute via MCP manager
            for server_id, client in _mcp_manager.connected_servers.items():
                if "internet" in client.name.lower():
                    result = await _mcp_manager.call_tool(server_id, "search", {"query": query})
                    if "error" not in result:
                        logger.info(f"FUNCTION COMPLETED at {execution_time}: MCP search successful")
                        return result.get("content", "Search completed successfully")
        
        # Fallback to Express API
        logger.info(f"Making Express API call for search: {query}")
        response = requests.post('http://localhost:5000/api/mcp/execute', 
                               json={"tool": "search", "params": {"query": query}}, 
                               timeout=10)
        logger.info(f"Express API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Express API response data: {data}")
            if data.get("success"):
                logger.info(f"FUNCTION COMPLETED at {execution_time}: Express API successful")
                return data.get("result", "Search completed")
            else:
                return f"Search failed: {data.get('error', 'Unknown error')}"
        else:
            return "Search service unavailable"
            
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return f"Search failed: {str(e)}"

@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Zapier MCP integration."""
    logger.info(f"FUNCTION ACTUALLY EXECUTED: send_email(to={to}, subject={subject})")
    execution_time = time.time()
    
    try:
        global _mcp_manager
        if _mcp_manager:
            # Try to execute via MCP manager
            for server_id, client in _mcp_manager.connected_servers.items():
                if "zapier" in client.name.lower() or "email" in client.name.lower():
                    result = await _mcp_manager.call_tool(server_id, "send_email", 
                                                       {"to": to, "subject": subject, "body": body})
                    if "error" not in result:
                        logger.info(f"FUNCTION COMPLETED at {execution_time}: MCP email successful")
                        return "Email sent successfully via MCP"
        
        # Fallback to Express API
        logger.info(f"Making Express API call for email: {to}")
        response = requests.post('http://localhost:5000/api/mcp/execute', 
                               json={"tool": "send_email", "params": {"to": to, "subject": subject, "body": body}}, 
                               timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                logger.info(f"FUNCTION COMPLETED at {execution_time}: Express API email successful")
                return "Email sent successfully"
            else:
                return f"Email send failed: {data.get('error', 'Unknown error')}"
        else:
            return "Email service unavailable"
            
    except Exception as e:
        logger.error(f"Error in email send: {e}")
        return f"Email send failed: {str(e)}"


async def get_agent_config(room_name: str):
    """Fetch agent configuration from the database based on room name."""
    try:
        # Default to agent config ID 1 for now
        agent_config_id = 1
        
        # Make request to get agent configuration
        response = requests.get(f'http://localhost:5000/api/agent-configs/{agent_config_id}', timeout=5)
        if response.status_code == 200:
            config = response.json()
            logger.info(f"Fetched config from database: {config['name']}")
            return config
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
    
    # Fallback configuration
    return {
        "systemPrompt": "You are a helpful AI assistant.",
        "voiceModel": "alloy",
        "temperature": 80,
        "responseLength": "medium"
    }


class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        super().__init__(instructions=system_prompt)
        self.config = config

    # Define MCP tools as proper class methods with function_tool decorator
    @function_tool
    async def search_web(self, query: str):
        """Search the web for current information using MCP internet access tools.
        
        Args:
            query: The search query to find current information
        """
        logger.info(f"Executing web search for: {query}")
        
        try:
            # Use MCP manager if available
            if self.mcp_manager and hasattr(self, '_mcp_tool_mapping'):
                for server_id, client in self.mcp_manager.connected_servers.items():
                    if "internet" in client.name.lower():
                        result = await self.mcp_manager.call_tool(server_id, "search", {"query": query})
                        if "error" not in result:
                            return result.get("content", "Search completed successfully")
            
            # Force Express API call for debugging
            logger.info(f"Making Express API call for search: {query}")
            response = requests.post('http://localhost:5000/api/mcp/execute', 
                                   json={"tool": "search", "params": {"query": query}}, 
                                   timeout=10)
            logger.info(f"Express API response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Express API response data: {data}")
                if data.get("success"):
                    return data.get("result", "Search completed")
                else:
                    return f"Search failed: {data.get('error', 'Unknown error')}"
                    
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return "Web search is currently unavailable. Please check MCP server connections."

    @function_tool
    async def send_email(self, to: str, subject: str, body: str):
        """Send an email via Zapier MCP integration.
        
        Args:
            to: Email recipient address
            subject: Email subject line
            body: Email message content
        """
        logger.info(f"Sending email to: {to}")
        
        try:
            # Use MCP manager if available
            if self.mcp_manager and hasattr(self, '_mcp_tool_mapping'):
                for server_id, client in self.mcp_manager.connected_servers.items():
                    if "zapier" in client.name.lower():
                        result = await self.mcp_manager.call_tool(server_id, "send_email", {
                            "to": to, "subject": subject, "body": body
                        })
                        if "error" not in result:
                            return result.get("content", "Email sent successfully via Zapier")
            
            return "Email functionality is available via Zapier MCP integration"
                    
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return "Email functionality is currently unavailable. Please check Zapier MCP server connection."

    @function_tool
    async def get_available_tools(self):
        """Lists available MCP tools and capabilities."""
        
        logger.info("Checking available MCP tools")
        
        if self.mcp_manager and self.mcp_manager.connected_servers:
            tools_info = []
            for server_id, server in self.mcp_manager.connected_servers.items():
                tools_info.append(f"- {server.name}: Connected and available")
            
            if self.mcp_tools:
                tools_info.append(f"- {len(self.mcp_tools)} tools loaded from MCP servers")
            
            return "Available external tools:\n" + "\n".join(tools_info)
        else:
            return "No external tools currently available. I can assist with general inquiries using my knowledge."




async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent following expert guidelines."""
    logger.info(f"Agent started for room: {ctx.room.name}")
    
    # Connect to room with audio-only subscription
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Ensure audio track subscription as recommended by expert
    @ctx.room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if publication.kind == "audio":
            publication.set_subscribed(True)
            logger.info(f"Subscribed to audio track from {participant.identity}")
    
    # Wait for a participant to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")
    
    # Get agent configuration from REST API
    try:
        config = await get_agent_config(ctx.room.name)
        logger.info(f"Using agent config: {config.get('name', 'Default')}")
        logger.info(f"System prompt: {config.get('systemPrompt', 'Default')[:100]}...")
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        config = {
            "systemPrompt": "You are a helpful AI assistant.",
            "voiceModel": "alloy",
            "temperature": 80,
            "responseLength": "medium"
        }
    
    # Map voice model names to OpenAI voice options
    voice_mapping = {
        "alloy": "alloy",
        "echo": "echo", 
        "fable": "fable",
        "onyx": "onyx",
        "nova": "nova",
        "shimmer": "shimmer",
        "coral": "coral"
    }
    
    voice = voice_mapping.get(config.get("voiceModel", "alloy"), "alloy")
    temp_raw = config.get("temperature", 80)
    realtime_temp = max(0.6, min(1.2, 0.6 + (float(temp_raw) / 100.0) * 0.6))
    
    logger.info(f"Voice: {voice}, Temperature: {realtime_temp}")

    try:
        logger.info("Attempting OpenAI Realtime API")
        
        # Create assistant and start MCP initialization asynchronously
        assistant = Assistant(config)
        
        # Start MCP initialization in background (non-blocking)
        mcp_task = asyncio.create_task(assistant.initialize_mcp(user_id=1))
        
        # Create AgentSession with Realtime API
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

        await session.start(
            room=ctx.room,
            agent=assistant,
        )
        
        # Generate initial greeting
        await session.generate_reply(
            instructions="Greet the user warmly and offer your assistance."
        )
        
        # Wait for MCP initialization with timeout
        try:
            mcp_servers = await asyncio.wait_for(mcp_task, timeout=10.0)
            if mcp_servers:
                logger.info(f"MCP servers loaded: {len(mcp_servers)}")
                await session.generate_reply(
                    instructions=f"Inform the user that {len(mcp_servers)} external tools are now available for enhanced assistance."
                )
        except asyncio.TimeoutError:
            logger.warning("MCP initialization timed out, continuing with voice-only functionality")
        
        logger.info("OpenAI Realtime API agent started successfully")
        
    except Exception as e:
        logger.error(f"Realtime API failed: {e}")
        logger.info("Falling back to STT-LLM-TTS pipeline")
        
        # Convert temperature for standard LLM
        llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
        
        # Create assistant for fallback
        assistant = Assistant(config)
        
        # Create STT-LLM-TTS pipeline as fallback
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(model="whisper-1"),
            llm=openai.LLM(model="gpt-4o", temperature=llm_temp),
            tts=openai.TTS(model="tts-1", voice=voice),
        )

        await session.start(
            room=ctx.room, 
            agent=assistant
        )
        
        logger.info("STT-LLM-TTS pipeline started successfully")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))