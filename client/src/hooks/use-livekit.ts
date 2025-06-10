import { useState, useRef, useCallback, useEffect } from "react";
import { Room, RoomEvent, RemoteParticipant, RemoteTrack, RemoteTrackPublication, DataPacket_Kind } from "livekit-client";

export function useLiveKit() {
  const [room, setRoom] = useState<Room | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<RemoteParticipant[]>([]);
  
  const roomRef = useRef<Room | null>(null);

  const connect = useCallback(async (roomName: string, token: string, livekitUrl?: string) => {
    try {
      setError(null);
      
      // Create new room instance
      const newRoom = new Room({
        // automatically manage quality based on bandwidth
        adaptiveStream: true,
        // optimize for voice
        dynacast: true,
      });

      // Set up event listeners
      newRoom.on(RoomEvent.Connected, () => {
        console.log('Connected to LiveKit room:', roomName);
        setIsConnected(true);
      });

      newRoom.on(RoomEvent.Disconnected, (reason) => {
        console.log('Disconnected from LiveKit room:', reason);
        setIsConnected(false);
        setParticipants([]);
      });

      newRoom.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        console.log('Participant connected:', participant.identity);
        setParticipants(prev => [...prev, participant]);
      });

      newRoom.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        console.log('Participant disconnected:', participant.identity);
        setParticipants(prev => prev.filter(p => p.identity !== participant.identity));
      });

      newRoom.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        console.log('Track subscribed:', track.kind, 'from', participant.identity);
        
        if (track.kind === 'audio') {
          // Handle audio track
          const audioElement = track.attach();
          document.body.appendChild(audioElement);
        }
      });

      newRoom.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        console.log('Track unsubscribed:', track.kind);
        track.detach();
      });

      newRoom.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant, kind?: DataPacket_Kind) => {
        const message = new TextDecoder().decode(payload);
        console.log('Data received from', participant?.identity, ':', message);
        
        try {
          const data = JSON.parse(message);
          if (data.type === 'ai-response') {
            console.log('AI Response:', data.message);
            
            // Play AI response audio if available
            if (data.audioData) {
              const audio = new Audio(`data:audio/mpeg;base64,${data.audioData}`);
              audio.play().catch(console.error);
            }
          }
        } catch (e) {
          // Not JSON data, ignore
        }
      });

      // Connect to room - use provided URL or fallback
      const wsURL = livekitUrl || import.meta.env.VITE_LIVEKIT_URL || 'wss://voiceagent-livekit-t3b8vrdx.livekit.cloud';
      console.log('Connecting to LiveKit at:', wsURL);
      console.log('Using token:', token);
      await newRoom.connect(wsURL, token);

      // Enable microphone and set up voice activity detection
      try {
        await newRoom.localParticipant.setMicrophoneEnabled(true);
        
        // Set up voice activity detection for speech processing
        const audioTracks = newRoom.localParticipant.audioTrackPublications;
        if (audioTracks.size > 0) {
          const audioTrack = Array.from(audioTracks.values())[0];
          if (audioTrack && audioTrack.track) {
            console.log('Audio track ready for voice detection');
            // Voice activity detection would go here in a full implementation
          }
        }
      } catch (micError) {
        console.warn('Microphone access failed:', micError);
        // Continue without microphone for now
      }

      roomRef.current = newRoom;
      setRoom(newRoom);
      
    } catch (err) {
      console.error('Failed to connect to LiveKit room:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to room');
      throw err;
    }
  }, []);

  const disconnect = useCallback(async () => {
    if (roomRef.current) {
      try {
        await roomRef.current.disconnect();
        roomRef.current = null;
        setRoom(null);
        setIsConnected(false);
        setParticipants([]);
        setError(null);
      } catch (err) {
        console.error('Error disconnecting from room:', err);
        setError(err instanceof Error ? err.message : 'Failed to disconnect');
      }
    }
  }, []);

  const sendData = useCallback(async (data: string, reliable: boolean = true) => {
    if (roomRef.current && isConnected) {
      try {
        const encoder = new TextEncoder();
        const payload = encoder.encode(data);
        await roomRef.current.localParticipant.publishData(
          payload, 
          { reliable: reliable }
        );
      } catch (err) {
        console.error('Failed to send data:', err);
        setError(err instanceof Error ? err.message : 'Failed to send data');
      }
    }
  }, [isConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (roomRef.current) {
        roomRef.current.disconnect();
      }
    };
  }, []);

  return {
    room,
    isConnected,
    error,
    participants,
    connect,
    disconnect,
    sendData
  };
}
