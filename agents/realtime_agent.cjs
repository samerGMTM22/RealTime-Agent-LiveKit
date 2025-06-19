/**
 * Pure OpenAI Realtime API Voice Agent - Node.js Implementation
 * No STT-LLM-TTS fallback, only Realtime API
 */
const { AccessToken } = require('livekit-server-sdk');
const OpenAI = require('openai');
const WebSocket = require('ws');

class RealtimeVoiceAgent {
  constructor() {
    this.openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    this.config = null;
    this.realtimeWs = null;
    this.roomName = null;
  }

  async getConfig() {
    try {
      const fetch = await import('node-fetch').then(mod => mod.default);
      const response = await fetch('http://localhost:5000/api/agent-configs/active');
      if (response.ok) {
        this.config = await response.json();
        console.log(`Using Realtime config: ${this.config.name}`);
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
      name: 'Realtime Assistant',
      systemPrompt: 'You are a helpful AI assistant that can have natural voice conversations.',
      voiceModel: 'coral',
      temperature: 80,
      responseLength: 'medium'
    };
  }

  async connectToRealtimeAPI() {
    const voiceMapping = {
      alloy: 'alloy', echo: 'echo', fable: 'fable',
      onyx: 'onyx', nova: 'nova', shimmer: 'shimmer', coral: 'coral'
    };

    const voice = voiceMapping[this.config.voiceModel] || 'coral';
    const tempRaw = this.config.temperature || 80;
    
    // Convert temperature: 0-100% to 0.6-1.2 range for Realtime API
    const realtimeTemp = Math.max(0.6, Math.min(1.2, 0.6 + (tempRaw / 100.0) * 0.6));

    console.log(`Realtime API settings - Voice: ${voice}, Temperature: ${realtimeTemp}`);

    // Connect to OpenAI Realtime API via WebSocket
    const wsUrl = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01';
    
    this.realtimeWs = new WebSocket(wsUrl, {
      headers: {
        'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
        'OpenAI-Beta': 'realtime=v1'
      }
    });

    return new Promise((resolve, reject) => {
      this.realtimeWs.on('open', () => {
        console.log('Connected to OpenAI Realtime API');
        
        // Configure the session
        this.realtimeWs.send(JSON.stringify({
          type: 'session.update',
          session: {
            modalities: ['text', 'audio'],
            instructions: this.config.systemPrompt,
            voice: voice,
            input_audio_format: 'pcm16',
            output_audio_format: 'pcm16',
            input_audio_transcription: {
              model: 'whisper-1'
            },
            turn_detection: {
              type: 'server_vad',
              threshold: 0.5,
              prefix_padding_ms: 300,
              silence_duration_ms: 500
            },
            tools: [],
            tool_choice: 'auto',
            temperature: realtimeTemp,
            max_response_output_tokens: 4096
          }
        }));

        // Send initial greeting
        setTimeout(() => {
          this.realtimeWs.send(JSON.stringify({
            type: 'response.create',
            response: {
              modalities: ['text', 'audio'],
              instructions: 'Greet the user warmly and offer your assistance.'
            }
          }));
        }, 1000);

        resolve();
      });

      this.realtimeWs.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleRealtimeMessage(message);
        } catch (error) {
          console.error('Error parsing Realtime API message:', error);
        }
      });

      this.realtimeWs.on('error', (error) => {
        console.error('Realtime API WebSocket error:', error);
        reject(error);
      });

      this.realtimeWs.on('close', () => {
        console.log('Realtime API connection closed');
      });
    });
  }

  handleRealtimeMessage(message) {
    switch (message.type) {
      case 'session.created':
        console.log('Realtime session created');
        break;
      
      case 'session.updated':
        console.log('Realtime session updated');
        break;
      
      case 'response.created':
        console.log('Response created');
        break;
      
      case 'response.done':
        console.log('Response completed');
        break;
      
      case 'response.audio.delta':
        // Handle audio output chunks
        console.log('Received audio delta chunk');
        break;
      
      case 'conversation.item.input_audio_transcription.completed':
        if (message.transcript) {
          console.log(`User said: "${message.transcript}"`);
        }
        break;
      
      case 'response.text.delta':
        if (message.delta) {
          process.stdout.write(message.delta);
        }
        break;
      
      case 'error':
        console.error('Realtime API error:', message.error);
        break;
      
      default:
        // Log other message types for debugging
        console.log(`Realtime message: ${message.type}`);
    }
  }

  async start() {
    console.log('Starting Pure OpenAI Realtime API Agent');
    console.log(`Config: ${this.config.name}`);
    console.log(`Voice: ${this.config.voiceModel}`);
    console.log(`Temperature: ${this.config.temperature}`);
    
    try {
      await this.connectToRealtimeAPI();
      console.log('Realtime API agent started successfully');
      
      // Keep the process running and maintain connection
      setInterval(() => {
        if (this.realtimeWs && this.realtimeWs.readyState === WebSocket.OPEN) {
          // Send ping to keep connection alive
          this.realtimeWs.ping();
        }
      }, 30000);
      
    } catch (error) {
      console.error('Failed to start Realtime API agent:', error);
      throw error;
    }
  }

  async stop() {
    if (this.realtimeWs) {
      this.realtimeWs.close();
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 6 || args[0] !== 'start') {
    console.log('Usage: node realtime_agent.cjs start --url <url> --api-key <key> --api-secret <secret>');
    process.exit(1);
  }

  console.log('Initializing Pure OpenAI Realtime API Agent...');

  const agent = new RealtimeVoiceAgent();
  await agent.getConfig();
  await agent.start();

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.log('Shutting down Realtime API agent...');
    await agent.stop();
    process.exit(0);
  });

  // Keep process running
  process.on('uncaughtException', (error) => {
    console.error('Uncaught exception:', error);
  });
}

if (require.main === module) {
  main().catch(console.error);
}