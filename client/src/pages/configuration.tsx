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
import { Plus, Trash2, Settings, Database, Globe, MessageSquare, CheckCircle, XCircle, AlertTriangle, ArrowLeft, TestTube, Zap, Search } from "lucide-react";
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

const LANGUAGES = [
  { value: 'en', label: 'English', description: 'Default language for responses' },
  { value: 'es', label: 'Spanish', description: 'Respuestas en español' },
  { value: 'fr', label: 'French', description: 'Réponses en français' },
  { value: 'de', label: 'German', description: 'Antworten auf Deutsch' },
  { value: 'it', label: 'Italian', description: 'Risposte in italiano' },
  { value: 'pt', label: 'Portuguese', description: 'Respostas em português' },
  { value: 'ja', label: 'Japanese', description: '日本語での回答' },
  { value: 'ko', label: 'Korean', description: '한국어로 응답' },
  { value: 'zh', label: 'Chinese', description: '中文回复' }
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
  const [webhookConfigs, setWebhookConfigs] = useState<WebhookConfig[]>([
    {
      id: '1',
      name: 'N8N Webhook',
      url: 'Configured via environment',
      type: 'n8n',
      status: 'connected',
      config: {},
      metadata: { responseTime: 120 }
    }
  ]);
  const [newWebhookConfig, setNewWebhookConfig] = useState({ name: '', url: '' });
  
  // Agent configuration state
  const [agentName, setAgentName] = useState("");
  const [agentCategory, setAgentCategory] = useState("voice-assistant");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [voiceModel, setVoiceModel] = useState("coral");
  const [responseLength, setResponseLength] = useState("moderate");
  const [temperature, setTemperature] = useState([70]);
  const [language, setLanguage] = useState("en");
  
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
      'external-tools': { enabled: true, status: 'connected' }
    }
  });

  const { data: activeAgent } = useQuery({
    queryKey: ["/api/agent-configs/active"],
  });

  const { data: systemStatus } = useQuery({
    queryKey: ["/api/status"],
    refetchInterval: 10000
  });

  // Query for discovered external tools
  const { data: discoveredTools, refetch: refetchDiscoveredTools } = useQuery({
    queryKey: ["/api/external-tools/discovered"],
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  // Mutation for triggering manual discovery
  const triggerDiscoveryMutation = useMutation({
    mutationFn: () => apiRequest('/api/external-tools/discover', { method: 'POST' }),
    onSuccess: () => {
      refetchDiscoveredTools();
      toast({
        title: "Tool Discovery",
        description: "External tools have been refreshed successfully",
      });
    },
    onError: () => {
      toast({
        title: "Discovery Failed", 
        description: "Failed to refresh external tools",
        variant: "destructive"
      });
    }
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
      setLanguage(agent.language || "en");
      
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

  // Initialize webhook configurations - now environment-based
  useEffect(() => {
    // Check if external tools are configured via environment
    if (systemStatus && typeof systemStatus === 'object') {
      const status = systemStatus as any;
      const hasWebhook = status.externalTools === 'ready'; // N8N webhook configured
      
      if (hasWebhook) {
        setWebhookConfigs([{
          id: 'n8n-webhook',
          type: 'n8n' as const,
          name: 'N8N External Tools',
          url: 'Configured via environment',
          status: 'connected' as const,
          config: {},
          metadata: { source: 'environment' }
        }]);
      } else {
        setWebhookConfigs([]);
      }
    }
  }, [systemStatus]);

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
          'external-tools': { enabled: prev.extras['external-tools'].enabled, status: status.externalTools === 'connected' ? 'connected' as const : 'error' as const }
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

  // External tool configuration mutations (webhook-based system)
  const testWebhookMutation = useMutation({
    mutationFn: async () => {
      return apiRequest('POST', '/api/external-tools/test-webhook');
    },
    onSuccess: (data) => {
      toast({
        title: "Webhook Connected",
        description: `External tools are available: ${data.availableTools?.join(', ') || 'Ready for tool calls'}`,
      });
    },
    onError: (error) => {
      toast({
        title: "Webhook Test Failed",
        description: "Unable to connect to external tool system. Check configuration.",
        variant: "destructive",
      });
    }
  });

  // Helper functions will be defined below

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
        language,
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
      queryClient.invalidateQueries({ queryKey: ["/api/agent-configs"] });
      queryClient.invalidateQueries({ queryKey: ["/api/external-tools"] });
      
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
            External Tools
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
                  <Label htmlFor="language">Language</Label>
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger className="glass-card border-white/20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="glass-card bg-slate-800">
                      {LANGUAGES.map((lang) => (
                        <SelectItem key={lang.value} value={lang.value} className="text-white">
                          <div>
                            <div className="font-medium">{lang.label}</div>
                            <div className="text-sm text-gray-400">{lang.description}</div>
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
              <CardTitle>External Tool Integration</CardTitle>
              <CardDescription>Configure external tools via webhook endpoints for enhanced agent capabilities</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              
              {/* Configuration Instructions */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Setup Instructions</h3>
                
                <div className="grid gap-4">
                  <div className="p-4 border border-blue-500/30 rounded-lg bg-blue-500/10">
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-blue-500/20 rounded-lg flex-shrink-0">
                        <Settings className="h-4 w-4 text-blue-400" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-blue-400 mb-2">1. Environment Configuration</h4>
                        <p className="text-sm text-blue-200/80 mb-3">
                          Configure external tool webhooks using environment variables for security:
                        </p>
                        <div className="space-y-2 text-xs font-mono bg-slate-800/50 p-3 rounded border">
                          <div>N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-id</div>
                          <div>ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/hooks/catch/your-hook</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border border-green-500/30 rounded-lg bg-green-500/10">
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-green-500/20 rounded-lg flex-shrink-0">
                        <Globe className="h-4 w-4 text-green-400" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-green-400 mb-2">2. Supported Platforms</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                            <span>N8N Automation Platform</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                            <span>Zapier Integration Hub</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                            <span>Custom Webhook Endpoints</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                            <span>API Gateway Integration</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border border-purple-500/30 rounded-lg bg-purple-500/10">
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-purple-500/20 rounded-lg flex-shrink-0">
                        <Zap className="h-4 w-4 text-purple-400" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-purple-400 mb-2">3. Tool Discovery</h4>
                        <p className="text-sm text-purple-200/80">
                          The system automatically discovers available tools at the start of each interaction. 
                          Tools are registered dynamically and made available to the voice agent immediately.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                
                {services.extras['external-tools'].status === 'connected' && (
                  <div className="flex gap-3 pt-4">
                    <Button
                      onClick={() => testWebhookMutation.mutate()}
                      disabled={testWebhookMutation.isPending}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {testWebhookMutation.isPending ? "Testing..." : "Test Connection"}
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Tool Status & Discovery</CardTitle>
              <CardDescription>Monitor discovered tools from background webhook queries</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* System Status */}
                <div className="flex items-center justify-between p-4 border border-white/20 rounded-lg bg-gradient-to-r from-blue-500/10 to-purple-500/10">
                  <div className="flex items-center space-x-4">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                      <Globe className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <h3 className="font-medium">Webhook System</h3>
                      <p className="text-sm text-gray-400">Background tool discovery & execution</p>
                      <p className="text-xs text-gray-500 mt-1">Updates automatically at interaction start + background refresh</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Badge variant="secondary" className={services.extras['external-tools'].status === 'connected' ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}>
                      {services.extras['external-tools'].status === 'connected' ? 'Active' : 'Not Configured'}
                    </Badge>
                    {getStatusIcon(services.extras['external-tools'].status === 'connected' ? 'connected' : 'disconnected')}
                  </div>
                </div>

                {/* Discovered Tools */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium text-gray-300">Discovered Tools</h4>
                    <div className="flex items-center space-x-2">
                      {discoveredTools?.lastDiscovery && (
                        <span className="text-xs text-gray-500">
                          Last: {new Date(discoveredTools.lastDiscovery).toLocaleTimeString()}
                        </span>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => triggerDiscoveryMutation.mutate()}
                        disabled={triggerDiscoveryMutation.isPending}
                        className="h-6 px-2 text-xs"
                      >
                        {triggerDiscoveryMutation.isPending ? "Refreshing..." : "Refresh"}
                      </Button>
                    </div>
                  </div>
                  
                  {discoveredTools?.tools && discoveredTools.tools.length > 0 ? (
                    <div className="grid gap-3">
                      {discoveredTools.tools.map((tool: any, index: number) => (
                        <div key={index} className="p-3 border border-green-500/30 rounded-lg bg-green-500/5">
                          <div className="flex items-center space-x-3">
                            <div className="p-1.5 bg-green-500/20 rounded">
                              {tool.category === 'search' ? (
                                <Search className="h-3 w-3 text-green-400" />
                              ) : tool.category === 'automation' ? (
                                <Zap className="h-3 w-3 text-green-400" />
                              ) : (
                                <Settings className="h-3 w-3 text-green-400" />
                              )}
                            </div>
                            <div className="flex-1">
                              <h5 className="text-sm font-medium">{tool.name}</h5>
                              <p className="text-xs text-gray-400">{tool.description}</p>
                            </div>
                            <Badge variant="outline" className="border-green-500/50 text-green-400 text-xs">
                              Available
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-gray-400">
                      <div className="space-y-2">
                        <Settings className="h-8 w-8 mx-auto text-gray-500" />
                        <p className="text-sm">
                          {services.extras['external-tools'].status === 'connected' 
                            ? "No tools discovered yet" 
                            : "External tools not configured"}
                        </p>
                        <p className="text-xs">
                          {services.extras['external-tools'].status === 'connected' 
                            ? "Click Refresh to discover available tools" 
                            : "Configure N8N_WEBHOOK_URL to enable tool discovery"}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
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
                        <h3 className="font-medium">{service === 'external-tools' ? 'External Tools' : service.charAt(0).toUpperCase() + service.slice(1)}</h3>
                        <p className="text-sm text-gray-400">
                          Webhook-based external tool integration (N8N, Zapier, etc.)
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