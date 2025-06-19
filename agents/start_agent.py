#!/usr/bin/env python3
"""Agent startup script that handles library dependencies"""
import os
import sys
import subprocess
import glob

def find_libstdcxx():
    """Find the libstdc++.so.6 library in the Nix store"""
    possible_paths = [
        "/nix/store/*/lib/libstdc++.so.6",
        "/nix/store/gcc*/lib/libstdc++.so.6", 
        "/nix/store/*gcc*/lib/libstdc++.so.6",
        "/nix/store/libstdcxx*/lib/libstdc++.so.6"
    ]
    
    for pattern in possible_paths:
        matches = glob.glob(pattern)
        if matches:
            return os.path.dirname(matches[0])
    
    return None

def setup_environment():
    """Set up the environment for LiveKit agent"""
    # Find libstdc++ library
    lib_path = find_libstdcxx()
    if lib_path:
        current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
        if current_ld_path:
            os.environ['LD_LIBRARY_PATH'] = f"{lib_path}:{current_ld_path}"
        else:
            os.environ['LD_LIBRARY_PATH'] = lib_path
        print(f"Set LD_LIBRARY_PATH to include: {lib_path}")
    else:
        print("Warning: Could not find libstdc++.so.6")

def main():
    """Main entry point"""
    setup_environment()
    
    # Import LiveKit after setting up environment
    try:
        from livekit import agents, rtc
        from livekit.agents import JobContext, WorkerOptions, cli, AutoSubscribe
        from livekit.plugins import openai, silero
        import asyncio
        import logging
        import httpx
        from typing import Dict
        from dotenv import load_dotenv
        
        load_dotenv()
        logger = logging.getLogger("voice-agent")
        
        async def get_agent_config(room_name: str) -> Dict:
            """Fetch agent configuration from database."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:5000/api/agent-configs/active")
                    if response.status_code == 200:
                        config = response.json()
                        logger.info(f"Using config: {config.get('name', 'Default')}")
                        return config
            except Exception as e:
                logger.error(f"Config fetch error: {e}")
            
            return {
                "systemPrompt": "You are a helpful AI assistant.",
                "voiceModel": "alloy", 
                "temperature": 80
            }
        
        async def entrypoint(ctx: JobContext):
            """Main entry point for the voice agent."""
            logger.info(f"Agent starting for room: {ctx.room.name}")
            
            await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
            
            @ctx.room.on("track_published")
            def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                if publication.kind == "audio":
                    publication.set_subscribed(True)
                    logger.info(f"Audio subscribed from {participant.identity}")
            
            participant = await ctx.wait_for_participant()
            logger.info(f"Participant joined: {participant.identity}")
            
            config = await get_agent_config(ctx.room.name)
            
            voice = config.get("voiceModel", "alloy")
            temp_raw = config.get("temperature", 80)
            llm_temp = min(2.0, float(temp_raw) / 100.0 * 2.0)
            
            logger.info(f"Voice: {voice}, Temperature: {llm_temp}")
            
            # Use standard STT-LLM-TTS pipeline
            agent = agents.VoiceAgent(
                vad=silero.VAD.load(),
                stt=openai.STT(model="whisper-1"),
                llm=openai.LLM(
                    model="gpt-4o",
                    temperature=llm_temp,
                ),
                tts=openai.TTS(model="tts-1", voice=voice),
            )
        
            await agent.start(ctx.room, participant)
            logger.info("Voice agent started successfully")
        
        # Run the agent
        cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("LibC dependency issue persists")
        sys.exit(1)
    except Exception as e:
        print(f"Agent error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()