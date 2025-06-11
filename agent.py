import os
import asyncio
import json
import sys
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, JobContext
from livekit.plugins import openai
import requests

load_dotenv()


class ConfigurableAssistant(Agent):
    def __init__(self, system_prompt: str) -> None:
        super().__init__(instructions=system_prompt)


async def get_agent_config(room_name: str):
    """Fetch agent configuration from the database based on room name."""
    try:
        # Extract session ID from room name
        session_parts = room_name.split('_')
        if len(session_parts) >= 4:
            # Default to agent config ID 1 for now
            # In a real implementation, you'd pass this through the room creation
            agent_config_id = 1
            
            # Make request to get agent configuration
            response = requests.get(f'http://localhost:5000/api/agent-configs/{agent_config_id}')
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"Error fetching agent config: {e}")
    
    # Fallback configuration
    return {
        "systemPrompt": "You are a helpful voice AI assistant for the Give Me the Mic YouTube channel. You help viewers with channel information, video content, and general music-related questions.",
        "voiceModel": "alloy",
        "temperature": 0.8,
        "responseLength": "medium"
    }


async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent."""
    print(f"Starting agent for room: {ctx.room.name}")
    
    # Get agent configuration from database
    config = await get_agent_config(ctx.room.name)
    print(f"Using agent config: {config}")
    
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
    temperature = float(config.get("temperature", 0.8))
    system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
    
    # Create the agent session with OpenAI Realtime API
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview",
            voice=voice,
            temperature=temperature
        )
    )

    # Start the session
    await session.start(
        room=ctx.room,
        agent=ConfigurableAssistant(system_prompt),
        room_input_options=RoomInputOptions(),
    )

    # Connect to the room
    await ctx.connect()
    print(f"Agent connected to room: {ctx.room.name}")

    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and introduce yourself as the Give Me the Mic channel assistant. Offer to help with any questions about the channel, videos, or music topics."
    )
    
    print("Give Me the Mic agent is running and ready for voice interactions")


if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )