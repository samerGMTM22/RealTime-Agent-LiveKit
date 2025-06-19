"""Universal MCP Voice Agent - Simplified Implementation"""

import asyncio
import logging
from typing import Dict, Any
from livekit.agents import JobContext, WorkerOptions, cli, llm, Agent
from livekit.agents.llm import function_tool
from livekit import rtc
import livekit.agents.openai as openai

from mcp_integration.universal_manager import UniversalMCPDispatcher
from mcp_integration.storage import PostgreSQLStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalMCPAssistant(Agent):
    """Voice assistant with universal MCP integration"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        self.mcp_dispatcher = None
        self.storage = None
    
    async def initialize_mcp(self, user_id: int = 1):
        """Initialize universal MCP integration"""
        try:
            self.storage = PostgreSQLStorage()
            await self.storage.connect()
            
            self.mcp_dispatcher = UniversalMCPDispatcher(self.storage)
            dynamic_tools = await self.mcp_dispatcher.initialize_tools(user_id)
            
            manifest = await self.mcp_dispatcher.get_tool_manifest()
            logger.info(f"Universal MCP ready: {manifest['total_servers']} servers, {manifest['total_tools']} tools")
            
            return manifest
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP: {e}")
            return {"total_servers": 0, "total_tools": 0}
    
    @function_tool
    async def search_web(self, query: str) -> str:
        """Search the web for current information using universal MCP dispatcher"""
        if not self.mcp_dispatcher:
            return "MCP system not initialized"
        
        # Find the best search tool available
        search_tools = [name for name in self.mcp_dispatcher.tool_registry.keys() 
                       if 'search' in name.lower()]
        
        if search_tools:
            tool_name = search_tools[0]  # Use first available search tool
            result = await self.mcp_dispatcher.execute_tool(tool_name, {"query": query})
            return result
        else:
            return "No search tools available in MCP integration"
    
    @function_tool
    async def get_mcp_capabilities(self) -> str:
        """Get available MCP tools and capabilities"""
        if not self.mcp_dispatcher:
            return "MCP system not initialized"
        
        manifest = await self.mcp_dispatcher.get_tool_manifest()
        
        capabilities = []
        capabilities.append(f"Connected to {manifest['total_servers']} MCP servers")
        capabilities.append(f"Available tools: {manifest['total_tools']}")
        
        for tool in manifest.get('tools', []):
            capabilities.append(f"- {tool['tool_name']}: {tool['description']}")
        
        return "\n".join(capabilities)
    
    async def cleanup(self):
        """Cleanup MCP connections"""
        if self.mcp_dispatcher:
            await self.mcp_dispatcher.cleanup()
        if self.storage:
            await self.storage.cleanup()

async def load_agent_config(user_id: int = 1) -> Dict[str, Any]:
    """Load agent configuration"""
    return {
        "name": "Universal MCP Voice Agent",
        "system_prompt": "You are a helpful AI assistant with access to various tools and services through universal MCP integration. Use search_web to find current information and get_mcp_capabilities to see what tools are available.",
        "personality": "friendly",
        "voice_model": "alloy",
        "temperature": 0.7
    }

async def entrypoint(ctx: JobContext):
    """Main entry point for universal MCP voice agent"""
    
    # Load configuration
    config = await load_agent_config()
    logger.info(f"Starting {config['name']}")
    
    # Create assistant with universal MCP integration
    assistant = UniversalMCPAssistant(config)
    
    # Initialize MCP system
    manifest = await assistant.initialize_mcp(user_id=1)
    
    # Enhanced system prompt with MCP capabilities
    enhanced_prompt = f"""{config['system_prompt']}

MCP Integration Status:
- Connected servers: {manifest.get('total_servers', 0)}
- Available tools: {manifest.get('total_tools', 0)}

Use search_web(query) to find current information.
Use get_mcp_capabilities() to see all available MCP tools."""
    
    # Initialize OpenAI Realtime model with tools
    model = openai.realtime.RealtimeModel(
        instructions=enhanced_prompt,
        voice=config.get("voice_model", "alloy"),
        temperature=config.get("temperature", 0.7),
        turn_detection=openai.realtime.ServerTurnDetection(
            type="server_vad",
            threshold=0.5,
            prefix_padding_ms=300,
            silence_duration_ms=500,
        ),
    )
    
    # Set up session and connect
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant connected: {participant.identity}")
    
    # Start session with tools
    session = model.sessions(
        chat_ctx=llm.ChatContext().append(role="system", text=enhanced_prompt),
        fnc_ctx=llm.FunctionContext(),
    )
    
    # Register MCP tools
    session.fnc_ctx.ai_functions = [
        assistant.search_web,
        assistant.get_mcp_capabilities,
    ]
    
    # Start the session
    session.conversation.on("function_calls", lambda call: logger.info(f"Function called: {call.tool_name}"))
    
    try:
        session.start(ctx.room, participant)
        await session.aclose()
    finally:
        await assistant.cleanup()
        logger.info("Universal MCP voice session ended")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))