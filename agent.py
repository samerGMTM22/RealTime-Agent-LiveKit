from dotenv import load_dotenv
import asyncio
import os

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool, RunContext
from livekit.plugins import openai

load_dotenv()


class GiveMeTheMicAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant for the "Give Me the Mic" YouTube channel. 
            You help users learn about the channel's content, music-related topics, and provide assistance.
            The channel has 484 subscribers and 249 videos focusing on music and entertainment.
            Keep responses conversational, helpful, and engaging."""
        )

    @function_tool()
    async def get_channel_info(self, context: RunContext) -> str:
        """Get information about the Give Me the Mic YouTube channel."""
        return """The Give Me the Mic channel is a music-focused YouTube channel with 484 subscribers and 249 videos. 
        The channel creates content around music, entertainment, and giving people a platform to share their voice. 
        You can find them at @givemethemicmusic on YouTube."""

    @function_tool()
    async def get_music_tips(self, context: RunContext, topic: str) -> str:
        """Provide music-related tips and advice.
        
        Args:
            topic: The music topic to provide tips about (singing, instruments, recording, etc.)
        """
        tips = {
            "singing": "Practice breathing exercises, warm up your voice, stay hydrated, and work on your pitch accuracy.",
            "recording": "Use a good microphone, record in a quiet space, avoid echo, and monitor your audio levels.",
            "instruments": "Start with basic chords or scales, practice regularly, use a metronome, and be patient with yourself.",
            "performance": "Practice in front of mirrors, know your material well, engage with your audience, and manage stage fright.",
            "songwriting": "Start with simple chord progressions, write about personal experiences, and don't be afraid to revise."
        }
        
        general_tip = f"For {topic}, focus on consistent practice and don't be afraid to experiment with different techniques."
        return tips.get(topic.lower(), general_tip)

    @function_tool()
    async def suggest_content(self, context: RunContext, interest: str) -> str:
        """Suggest Give Me the Mic content based on user interests.
        
        Args:
            interest: The type of content the user is interested in
        """
        return f"""Based on your interest in {interest}, I recommend checking out the Give Me the Mic channel's 
        latest videos. With 249 videos available, there's likely content that matches what you're looking for. 
        The channel focuses on music and entertainment, giving people a platform to showcase their talents."""


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the LiveKit agent."""
    
    print(f"Starting agent for room: {ctx.room.name}")
    
    # Create session with OpenAI Realtime API
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="coral",  # Use a warm, friendly voice
            temperature=0.8,
            model="gpt-4o-realtime-preview"
        )
    )

    # Start the session
    await session.start(
        room=ctx.room,
        agent=GiveMeTheMicAssistant(),
    )

    # Connect to the room
    await ctx.connect()
    print(f"Agent connected to room: {ctx.room.name}")

    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and introduce yourself as the Give Me the Mic channel assistant. Ask how you can help them today."
    )
    
    print("Initial greeting sent to user")


if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))