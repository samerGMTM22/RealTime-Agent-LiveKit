from dotenv import load_dotenv
import asyncio
import os

from livekit import agents
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.plugins import openai, silero
from livekit.agents import VoiceAssistant

load_dotenv()


class GiveMeTheMicAssistant:
    """Give Me the Mic YouTube channel assistant."""
    
    def __init__(self):
        self.channel_info = """Give Me the Mic (@givemethemicmusic) is a music-focused YouTube channel with:
        
• 484 subscribers and growing
• 249 videos of music content
• 75,000+ total views
• Focus on music education, tutorials, and entertainment
• Gives aspiring musicians a platform to share their voice
• Features content on singing techniques, instrument tutorials, recording tips, and music industry insights
        
The channel is dedicated to helping people develop their musical talents and provides valuable resources for musicians at all skill levels."""

    def get_system_prompt(self):
        return f"""You are a helpful voice AI assistant for the "Give Me the Mic" YouTube channel. 
        You help users learn about the channel's content, music-related topics, and provide assistance.
        The channel has 484 subscribers and 249 videos focusing on music and entertainment.
        Keep responses conversational, helpful, and engaging.
        
        Channel Information: {self.channel_info}
        
        You can help with:
        - Information about the Give Me the Mic channel
        - Music tips and advice (singing, instruments, recording, performance, songwriting)
        - Content suggestions from the channel
        - General music-related questions
        """


async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent."""
    print(f"Starting agent for room: {ctx.room.name}")
    
    # Connect to the room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    print(f"Agent connected to room: {ctx.room.name}")
    
    # Create assistant instance
    assistant_helper = GiveMeTheMicAssistant()
    
    try:
        # Create voice assistant with OpenAI integration
        assistant = VoiceAssistant(
            vad=silero.VAD.load(),
            stt=openai.STT(),
            llm=openai.LLM(
                model="gpt-4o",
                temperature=0.8,
            ),
            tts=openai.TTS(voice="alloy"),
            chat_ctx=openai.ChatContext().append(
                role="system", 
                text=assistant_helper.get_system_prompt()
            ),
        )
        
        # Start the assistant
        assistant.start(ctx.room)
        print("Voice assistant started successfully")
        
        # Send initial greeting
        await assistant.say(
            "Hello! I'm your Give Me the Mic assistant. I can help you with information about our YouTube channel, music tips, and answer any questions you have about music. How can I help you today?",
            allow_interruptions=True
        )
        print("Initial greeting sent")
        
        # Keep the agent running
        await asyncio.sleep(0.1)  # Small delay to ensure greeting is sent
        
    except Exception as e:
        print(f"Error starting voice assistant: {e}")
        # Basic fallback - just stay connected
        print("Agent remains connected for basic functionality")


if __name__ == "__main__":
    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )