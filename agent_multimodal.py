import logging
import os
import asyncio
import time
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    llm,
    function_tool
)
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import openai

from mcp_integration.simple_client import SimpleMCPManager

logger = logging.getLogger("voice-agent")
load_dotenv()

# Define function tools at module level for MultimodalAgent compatibility
@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    logger.info(f"FUNCTION ACTUALLY EXECUTED: search_web({query})")
    execution_time = time.time()
    
    try:
        # Get the current job context to access MCP manager
        ctx = get_current_job_context()
        mcp_manager = ctx.userdata.get("mcp_manager")
        
        if mcp_manager:
            # Try to execute via MCP manager
            for server_id, client in mcp_manager.connected_servers.items():
                if "internet" in client.name.lower():
                    result = await mcp_manager.call_tool(server_id, "search", {"query": query})
                    if "error" not in result:
                        logger.info(f"FUNCTION COMPLETED at {execution_time}: MCP search successful")
                        return result.get("content", "Search completed successfully")
            
            # Fallback to Express API
            logger.info(f"Making Express API call for search: {query}")
            import requests
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
            logger.error("MCP manager not available in context")
            return "MCP manager not available"
            
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return f"Search failed: {str(e)}"

@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Zapier MCP integration."""
    logger.info(f"FUNCTION ACTUALLY EXECUTED: send_email(to={to}, subject={subject})")
    execution_time = time.time()
    
    try:
        ctx = get_current_job_context()
        mcp_manager = ctx.userdata.get("mcp_manager")
        
        if mcp_manager:
            # Try to execute via MCP manager
            for server_id, client in mcp_manager.connected_servers.items():
                if "zapier" in client.name.lower() or "email" in client.name.lower():
                    result = await mcp_manager.call_tool(server_id, "send_email", 
                                                       {"to": to, "subject": subject, "body": body})
                    if "error" not in result:
                        logger.info(f"FUNCTION COMPLETED at {execution_time}: MCP email successful")
                        return "Email sent successfully via MCP"
            
            # Fallback to Express API
            logger.info(f"Making Express API call for email: {to}")
            import requests
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
            logger.error("MCP manager not available in context")
            return "MCP manager not available"
            
    except Exception as e:
        logger.error(f"Error in email send: {e}")
        return f"Email send failed: {str(e)}"

async def load_agent_config(user_id: int = 1) -> Dict[str, Any]:
    """Load agent configuration from database"""
    try:
        import requests
        response = requests.get(f'http://localhost:5000/api/agent-configs/{user_id}')
        if response.status_code == 200:
            config = response.json()
            logger.info(f"Fetched config from database: {config.get('name', 'Unknown')}")
            return config
        else:
            logger.warning("Failed to fetch config from database, using defaults")
            return {
                "name": "Default Assistant",
                "system_prompt": "You are a helpful AI assistant.",
                "voice_model": "echo",
                "temperature": 80
            }
    except Exception as e:
        logger.error(f"Error loading agent config: {e}")
        return {
            "name": "Default Assistant", 
            "system_prompt": "You are a helpful AI assistant.",
            "voice_model": "echo",
            "temperature": 80
        }

async def entrypoint(ctx: JobContext):
    """Main entry point with proper MultimodalAgent setup following expert guidelines."""
    await ctx.connect()
    
    logger.info("Initializing MCP integration...")
    
    # Initialize MCP manager
    mcp_manager = SimpleMCPManager()
    
    # Load MCP servers from database
    try:
        mcp_servers = await mcp_manager.initialize_user_servers(user_id=1)
        connected_count = len([s for s in mcp_servers if s.get("status") == "connected"])
        logger.info(f"Connected to {connected_count} MCP servers")
        
        # Store MCP manager in context userdata for function tools
        ctx.userdata["mcp_manager"] = mcp_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP servers: {e}")
        ctx.userdata["mcp_manager"] = None
    
    # Create function context with MCP tools
    fnc_ctx = llm.FunctionContext()
    fnc_ctx.add_function(search_web)
    fnc_ctx.add_function(send_email)
    
    logger.info("Function tools registered in context")
    
    # Get agent configuration
    agent_config = await load_agent_config(user_id=1)
    
    logger.info(f"Using agent config: {agent_config.get('name', 'Unknown')}")
    logger.info(f"System prompt: {agent_config.get('system_prompt', 'Default')[:100]}...")
    logger.info(f"Voice: {agent_config.get('voice_model', 'echo')}, Temperature: {agent_config.get('temperature', 80)/100}")
    
    # Create chat context with system prompt
    chat_ctx = llm.ChatContext().append(
        role="system",
        text=agent_config.get("system_prompt", "You are a helpful assistant.")
    )
    
    logger.info("Attempting OpenAI Realtime API with MultimodalAgent")
    
    try:
        # Initialize OpenAI Realtime model
        model = openai.realtime.RealtimeModel(
            instructions=agent_config.get("system_prompt"),
            voice=agent_config.get("voice_model", "echo"),
            temperature=agent_config.get("temperature", 80) / 100,
            modalities=["text", "audio"],
            turn_detection=openai.realtime.TurnDetection(
                type="server_vad",
                threshold=0.5,
                prefix_padding_ms=300,
                silence_duration_ms=700,
                create_response=True,
                interrupt_response=True,
            )
        )
        
        # Create MultimodalAgent with function context
        agent = MultimodalAgent(
            model=model,
            chat_ctx=chat_ctx,
            fnc_ctx=fnc_ctx  # Pass function context here!
        )
        
        # Add event listeners to monitor function calls
        @agent.on("function_calls_collected")
        def on_function_calls(fnc_call_infos: List[llm.FunctionCallInfo]):
            logger.info(f"Function calls collected: {[f.function_name for f in fnc_call_infos]}")
        
        @agent.on("function_calls_finished")
        def on_function_calls_finished(called_fncs: List[llm.CalledFunction]):
            for func in called_fncs:
                logger.info(f"Function {func.function_info.function_name} completed with result: {func.result[:100] if func.result else 'None'}")
        
        # Wait for participant
        participant = await ctx.wait_for_participant()
        logger.info(f"Participant joined: {participant.identity}")
        
        # Start the agent
        agent.start(ctx.room, participant)
        
        logger.info("OpenAI Realtime API MultimodalAgent started successfully")
        
        # Keep the agent running
        await asyncio.sleep(0.1)
        await agent.say("Hello! I'm your AI assistant. I can help you search the web and send emails. How can I assist you today?")
        
    except Exception as e:
        logger.error(f"MultimodalAgent failed: {e}")
        # Fallback implementation could go here if needed
        raise

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))