import { Room, RoomEvent, RemoteParticipant, LocalTrack, Track, AudioTrack } from 'livekit-client';
import { openaiService } from './openai.js';
import { liveKitService } from './livekit.js';
import { storage } from '../storage.js';

export class VoiceAgent {
  private room: Room | null = null;
  private agentConfigId: number;
  private sessionId: string;
  private isListening = false;
  private audioBuffer: Float32Array[] = [];
  private recordingStartTime: number = 0;
  private silenceTimeout: NodeJS.Timeout | null = null;

  constructor(sessionId: string, agentConfigId: number) {
    this.sessionId = sessionId;
    this.agentConfigId = agentConfigId;
  }

  async connect(): Promise<void> {
    try {
      console.log(`Voice agent connecting to session: ${this.sessionId}`);
      
      // Create agent token
      const token = await liveKitService.createAccessToken(this.sessionId, 'ai-agent', {
        canPublish: true,
        canSubscribe: true,
        canPublishData: true
      });

      // Create room instance
      this.room = new Room({
        adaptiveStream: true,
        dynacast: true,
      });

      // Set up event listeners
      this.setupEventListeners();

      // Connect to room
      const wsURL = process.env.LIVEKIT_URL!;
      await this.room.connect(wsURL, token);

      console.log(`Voice agent connected to room: ${this.sessionId}`);

      // Send welcome message after connection
      setTimeout(() => this.sendWelcomeMessage(), 2000);

    } catch (error) {
      console.error('Voice agent connection failed:', error);
      throw error;
    }
  }

  private setupEventListeners(): void {
    if (!this.room) return;

    this.room.on(RoomEvent.Connected, () => {
      console.log('Voice agent connected to LiveKit room');
    });

    this.room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
      console.log(`User joined: ${participant.identity}`);
      if (participant.identity === 'user') {
        // User has joined, start listening for their audio
        this.subscribeToUserAudio(participant);
      }
    });

    this.room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === 'audio' && participant.identity === 'user') {
        console.log('Subscribed to user audio track');
        this.processUserAudio(track as AudioTrack);
      }
    });

    this.room.on(RoomEvent.Disconnected, () => {
      console.log('Voice agent disconnected from room');
      this.cleanup();
    });
  }

  private subscribeToUserAudio(participant: RemoteParticipant): void {
    // Subscribe to all audio tracks from the user
    participant.audioTrackPublications.forEach((publication) => {
      if (publication.track) {
        console.log('Already have user audio track');
        this.processUserAudio(publication.track as AudioTrack);
      } else {
        publication.setSubscribed(true);
      }
    });
  }

  private processUserAudio(audioTrack: AudioTrack): void {
    console.log('Setting up audio processing for user speech');
    
    // In a real implementation, we would:
    // 1. Capture audio data from the track
    // 2. Detect voice activity
    // 3. Buffer audio during speech
    // 4. Send to OpenAI Realtime API for transcription and response
    // 5. Stream back AI response audio
    
    // For now, we'll simulate this with a simple voice activity detection
    this.startVoiceActivityDetection(audioTrack);
  }

  private startVoiceActivityDetection(audioTrack: AudioTrack): void {
    // This is a simplified implementation
    // In reality, you'd analyze the audio stream for voice activity
    console.log('Voice activity detection started');
    
    // Simulate periodic processing of user speech
    const processInterval = setInterval(async () => {
      if (this.room?.state === 'connected') {
        // Simulate detecting speech and processing it
        try {
          await this.simulateVoiceProcessing();
        } catch (error) {
          console.error('Error processing voice:', error);
        }
      } else {
        clearInterval(processInterval);
      }
    }, 10000); // Check every 10 seconds for demo purposes
  }

  private async simulateVoiceProcessing(): Promise<void> {
    try {
      // Get agent configuration
      const agentConfig = await storage.getAgentConfig(this.agentConfigId);
      if (!agentConfig) return;

      // Simulate transcribed user speech
      const userMessage = "Can you tell me about the Give Me the Mic channel?";
      console.log('Simulated user speech:', userMessage);

      // Generate AI response
      const response = await openaiService.generateChatResponse([
        { 
          role: 'system', 
          content: `You are an AI assistant for the "Give Me the Mic" YouTube channel. You help users learn about the channel, its content, and music-related topics. Keep responses conversational and helpful.` 
        },
        { role: 'user', content: userMessage }
      ]);

      console.log('AI response generated:', response);

      // Generate speech audio
      const audioBuffer = await openaiService.generateVoiceResponse(response, {
        voice: agentConfig.voiceModel as any,
        speed: 1.0
      });

      // Play response audio in the room
      await this.playResponseAudio(audioBuffer);

      // Save conversation
      await storage.createConversation({
        sessionId: this.sessionId,
        agentConfigId: this.agentConfigId,
        userMessage,
        agentResponse: response
      });

    } catch (error) {
      console.error('Error in voice processing simulation:', error);
    }
  }

  private async playResponseAudio(audioBuffer: Buffer): Promise<void> {
    if (!this.room) return;

    try {
      // Send audio data via data channel for client playback
      await this.room.localParticipant.publishData(
        new TextEncoder().encode(JSON.stringify({
          type: 'ai-response',
          audioData: audioBuffer.toString('base64'),
          timestamp: new Date().toISOString()
        })),
        { reliable: true }
      );

      console.log('AI response audio sent to user');
    } catch (error) {
      console.error('Failed to send response audio:', error);
    }
  }

  private async sendWelcomeMessage(): Promise<void> {
    try {
      const agentConfig = await storage.getAgentConfig(this.agentConfigId);
      if (!agentConfig) return;

      const welcomeMessage = `Hello! I'm your ${agentConfig.name}. I can help you with information about the Give Me the Mic channel. What would you like to know?`;
      
      // Generate welcome audio
      const audioBuffer = await openaiService.generateVoiceResponse(welcomeMessage, {
        voice: agentConfig.voiceModel as any,
        speed: 1.0
      });

      // Send welcome message
      await this.playResponseAudio(audioBuffer);

      // Save to conversation history
      await storage.createConversation({
        sessionId: this.sessionId,
        agentConfigId: this.agentConfigId,
        userMessage: "Session started",
        agentResponse: welcomeMessage
      });

      console.log('Welcome message sent to user');
    } catch (error) {
      console.error('Failed to send welcome message:', error);
    }
  }

  async disconnect(): Promise<void> {
    if (this.room) {
      await this.room.disconnect();
      this.cleanup();
    }
  }

  private cleanup(): void {
    if (this.silenceTimeout) {
      clearTimeout(this.silenceTimeout);
      this.silenceTimeout = null;
    }
    this.audioBuffer = [];
    this.isListening = false;
    this.room = null;
  }
}

// Agent manager to handle multiple voice agents
class VoiceAgentManager {
  private agents = new Map<string, VoiceAgent>();

  async startAgent(sessionId: string, agentConfigId: number): Promise<VoiceAgent> {
    console.log(`Starting voice agent for session: ${sessionId}`);
    
    // Stop existing agent if any
    await this.stopAgent(sessionId);

    // Create new agent
    const agent = new VoiceAgent(sessionId, agentConfigId);
    await agent.connect();
    
    this.agents.set(sessionId, agent);
    return agent;
  }

  async stopAgent(sessionId: string): Promise<void> {
    const agent = this.agents.get(sessionId);
    if (agent) {
      await agent.disconnect();
      this.agents.delete(sessionId);
      console.log(`Voice agent stopped for session: ${sessionId}`);
    }
  }

  getAgent(sessionId: string): VoiceAgent | undefined {
    return this.agents.get(sessionId);
  }
}

export const voiceAgentManager = new VoiceAgentManager();