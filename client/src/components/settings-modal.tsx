import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { X, AlertTriangle } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeAgent?: any;
}

export default function SettingsModal({ isOpen, onClose, activeAgent }: SettingsModalProps) {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("agent");
  
  // Agent settings state
  const [systemPrompt, setSystemPrompt] = useState(
    activeAgent?.systemPrompt || 
    `You are a helpful voice AI assistant for the "Give Me the Mic" YouTube channel. 
You help users learn about the channel's content, music-related topics, and provide assistance.
The channel has 484 subscribers and 249 videos focusing on music and entertainment.
Keep responses conversational, helpful, and engaging.`
  );
  const [responseLength, setResponseLength] = useState(activeAgent?.responseLength || "moderate");
  const [temperature, setTemperature] = useState([activeAgent?.temperature || 70]);
  
  // Advanced settings state
  const [audioQuality, setAudioQuality] = useState("high");
  const [bufferSize, setBufferSize] = useState("2048");
  const [enableLogging, setEnableLogging] = useState(true);
  const [autoReconnect, setAutoReconnect] = useState(true);

  const updateSettingsMutation = useMutation({
    mutationFn: async (settings: any) => {
      if (activeAgent) {
        return apiRequest('PUT', `/api/agent-configs/${activeAgent.id}`, settings);
      }
      throw new Error("No active agent to update");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/agent-configs/active"] });
      toast({
        title: "Success",
        description: "Settings saved successfully",
      });
      onClose();
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to save settings",
        variant: "destructive",
      });
    }
  });

  const handleSaveSettings = () => {
    const settings = {
      systemPrompt,
      responseLength,
      temperature: temperature[0],
      settings: {
        audioQuality,
        bufferSize: parseInt(bufferSize),
        enableLogging,
        autoReconnect
      }
    };
    
    updateSettingsMutation.mutate(settings);
  };

  const handleResetSettings = () => {
    setSystemPrompt(activeAgent?.systemPrompt || "");
    setResponseLength(activeAgent?.responseLength || "moderate");
    setTemperature([activeAgent?.temperature || 70]);
    setAudioQuality("high");
    setBufferSize("2048");
    setEnableLogging(true);
    setAutoReconnect(true);
    
    toast({
      title: "Settings Reset",
      description: "All settings have been reset to defaults",
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="glass-card max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between text-2xl font-bold gradient-text">
            Advanced Settings
            <Button
              onClick={onClose}
              variant="ghost"
              size="icon"
              className="text-gray-400 hover:text-white"
            >
              <X className="h-5 w-5" />
            </Button>
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 glass-card">
            <TabsTrigger value="agent" className="data-[state=active]:bg-electric-blue/30">
              Agent Settings
            </TabsTrigger>
            <TabsTrigger value="api" className="data-[state=active]:bg-electric-blue/30">
              API Configuration
            </TabsTrigger>
            <TabsTrigger value="advanced" className="data-[state=active]:bg-electric-blue/30">
              Advanced
            </TabsTrigger>
          </TabsList>

          <TabsContent value="agent" className="space-y-6 mt-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                System Prompt
              </label>
              <Textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="You are a helpful AI assistant for the GiveMeTheMic YouTube channel..."
                className="glass-card border border-white/20 text-white bg-transparent min-h-32 resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Response Length
                </label>
                <Select value={responseLength} onValueChange={setResponseLength}>
                  <SelectTrigger className="glass-card border border-white/20 text-white bg-slate-800/50">
                    <SelectValue className="text-white" />
                  </SelectTrigger>
                  <SelectContent className="glass-card border border-white/20 bg-slate-800">
                    <SelectItem value="concise" className="text-white hover:bg-slate-700">Concise</SelectItem>
                    <SelectItem value="moderate" className="text-white hover:bg-slate-700">Moderate</SelectItem>
                    <SelectItem value="detailed" className="text-white hover:bg-slate-700">Detailed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Temperature: {temperature[0] / 100}
                </label>
                <Slider
                  value={temperature}
                  onValueChange={setTemperature}
                  max={100}
                  min={0}
                  step={10}
                  className="w-full"
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="api" className="space-y-6 mt-6">
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
              <div className="flex items-center space-x-2 text-yellow-400 mb-2">
                <AlertTriangle className="h-5 w-5" />
                <span className="font-medium">Security Notice</span>
              </div>
              <p className="text-sm text-yellow-300">
                API keys should be stored in environment variables, not in the frontend code.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  OpenAI API Status
                </label>
                <div className="flex items-center space-x-3 glass-card p-3 rounded-lg">
                  <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                  <span className="text-sm">Connected and configured via environment</span>
                  <Badge variant="secondary" className="ml-auto">Active</Badge>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  LiveKit Configuration
                </label>
                <div className="flex items-center space-x-3 glass-card p-3 rounded-lg">
                  <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                  <span className="text-sm">Room configured and active</span>
                  <Badge variant="secondary" className="ml-auto">Connected</Badge>
                </div>
              </div>


            </div>
          </TabsContent>

          <TabsContent value="advanced" className="space-y-6 mt-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Audio Quality
                </label>
                <Select value={audioQuality} onValueChange={setAudioQuality}>
                  <SelectTrigger className="glass-card border border-white/20 text-white bg-slate-800/50">
                    <SelectValue className="text-white" />
                  </SelectTrigger>
                  <SelectContent className="glass-card border border-white/20 bg-slate-800">
                    <SelectItem value="high" className="text-white hover:bg-slate-700">High (48kHz)</SelectItem>
                    <SelectItem value="standard" className="text-white hover:bg-slate-700">Standard (24kHz)</SelectItem>
                    <SelectItem value="low" className="text-white hover:bg-slate-700">Low (16kHz)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Buffer Size
                </label>
                <Select value={bufferSize} onValueChange={setBufferSize}>
                  <SelectTrigger className="glass-card border border-white/20 text-white bg-slate-800/50">
                    <SelectValue className="text-white" />
                  </SelectTrigger>
                  <SelectContent className="glass-card border border-white/20 bg-slate-800">
                    <SelectItem value="1024" className="text-white hover:bg-slate-700">1024 samples</SelectItem>
                    <SelectItem value="2048" className="text-white hover:bg-slate-700">2048 samples</SelectItem>
                    <SelectItem value="4096" className="text-white hover:bg-slate-700">4096 samples</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <Checkbox
                  id="enableLogging"
                  checked={enableLogging}
                  onCheckedChange={setEnableLogging}
                  className="border-gray-600"
                />
                <label htmlFor="enableLogging" className="text-sm">
                  Enable detailed logging
                </label>
              </div>

              <div className="flex items-center space-x-3">
                <Checkbox
                  id="autoReconnect"
                  checked={autoReconnect}
                  onCheckedChange={setAutoReconnect}
                  className="border-gray-600"
                />
                <label htmlFor="autoReconnect" className="text-sm">
                  Auto-reconnect on connection loss
                </label>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex items-center justify-end space-x-4 pt-6 border-t border-white/10">
          <Button
            onClick={handleResetSettings}
            variant="ghost"
            className="text-gray-400 hover:text-white"
          >
            Reset to Defaults
          </Button>
          <Button
            onClick={handleSaveSettings}
            disabled={updateSettingsMutation.isPending}
            className="bg-gradient-to-r from-electric-blue to-cyber-cyan hover:from-electric-blue/80 hover:to-cyber-cyan/80 transition-all duration-300"
          >
            {updateSettingsMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
