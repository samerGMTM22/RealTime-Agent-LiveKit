import { useState, useRef, useCallback, useEffect } from "react";
import { Room, RoomEvent, RemoteParticipant, RemoteTrack, RemoteTrackPublication, DataPacket_Kind, Track } from "livekit-client";

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

      // Monitor local track publishing
      newRoom.on(RoomEvent.LocalTrackPublished, (publication, participant) => {
        console.log('Local track published:', publication.kind, publication.source);
        if (publication.kind === Track.Kind.Audio) {
          console.log('Local audio track published successfully');
        }
      });

      newRoom.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        console.log('Track subscribed:', track.kind, 'from', participant.identity);

        if (track.kind === Track.Kind.Audio) {
          console.log('Audio track subscribed, attempting to play');
          const audioElement = track.attach();
          if (audioElement instanceof HTMLAudioElement) {
            audioElement.autoplay = true;
            audioElement.volume = 1.0;
            audioElement.playsInline = true;
            audioElement.controls = false;
            
            // Add event listeners for debugging
            audioElement.addEventListener('canplay', () => {
              console.log('Audio element can play');
            });
            
            audioElement.addEventListener('play', () => {
              console.log('Audio element started playing');
            });
            
            audioElement.addEventListener('error', (e) => {
              console.error('Audio element error:', e);
            });
            
            // Ensure audio plays in browsers that require user interaction
            audioElement.play().catch(err => {
              console.warn('Auto-play failed, will retry on user interaction:', err);
              // Try to play after a user gesture
              document.addEventListener('click', () => {
                audioElement.play().catch(console.error);
              }, { once: true });
            });
            
            document.body.appendChild(audioElement);
            console.log('Audio element attached and configured for playback');
          }
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

      // Request microphone permissions first
      try {
        console.log('Requesting microphone permissions...');
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: 48000
          } 
        });
        console.log('Microphone permissions granted');
        
        // Stop the test stream
        stream.getTracks().forEach(track => track.stop());
      } catch (err) {
        console.error('Microphone permission denied:', err);
        setError('Microphone permission is required for voice interaction');
        throw new Error('Microphone permission denied');
      }

      // Connect to room - use provided URL or fallback
      const wsURL = livekitUrl || import.meta.env.VITE_LIVEKIT_URL || 'wss://voiceagent-livekit-t3b8vrdx.livekit.cloud';
      console.log('Connecting to LiveKit at:', wsURL);
      console.log('Using token:', token);
      await newRoom.connect(wsURL, token);

      console.log('Connected to LiveKit room:', roomName);

      // Enable microphone for voice input with better error handling
      try {
        console.log('Enabling microphone...');
        await newRoom.localParticipant.setMicrophoneEnabled(true);
        
        // Verify microphone is actually enabled
        const micTrack = newRoom.localParticipant.audioTrackPublications.values().next().value;
        if (micTrack && micTrack.track) {
          console.log('Microphone enabled and audio track created successfully');
        } else {
          console.warn('Microphone enabled but no audio track detected');
        }
      } catch (err) {
        console.error('Failed to enable microphone:', err);
        setError(`Failed to enable microphone: ${err.message}`);
        throw err;
      }

      setRoom(newRoom);
      setIsConnected(true);

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