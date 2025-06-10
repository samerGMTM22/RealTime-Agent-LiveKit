import { Room, RoomOptions, ConnectOptions, RemoteParticipant, Track } from 'livekit-client';

export interface LiveKitConfig {
  url: string;
  token: string;
  options?: RoomOptions;
  connectOptions?: ConnectOptions;
}

export class LiveKitManager {
  private room: Room | null = null;
  private config: LiveKitConfig | null = null;

  constructor() {
    this.room = null;
  }

  async connect(config: LiveKitConfig): Promise<Room> {
    this.config = config;
    
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      publishDefaults: {
        audioPreset: {
          maxBitrate: 64_000,
        },
      },
      ...config.options,
    });

    // Set up event listeners
    this.setupEventListeners(room);

    // Connect to the room
    await room.connect(config.url, config.token, {
      autoSubscribe: true,
      ...config.connectOptions,
    });

    this.room = room;
    return room;
  }

  async disconnect(): Promise<void> {
    if (this.room) {
      await this.room.disconnect();
      this.room = null;
    }
  }

  async enableMicrophone(enabled: boolean = true): Promise<void> {
    if (this.room) {
      await this.room.localParticipant.setMicrophoneEnabled(enabled);
    }
  }

  async enableCamera(enabled: boolean = true): Promise<void> {
    if (this.room) {
      await this.room.localParticipant.setCameraEnabled(enabled);
    }
  }

  async sendData(data: string | Uint8Array, reliable: boolean = true): Promise<void> {
    if (this.room) {
      const payload = typeof data === 'string' ? new TextEncoder().encode(data) : data;
      await this.room.localParticipant.publishData(payload, { reliable });
    }
  }

  getRoom(): Room | null {
    return this.room;
  }

  getParticipants(): RemoteParticipant[] {
    return this.room ? Array.from(this.room.remoteParticipants.values()) : [];
  }

  private setupEventListeners(room: Room): void {
    room.on('connected', () => {
      console.log('Connected to LiveKit room');
    });

    room.on('disconnected', (reason?: string) => {
      console.log('Disconnected from LiveKit room:', reason);
    });

    room.on('participantConnected', (participant: RemoteParticipant) => {
      console.log('Participant connected:', participant.identity);
    });

    room.on('participantDisconnected', (participant: RemoteParticipant) => {
      console.log('Participant disconnected:', participant.identity);
    });

    room.on('trackSubscribed', (track: Track, publication: any, participant: RemoteParticipant) => {
      console.log('Track subscribed:', track.kind, 'from', participant.identity);
      
      if (track.kind === Track.Kind.Audio && track.source === Track.Source.Microphone) {
        // Handle audio track
        const audioElement = track.attach();
        document.body.appendChild(audioElement);
      }
    });

    room.on('trackUnsubscribed', (track: Track) => {
      console.log('Track unsubscribed:', track.kind);
      track.detach();
    });

    room.on('dataReceived', (payload: Uint8Array, participant?: RemoteParticipant) => {
      const message = new TextDecoder().decode(payload);
      console.log('Data received from', participant?.identity || 'unknown', ':', message);
    });
  }
}

// Singleton instance
export const liveKitManager = new LiveKitManager();
