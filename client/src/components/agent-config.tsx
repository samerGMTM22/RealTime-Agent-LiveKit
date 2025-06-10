import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Settings, Save } from "lucide-react";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

const AGENT_TYPES = [
  { value: 'youtube-assistant', label: 'YouTube Channel Assistant' },
  { value: 'customer-service', label: 'Customer Service Agent' },
  { value: 'real-estate', label: 'Real Estate Sales Agent' },
  { value: 'custom', label: 'Custom Agent' }
];

const VOICE_MODELS = [
  { value: 'alloy', label: 'Alloy (Balanced)' },
  { value: 'echo', label: 'Echo (Male)' },
  { value: 'fable', label: 'Fable (British)' },
  { value: 'onyx', label: 'Onyx (Deep)' },
  { value: 'nova', label: 'Nova (Female)' },
  { value: 'shimmer', label: 'Shimmer (Soft)' }
];

const PERSONALITIES = [
  { value: 'friendly', label: 'Friendly' },
  { value: 'professional', label: 'Professional' },
  { value: 'casual', label: 'Casual' },
  { value: 'enthusiastic', label: 'Enthusiastic' }
];

export default function AgentConfig() {
  const { toast } = useToast();
  const [selectedAgentType, setSelectedAgentType] = useState('youtube-assistant');
  const [selectedVoice, setSelectedVoice] = useState('alloy');
  const [selectedPersonality, setSelectedPersonality] = useState('friendly');

  const { data: activeAgent } = useQuery({
    queryKey: ["/api/agent-configs/active"],
  });

  const updateAgentMutation = useMutation({
    mutationFn: async (data: any) => {
      if (activeAgent) {
        return apiRequest('PUT', `/api/agent-configs/${activeAgent.id}`, data);
      } else {
        return apiRequest('POST', '/api/agent-configs/from-template', {
          type: selectedAgentType,
          customizations: data
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/agent-configs"] });
      queryClient.invalidateQueries({ queryKey: ["/api/agent-configs/active"] });
      toast({
        title: "Success",
        description: "Agent configuration saved successfully",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to save agent configuration",
        variant: "destructive",
      });
    }
  });

  const handleSaveConfig = () => {
    updateAgentMutation.mutate({
      type: selectedAgentType,
      voiceModel: selectedVoice,
      personality: selectedPersonality,
      isActive: true
    });
  };

  return (
    <Card className="glass-card rounded-2xl premium-shadow">
      <CardHeader>
        <CardTitle className="flex items-center text-xl font-semibold">
          <Settings className="text-electric-blue mr-3" />
          Agent Configuration
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Agent Type Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Agent Type</label>
          <Select value={selectedAgentType} onValueChange={setSelectedAgentType}>
            <SelectTrigger className="glass-card border border-white/20 text-white bg-transparent">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="glass-card border border-white/20 bg-slate-800">
              {AGENT_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value} className="text-white">
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Voice Settings */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Voice Model</label>
          <Select value={selectedVoice} onValueChange={setSelectedVoice}>
            <SelectTrigger className="glass-card border border-white/20 text-white bg-transparent">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="glass-card border border-white/20 bg-slate-800">
              {VOICE_MODELS.map((voice) => (
                <SelectItem key={voice.value} value={voice.value} className="text-white">
                  {voice.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Personality Traits */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">Personality</label>
          <div className="grid grid-cols-2 gap-2">
            {PERSONALITIES.map((personality) => (
              <Button
                key={personality.value}
                onClick={() => setSelectedPersonality(personality.value)}
                variant="ghost"
                className={`glass-card transition-all duration-300 px-3 py-2 rounded-lg text-sm ${
                  selectedPersonality === personality.value
                    ? 'border border-electric-blue bg-electric-blue/30'
                    : 'hover:bg-white/20'
                }`}
              >
                {personality.label}
              </Button>
            ))}
          </div>
        </div>

        <Button
          onClick={handleSaveConfig}
          disabled={updateAgentMutation.isPending}
          className="w-full bg-gradient-to-r from-electric-blue to-cyber-cyan hover:from-electric-blue/80 hover:to-cyber-cyan/80 transition-all duration-300 py-3 rounded-lg font-semibold"
        >
          <Save className="mr-2 h-4 w-4" />
          {updateAgentMutation.isPending ? 'Saving...' : 'Save Configuration'}
        </Button>
      </CardContent>
    </Card>
  );
}
