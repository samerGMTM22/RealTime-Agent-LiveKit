import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import VoiceInterface from "@/components/voice-interface";
import AgentConfig from "@/components/agent-config";
import ConversationHistory from "@/components/conversation-history";
import SystemStatus from "@/components/system-status";
import DataSources from "@/components/data-sources";
import SettingsModal from "@/components/settings-modal";
import { Button } from "@/components/ui/button";
import { Settings, Mic, MicOff, Play, Square, Cog } from "lucide-react";
import { Link } from "wouter";

export default function Dashboard() {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
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
            {/* Status Indicator */}
            <div className="flex items-center space-x-2 glass-card px-4 py-2 rounded-full">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium">
                {systemStatus?.livekit === 'online' ? 'Connected' : 'Disconnected'}
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
              <AgentConfig />
              <SystemStatus status={systemStatus} />
              {activeAgent && <DataSources agentConfigId={activeAgent.id} />}
            </div>
          </div>
        </div>
      </main>

      {/* Floating Action Button */}
      <Button
        onClick={() => setIsSettingsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-r from-electric-blue to-cyber-cyan hover:from-electric-blue/80 hover:to-cyber-cyan/80 rounded-full premium-shadow animate-float z-40"
        size="icon"
      >
        <Settings className="text-white text-xl" />
      </Button>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        activeAgent={activeAgent}
      />
    </div>
  );
}
