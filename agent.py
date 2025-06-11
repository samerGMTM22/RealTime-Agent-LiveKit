import os
import asyncio
from dotenv import load_dotenv

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.plugins import openai
from openai.types.beta.realtime.session import TurnDetection
import requests

load_dotenv()


async def get_agent_config(room_name: str):
    """Fetch agent configuration from the database based on room name."""
    try:
        # Default to agent config ID 1 for now
        agent_config_id = 1
        
        # Make request to get agent configuration
        response = requests.get(f'http://localhost:5000/api/agent-configs/{agent_config_id}', timeout=5)
        if response.status_code == 200:
            config = response.json()
            print(f"Fetched config from database: {config['name']}")
            return config
    except Exception as e:
        print(f"Error fetching agent config: {e}")
    
    # Fallback configuration
    return {
        "systemPrompt": "You are a helpful voice AI assistant for the Give Me the Mic YouTube channel. You help viewers with channel information, video content, and general music-related questions.",
        "voiceModel": "alloy",
        "temperature": 80,
        "responseLength": "medium"
    }


async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent."""
    print(f"Starting agent for room: {ctx.room.name}")
    
    # Get agent configuration from database
    config = await get_agent_config(ctx.room.name)
    print(f"Using agent config: {config.get('name', 'Default')}")
    
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
    # Convert temperature from percentage (0-100) to decimal (0.6-1.2)
    temp_raw = config.get("temperature", 80)
    temperature = max(0.6, min(1.2, float(temp_raw) / 100.0))
    system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
    
    print(f"Voice: {voice}, Temperature: {temperature}")
    
    # Connect to the room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    print(f"Agent connected to room: {ctx.room.name}")

    # Create the OpenAI Realtime model with proper configuration
    realtime_model = openai.realtime.RealtimeModel(
        voice=voice,
        temperature=temperature,
        instructions=system_prompt,
        turn_detection=TurnDetection(
            type="server_vad",
            threshold=0.5,
            prefix_padding_ms=300,
            silence_duration_ms=500,
            create_response=True,
            interrupt_response=True,
        )
    )

    print("OpenAI Realtime model created successfully")
    print("Give Me the Mic agent is running and ready for voice interactions")


if __name__ == "__main__":
    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )