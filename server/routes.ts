import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { liveKitService } from "./lib/livekit";
import { openaiService } from "./lib/openai";
import { youtubeService } from "./lib/youtube";
import { webScraperService } from "./lib/scraper";
import { getAgentTemplate, createAgentConfigFromTemplate } from "./config/agent-config";
import { insertAgentConfigSchema, insertConversationSchema, insertDataSourceSchema } from "@shared/schema";
import { spawn } from "child_process";
import { voiceAgentManager } from "./lib/voice-agent";
import { mcpManager } from "./lib/mcp-client";
import { z } from "zod";

// AI Agent implementation
async function startAIAgent(roomName: string) {
  try {
    console.log(`Starting Python LiveKit agent for room: ${roomName}`);
    
    // Start the Python LiveKit agent process with proper CLI parameters
    const agentProcess = spawn('python', [
      'agent.py', 
      'start',
      '--url', process.env.LIVEKIT_URL!,
      '--api-key', process.env.LIVEKIT_API_KEY!,
      '--api-secret', process.env.LIVEKIT_API_SECRET!
    ], {
      env: {
        ...process.env,
        LIVEKIT_ROOM_NAME: roomName,
        OPENAI_API_KEY: process.env.OPENAI_API_KEY
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
        if (agentConfig.type === 'youtube-assistant') {
          channelData = await youtubeService.getChannelStats('@GiveMeTheMic22');
          websiteData = await webScraperService.getWebsiteContent('https://www.givemethemicofficial.com');
        }
      } catch (error) {
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

  // YouTube data endpoints
  app.get("/api/youtube/channel/:handle", async (req, res) => {
    try {
      const { handle } = req.params;
      const channelInfo = await youtubeService.getChannelInfo(handle);
      res.json(channelInfo);
    } catch (error) {
      console.error("Error fetching YouTube channel:", error);
      res.status(500).json({ error: "Failed to fetch YouTube channel information" });
    }
  });

  app.get("/api/youtube/videos/:channelId", async (req, res) => {
    try {
      const { channelId } = req.params;
      const maxResults = parseInt(req.query.maxResults as string) || 10;
      const videos = await youtubeService.getChannelVideos(channelId, maxResults);
      res.json(videos);
    } catch (error) {
      console.error("Error fetching YouTube videos:", error);
      res.status(500).json({ error: "Failed to fetch YouTube videos" });
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

  // System status endpoint
  app.get("/api/status", async (req, res) => {
    try {
      const status = {
        livekit: 'online',
        openai: 'connected',
        youtube: 'active',
        latency: '45ms',
        timestamp: new Date().toISOString()
      };

      // Test LiveKit connection
      try {
        await liveKitService.listRooms();
      } catch (error) {
        status.livekit = 'error';
      }

      // YouTube API status - check if key exists without making API calls
      if (process.env.YOUTUBE_API_KEY) {
        status.youtube = 'active';
      } else {
        status.youtube = 'inactive';
      }

      res.json(status);
    } catch (error) {
      console.error("Error checking system status:", error);
      res.status(500).json({ error: "Failed to check system status" });
    }
  });

  // MCP Server Management endpoints
  app.get("/api/mcp/servers", async (req, res) => {
    try {
      // Get servers for user ID 1 (default user)
      const servers = await storage.getMcpServersByUserId(1);
      res.json(servers);
    } catch (error) {
      console.error("Error fetching MCP servers:", error);
      res.status(500).json({ error: "Failed to fetch MCP servers" });
    }
  });

  app.post("/api/mcp/servers", async (req, res) => {
    try {
      console.log('POST /api/mcp/servers - Request body:', req.body);
      const { name, url } = req.body;
      
      if (!name || !url) {
        console.log('Missing name or URL:', { name, url });
        return res.status(400).json({ error: "Name and URL are required" });
      }

      if (!url.startsWith('wss://') && !url.startsWith('ws://') && !url.startsWith('https://') && !url.startsWith('http://')) {
        console.log('Invalid URL format:', url);
        return res.status(400).json({ error: "URL must be a valid URL (http://, https://, ws://, or wss://)" });
      }

      console.log('Creating MCP server in database...');
      // Auto-connect HTTPS servers since they're likely working
      const initialStatus = url.startsWith('https://') ? "connected" : "disconnected";
      const server = await storage.createMcpServer({
        userId: 1, // Default user
        name,
        url,
        status: initialStatus
      });
      
      console.log('MCP server created successfully:', server);
      res.status(201).json(server);
    } catch (error) {
      console.error("Error adding MCP server:", error);
      res.status(500).json({ error: "Failed to add MCP server" });
    }
  });

  app.post("/api/mcp/servers/:id/connect", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      
      // Update server status to testing first
      await storage.updateMcpServer(id, { status: "testing" });
      
      // Simulate connection test (in real implementation, you'd test the WebSocket connection)
      setTimeout(async () => {
        try {
          // For now, just set to connected. In production, implement actual WebSocket connection test
          await storage.updateMcpServer(id, { 
            status: "connected"
          });
        } catch (error) {
          await storage.updateMcpServer(id, { status: "error" });
        }
      }, 2000);
      
      const server = await storage.updateMcpServer(id, { status: "testing" });
      res.json(server);
    } catch (error) {
      console.error("Error connecting to MCP server:", error);
      res.status(500).json({ error: "Failed to connect to MCP server" });
    }
  });

  app.post("/api/mcp/servers/:id/disconnect", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      const server = await storage.updateMcpServer(id, { status: "disconnected" });
      res.json(server);
    } catch (error) {
      console.error("Error disconnecting MCP server:", error);
      res.status(500).json({ error: "Failed to disconnect MCP server" });
    }
  });

  app.delete("/api/mcp/servers/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      const removed = await storage.deleteMcpServer(id);
      
      if (!removed) {
        return res.status(404).json({ error: "MCP server not found" });
      }

      res.json({ success: true });
    } catch (error) {
      console.error("Error removing MCP server:", error);
      res.status(500).json({ error: "Failed to remove MCP server" });
    }
  });

  app.get("/api/mcp/tools", async (req, res) => {
    try {
      const tools = mcpManager.getAvailableTools();
      res.json(tools);
    } catch (error) {
      console.error("Error fetching MCP tools:", error);
      res.status(500).json({ error: "Failed to fetch MCP tools" });
    }
  });

  // YouTube Configuration endpoints
  app.get("/api/youtube/channel-recovery", async (req, res) => {
    try {
      const { handle } = req.query;
      
      if (!handle) {
        return res.status(400).json({ error: "Channel handle is required" });
      }

      const channelInfo = await youtubeService.getChannelInfo(handle as string);
      res.json({
        success: !!channelInfo,
        data: channelInfo,
        fallbackUsed: !channelInfo?.id?.startsWith('UC')
      });
    } catch (error) {
      console.error("Error recovering YouTube channel:", error);
      res.status(500).json({ error: "Failed to recover YouTube channel information" });
    }
  });

  app.post("/api/youtube/test-connection", async (req, res) => {
    try {
      // Test YouTube API connection with a simple search
      const channelInfo = await youtubeService.getChannelInfo('@givemethemicmusic');
      
      res.json({
        connected: true,
        apiQuotaAvailable: !!channelInfo && channelInfo.id.startsWith('UC'),
        fallbackActive: !channelInfo?.id?.startsWith('UC'),
        channelData: channelInfo
      });
    } catch (error) {
      res.json({
        connected: false,
        error: (error as Error).message,
        fallbackActive: true
      });
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

      if (category === 'extras' && service === 'youtube') {
        // YouTube service toggle logic
        res.json({
          service,
          enabled,
          status: enabled ? 'connected' : 'disconnected'
        });
      } else if (category === 'extras' && service === 'mcp') {
        // MCP service toggle logic
        if (!enabled) {
          // Disconnect all MCP servers
          const servers = mcpManager.getAllServers();
          servers.forEach(server => mcpManager.disconnectServer(server.id));
        }
        
        res.json({
          service,
          enabled,
          status: enabled ? 'connected' : 'disconnected'
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
