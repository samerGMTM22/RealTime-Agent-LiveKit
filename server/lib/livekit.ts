import { AccessToken, RoomServiceClient, WebhookReceiver } from 'livekit-server-sdk';

const livekitHost = process.env.LIVEKIT_URL || process.env.LIVEKIT_HOST || 'wss://default-host';
const apiKey = process.env.LIVEKIT_API_KEY || process.env.LIVEKIT_KEY || 'default_key';
const apiSecret = process.env.LIVEKIT_API_SECRET || process.env.LIVEKIT_SECRET || 'default_secret';

export class LiveKitService {
  private roomService: RoomServiceClient;
  private webhookReceiver: WebhookReceiver;

  constructor() {
    this.roomService = new RoomServiceClient(livekitHost, apiKey, apiSecret);
    this.webhookReceiver = new WebhookReceiver(apiKey, apiSecret);
  }

  async createAccessToken(
    roomName: string, 
    participantName: string, 
    permissions?: {
      canPublish?: boolean;
      canSubscribe?: boolean;
      canPublishData?: boolean;
      canPublishSources?: string[];
    }
  ): Promise<string> {
    try {
      const token = new AccessToken(apiKey, apiSecret, {
        identity: participantName,
        ttl: '10m',
      });

      token.addGrant({
        roomJoin: true,
        room: roomName,
        canPublish: permissions?.canPublish ?? true,
        canSubscribe: permissions?.canSubscribe ?? true,
        canPublishData: permissions?.canPublishData ?? true,
        canPublishSources: permissions?.canPublishSources,
      });

      return token.toJwt();
    } catch (error) {
      console.error("Error creating LiveKit access token:", error);
      throw new Error(`Failed to create access token: ${error.message}`);
    }
  }

  async createRoom(roomName: string, maxParticipants: number = 10): Promise<any> {
    try {
      const room = await this.roomService.createRoom({
        name: roomName,
        emptyTimeout: 10 * 60, // 10 minutes
        maxParticipants,
        metadata: JSON.stringify({
          createdAt: new Date().toISOString(),
          type: 'voice-agent-session'
        })
      });

      return room;
    } catch (error) {
      console.error("Error creating LiveKit room:", error);
      throw new Error(`Failed to create room: ${error.message}`);
    }
  }

  async listRooms(): Promise<any[]> {
    try {
      const rooms = await this.roomService.listRooms();
      return rooms;
    } catch (error) {
      console.error("Error listing LiveKit rooms:", error);
      throw new Error(`Failed to list rooms: ${error.message}`);
    }
  }

  async deleteRoom(roomName: string): Promise<void> {
    try {
      await this.roomService.deleteRoom(roomName);
    } catch (error) {
      console.error("Error deleting LiveKit room:", error);
      throw new Error(`Failed to delete room: ${error.message}`);
    }
  }

  async getParticipants(roomName: string): Promise<any[]> {
    try {
      const participants = await this.roomService.listParticipants(roomName);
      return participants;
    } catch (error) {
      console.error("Error getting LiveKit participants:", error);
      throw new Error(`Failed to get participants: ${error.message}`);
    }
  }

  verifyWebhook(body: string, authorization: string): any {
    try {
      return this.webhookReceiver.receive(body, authorization);
    } catch (error) {
      console.error("Error verifying LiveKit webhook:", error);
      throw new Error(`Failed to verify webhook: ${error.message}`);
    }
  }

  async sendDataMessage(roomName: string, data: any, participantSids?: string[]): Promise<void> {
    try {
      const message = JSON.stringify(data);
      await this.roomService.sendData(roomName, message, 'reliable', participantSids);
    } catch (error) {
      console.error("Error sending data message:", error);
      throw new Error(`Failed to send data message: ${error.message}`);
    }
  }
}

export const liveKitService = new LiveKitService();
