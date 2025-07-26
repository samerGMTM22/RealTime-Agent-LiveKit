#!/usr/bin/env python3

"""
LiveKit Voice Agent with External Tool Integration via Webhooks
Following the working patterns from LIVEKIT_REALTIME_API_GUIDE.md

Architecture:
Voice Input → OpenAI Realtime API → Function Tools → N8N Webhook → Results → Voice Output
"""

import asyncio
import logging
import os
import sys
import json
import aiohttp
from typing import Dict, Any, Optional

# Add the project root to the Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LiveKit imports - following guide patterns
from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe, AgentSession, Agent
from livekit.plugins import openai, silero
from livekit.agents.llm import function_tool

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
        
        # Fallback return - should not reach here
        return {
            'success': False,
            'error': 'Tool execution failed - no session available'
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
                       openai_model, livekit_room_name
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
                        'voice_model': 'coral',
                        'temperature': 80,
                        'openai_model': 'gpt-4o',
                        'livekit_room_name': 'default'
                    }
                
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'system_prompt': row['system_prompt'],
                    'voice_model': row['voice_model'],
                    'temperature': row['temperature'],
                    'openai_model': row['openai_model'],
                    'livekit_room_name': row['livekit_room_name']
                }
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Database error: {e}")
            # Return default configuration on error
            return {
                'id': 1,
                'name': 'Default Voice Agent',
                'system_prompt': 'You are a helpful voice assistant with access to external tools. Be concise and conversational.',
                'voice_model': 'coral',
                'temperature': 80,
                'openai_model': 'gpt-4o',
                'livekit_room_name': 'default'
            }

# Initialize global webhook executor
webhook_executor = WebhookToolExecutor()

@function_tool
async def execute_web_search(query: str) -> str:
    """Search the internet for current information"""
    logger.info(f"Executing web search: {query}")
    
    result = await webhook_executor.execute_external_tool('web_search', {
        'query': query
    })
    
    if result['success']:
        return f"Search results for '{query}': {result['result']}"
    else:
        return f"Search failed: {result['error']}"

@function_tool
async def execute_automation(action: str, params: str = "{}") -> str:
    """Execute automation workflows and tasks"""
    logger.info(f"Executing automation: {action}")
    
    # Parse JSON string params to avoid OpenAI schema issues
    try:
        import json
        parsed_params = json.loads(params) if params != "{}" else {}
    except:
        parsed_params = {}
    
    result = await webhook_executor.execute_external_tool('automation', {
        'action': action,
        'params': parsed_params
    })
    
    if result['success']:
        return f"Automation '{action}' completed: {result['result']}"
    else:
        return f"Automation failed: {result['error']}"

async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent - following working patterns from guide"""
    
    logger.info("Initializing voice agent with webhook integration...")
    
    # Load configuration from database
    db_config = DatabaseConfig()
    agent_config = await db_config.get_agent_config()
    logger.info(f"Loaded agent config: {agent_config['name']}")
    
    # Convert temperature from percentage to Realtime API range (0.6-1.2)
    temp_raw = float(agent_config.get('temperature', 80))
    realtime_temp = max(0.6, min(1.2, 0.6 + (temp_raw / 100.0) * 0.6))
    
    logger.info(f"Using voice model: {agent_config.get('voice_model', 'coral')}, temperature: {realtime_temp}")
    
    try:
        # Connect to room with audio-only subscription (from guide pattern)
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        logger.info(f"Connected to room: {ctx.room.name}")
        
        # Subscribe to audio tracks (critical for audio flow)
        @ctx.room.on("track_published")
        def on_track_published(publication, participant):
            if publication.kind == rtc.TrackKind.KIND_AUDIO:
                publication.set_subscribed(True)
                logger.info(f"Subscribed to audio track from {participant.identity}")
        
        # Wait for participant before starting agent
        participant = await ctx.wait_for_participant()
        logger.info(f"Participant joined: {participant.identity}")
        
        # Try Realtime API first (preferred approach from guide)
        try:
            from livekit.plugins.openai import realtime
            
            session = AgentSession(
                llm=realtime.RealtimeModel(
                    model="gpt-4o-realtime-preview",
                    voice=agent_config.get('voice_model', 'coral'),
                    temperature=realtime_temp,
                ),
                allow_interruptions=True,
                min_interruption_duration=0.5,
                min_endpointing_delay=0.5,
                max_endpointing_delay=6.0,
            )
            
            # Create agent with external tools for Realtime API
            agent = Agent(
                instructions=agent_config.get('system_prompt', 'You are a helpful voice assistant with access to external tools.'),
                tools=[execute_web_search, execute_automation]
            )
            
            # Start session with agent
            await session.start(room=ctx.room, agent=agent)
            
            # Generate initial greeting
            await session.generate_reply(
                instructions="Greet the user warmly and let them know you have access to web search and automation tools."
            )
            
            logger.info("Voice agent started successfully with OpenAI Realtime API")
            
        except Exception as realtime_error:
            logger.error(f"Realtime API failed: {realtime_error}")
            
            # Fallback to STT-LLM-TTS pipeline
            logger.info("Falling back to STT-LLM-TTS pipeline...")
            
            # Convert temperature for standard LLM (0-2 range)
            llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
            
            session = AgentSession(
                vad=silero.VAD.load(),
                stt=openai.STT(language="en"),
                llm=openai.LLM(
                    model="gpt-4o",
                    temperature=llm_temp,
                ),
                tts=openai.TTS(voice=agent_config.get('voice_model', 'coral')),
                allow_interruptions=True,
                min_interruption_duration=0.5,
                min_endpointing_delay=0.5,
                max_endpointing_delay=6.0,
            )
            
            # Create agent with external tools
            agent = Agent(
                instructions=agent_config.get('system_prompt', 'You are a helpful voice assistant with access to external tools.'),
                tools=[execute_web_search, execute_automation]
            )
            
            # Start session with agent
            await session.start(room=ctx.room, agent=agent)
            
            # Generate initial greeting
            await session.generate_reply(
                instructions="Greet the user warmly and let them know you have access to web search and automation tools."
            )
            
            logger.info("Voice agent started successfully with STT-LLM-TTS fallback")
        
    except Exception as e:
        logger.error(f"Failed to start voice agent: {e}")
        raise

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))