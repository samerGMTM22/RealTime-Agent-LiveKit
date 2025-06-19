/**
 * LiveKit Voice Agent - Node.js Implementation
 * Bypasses Python library dependency issues
 */
import { Room, RoomEvent } from 'livekit-client';
import { AccessToken } from 'livekit-server-sdk';
import OpenAI from 'openai';
import fetch from 'node-fetch';

class VoiceAgent {
  constructor() {
    this.room = null;
    this.openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    this.config = null;
  }

  async getConfig() {
    try {
      const response = await fetch('http://localhost:5000/api/agent-configs/active');
      if (response.ok) {
        this.config = await response.json();
        console.log(`Using config: ${this.config.name}`);
      } else {
        this.config = this.getDefaultConfig();
      }
    } catch (error) {
      console.error('Config fetch error:', error);
      this.config = this.getDefaultConfig();
    }
  }

  getDefaultConfig() {
    return {
      name: 'Node.js Voice Agent',
      systemPrompt: 'You are a helpful AI assistant.',
      voiceModel: 'alloy',
      temperature: 80
    };
  }

  async connect(url, token) {
    this.room = new Room();
    
    this.room.on(RoomEvent.TrackPublished, (publication, participant) => {
      console.log(`Track published: ${publication.kind} from ${participant.identity}`);
      if (publication.kind === 'audio') {
        publication.setSubscribed(true);
      }
    });

    this.room.on(RoomEvent.ParticipantConnected, (participant) => {
      console.log(`Participant joined: ${participant.identity}`);
      this.startConversation(participant);
    });

    await this.room.connect(url, token);
    console.log('Agent connected to room');
  }

  async startConversation(participant) {
    // Send initial greeting
    const greeting = "Hello! I'm your voice assistant. How can I help you today?";
    await this.synthesizeAndSendAudio(greeting);
  }

  async synthesizeAndSendAudio(text) {
    try {
      const voice = this.config.voiceModel || 'alloy';
      
      // Use OpenAI TTS to generate audio
      const response = await this.openai.audio.speech.create({
        model: 'tts-1',
        voice: voice,
        input: text,
      });

      const audioBuffer = Buffer.from(await response.arrayBuffer());
      
      // Create audio track and publish to room
      // Note: This is a simplified implementation
      console.log(`Synthesized audio response: "${text}"`);
      console.log(`Audio buffer size: ${audioBuffer.length} bytes`);
      
    } catch (error) {
      console.error('TTS error:', error);
    }
  }

  async processAudioInput(audioData) {
    try {
      // Transcribe audio using OpenAI Whisper
      const transcription = await this.openai.audio.transcriptions.create({
        file: audioData,
        model: 'whisper-1',
      });

      const userText = transcription.text;
      console.log(`User said: "${userText}"`);

      // Generate response using GPT
      const temp = Math.min(2.0, (this.config.temperature / 100.0) * 2.0);
      
      const completion = await this.openai.chat.completions.create({
        model: 'gpt-4o',
        messages: [
          { role: 'system', content: this.config.systemPrompt },
          { role: 'user', content: userText }
        ],
        temperature: temp,
      });

      const responseText = completion.choices[0].message.content;
      console.log(`Agent response: "${responseText}"`);

      // Synthesize and send audio response
      await this.synthesizeAndSendAudio(responseText);

    } catch (error) {
      console.error('Audio processing error:', error);
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 6 || args[0] !== 'start') {
    console.log('Usage: node voice_agent.js start --url <url> --api-key <key> --api-secret <secret>');
    process.exit(1);
  }

  const url = args[2];
  const apiKey = args[4];
  const apiSecret = args[6];
  
  console.log('Starting Node.js Voice Agent...');

  const agent = new VoiceAgent();
  await agent.getConfig();

  // Generate access token for the agent
  const token = new AccessToken(apiKey, apiSecret, {
    identity: 'voice-agent',
    ttl: '1h',
  });
  
  token.addGrant({
    roomJoin: true,
    room: process.env.LIVEKIT_ROOM_NAME,
    canPublish: true,
    canSubscribe: true,
  });

  const jwt = token.toJwt();
  
  try {
    await agent.connect(url, jwt);
    console.log('Voice agent started successfully');
    
    // Keep the process running
    process.on('SIGINT', () => {
      console.log('Shutting down voice agent...');
      process.exit(0);
    });
    
  } catch (error) {
    console.error('Agent connection failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch(console.error);
}