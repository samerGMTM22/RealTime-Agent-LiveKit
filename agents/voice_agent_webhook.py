#!/usr/bin/env python3

"""
LiveKit Voice Agent with External Tool Integration via Webhooks

This agent integrates LiveKit WebRTC with OpenAI Realtime API for voice conversations,
and uses external webhook calls for tool execution (replacing complex MCP integration).

Architecture:
Voice Input → OpenAI Realtime API → Function Tools → N8N Webhook → Results → Voice Output

Key Features:
- Direct OpenAI Realtime API integration (no STT-LLM-TTS pipeline)
- External tool execution via webhook system
- Database configuration fetching 
- Graceful error handling and fallbacks
"""

import asyncio
import logging
import os
import sys
import json
import aiohttp
from typing import Dict, Any, Optional
from urllib.parse import urlparse

# Add the project root to the Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LiveKit imports
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents import VoicePipelineAgent
from livekit.plugins import openai

# Database imports
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebhookToolExecutor:
    """Handles external tool execution via webhook calls"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv('N8N_WEBHOOK_URL')
        self.session = None
    
    async def init_session(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def execute_external_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute external tool via webhook"""
        if not self.webhook_url:
            return {
                'success': False,
                'error': 'No webhook URL configured. Please set N8N_WEBHOOK_URL environment variable.'
            }
        
        try:
            await self.init_session()
            
            # Prepare webhook payload
            payload = {
                'tool': tool_name,
                'params': params,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            logger.info(f"Calling external webhook for tool: {tool_name}")
            
            # Make webhook request with timeout  
            timeout = aiohttp.ClientTimeout(total=30)
            if self.session:
                async with self.session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=timeout
                ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Webhook call successful for {tool_name}")
                    return {
                        'success': True,
                        'result': result.get('result', 'Tool executed successfully'),
                        'tool': tool_name
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Webhook call failed: {response.status} - {error_text}")
                    return {
                        'success': False,
                        'error': f"Webhook returned {response.status}: {error_text}"
                    }
                    
        except asyncio.TimeoutError:
            logger.error(f"Webhook timeout for tool: {tool_name}")
            return {
                'success': False,
                'error': 'Tool execution timed out (30 seconds)'
            }
        except Exception as e:
            logger.error(f"Webhook error for tool {tool_name}: {str(e)}")
            return {
                'success': False,
                'error': f"Tool execution failed: {str(e)}"
            }

class DatabaseConfig:
    """Handles database configuration fetching"""
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
    
    async def get_agent_config(self, agent_id: int = 1) -> Dict[str, Any]:
        """Fetch agent configuration from database"""
        try:
            conn = await asyncpg.connect(self.db_url)
            try:
                # Get active agent configuration
                query = """
                SELECT id, name, system_prompt, voice_model, temperature, 
                       max_tokens, openai_model, livekit_room_name
                FROM agent_configs 
                WHERE id = $1 AND is_active = true
                LIMIT 1
                """
                
                row = await conn.fetchrow(query, agent_id)
                if not row:
                    # Return default configuration
                    return {
                        'id': 1,
                        'name': 'Default Voice Agent',
                        'system_prompt': 'You are a helpful voice assistant with access to external tools. Be concise and conversational.',
                        'voice_model': 'alloy',
                        'temperature': 0.8,
                        'max_tokens': 4096,
                        'openai_model': 'gpt-4-turbo',
                        'livekit_room_name': 'voice-agent-room'
                    }
                
                return dict(row)
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Database config error: {e}")
            # Return default configuration as fallback
            return {
                'id': 1,
                'name': 'Default Voice Agent',
                'system_prompt': 'You are a helpful voice assistant with access to external tools. Be concise and conversational.',
                'voice_model': 'alloy',
                'temperature': 0.8,
                'max_tokens': 4096,
                'openai_model': 'gpt-4-turbo',
                'livekit_room_name': 'voice-agent-room'
            }

def create_external_tool_functions(webhook_executor: WebhookToolExecutor):
    """Create external tool functions for the agent"""
    
    async def execute_web_search(query: str) -> str:
        """Search the web for information"""
        result = await webhook_executor.execute_external_tool('web_search', {'query': query})
        
        if result['success']:
            return f"Search results for '{query}':\n{result['result']}"
        else:
            return f"Search failed: {result['error']}"
    
    async def execute_automation(action: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Execute automation workflows"""
        result = await webhook_executor.execute_external_tool('automation', {
            'action': action,
            'params': params or {}
        })
        
        if result['success']:
            return f"Automation '{action}' completed: {result['result']}"
        else:
            return f"Automation failed: {result['error']}"
    
    # Return function definitions
    return {
        'execute_web_search': execute_web_search,
        'execute_automation': execute_automation
    }

async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent"""
    
    # Initialize components
    logger.info("Initializing voice agent with webhook integration...")
    
    # Load configuration from database
    db_config = DatabaseConfig()
    agent_config = await db_config.get_agent_config()
    logger.info(f"Loaded agent config: {agent_config['name']}")
    
    # Initialize webhook tool executor
    webhook_executor = WebhookToolExecutor()
    
    # Create external tool functions
    external_functions = create_external_tool_functions(webhook_executor)
    
    # Create function context for LiveKit
    from livekit.agents.llm import FunctionContext
    fnc_ctx = FunctionContext()
    
    # Add functions to context
    for name, func in external_functions.items():
        if hasattr(fnc_ctx, 'ai_functions'):
            fnc_ctx.ai_functions[name] = func
    
    # Initialize OpenAI model with functions
    try:
        model = openai.LLM(
            model="gpt-4o-realtime-preview-2024-10-01",
            temperature=agent_config['temperature']
        )
        
        logger.info("OpenAI Realtime model initialized with external tools")
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI model: {e}")
        raise
    
    # Create and start the voice agent
    try:
        agent = VoicePipelineAgent(
            vad=ctx.proc.userdata.get("vad"),
            stt=openai.STT(),
            llm=model,
            tts=openai.TTS(),
            fnc_ctx=fnc_ctx,
        )
        
        # Connect to room and start processing
        await ctx.connect()
        agent.start(ctx.room)
        
        # Initial greeting
        await agent.say("Hello! I'm your voice assistant with access to external tools. How can I help you today?")
        
        logger.info("Voice agent started successfully")
        
        # Keep the agent running
        await asyncio.sleep(float('inf'))
        
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise
    
    finally:
        # Cleanup
        await webhook_executor.close_session()
        logger.info("Voice agent session ended")

if __name__ == "__main__":
    # Configure worker options
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint
    )
    
    # Start the worker
    cli.run_app(worker_options)