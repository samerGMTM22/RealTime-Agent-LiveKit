import { useState, useEffect } from "react";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Label } from "@/components/ui/label";
import { Plus, Trash2, Settings, Database, Globe, MessageSquare, CheckCircle, XCircle, AlertTriangle, ArrowLeft, TestTube } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

const AGENT_CATEGORIES = [
  { value: 'youtube-assistant', label: 'YouTube Channel Assistant', description: 'Specialized for YouTube channel management and audience engagement' },
  { value: 'customer-service', label: 'Customer Service Agent', description: 'Handle customer inquiries, support tickets, and general assistance' },
  { value: 'real-estate', label: 'Real Estate Agent', description: 'Property information, market insights, and client guidance' },
  { value: 'fitness-coach', label: 'Fitness & Wellness Coach', description: 'Health advice, workout plans, and wellness guidance' },
  { value: 'sales-assistant', label: 'Sales Assistant', description: 'Lead qualification, product information, and sales support' },
  { value: 'educational-tutor', label: 'Educational Tutor', description: 'Learning support, explanations, and educational guidance' },
  { value: 'technical-support', label: 'Technical Support', description: 'IT help, troubleshooting, and technical guidance' },
  { value: 'general-assistant', label: 'General Assistant', description: 'Versatile AI assistant for various tasks and inquiries' }
];

const VOICE_MODELS = [
  { value: 'alloy', label: 'Alloy (Balanced)' },
  { value: 'echo', label: 'Echo (Authoritative)' },
  { value: 'fable', label: 'Fable (Expressive)' },
  { value: 'onyx', label: 'Onyx (Deep)' },
  { value: 'nova', label: 'Nova (Warm)' },
  { value: 'shimmer', label: 'Shimmer (Bright)' },
  { value: 'coral', label: 'Coral (Friendly)' }
];

const RESPONSE_LENGTHS = [
  { value: 'concise', label: 'Concise', description: 'Brief, direct responses' },
  { value: 'moderate', label: 'Moderate', description: 'Balanced detail level' },
  { value: 'detailed', label: 'Detailed', description: 'Comprehensive responses' }
];

interface DataSource {
  id: string;
  type: 'mcp' | 'youtube' | 'website' | 'database';
  name: string;
  url?: string;
  config: Record<string, any>;
  status: 'connected' | 'disconnected' | 'error';
}

export default function Configuration() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("agent");
  const [mcpServers, setMcpServers] = useState<Array<{
    id: string;
    name: string;
    url: string;
    status: 'connected' | 'disconnected' | 'error' | 'testing';
  }>>([]);
  const [newMcpServer, setNewMcpServer] = useState({ name: '', url: '' });
  
  // Agent configuration state
  const [agentName, setAgentName] = useState("");
  const [agentCategory, setAgentCategory] = useState("youtube-assistant");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [voiceModel, setVoiceModel] = useState("coral");
  const [responseLength, setResponseLength] = useState("moderate");
  const [temperature, setTemperature] = useState([70]);
  
  // Data sources state (deprecated - using mcpServers instead)
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  
  // Service connections state
  const [services, setServices] = useState<{
    basic: {
      livekit: { enabled: boolean; status: 'connected' | 'error' };
      openai: { enabled: boolean; status: 'connected' | 'error' };
    };
    extras: {
      youtube: { enabled: boolean; status: 'connected' | 'error' };
      mcp: { enabled: boolean; status: 'disconnected' | 'connected' | 'error' };
    };
  }>({
    basic: {
      livekit: { enabled: true, status: 'connected' },
      openai: { enabled: true, status: 'connected' }
    },
    extras: {
      youtube: { enabled: true, status: 'connected' },
      mcp: { enabled: false, status: 'disconnected' }
    }
  });

  const { data: activeAgent } = useQuery({
    queryKey: ["/api/agent-configs/active"],
  });

  const { data: systemStatus } = useQuery({
    queryKey: ["/api/status"],
    refetchInterval: 10000
  });

  const { data: existingMcpServers, refetch: refetchMcpServers } = useQuery({
    queryKey: ["/api/mcp/servers"],
    staleTime: 0, // Always fetch fresh data
    refetchOnMount: true,
    refetchOnWindowFocus: true
  });

  // Initialize form with active agent data
  useEffect(() => {
    if (activeAgent && typeof activeAgent === 'object') {
      const agent = activeAgent as any;
      setAgentName(agent.name || "Give Me the Mic Assistant");
      setAgentCategory(agent.type || "youtube-assistant");
      setSystemPrompt(agent.systemPrompt || getDefaultPrompt("youtube-assistant"));
      setVoiceModel(agent.voiceModel || "coral");
      setResponseLength(agent.responseLength || "moderate");
      setTemperature([agent.temperature || 70]);
    }
  }, [activeAgent]);

  // Initialize MCP servers from API and always sync with database
  useEffect(() => {
    if (existingMcpServers && Array.isArray(existingMcpServers)) {
      const servers = existingMcpServers.map((server: any) => ({
        id: server.id.toString(), // Ensure ID is string for frontend
        name: server.name,
        url: server.url,
        status: server.status || 'disconnected'
      }));
      setMcpServers(servers);
    } else {
      setMcpServers([]); // Clear servers if no data
    }
  }, [existingMcpServers]);

  // Refresh MCP servers when page loads or tab changes
  useEffect(() => {
    refetchMcpServers();
  }, []); // Fetch on mount

  useEffect(() => {
    if (activeTab === 'datasources') {
      refetchMcpServers();
    }
  }, [activeTab, refetchMcpServers]);

  // Update services status from system status
  useEffect(() => {
    if (systemStatus && typeof systemStatus === 'object') {
      const status = systemStatus as any;
      setServices(prev => ({
        basic: {
          livekit: { enabled: true, status: status.livekit === 'online' ? 'connected' as const : 'error' as const },
          openai: { enabled: true, status: status.openai === 'connected' ? 'connected' as const : 'error' as const }
        },
        extras: {
          youtube: { enabled: prev.extras.youtube.enabled, status: status.youtube === 'active' ? 'connected' as const : 'error' as const },
          mcp: { enabled: prev.extras.mcp.enabled, status: 'disconnected' as const }
        }
      }));
    }
  }, [systemStatus]);

  function getDefaultPrompt(category: string): string {
    const prompts: Record<string, string> = {
      'youtube-assistant': `You are a helpful voice AI assistant for the "Give Me the Mic" YouTube channel. 
You help users learn about the channel's content, music-related topics, and provide assistance.
The channel has 484 subscribers and 249 videos focusing on music and entertainment.
Keep responses conversational, helpful, and engaging.`,
      'customer-service': `You are a professional customer service agent. Your role is to assist customers with their inquiries, resolve issues, and provide helpful information about products and services. Maintain a friendly, patient, and solution-oriented approach.`,
      'real-estate': `You are a knowledgeable real estate agent assistant. Help clients with property information, market insights, neighborhood details, and guide them through the buying or selling process. Provide accurate, helpful information while being professional and trustworthy.`,
      'fitness-coach': `You are a certified fitness and wellness coach. Provide workout advice, nutrition guidance, and motivation to help users achieve their health goals. Always prioritize safety and encourage consulting healthcare professionals when appropriate.`,
      'sales-assistant': `You are a professional sales assistant. Help qualify leads, provide product information, answer questions, and guide potential customers through the sales process. Be informative, persuasive, and focused on customer needs.`,
      'educational-tutor': `You are an educational tutor and learning assistant. Help students understand concepts, provide explanations, offer study tips, and support their learning journey. Adapt your teaching style to different learning preferences.`,
      'technical-support': `You are a technical support specialist. Help users troubleshoot issues, provide step-by-step solutions, and explain technical concepts in an accessible way. Be patient, thorough, and solution-focused.`,
      'general-assistant': `You are a versatile AI assistant ready to help with a wide variety of tasks and questions. Provide helpful, accurate information while maintaining a friendly and professional demeanor.`
    };
    return prompts[category] || prompts['general-assistant'];
  }

  const updateAgentMutation = useMutation({
    mutationFn: async (data: any) => {
      if (activeAgent && typeof activeAgent === 'object') {
        const agent = activeAgent as any;
        return apiRequest('PUT', `/api/agent-configs/${agent.id}`, data);
      } else {
        return apiRequest('POST', '/api/agent-configs', data);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/agent-configs"] });
      queryClient.invalidateQueries({ queryKey: ["/api/agent-configs/active"] });
      toast({
        title: "Configuration Saved",
        description: "Agent settings have been updated and persisted successfully",
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

  // MCP Server mutations
  const addMcpServerMutation = useMutation({
    mutationFn: async (serverData: { name: string; url: string }) => {
      return apiRequest('POST', '/api/mcp/servers', serverData);
    },
    onSuccess: async (newServer) => {
      // Immediately refetch to sync with database
      await refetchMcpServers();
      queryClient.invalidateQueries({ queryKey: ["/api/mcp/servers"] });
      setNewMcpServer({ name: '', url: '' });
      toast({
        title: "MCP Server Added",
        description: "Server has been added and saved to database",
      });
    }
  });

  const testMcpConnectionMutation = useMutation({
    mutationFn: async (serverId: string) => {
      return apiRequest('POST', `/api/mcp/servers/${serverId}/connect`);
    },
    onMutate: (serverId) => {
      setMcpServers(prev => prev.map(server => 
        server.id === serverId ? { ...server, status: 'testing' as const } : server
      ));
    },
    onSuccess: (data, serverId) => {
      queryClient.invalidateQueries({ queryKey: ["/api/mcp/servers"] });
      setMcpServers(prev => prev.map(server => 
        server.id === serverId ? { ...server, status: 'connected' as const } : server
      ));
    },
    onError: (error, serverId) => {
      setMcpServers(prev => prev.map(server => 
        server.id === serverId ? { ...server, status: 'error' as const } : server
      ));
    }
  });

  const removeMcpServerMutation = useMutation({
    mutationFn: async (serverId: string) => {
      return apiRequest('DELETE', `/api/mcp/servers/${serverId}`);
    },
    onSuccess: async (data, serverId) => {
      // Immediately refetch to sync with database
      await refetchMcpServers();
      queryClient.invalidateQueries({ queryKey: ["/api/mcp/servers"] });
      toast({
        title: "MCP Server Removed",
        description: "Server has been permanently removed from database",
      });
    }
  });

  const handleSaveAgent = async () => {
    try {
      // Save agent configuration
      const config = {
        name: agentName,
        type: agentCategory,
        systemPrompt,
        voiceModel,
        responseLength,
        temperature: temperature[0],
        userId: 1,
        isActive: true,
        settings: {
          services: services,
          advancedSettings: {
            // Add any advanced settings here
          }
        }
      };
      
      // Update agent configuration
      await updateAgentMutation.mutateAsync(config);
      
      // Refresh all data to ensure consistency
      await refetchMcpServers();
      queryClient.invalidateQueries({ queryKey: ["/api/agent-configs"] });
      queryClient.invalidateQueries({ queryKey: ["/api/mcp/servers"] });
      
      toast({
        title: "Configuration Saved",
        description: "All settings have been saved successfully across all tabs",
      });
    } catch (error) {
      toast({
        title: "Save Failed",
        description: "There was an error saving the configuration. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleCategoryChange = (category: string) => {
    setAgentCategory(category);
    setSystemPrompt(getDefaultPrompt(category));
  };



  const toggleService = (category: 'basic' | 'extras', service: string) => {
    if (category === 'basic') {
      toast({
        title: "Basic Service",
        description: "Basic services cannot be disabled",
        variant: "destructive",
      });
      return;
    }

    setServices(prev => {
      const extrasServices = prev.extras as Record<string, any>;
      const currentService = extrasServices[service];
      
      return {
        ...prev,
        extras: {
          ...prev.extras,
          [service]: {
            ...currentService,
            enabled: !currentService.enabled,
            status: !currentService.enabled ? 'connected' as const : 'disconnected' as const
          }
        }
      };
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error': return <XCircle className="h-4 w-4 text-red-500" />;
      default: return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    }
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-4 mb-4">
            <Link href="/">
              <Button variant="outline" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Agent
              </Button>
            </Link>
          </div>
          <h1 className="text-3xl font-bold gradient-text">Agent Configuration</h1>
          <p className="text-gray-400 mt-2">Customize your voice agent settings and integrations</p>
        </div>
        <Button 
          onClick={handleSaveAgent}
          disabled={updateAgentMutation.isPending}
          className="bg-electric-blue hover:bg-electric-blue/80"
        >
          {updateAgentMutation.isPending ? "Saving..." : "Save Configuration"}
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4 glass-card">
          <TabsTrigger value="agent" className="data-[state=active]:bg-electric-blue/30">
            <MessageSquare className="h-4 w-4 mr-2" />
            Agent Settings
          </TabsTrigger>
          <TabsTrigger value="datasources" className="data-[state=active]:bg-electric-blue/30">
            <Database className="h-4 w-4 mr-2" />
            Data Sources
          </TabsTrigger>
          <TabsTrigger value="services" className="data-[state=active]:bg-electric-blue/30">
            <Globe className="h-4 w-4 mr-2" />
            Services
          </TabsTrigger>
          <TabsTrigger value="advanced" className="data-[state=active]:bg-electric-blue/30">
            <Settings className="h-4 w-4 mr-2" />
            Advanced
          </TabsTrigger>
        </TabsList>

        <TabsContent value="agent" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>Basic Information</CardTitle>
                <CardDescription>Configure your agent's identity and behavior</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="agentName">Agent Name</Label>
                  <Input
                    id="agentName"
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    placeholder="Enter agent name"
                    className="glass-card border-white/20"
                  />
                </div>
                
                <div>
                  <Label htmlFor="agentCategory">Use Case Category</Label>
                  <Select value={agentCategory} onValueChange={handleCategoryChange}>
                    <SelectTrigger className="glass-card border-white/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="glass-card bg-slate-800">
                      {AGENT_CATEGORIES.map((category) => (
                        <SelectItem key={category.value} value={category.value} className="text-white">
                          <div>
                            <div className="font-medium">{category.label}</div>
                            <div className="text-sm text-gray-400">{category.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="voiceModel">Voice Model</Label>
                  <Select value={voiceModel} onValueChange={setVoiceModel}>
                    <SelectTrigger className="glass-card border-white/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="glass-card bg-slate-800">
                      {VOICE_MODELS.map((voice) => (
                        <SelectItem key={voice.value} value={voice.value} className="text-white">
                          {voice.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="responseLength">Response Length</Label>
                  <Select value={responseLength} onValueChange={setResponseLength}>
                    <SelectTrigger className="glass-card border-white/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="glass-card bg-slate-800">
                      {RESPONSE_LENGTHS.map((length) => (
                        <SelectItem key={length.value} value={length.value} className="text-white">
                          <div>
                            <div className="font-medium">{length.label}</div>
                            <div className="text-sm text-gray-400">{length.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="temperature">Temperature: {temperature[0]}%</Label>
                  <Slider
                    id="temperature"
                    min={0}
                    max={100}
                    step={5}
                    value={temperature}
                    onValueChange={setTemperature}
                    className="mt-2"
                  />
                  <div className="text-sm text-gray-400 mt-1">
                    Lower values = more focused, Higher values = more creative
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card">
              <CardHeader>
                <CardTitle>System Prompt</CardTitle>
                <CardDescription>Define your agent's personality and instructions</CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="Enter system prompt..."
                  className="glass-card border-white/20 min-h-[300px] resize-none"
                />
                <div className="text-sm text-gray-400 mt-2">
                  This prompt defines how your agent behaves and responds to users.
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="datasources" className="space-y-6">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Add MCP Data Source</CardTitle>
              <CardDescription>Connect Model Context Protocol servers for extended capabilities</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div className="flex gap-3">
                  <Input
                    placeholder="MCP Server Name (e.g., internet access)"
                    value={newMcpServer.name}
                    onChange={(e) => setNewMcpServer(prev => ({ ...prev, name: e.target.value }))}
                    className="glass-card border-white/20 flex-1"
                  />
                  <Input
                    placeholder="MCP Server URL (wss://...)"
                    value={newMcpServer.url}
                    onChange={(e) => setNewMcpServer(prev => ({ ...prev, url: e.target.value }))}
                    className="glass-card border-white/20 flex-1"
                  />
                  <Button 
                    onClick={() => {
                      if (!newMcpServer.name.trim() || !newMcpServer.url.trim()) {
                        toast({
                          title: "Missing Information",
                          description: "Please provide both name and URL for the MCP server",
                          variant: "destructive",
                        });
                        return;
                      }
                      addMcpServerMutation.mutate(newMcpServer);
                    }}
                    disabled={addMcpServerMutation.isPending}
                    className="bg-electric-blue hover:bg-electric-blue/80 px-8 whitespace-nowrap"
                  >
                    {addMcpServerMutation.isPending ? "Adding..." : "Add"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Connected Data Sources</CardTitle>
              <CardDescription>Manage your agent's data connections</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Default YouTube data source */}
                <div className="flex items-center justify-between p-4 border border-white/20 rounded-lg">
                  <div className="flex items-center space-x-4">
                    <div className="p-2 bg-red-500/20 rounded-lg">
                      <MessageSquare className="h-5 w-5 text-red-400" />
                    </div>
                    <div>
                      <h3 className="font-medium">YouTube Channel Data</h3>
                      <p className="text-sm text-gray-400">Give Me the Mic channel information</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant="secondary" className="bg-green-500/20 text-green-400">
                      Built-in
                    </Badge>
                    {getStatusIcon('connected')}
                  </div>
                </div>

                {mcpServers.map((server) => (
                  <div key={server.id} className="flex items-center justify-between p-4 border border-white/20 rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div className="p-2 bg-electric-blue/20 rounded-lg">
                        <Database className="h-5 w-5 text-electric-blue" />
                      </div>
                      <div>
                        <h3 className="font-medium">{server.name}</h3>
                        <p className="text-sm text-gray-400">{server.url}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className="border-electric-blue/50 text-electric-blue">
                        MCP
                      </Badge>
                      {server.status === 'testing' ? (
                        <div className="flex items-center space-x-1">
                          <div className="animate-spin h-4 w-4 border-2 border-electric-blue border-t-transparent rounded-full"></div>
                          <span className="text-sm text-gray-400">Testing...</span>
                        </div>
                      ) : (
                        getStatusIcon(server.status)
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => testMcpConnectionMutation.mutate(server.id)}
                        disabled={testMcpConnectionMutation.isPending}
                        className="text-blue-400 hover:text-blue-300"
                      >
                        <TestTube className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeMcpServerMutation.mutate(server.id)}
                        disabled={removeMcpServerMutation.isPending}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}

                {mcpServers.length === 0 && (
                  <div className="text-center py-8 text-gray-400">
                    No MCP servers configured. Add MCP servers above to extend your agent's capabilities.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="services" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>Basic Services</CardTitle>
                <CardDescription>Core services required for agent operation</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {Object.entries(services.basic).map(([service, config]) => (
                  <div key={service} className="flex items-center justify-between p-4 border border-white/20 rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div>
                        <h3 className="font-medium capitalize">{service}</h3>
                        <p className="text-sm text-gray-400">
                          {service === 'livekit' ? 'Real-time voice communication' : 'AI language processing'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                        Required
                      </Badge>
                      {getStatusIcon(config.status)}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="glass-card">
              <CardHeader>
                <CardTitle>Extra Services</CardTitle>
                <CardDescription>Optional services that can be enabled or disabled</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {Object.entries(services.extras).map(([service, config]) => (
                  <div key={service} className="flex items-center justify-between p-4 border border-white/20 rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div>
                        <h3 className="font-medium capitalize">{service}</h3>
                        <p className="text-sm text-gray-400">
                          {service === 'youtube' ? 'YouTube channel integration' : 'Model Context Protocol servers'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Switch
                        checked={config.enabled}
                        onCheckedChange={() => toggleService('extras', service)}
                      />
                      {config.enabled && getStatusIcon(config.status)}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-6">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Advanced Settings</CardTitle>
              <CardDescription>Fine-tune your agent's performance and behavior</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label>Audio Quality</Label>
                  <Select defaultValue="high">
                    <SelectTrigger className="glass-card border-white/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="glass-card bg-slate-800">
                      <SelectItem value="standard">Standard</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="ultra">Ultra</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Buffer Size</Label>
                  <Select defaultValue="2048">
                    <SelectTrigger className="glass-card border-white/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="glass-card bg-slate-800">
                      <SelectItem value="1024">1024</SelectItem>
                      <SelectItem value="2048">2048</SelectItem>
                      <SelectItem value="4096">4096</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Enable Logging</Label>
                    <p className="text-sm text-gray-400">Log conversations for debugging</p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Auto Reconnect</Label>
                    <p className="text-sm text-gray-400">Automatically reconnect on disconnection</p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}