import { useState, useRef, useCallback } from "react";
import { useLiveKit } from "./use-livekit";
import { apiRequest } from "@/lib/queryClient";

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export function useVoiceSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  
  const { 
    room, 
    isConnected, 
    connect: connectToRoom, 
    disconnect: disconnectFromRoom,
    error: livekitError 
  } = useLiveKit();

  const startSession = useCallback(async (agentConfigId: number): Promise<string> => {
    try {
      setConnectionStatus('connecting');
      
      // Generate session ID
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Create LiveKit room
      const roomName = `voice_agent_${newSessionId}`;
      await apiRequest('POST', '/api/livekit/rooms', {
        roomName,
        maxParticipants: 2
      });

      // Get access token
      const tokenResponse = await apiRequest('POST', '/api/livekit/token', {
        roomName,
        participantName: 'user'
      });
      
      const tokenData = await tokenResponse.json();
      
      // Connect to room
      await connectToRoom(roomName, tokenData.token);
      
      setSessionId(newSessionId);
      setConnectionStatus('connected');
      setIsRecording(true);
      
      return newSessionId;
    } catch (error) {
      console.error('Failed to start voice session:', error);
      setConnectionStatus('error');
      throw error;
    }
  }, [connectToRoom]);

  const stopSession = useCallback(async () => {
    try {
      setIsRecording(false);
      setConnectionStatus('disconnected');
      
      if (room) {
        await disconnectFromRoom();
      }
      
      setSessionId(null);
      setIsMuted(false);
    } catch (error) {
      console.error('Failed to stop voice session:', error);
      setConnectionStatus('error');
    }
  }, [room, disconnectFromRoom]);

  const toggleMute = useCallback(() => {
    if (room) {
      const audioTrack = room.localParticipant.audioTracks.values().next().value;
      if (audioTrack) {
        const newMutedState = !isMuted;
        audioTrack.mute(newMutedState);
        setIsMuted(newMutedState);
      }
    }
  }, [room, isMuted]);

  return {
    sessionId,
    isConnected,
    isRecording,
    isMuted,
    connectionStatus,
    startSession,
    stopSession,
    toggleMute,
    error: livekitError
  };
}
