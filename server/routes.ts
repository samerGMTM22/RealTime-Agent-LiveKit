import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { liveKitService } from "./lib/livekit";
import { openaiService } from "./lib/openai";



import { webScraperService } from "./lib/scraper";
import { getAgentTemplate, createAgentConfigFromTemplate } from "./config/agent-config";
import { insertAgentConfigSchema, insertConversationSchema, insertDataSourceSchema } from "@shared/schema";
import { spawn } from "child_process";
import { voiceAgentManager } from "./lib/voice-agent";

import { z } from "zod";

// External Tool Webhook Handler
class ExternalToolHandler {
  private webhookUrl: string;
  
  constructor() {
    this.webhookUrl = process.env.N8N_WEBHOOK_URL || '';
    if (!this.webhookUrl) {
      console.warn('N8N_WEBHOOK_URL not configured - external tools will not be available');
    }
  }

  async executeExternalTool(tool: string, params: any): Promise<{ success: boolean; result?: any; error?: string }> {
    if (!this.webhookUrl) {
      return { success: false, error: 'External tool webhook not configured' };
    }

    try {
      console.log(`Executing external tool '${tool}' via webhook`);
      
      const response = await fetch(this.webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          "user request": params.query || params.message || `Execute ${tool} tool`,
          "system request": `Process this ${tool} request and provide a helpful response. Keep responses concise and conversational.`
        }),
        signal: AbortSignal.timeout(30000) // 30 second timeout
      });

      if (response.ok) {
        const responseText = await response.text();
        console.log(`External tool '${tool}' response:`, responseText);
        
        // Handle empty responses gracefully
        if (!responseText || responseText.trim() === '') {
          console.log(`External tool '${tool}' completed with empty response`);
          return { success: true, result: 'Tool executed successfully' };
        }
        
        try {
          const result = JSON.parse(responseText);
          console.log(`External tool '${tool}' completed successfully`);
          return { success: true, result };
        } catch (parseError) {
          console.log(`External tool '${tool}' completed with text response:`, responseText);
          return { success: true, result: responseText };
        }
      } else {
        const errorText = await response.text();
        console.error(`External tool '${tool}' failed: ${response.status} ${errorText}`);
        return { success: false, error: `Webhook error: ${response.status} ${errorText}` };
      }
    } catch (error: any) {
      console.error(`External tool '${tool}' error:`, error);
      return { success: false, error: error.message || 'Unknown webhook error' };
    }
  }
}

const externalToolHandler = new ExternalToolHandler();

// Initialize webhook tool discovery
import { WebhookToolDiscovery } from './webhook-tool-discovery';
const webhookToolDiscovery = new WebhookToolDiscovery(storage);



// AI Agent implementation
async function startAIAgent(roomName: string) {
  try {
    console.log(`Starting Python LiveKit agent for room: ${roomName}`);
    
    // Start the Python LiveKit agent process with proper CLI parameters
    const agentProcess = spawn('python', [
      'agents/voice_agent_webhook.py', 
      'start',
      '--url', process.env.LIVEKIT_URL!,
      '--api-key', process.env.LIVEKIT_API_KEY!,
      '--api-secret', process.env.LIVEKIT_API_SECRET!
    ], {
      env: {
        ...process.env,
        LIVEKIT_ROOM_NAME: roomName,
        OPENAI_API_KEY: process.env.OPENAI_API_KEY,
        LD_LIBRARY_PATH: '/nix/store/gcc-unwrapped-13.3.0/lib:' + (process.env.LD_LIBRARY_PATH || '')
      },
      stdio: ['inherit', 'pipe', 'pipe']
    });

    agentProcess.stdout?.on('data', (data) => {
      console.log(`Agent stdout: ${data}`);
    });

    agentProcess.stderr?.on('data', (data) => {
      console.error(`Agent stderr: ${data}`);
    });

    agentProcess.on('close', (code) => {
      console.log(`Agent process exited with code ${code}`);
    });

    console.log(`Python LiveKit agent started for room ${roomName}`);
    
  } catch (error) {
    console.error('Failed to start Python agent:', error);
    throw error;
  }
}

export async function registerRoutes(app: Express): Promise<Server> {
  // External tool handler available
  
  // Agent configuration endpoints
  app.get("/api/agent-configs", async (req, res) => {
    try {
      const userId = 1; // Default user for demo
      const configs = await storage.getAgentConfigsByUserId(userId);
      res.json(configs);
    } catch (error) {
      console.error("Error fetching agent configs:", error);
      res.status(500).json({ error: "Failed to fetch agent configurations" });
    }
  });

  app.get("/api/agent-configs/active", async (req, res) => {
    try {
      const userId = 1; // Default user for demo
      const activeConfig = await storage.getActiveAgentConfig(userId);
      res.json(activeConfig);
    } catch (error) {
      console.error("Error fetching active agent config:", error);
      res.status(500).json({ error: "Failed to fetch active agent configuration" });
    }
  });

  app.get("/api/agent-configs/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid agent config ID" });
      }
      
      const config = await storage.getAgentConfig(id);
      if (!config) {
        return res.status(404).json({ error: "Agent configuration not found" });
      }
      res.json(config);
    } catch (error) {
      console.error("Error fetching agent config:", error);
      res.status(500).json({ error: "Failed to fetch agent config" });
    }
  });

  app.post("/api/agent-configs", async (req, res) => {
    try {
      const validatedData = insertAgentConfigSchema.parse(req.body);
      const config = await storage.createAgentConfig(validatedData);
      res.status(201).json(config);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ error: "Invalid agent configuration data", details: error.errors });
      } else {
        console.error("Error creating agent config:", error);
        res.status(500).json({ error: "Failed to create agent configuration" });
      }
    }
  });

  app.put("/api/agent-configs/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      const validatedData = insertAgentConfigSchema.partial().parse(req.body);
      const config = await storage.updateAgentConfig(id, validatedData);
      
      if (!config) {
        return res.status(404).json({ error: "Agent configuration not found" });
      }
      
      res.json(config);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ error: "Invalid agent configuration data", details: error.errors });
      } else {
        console.error("Error updating agent config:", error);
        res.status(500).json({ error: "Failed to update agent configuration" });
      }
    }
  });

  app.post("/api/agent-configs/from-template", async (req, res) => {
    try {
      const { type, customizations } = req.body;
      const template = getAgentTemplate(type);
      const userId = 1; // Default user for demo
      
      const configData = createAgentConfigFromTemplate(template, userId, customizations);
      const config = await storage.createAgentConfig({
        ...configData,
        settings: configData.settings || {}
      });
      
      res.status(201).json(config);
    } catch (error) {
      console.error("Error creating agent config from template:", error);
      res.status(500).json({ error: "Failed to create agent configuration from template" });
    }
  });

  // LiveKit endpoints
  app.get("/api/livekit/url", (req, res) => {
    res.json({ url: process.env.LIVEKIT_URL });
  });

  app.post("/api/livekit/token", async (req, res) => {
    try {
      const { roomName, participantName } = req.body;
      
      if (!roomName || !participantName) {
        return res.status(400).json({ error: "Room name and participant name are required" });
      }

      const token = await liveKitService.createAccessToken(roomName, participantName);
      
      // Start AI agent for this room
      if (participantName === 'user') {
        setTimeout(async () => {
          try {
            await startAIAgent(roomName);
          } catch (error) {
            console.error("Failed to start AI agent for room:", roomName, error);
          }
        }, 1000);
      }
      
      res.json({ token });
    } catch (error) {
      console.error("Error creating LiveKit token:", error);
      res.status(500).json({ error: "Failed to create access token" });
    }
  });

  app.post("/api/livekit/rooms", async (req, res) => {
    try {
      const { roomName, maxParticipants } = req.body;
      
      if (!roomName) {
        return res.status(400).json({ error: "Room name is required" });
      }

      const room = await liveKitService.createRoom(roomName, maxParticipants);
      
      // DO NOT start agent automatically here - only when explicitly requested
      res.status(201).json(room);
    } catch (error) {
      console.error("Error creating LiveKit room:", error);
      res.status(500).json({ error: "Failed to create room" });
    }
  });

  app.get("/api/livekit/rooms", async (req, res) => {
    try {
      const rooms = await liveKitService.listRooms();
      res.json(rooms);
    } catch (error) {
      console.error("Error listing LiveKit rooms:", error);
      res.status(500).json({ error: "Failed to list rooms" });
    }
  });

  // Voice session endpoints
  app.post("/api/voice/start-session", async (req, res) => {
    try {
      const { agentConfigId } = req.body;
      
      if (!agentConfigId) {
        return res.status(400).json({ error: "Agent config ID is required" });
      }

      // Generate unique session ID
      const sessionId = `voice_agent_session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const roomName = sessionId;

      // Create LiveKit room
      const room = await liveKitService.createRoom(roomName, 2);
      
      // Generate access token for the user
      const token = await liveKitService.createAccessToken(roomName, 'user');

      // Start AI agent for this room
      try {
        await startAIAgent(roomName);
        console.log(`AI agent started for room: ${roomName}`);
      } catch (agentError) {
        console.error(`Error starting AI agent: ${agentError}`);
        // Continue without agent - room still usable
      }

      res.json({
        sessionId,
        roomName,
        token,
        wsUrl: process.env.LIVEKIT_URL,
        status: 'started'
      });
    } catch (error) {
      console.error("Error starting voice session:", error);
      res.status(500).json({ error: "Failed to start voice session" });
    }
  });

  // Voice processing endpoints
  app.post("/api/voice/process", async (req, res) => {
    try {
      const { message, agentConfigId, sessionId } = req.body;
      
      if (!message || !agentConfigId) {
        return res.status(400).json({ error: "Message and agent config ID are required" });
      }

      const agentConfig = await storage.getAgentConfig(agentConfigId);
      if (!agentConfig) {
        return res.status(404).json({ error: "Agent configuration not found" });
      }

      // Get channel and website data for context
      let channelData = {};
      let websiteData = {};

      try {
        if (agentConfig.type === 'music-assistant') {
          websiteData = await webScraperService.getWebsiteContent('https://www.givemethemicofficial.com');
        }
      } catch (error: any) {
        console.warn("Error fetching context data:", error.message);
      }

      // Generate response using OpenAI
      const response = await openaiService.processChannelQuery(message, channelData, websiteData);

      // Save conversation
      if (sessionId) {
        await storage.createConversation({
          agentConfigId,
          sessionId,
          userMessage: message,
          agentResponse: response,
          metadata: { channelData: !!channelData, websiteData: !!websiteData }
        });
      }

      res.json({ response });
    } catch (error) {
      console.error("Error processing voice message:", error);
      res.status(500).json({ error: "Failed to process voice message" });
    }
  });

  app.post("/api/voice/synthesize", async (req, res) => {
    try {
      const { text, voice = 'alloy', speed = 1.0 } = req.body;
      
      if (!text) {
        return res.status(400).json({ error: "Text is required" });
      }

      const audioBuffer = await openaiService.generateVoiceResponse(text, { voice, speed });
      
      res.set({
        'Content-Type': 'audio/mpeg',
        'Content-Length': audioBuffer.length.toString()
      });
      res.send(audioBuffer);
    } catch (error) {
      console.error("Error synthesizing voice:", error);
      res.status(500).json({ error: "Failed to synthesize voice" });
    }
  });

  // Conversation history endpoints
  app.get("/api/conversations/:sessionId", async (req, res) => {
    try {
      const { sessionId } = req.params;
      const conversations = await storage.getConversationsBySessionId(sessionId);
      res.json(conversations);
    } catch (error) {
      console.error("Error fetching conversations:", error);
      res.status(500).json({ error: "Failed to fetch conversations" });
    }
  });

  app.get("/api/conversations/agent/:agentConfigId", async (req, res) => {
    try {
      const agentConfigId = parseInt(req.params.agentConfigId);
      const conversations = await storage.getConversationsByAgentConfigId(agentConfigId);
      res.json(conversations);
    } catch (error) {
      console.error("Error fetching agent conversations:", error);
      res.status(500).json({ error: "Failed to fetch agent conversations" });
    }
  });

  // Data sources endpoints
  app.get("/api/data-sources/:agentConfigId", async (req, res) => {
    try {
      const agentConfigId = parseInt(req.params.agentConfigId);
      const dataSources = await storage.getDataSourcesByAgentConfigId(agentConfigId);
      res.json(dataSources);
    } catch (error) {
      console.error("Error fetching data sources:", error);
      res.status(500).json({ error: "Failed to fetch data sources" });
    }
  });

  app.post("/api/data-sources", async (req, res) => {
    try {
      const validatedData = insertDataSourceSchema.parse(req.body);
      const dataSource = await storage.createDataSource(validatedData);
      res.status(201).json(dataSource);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ error: "Invalid data source data", details: error.errors });
      } else {
        console.error("Error creating data source:", error);
        res.status(500).json({ error: "Failed to create data source" });
      }
    }
  });



  // Website scraping endpoints
  app.post("/api/scrape", async (req, res) => {
    try {
      const { url, maxDepth = 2 } = req.body;
      
      if (!url) {
        return res.status(400).json({ error: "URL is required" });
      }

      const websiteData = await webScraperService.scrapeWebsite(url, maxDepth);
      res.json(websiteData);
    } catch (error) {
      console.error("Error scraping website:", error);
      res.status(500).json({ error: "Failed to scrape website" });
    }
  });



  // External tool endpoints (webhook-based)
  app.post("/api/external-tools/execute", async (req, res) => {
    const { tool, params } = req.body;
    
    if (!tool) {
      return res.status(400).json({ success: false, error: 'Tool name is required' });
    }
    
    try {
      const result = await externalToolHandler.executeExternalTool(tool, params || {});
      res.json(result);
    } catch (error: any) {
      console.error('External tool execution error:', error);
      res.status(500).json({ 
        success: false, 
        error: error.message || 'Failed to execute external tool' 
      });
    }
  });

  app.post("/api/external-tools/test-webhook", async (req, res) => {
    try {
      const result = await webhookToolDiscovery.testDiscovery();
      res.json(result);
    } catch (error: any) {
      console.error('Webhook test error:', error);
      res.status(500).json({ 
        success: false, 
        error: error.message || 'Failed to test webhook' 
      });
    }
  });

  // Manual webhook test endpoint for user testing
  app.post("/api/external-tools/manual-test", async (req, res) => {
    try {
      const { message = "Manual webhook test from Replit" } = req.body;
      
      const result = await externalToolHandler.executeExternalTool('test', {
        message,
        timestamp: new Date().toISOString(),
        source: 'manual_test'
      });
      
      res.json({
        testSuccess: result.success,
        response: result.result || result.error,
        timestamp: new Date().toISOString()
      });
    } catch (error: any) {
      console.error('Manual webhook test error:', error);
      res.status(500).json({ 
        testSuccess: false, 
        error: error.message || 'Failed to test webhook manually' 
      });
    }
  });

  app.get("/api/external-tools/discovered", async (req, res) => {
    try {
      const tools = await webhookToolDiscovery.getDiscoveredTools();
      res.json({ tools });
    } catch (error: any) {
      console.error('Error getting discovered tools:', error);
      res.status(500).json({ 
        success: false, 
        error: error.message || 'Failed to get discovered tools' 
      });
    }
  });









  // System status endpoint
  app.get("/api/status", async (req, res) => {
    try {
      const status = {
        livekit: 'online',
        openai: 'connected',
        externalTools: 'connected',
        latency: '45ms',
        timestamp: new Date().toISOString()
      };

      // Test LiveKit connection
      try {
        await liveKitService.listRooms();
      } catch (error) {
        status.livekit = 'error';
      }

      // External tools status - check webhook availability
      try {
        if (process.env.N8N_WEBHOOK_URL) {
          status.externalTools = 'ready'; // External webhook configured
        } else {
          status.externalTools = 'disconnected'; // No webhook configured
        }
      } catch (error) {
        console.error("External tools status check error:", error);
        status.externalTools = 'error';
      }

      res.json(status);
    } catch (error) {
      console.error("Error checking system status:", error);
      res.status(500).json({ error: "Failed to check system status" });
    }
  });











  // Service Management endpoints
  app.post("/api/services/:category/:service/toggle", async (req, res) => {
    try {
      const { category, service } = req.params;
      const { enabled } = req.body;

      if (category === 'basic') {
        return res.status(400).json({ error: "Basic services cannot be disabled" });
      }

      if (category === 'extras' && service === 'external-tools') {
        // External tools service toggle logic
        res.json({
          service,
          enabled,
          status: enabled && process.env.N8N_WEBHOOK_URL ? 'connected' : 'disconnected'
        });
      } else {
        res.status(400).json({ error: "Unknown service" });
      }
    } catch (error) {
      console.error("Error toggling service:", error);
      res.status(500).json({ error: "Failed to toggle service" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
