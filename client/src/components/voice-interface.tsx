import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Mic, MicOff, Play, Square } from "lucide-react";
import { useVoiceSession } from "@/hooks/use-voice-session";
import { cn } from "@/lib/utils";

interface VoiceInterfaceProps {
  activeAgent: any;
  sessionId: string | null;
  onSessionStart: (sessionId: string) => void;
}

export default function VoiceInterface({ activeAgent, sessionId, onSessionStart }: VoiceInterfaceProps) {
  const {
    isConnected,
    isRecording,
    isMuted,
    startSession,
    stopSession,
    toggleMute,
    connectionStatus
  } = useVoiceSession();

  const handleStartSession = async () => {
    try {
      const newSessionId = await startSession(activeAgent?.id || 1);
      onSessionStart(newSessionId);
    } catch (error) {
      console.error("Failed to start voice session:", error);
    }
  };

  return (
    <Card className="glass-card rounded-2xl p-8 premium-shadow animate-float">
      <CardContent className="p-0">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold gradient-text mb-2">Voice Assistant</h2>
          <p className="text-gray-300">Speak naturally to interact with your AI agent</p>
          {activeAgent && (
            <p className="text-sm text-cyber-cyan mt-2">
              Active: {activeAgent.name} ({activeAgent.type})
            </p>
          )}
        </div>

        {/* Voice Visualizer */}
        <div className="flex items-center justify-center mb-8">
          <div className="relative">
            <div className={cn(
              "w-32 h-32 rounded-full opacity-30 animate-pulse-slow",
              isRecording 
                ? "bg-gradient-to-r from-red-500 to-pink-500" 
                : "bg-gradient-to-r from-electric-blue to-cyber-cyan"
            )}></div>
            <div className={cn(
              "absolute inset-4 w-24 h-24 rounded-full flex items-center justify-center",
              isRecording 
                ? "bg-gradient-to-r from-red-500 to-pink-500" 
                : "bg-gradient-to-r from-electric-blue to-cyber-cyan"
            )}>
              <Mic className="text-white text-2xl" />
            </div>
          </div>
        </div>

        {/* Voice Wave Visualizer */}
        <div className="flex items-center justify-center space-x-1 mb-8">
          {[...Array(7)].map((_, i) => (
            <div
              key={i}
              className={cn(
                "voice-wave",
                isRecording ? "animate-voice-wave" : ""
              )}
              style={{
                animationDelay: `${i * 0.1}s`,
                animationPlayState: isRecording ? 'running' : 'paused'
              }}
            />
          ))}
        </div>

        {/* Connection Status */}
        <div className="text-center mb-6">
          <div className={cn(
            "inline-flex items-center space-x-2 px-4 py-2 rounded-full glass-card",
            connectionStatus === 'connected' ? 'text-green-400' : 'text-yellow-400'
          )}>
            <div className={cn(
              "w-2 h-2 rounded-full",
              connectionStatus === 'connected' ? 'bg-green-400' : 'bg-yellow-400',
              'animate-pulse'
            )}></div>
            <span className="text-sm font-medium capitalize">{connectionStatus}</span>
          </div>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center justify-center space-x-4">
          <Button
            onClick={handleStartSession}
            disabled={isConnected || !activeAgent}
            className="glass-card hover:bg-green-500/20 transition-all duration-300 px-6 py-3 rounded-xl flex items-center space-x-2"
            variant="ghost"
          >
            <Play className="h-5 w-5 text-green-400" />
            <span>Start Session</span>
          </Button>

          <Button
            onClick={stopSession}
            disabled={!isConnected}
            className="glass-card hover:bg-red-500/20 transition-all duration-300 px-6 py-3 rounded-xl flex items-center space-x-2"
            variant="ghost"
          >
            <Square className="h-5 w-5 text-red-400" />
            <span>Stop</span>
          </Button>

          <Button
            onClick={toggleMute}
            disabled={!isConnected}
            className="glass-card hover:bg-yellow-500/20 transition-all duration-300 px-6 py-3 rounded-xl flex items-center space-x-2"
            variant="ghost"
          >
            {isMuted ? (
              <MicOff className="h-5 w-5 text-yellow-400" />
            ) : (
              <Mic className="h-5 w-5 text-green-400" />
            )}
            <span>{isMuted ? 'Unmute' : 'Mute'}</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}