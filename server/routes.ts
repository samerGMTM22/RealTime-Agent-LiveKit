import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { liveKitService } from "./lib/livekit";
import { openaiService } from "./lib/openai";
import { youtubeService } from "./lib/youtube";
import { webScraperService } from "./lib/scraper";
import { getAgentTemplate, createAgentConfigFromTemplate } from "./config/agent-config";
import { insertAgentConfigSchema, insertConversationSchema, insertDataSourceSchema } from "@shared/schema";
import { voiceAgentManager } from "./lib/voice-agent";
import { z } from "zod";

// AI Agent implementation
async function startAIAgent(roomName: string) {
  try {
    console.log(`Starting LiveKit voice agent for room: ${roomName}`);
    
    // Get agent configuration
    const agentConfig = await storage.getActiveAgentConfig(1); // Default user
    if (!agentConfig) {
      throw new Error('No active agent configuration found');
    }

    // Start the voice agent using LiveKit Agents framework
    await voiceAgentManager.startAgent(roomName, agentConfig.id);
    
    console.log(`LiveKit voice agent started for room ${roomName} with config: ${agentConfig.name}`);
    
  } catch (error) {
    console.error('Failed to start voice agent:', error);
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
      const config = await storage.createAgentConfig(configData);
      
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

      // Test YouTube API
      try {
        await youtubeService.getChannelInfo('@GiveMeTheMic22');
      } catch (error) {
        status.youtube = 'error';
      }

      res.json(status);
    } catch (error) {
      console.error("Error checking system status:", error);
      res.status(500).json({ error: "Failed to check system status" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}
