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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent-direct-tools")
load_dotenv()

# Configure URLs from environment or defaults
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "https://n8n.srv755489.hstgr.cloud/mcp/43a3ec6f-728e-489b-9456-45f9d41750b7")
ZAPIER_MCP_URL = os.environ.get("ZAPIER_MCP_URL", "https://mcp.zapier.com/api/mcp/s/MDRmNjkzMDUtYzI0NS00Y2FlLTgzODQtNzU5ZmRjMjViNDI1OmU3ZWQ4YWJjLTIxNDEtNDI5OC1iNTBiLWRlYWUxMjkxYWRkMw==")

# Define function tools directly
@function_tool
async def execute_web_search(query: str = "") -> str:
    """
    Executes a web search using N8N workflow.
    Use this tool to search the internet for current information, news, or research.
    Provide a search query as the 'query' parameter.
    """
    if not N8N_WEBHOOK_URL:
        return "N8N webhook URL is not configured."

    logger.info(f"Executing N8N web search with query: {query}")

    headers = {"Content-Type": "application/json"}
    
    try:
        # Prepare payload for N8N workflow
        payload = {"query": query}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(f"N8N search completed successfully")
                
                # Format result for voice response
                if isinstance(result, dict) and 'result' in result:
                    content = result['result']
                else:
                    content = str(result)
                
                return content
                
    except aiohttp.ClientError as e:
        logger.error(f"Error calling N8N workflow: {e}")
        return f"I encountered an error while searching: {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred in N8N tool: {e}")
        return "I encountered an unexpected error while searching. Let me help with what I know instead."

@function_tool
async def send_email(to: str = "", subject: str = "", body: str = "") -> str:
    """
    Sends an email using Zapier integration.
    Use this tool to send emails to users or contacts.
    Provide 'to' (recipient email), 'subject', and 'body' parameters.
    """
    if not ZAPIER_MCP_URL:
        return "Zapier MCP URL is not configured."

    logger.info(f"Sending email via Zapier to: {to}")

    headers = {"Content-Type": "application/json"}

    try:
        # Prepare payload for Zapier
        payload = {"to": to, "subject": subject, "body": body}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ZAPIER_MCP_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(f"Zapier email sent successfully")
                return f"Email sent successfully to {to}"
                
    except aiohttp.ClientError as e:
        logger.error(f"Error calling Zapier action: {e}")
        return f"I encountered an error while sending the email: {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred in Zapier tool: {e}")
        return "I encountered an unexpected error while sending the email."

async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent with direct tool integration."""
    
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
        tools=[execute_web_search, send_email]  # Register our function tools directly
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