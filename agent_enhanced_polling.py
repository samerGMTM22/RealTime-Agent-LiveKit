"""Enhanced LiveKit Voice Agent with Job Polling MCP Integration"""
import logging
import os
import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv

# Add the workspace root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, llm, AgentSession, Agent
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero
import httpx

# Import the new job polling MCP integration
from mcp_integration.storage import PostgreSQLStorage
from mcp_integration.universal_manager import UniversalMCPDispatcher

# Global MCP dispatcher
_mcp_dispatcher = None

logger = logging.getLogger("voice-agent")
load_dotenv()

def format_search_results(result: Any) -> str:
    """Format search results for better voice output."""
    try:
        if isinstance(result, dict):
            # Handle structured search results
            if 'content' in result:
                content = result['content']
                if isinstance(content, list):
                    formatted = "Here's what I found:\n\n"
                    for i, item in enumerate(content[:3], 1):
                        if isinstance(item, dict):
                            title = item.get('title', item.get('name', ''))
                            snippet = item.get('snippet', item.get('description', ''))
                            formatted += f"{i}. {title}\n"
                            if snippet:
                                formatted += f"   {snippet[:100]}...\n\n"
                        else:
                            formatted += f"{i}. {str(item)[:100]}...\n\n"
                    return formatted
                else:
                    return str(content)[:500]
            else:
                return str(result)[:500]
        elif isinstance(result, list):
            formatted = "Here are the results:\n\n"
            for i, item in enumerate(result[:3], 1):
                formatted += f"{i}. {str(item)[:100]}...\n\n"
            return formatted
        else:
            formatted = str(result)
            if len(formatted) > 500:
                formatted = formatted[:500] + "... I can provide more details if needed."
            return formatted
    except Exception as e:
        logger.error(f"Error formatting search results: {e}")
        return "I found some results but had trouble formatting them. Let me try again."

async def search_web(query: str) -> str:
    """Search the web for current information using MCP job polling."""
    global _mcp_dispatcher
    
    if not _mcp_dispatcher:
        return "MCP dispatcher not initialized. Please wait a moment and try again."
    
    try:
        logger.info(f"Searching web for: {query}")
        
        # Look for web search tools in the registry
        available_tools = await _mcp_dispatcher.get_available_tools()
        search_tools = [t for t in available_tools if 'search' in t['name'].lower() or 'web' in t['name'].lower()]
        
        if not search_tools:
            return "No web search tools are currently available. Please check your MCP server configuration."
        
        # Use the first available search tool
        search_tool = search_tools[0]
        tool_name = search_tool['name']
        
        logger.info(f"Using search tool: {tool_name}")
        
        # Execute the search with polling
        result = await _mcp_dispatcher.execute_tool(
            tool_name=tool_name,
            params={"query": query},
            timeout=35  # Extended timeout for polling
        )
        
        if result:
            formatted_result = format_search_results(result)
            logger.info(f"Search completed successfully for: {query}")
            return formatted_result
        else:
            return "I completed the search but didn't receive any results. The search might be processing."
            
    except asyncio.TimeoutError:
        logger.error(f"Search timed out for query: {query}")
        return "The search is taking longer than expected. This might be due to high server load. Please try again in a moment."
    except Exception as e:
        logger.error(f"Search error for query '{query}': {e}")
        return f"I encountered an error while searching: {str(e)[:100]}. Please try rephrasing your query."

async def send_email_disabled(to: str, subject: str, body: str) -> str:
    """Send an email via MCP integration - TEMPORARILY DISABLED."""
    return "Email functionality is temporarily disabled while we upgrade the system. Please try again later."

async def get_agent_config(room_name: str):
    """Fetch agent configuration from the database based on room name."""
    try:
        # Use the Express API to get agent config
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:5000/api/agent-configs/active")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch agent config: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error fetching agent config: {e}")
        return None

class Assistant(Agent):
    def __init__(self, config: dict, tools: list = None) -> None:
        super().__init__()
        
        # Initialize with enhanced configuration
        self.config = config
        self.system_prompt = config.get('systemPrompt', 'You are a helpful voice assistant.')
        self.personality = config.get('personality', 'friendly')
        self.voice_model = config.get('voiceModel', 'alloy')
        self.temperature = config.get('temperature', 70) / 100.0  # Convert to 0-1 scale
        
        # Initialize OpenAI LLM with configuration
        self.llm = openai.LLM(
            model="gpt-4o-mini",
            temperature=self.temperature,
        )
        
        # Initialize TTS
        self.tts = openai.TTS(
            voice=self.voice_model,
            model="tts-1",
        )
        
        # Initialize tools - include MCP tools when available
        default_tools = [
            llm.function_tool(search_web),
            llm.function_tool(send_email_disabled),
        ]
        
        self.tools = tools if tools else default_tools
        
        logger.info(f"Assistant initialized with personality: {self.personality}, voice: {self.voice_model}")

    async def initialize_mcp(self, user_id: int = 1):
        """Initialize MCP dispatcher with job polling."""
        global _mcp_dispatcher
        
        try:
            logger.info("Initializing MCP dispatcher with job polling...")
            
            # Create storage and dispatcher
            storage = PostgreSQLStorage()
            _mcp_dispatcher = UniversalMCPDispatcher(storage)
            
            # Initialize tools from database
            await _mcp_dispatcher.initialize_tools(user_id)
            
            # Get available tools and add them to the agent
            available_tools = await _mcp_dispatcher.get_available_tools()
            
            logger.info(f"MCP initialization complete. Available tools: {len(available_tools)}")
            
            # Add dynamic MCP tools
            for tool_info in available_tools:
                tool_name = tool_info['name']
                
                # Create a dynamic function for each MCP tool
                async def mcp_tool_wrapper(tool_name=tool_name, **kwargs):
                    try:
                        result = await _mcp_dispatcher.execute_tool(tool_name, kwargs)
                        return format_search_results(result)
                    except Exception as e:
                        logger.error(f"MCP tool '{tool_name}' error: {e}")
                        return f"Error executing {tool_name}: {str(e)[:100]}"
                
                # Add the tool to the available tools
                self.tools.append(llm.function_tool(mcp_tool_wrapper))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP dispatcher: {e}")
            return False

    async def cleanup_mcp(self):
        """Cleanup MCP resources."""
        global _mcp_dispatcher
        if _mcp_dispatcher:
            await _mcp_dispatcher.cleanup()
            _mcp_dispatcher = None

async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent with job polling MCP integration."""
    
    # Get agent configuration
    room_name = ctx.room.name if ctx.room else "default"
    config = await get_agent_config(room_name)
    
    if not config:
        logger.warning("Using default agent configuration")
        config = {
            'systemPrompt': 'You are a helpful voice assistant with access to web search and other tools.',
            'personality': 'friendly',
            'voiceModel': 'alloy',
            'temperature': 70
        }
    
    # Initialize the assistant
    assistant = Assistant(config)
    
    # Initialize MCP with job polling
    mcp_success = await assistant.initialize_mcp()
    if mcp_success:
        logger.info("MCP job polling integration initialized successfully")
    else:
        logger.warning("MCP initialization failed, continuing with basic functionality")
    
    # Start the agent session
    await ctx.add_participant(assistant)
    
    logger.info(f"Agent started for room: {room_name}")
    
    # Set up cleanup on disconnect
    async def cleanup_on_disconnect():
        logger.info("Cleaning up MCP resources...")
        await assistant.cleanup_mcp()
    
    # Register cleanup handler
    ctx.on_disconnect(cleanup_on_disconnect)
    
    # Keep the agent running
    await ctx.wait_for_participant()

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=None,
        )
    )