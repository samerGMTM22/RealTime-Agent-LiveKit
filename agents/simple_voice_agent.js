/**
 * Simple Voice Agent - CommonJS Implementation
 */
const { AccessToken } = require('livekit-server-sdk');
const OpenAI = require('openai');

class SimpleVoiceAgent {
  constructor() {
    this.openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    this.config = null;
  }

  async getConfig() {
    try {
      const fetch = await import('node-fetch').then(mod => mod.default);
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
      name: 'Simple Voice Agent',
      systemPrompt: 'You are a helpful AI assistant.',
      voiceModel: 'alloy',
      temperature: 80
    };
  }

  async generateResponse(userInput) {
    try {
      const temp = Math.min(2.0, (this.config.temperature / 100.0) * 2.0);
      
      const completion = await this.openai.chat.completions.create({
        model: 'gpt-4o',
        messages: [
          { role: 'system', content: this.config.systemPrompt },
          { role: 'user', content: userInput }
        ],
        temperature: temp,
      });

      return completion.choices[0].message.content;
    } catch (error) {
      console.error('Chat completion error:', error);
      return 'I apologize, but I encountered an error processing your request.';
    }
  }

  async synthesizeAudio(text) {
    try {
      const response = await this.openai.audio.speech.create({
        model: 'tts-1',
        voice: this.config.voiceModel || 'alloy',
        input: text,
      });

      console.log(`Synthesized audio for: "${text}"`);
      return Buffer.from(await response.arrayBuffer());
    } catch (error) {
      console.error('TTS error:', error);
      return null;
    }
  }

  async start() {
    console.log('Simple Voice Agent started');
    console.log(`Config: ${this.config.name}`);
    console.log(`Voice: ${this.config.voiceModel}`);
    console.log(`Temperature: ${this.config.temperature}`);
    
    // Simulate agent activity
    const greeting = "Hello! I'm your voice assistant. How can I help you today?";
    await this.synthesizeAudio(greeting);
    
    // Keep the process running
    setInterval(() => {
      console.log('Voice agent running...');
    }, 30000);
  }
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 6 || args[0] !== 'start') {
    console.log('Usage: node simple_voice_agent.js start --url <url> --api-key <key> --api-secret <secret>');
    process.exit(1);
  }

  console.log('Starting Simple Voice Agent...');

  const agent = new SimpleVoiceAgent();
  await agent.getConfig();
  await agent.start();

  // Keep the process running
  process.on('SIGINT', () => {
    console.log('Shutting down voice agent...');
    process.exit(0);
  });
}

if (require.main === module) {
  main().catch(console.error);
}