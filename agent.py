from dotenv import load_dotenv
import asyncio
import os

from livekit import agents
from livekit.agents import JobContext, cli

load_dotenv()


async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent."""
    print(f"Starting agent for room: {ctx.room.name}")
    
    # Connect to the room
    await ctx.connect()
    print(f"Agent connected to room: {ctx.room.name}")
    
    # Keep the connection alive
    try:
        # Basic agent that just maintains connection
        print("Give Me the Mic agent is running and ready for voice interactions")
        
        # Wait indefinitely to keep the agent running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Agent shutting down...")
    except Exception as e:
        print(f"Agent error: {e}")


if __name__ == "__main__":
    # Run the agent
    cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )