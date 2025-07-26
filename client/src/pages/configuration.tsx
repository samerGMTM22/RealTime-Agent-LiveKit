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
  { value: 'voice-assistant', label: 'Voice Assistant', description: 'General purpose voice assistant for various tasks and inquiries' },
  { value: 'customer-service', label: 'Customer Service Agent', description: 'Handle customer inquiries, support tickets, and general assistance' },
  { value: 'real-estate', label: 'Real Estate Agent', description: 'Property information, market insights, and client guidance' },
  { value: 'fitness-coach', label: 'Fitness & Wellness Coach', description: 'Health advice, workout plans, and wellness guidance' },
  { value: 'sales-assistant', label: 'Sales Assistant', description: 'Lead qualification, product information, and sales support' },
  { value: 'educational-tutor', label: 'Educational Tutor', description: 'Learning support, explanations, and educational guidance' },
  { value: 'technical-support', label: 'Technical Support', description: 'IT help, troubleshooting, and technical guidance' },
  { value: 'custom', label: 'Custom Assistant', description: 'Create your own custom voice assistant configuration' }
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

interface WebhookConfig {
  id: string;
  type: 'webhook' | 'n8n' | 'zapier';
  name: string;
  url?: string;
  config: Record<string, any>;
  status: 'connected' | 'disconnected' | 'error' | 'testing';
  metadata?: {
    responseTime?: number;
    lastTestResult?: any;
    lastTestTime?: string;
    [key: string]: any;
  };
}

export default function Configuration() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("agent");
  const [webhookConfigs, setWebhookConfigs] = useState<WebhookConfig[]>([]);
  const [newWebhookConfig, setNewWebhookConfig] = useState({ name: '', url: '' });
  
  // Agent configuration state
  const [agentName, setAgentName] = useState("");
  const [agentCategory, setAgentCategory] = useState("voice-assistant");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [voiceModel, setVoiceModel] = useState("coral");
  const [responseLength, setResponseLength] = useState("moderate");
  const [temperature, setTemperature] = useState([70]);
  
  // Service connections state  
  const [services, setServices] = useState<{
    basic: {
      livekit: { enabled: boolean; status: 'connected' | 'error' };
      openai: { enabled: boolean; status: 'connected' | 'error' };
    };
    extras: {
      'external-tools': { enabled: boolean; status: 'disconnected' | 'connected' | 'error' };
    };
  }>({
    basic: {
      livekit: { enabled: true, status: 'connected' },
      openai: { enabled: true, status: 'connected' }
    },
    extras: {
      'external-tools': { enabled: false, status: 'disconnected' }
    }
  });

  const { data: activeAgent } = useQuery({
    queryKey: ["/api/agent-configs/active"],
  });

  const { data: systemStatus } = useQuery({
    queryKey: ["/api/status"],
    refetchInterval: 10000
  });

  // No longer needed - webhook configuration is environment-based

  // Initialize form with active agent data
  useEffect(() => {
    if (activeAgent && typeof activeAgent === 'object') {
      const agent = activeAgent as any;
      setAgentName(agent.name || "Voice Assistant");
      setAgentCategory(agent.type || "voice-assistant");
      setSystemPrompt(agent.systemPrompt || getDefaultPrompt("voice-assistant"));
      setVoiceModel(agent.voiceModel || "coral");
      setResponseLength(agent.responseLength || "moderate");
      setTemperature([agent.temperature || 70]);
      
      // Load service settings from agent configuration
      if (agent.settings && agent.settings.services) {
        setServices(prev => ({
          ...prev,
          extras: {
            ...prev.extras,
            ...agent.settings.services.extras
          }
        }));
      }
    }
  }, [activeAgent]);

  // Initialize MCP servers from API and always sync with database
  useEffect(() => {
    if (existingMcpServers && Array.isArray(existingMcpServers)) {
      const servers = existingMcpServers.map((server: any) => ({
        id: server.id.toString(), // Ensure ID is string for frontend
        name: server.name,
        url: server.url,
        status: server.connectionStatus || 'disconnected',
        metadata: server.metadata || {},
        type: 'mcp' as const,
        config: {}
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
          mcp: { enabled: prev.extras.mcp.enabled, status: status.mcp === 'connected' ? 'connected' as const : 'error' as const }
        }
      }));
    }
  }, [systemStatus]);

  function getDefaultPrompt(category: string): string {
    const prompts: Record<string, string> = {
      'voice-assistant': `You are a helpful voice AI assistant. 
You assist users with general questions and tasks, provide helpful information, and engage in natural conversations.
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
      console.log('Adding MCP server:', serverData);
      const response = await apiRequest('POST', '/api/mcp/servers', serverData);
      console.log('Server added successfully:', response);
      return response;
    },
    onSuccess: async (newServer) => {
      console.log('MCP server saved, refreshing list...');
      // Immediately refetch to sync with database
      await refetchMcpServers();
      queryClient.invalidateQueries({ queryKey: ["/api/mcp/servers"] });
      setNewMcpServer({ name: '', url: '' });
      toast({
        title: "MCP Server Added",
        description: "Server has been added and saved to database",
      });
    },
    onError: (error) => {
      console.error('Failed to add MCP server:', error);
      toast({
        title: "Error",
        description: "Failed to add MCP server. Please try again.",
        variant: "destructive",
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
        server.id === serverId ? { 
          ...server, 
          status: 'connected' as const,
          metadata: { ...server.metadata, ...data.metadata }
        } : server
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
            MCP Servers
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
              <CardTitle>External Tool Configuration</CardTitle>
              <CardDescription>Configure webhook endpoints for external tool integration (N8N, Zapier, etc.)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <Input
                  placeholder="MCP Server Name (e.g., internet access)"
                  value={newMcpServer.name}
                  onChange={(e) => setNewMcpServer(prev => ({ ...prev, name: e.target.value }))}
                  className="glass-card border-white/20 w-full"
                />
                <div className="flex gap-3">
                  <Input
                    placeholder="MCP Server URL (https://... or wss://...)"
                    value={newMcpServer.url}
                    onChange={(e) => setNewMcpServer(prev => ({ ...prev, url: e.target.value }))}
                    className="glass-card border-white/20 flex-1"
                  />
                  <button 
                    onClick={() => {
                      console.log('Add button clicked! Current values:', newMcpServer);
                      if (!newMcpServer.name.trim() || !newMcpServer.url.trim()) {
                        console.log('Validation failed - missing name or URL');
                        toast({
                          title: "Missing Information",
                          description: "Please provide both name and URL for the MCP server",
                          variant: "destructive",
                        });
                        return;
                      }
                      console.log('Validation passed, calling mutation...');
                      addMcpServerMutation.mutate(newMcpServer);
                    }}
                    disabled={addMcpServerMutation.isPending}
                    style={{
                      backgroundColor: '#0ea5e9',
                      color: 'white',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      cursor: 'pointer',
                      fontWeight: '500',
                      minWidth: '80px'
                    }}
                  >
                    {addMcpServerMutation.isPending ? "Adding..." : "Add"}
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Connected MCP Servers</CardTitle>
              <CardDescription>Manage your agent's external tool connections and capabilities</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* MCP Protocol Status */}
                <div className="flex items-center justify-between p-4 border border-white/20 rounded-lg bg-gradient-to-r from-blue-500/10 to-purple-500/10">
                  <div className="flex items-center space-x-4">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                      <MessageSquare className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <h3 className="font-medium">MCP Protocol</h3>
                      <p className="text-sm text-gray-400">Model Context Protocol framework for external integrations</p>
                      <p className="text-xs text-gray-500 mt-1">Enables secure connections to external APIs, databases, and services</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                      Active
                    </Badge>
                    {getStatusIcon('ready')}
                  </div>
                </div>

                {mcpServers.map((server) => (
                  <div key={server.id} className="p-4 border border-white/20 rounded-lg bg-gradient-to-r from-electric-blue/5 to-cyber-cyan/5">
                    <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                      <div className="flex items-start space-x-4 flex-1 min-w-0">
                        <div className="p-2 bg-electric-blue/20 rounded-lg flex-shrink-0">
                          <Database className="h-5 w-5 text-electric-blue" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <h3 className="font-medium truncate">{server.name}</h3>
                            <Badge variant="outline" className="border-electric-blue/50 text-electric-blue text-xs flex-shrink-0">
                              MCP
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-400 mb-2 break-all">{server.url}</p>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                            <span className="whitespace-nowrap">Protocol: Model Context Protocol</span>
                            <span className="hidden sm:inline">•</span>
                            <span className="whitespace-nowrap">Type: External Service</span>
                            {server.status === 'connected' && (
                              <>
                                <span className="hidden sm:inline">•</span>
                                <span className="text-green-400 whitespace-nowrap">Live Connection</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        {server.status === 'testing' ? (
                          <div className="flex items-center space-x-1">
                            <div className="animate-spin h-4 w-4 border-2 border-electric-blue border-t-transparent rounded-full"></div>
                            <span className="text-sm text-gray-400">Testing...</span>
                          </div>
                        ) : (
                          <div className="flex items-center space-x-1">
                            {getStatusIcon(server.status)}
                            {server.metadata?.responseTime && (
                              <span className="text-xs text-gray-400">
                                ({server.metadata.responseTime}ms)
                              </span>
                            )}
                          </div>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => testMcpConnectionMutation.mutate(server.id)}
                          disabled={testMcpConnectionMutation.isPending}
                          className="text-blue-400 hover:text-blue-300"
                          title="Test Connection"
                        >
                          <TestTube className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeMcpServerMutation.mutate(server.id)}
                          disabled={removeMcpServerMutation.isPending}
                          className="text-red-400 hover:text-red-300"
                          title="Remove Server"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
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
                        <h3 className="font-medium">{service === 'mcp' ? 'MCP' : service.charAt(0).toUpperCase() + service.slice(1)}</h3>
                        <p className="text-sm text-gray-400">
                          Model Context Protocol servers for external tool integration
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