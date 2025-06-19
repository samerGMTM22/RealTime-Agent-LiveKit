#!/usr/bin/env python3
"""Test OpenAI Realtime API access"""

import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_openai_realtime_access():
    """Test if we have access to OpenAI Realtime API"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OPENAI_API_KEY found")
        return False
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1"
    }
    
    try:
        print("🔄 Testing OpenAI Realtime API WebSocket connection...")
        async with websockets.connect(
            "wss://api.openai.com/v1/realtime",
            additional_headers=headers,
            timeout=10
        ) as websocket:
            print("✅ WebSocket connected successfully")
            
            # Send session update to test model access
            session_update = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "model": "gpt-4o-realtime-preview",
                    "voice": "coral"
                }
            }
            
            await websocket.send(json.dumps(session_update))
            print("📤 Sent session update")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)
            print(f"📥 Response: {data.get('type', 'unknown')}")
            
            if data.get('type') == 'session.updated':
                print("✅ Realtime API access confirmed!")
                return True
            elif data.get('type') == 'error':
                print(f"❌ API Error: {data.get('error', {}).get('message', 'unknown')}")
                return False
                
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False
    except asyncio.TimeoutError:
        print("❌ Connection timeout - likely no Realtime API access")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    has_access = asyncio.run(test_openai_realtime_access())
    if has_access:
        print("\n🎉 You have OpenAI Realtime API access!")
    else:
        print("\n⚠️  Realtime API access not available. Using STT-LLM-TTS fallback recommended.")