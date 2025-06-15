"""Universal MCP Voice Agent - Implements Gemini's universal architecture"""

import asyncio
import logging
import os
from typing import Dict, Any
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.multimodal import MultimodalAgent
from livekit import rtc
import livekit.agents.openai as openai

from mcp_integration.universal_manager import UniversalMCPDispatcher
from mcp_integration.storage import PostgreSQLStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def load_agent_config(user_id: int = 1) -> Dict[str, Any]:
    """Load agent configuration from database"""
    storage = PostgreSQLStorage()
    try:
        await storage.connect()
        config = await storage.getAgentConfigByUserId(user_id)
        return config or {
            "name": "Universal MCP Voice Agent",
            "system_prompt": "You are a helpful AI assistant with access to various tools and services through MCP integration. Use the available tools to help users with their requests.",
            "personality": "friendly",
            "voice_model": "alloy",
            "temperature": 0.7
        }
    except Exception as e:
        logger.error(f"Failed to load agent config: {e}")
        return {
            "name": "Universal MCP Voice Agent",
            "system_prompt": "You are a helpful AI assistant with access to various tools and services through MCP integration.",
            "personality": "friendly", 
            "voice_model": "alloy",
            "temperature": 0.7
        }
    finally:
        await storage.cleanup()

async def entrypoint(ctx: JobContext):
    """Main entry point with universal MCP integration architecture"""
    
    # Load agent configuration
    config = await load_agent_config()
    logger.info(f"Loaded agent config: {config['name']}")
    
    # Initialize universal MCP dispatcher
    storage = PostgreSQLStorage()
    await storage.connect()
    
    mcp_dispatcher = UniversalMCPDispatcher(storage)
    
    # Initialize all MCP tools dynamically - this single call discovers and prepares all tools
    logger.info("Initializing universal MCP integration...")
    dynamic_tools = await mcp_dispatcher.initialize_tools(user_id=1)
    
    # Get tool manifest for debugging
    manifest = await mcp_dispatcher.get_tool_manifest()
    logger.info(f"Universal MCP integration ready: {manifest['total_servers']} servers, {manifest['total_tools']} tools")
    
    # Create single universal tool executor
    @function_tool
    async def execute_mcp_tool(tool_name: str, **kwargs) -> str:
        """Universal tool executor that dispatches to any discovered MCP function"""
        logger.info(f"Dispatching tool '{tool_name}' to Universal MCP Dispatcher")
        try:
            result = await mcp_dispatcher.execute_tool(tool_name, kwargs)
            logger.info(f"Tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error executing tool: {str(e)}"
    
    # Create system prompt that includes available tools
    available_tools = []
    for tool_name, tool_data in mcp_dispatcher.tool_registry.items():
        tool_info = tool_data['tool_info']
        available_tools.append(f"- {tool_name}: {tool_info.get('description', 'No description')}")
    
    tools_description = "\n".join(available_tools) if available_tools else "No tools currently available"
    
    enhanced_system_prompt = f"""{config['system_prompt']}

Available MCP Tools:
{tools_description}

To use any tool, simply call execute_mcp_tool with the tool_name parameter and any required arguments.
For example: execute_mcp_tool(tool_name="execute_web_search", query="latest AI news")

Be helpful and use the appropriate tools to assist users with their requests."""

    # Initialize OpenAI Realtime model
    initial_ctx = llm.ChatContext().append(
        role="system", text=enhanced_system_prompt
    )
    
    # Create MultimodalAgent with universal tool
    await ctx.connect(auto_subscribe=rtc.TrackKind.KIND_AUDIO)
    
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant connected: {participant.identity}")
    
    agent = MultimodalAgent(
        model=openai.realtime.RealtimeModel(
            instructions=enhanced_system_prompt,
            voice=config.get("voice_model", "alloy"),
            temperature=config.get("temperature", 0.7),
            modalities=["text", "audio"],
            turn_detection=openai.realtime.ServerTurnDetection(
                type="server_vad",
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=500,
            ),
        ),
        chat_ctx=initial_ctx,
        fnc_ctx=llm.FunctionContext(),
    )
    
    # Register the universal tool
    agent.fnc_ctx.ai_functions = [execute_mcp_tool]
    
    # Set up event handlers
    def on_function_calls(fnc_call_infos):
        """Handle function call events"""
        logger.info(f"Function calls requested: {[f.tool_name for f in fnc_call_infos]}")
    
    def on_function_calls_finished(called_fncs):
        """Handle function call completion events"""
        for fnc in called_fncs:
            if fnc.exception:
                logger.error(f"Function {fnc.call_info.tool_name} failed: {fnc.exception}")
            else:
                logger.info(f"Function {fnc.call_info.tool_name} completed successfully")
    
    agent.on("function_calls", on_function_calls)
    agent.on("function_calls_finished", on_function_calls_finished)
    
    # Start the agent
    agent.start(ctx.room, participant)
    
    # Keep alive and handle cleanup
    try:
        await agent.aclose()
    finally:
        await mcp_dispatcher.cleanup()
        await storage.cleanup()
        logger.info("Universal MCP Voice Agent session ended")

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=None,  # Optional prewarming function
        )
    )