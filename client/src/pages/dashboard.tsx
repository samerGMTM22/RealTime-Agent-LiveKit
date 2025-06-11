import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import VoiceInterface from "@/components/voice-interface";
import ConversationHistory from "@/components/conversation-history";
import SystemStatus from "@/components/system-status";
import { Button } from "@/components/ui/button";
import { Mic, Cog } from "lucide-react";
import { Link } from "wouter";

export default function Dashboard() {
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  const { data: activeAgent } = useQuery({
    queryKey: ["/api/agent-configs/active"],
  });

  const { data: systemStatus } = useQuery({
    queryKey: ["/api/status"],
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-space-blue via-slate-800 to-deep-purple text-white">
      {/* Header */}
      <header className="glass-card border-b border-white/10 p-4 md:p-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-r from-electric-blue to-cyber-cyan flex items-center justify-center">
              <Mic className="text-white text-xl" />
            </div>
            <div>
              <h1 className="text-2xl font-bold gradient-text">VoiceAgent Pro</h1>
              <p className="text-sm text-gray-300">AI Voice Assistant Platform</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Enhanced Status Indicator */}
            <div className="flex items-center space-x-2 glass-card px-4 py-2 rounded-full">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium">
                {systemStatus && typeof systemStatus === 'object' ? (
                  (() => {
                    const status = systemStatus as any;
                    const services = [];
                    if (status.livekit === 'online') services.push('LiveKit');
                    if (status.openai === 'connected') services.push('OpenAI');
                    if (status.youtube === 'active') services.push('YouTube');
                    return services.length > 0 ? `${services.length} Services Active` : 'Disconnected';
                  })()
                ) : 'Checking...'}
              </span>
            </div>
            
            {/* Configuration Button */}
            <Link href="/configuration">
              <Button 
                variant="ghost" 
                size="sm"
                className="text-gray-300 hover:text-white hover:bg-white/10"
              >
                <Cog className="h-5 w-5 mr-2" />
                Configuration
              </Button>
            </Link>
            
            {/* User Profile */}
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
              <span className="text-sm font-bold">U</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4 md:p-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
            
            {/* Voice Interaction Panel */}
            <div className="lg:col-span-2 space-y-6">
              <VoiceInterface 
                activeAgent={activeAgent}
                sessionId={currentSessionId}
                onSessionStart={setCurrentSessionId}
              />
              
              {currentSessionId && (
                <ConversationHistory sessionId={currentSessionId} />
              )}
            </div>

            {/* Control Panel */}
            <div className="space-y-6">
              {/* Agent Info Card - Essential details only */}
              <div className="glass-card p-6 rounded-xl border border-white/10">
                <h3 className="text-xl font-semibold mb-4 gradient-text">Agent Information</h3>
                {activeAgent && typeof activeAgent === 'object' ? (
                  <div className="space-y-3">
                    <div>
                      <span className="text-gray-400">Name:</span>
                      <span className="ml-2 text-white">{(activeAgent as any).name}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Type:</span>
                      <span className="ml-2 text-white capitalize">{(activeAgent as any).type?.replace('-', ' ')}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Voice Model:</span>
                      <span className="ml-2 text-white">{(activeAgent as any).voiceModel}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-400">Loading agent information...</p>
                )}
              </div>
              
              <SystemStatus status={systemStatus as any} />
            </div>
          </div>
        </div>
      </main>


    </div>
  );
}
