import { 
  users, agentConfigs, conversations, dataSources, mcpServers,
  type User, type InsertUser, 
  type AgentConfig, type InsertAgentConfig,
  type Conversation, type InsertConversation,
  type DataSource, type InsertDataSource,
  type McpServer, type InsertMcpServer
} from "@shared/schema";
import { db } from "./db";
import { eq } from "drizzle-orm";

export interface IStorage {
  // User methods
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  // Agent config methods
  getAgentConfig(id: number): Promise<AgentConfig | undefined>;
  getAgentConfigsByUserId(userId: number): Promise<AgentConfig[]>;
  getActiveAgentConfig(userId: number): Promise<AgentConfig | undefined>;
  createAgentConfig(config: InsertAgentConfig): Promise<AgentConfig>;
  updateAgentConfig(id: number, config: Partial<InsertAgentConfig>): Promise<AgentConfig | undefined>;
  deleteAgentConfig(id: number): Promise<boolean>;

  // Conversation methods
  getConversationsBySessionId(sessionId: string): Promise<Conversation[]>;
  getConversationsByAgentConfigId(agentConfigId: number): Promise<Conversation[]>;
  createConversation(conversation: InsertConversation): Promise<Conversation>;

  // Data source methods
  getDataSourcesByAgentConfigId(agentConfigId: number): Promise<DataSource[]>;
  createDataSource(dataSource: InsertDataSource): Promise<DataSource>;
  updateDataSource(id: number, dataSource: Partial<InsertDataSource>): Promise<DataSource | undefined>;
  deleteDataSource(id: number): Promise<boolean>;

  // MCP server methods
  getMcpServersByUserId(userId: number): Promise<McpServer[]>;
  createMcpServer(mcpServer: InsertMcpServer): Promise<McpServer>;
  updateMcpServer(id: number, mcpServer: Partial<InsertMcpServer>): Promise<McpServer | undefined>;
  deleteMcpServer(id: number): Promise<boolean>;
}

export class DatabaseStorage implements IStorage {
  constructor() {
    this.initializeDefaultData();
  }

  private async initializeDefaultData() {
    try {
      // Check if default user exists
      const existingUser = await this.getUserByUsername("demo");
      if (!existingUser) {
        // Create default user
        await this.createUser({
          username: "demo",
          password: "demo123"
        });
      }
    } catch (error) {
      console.log("Database initialization skipped - tables may not exist yet");
    }
  }

  async getUser(id: number): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user || undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user || undefined;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db
      .insert(users)
      .values(insertUser)
      .returning();
    return user;
  }

  async getAgentConfig(id: number): Promise<AgentConfig | undefined> {
    const [config] = await db.select().from(agentConfigs).where(eq(agentConfigs.id, id));
    return config || undefined;
  }

  async getAgentConfigsByUserId(userId: number): Promise<AgentConfig[]> {
    return await db.select().from(agentConfigs).where(eq(agentConfigs.userId, userId));
  }

  async getActiveAgentConfig(userId: number): Promise<AgentConfig | undefined> {
    const [config] = await db.select().from(agentConfigs)
      .where(eq(agentConfigs.userId, userId));
    return config || undefined;
  }

  async createAgentConfig(insertConfig: InsertAgentConfig): Promise<AgentConfig> {
    const [config] = await db
      .insert(agentConfigs)
      .values(insertConfig)
      .returning();
    return config;
  }

  async updateAgentConfig(id: number, updateData: Partial<InsertAgentConfig>): Promise<AgentConfig | undefined> {
    const [updated] = await db
      .update(agentConfigs)
      .set(updateData)
      .where(eq(agentConfigs.id, id))
      .returning();
    return updated || undefined;
  }

  async deleteAgentConfig(id: number): Promise<boolean> {
    const result = await db.delete(agentConfigs).where(eq(agentConfigs.id, id));
    return result.rowCount > 0;
  }

  async getConversationsBySessionId(sessionId: string): Promise<Conversation[]> {
    return await db.select().from(conversations).where(eq(conversations.sessionId, sessionId));
  }

  async getConversationsByAgentConfigId(agentConfigId: number): Promise<Conversation[]> {
    return await db.select().from(conversations).where(eq(conversations.agentConfigId, agentConfigId));
  }

  async createConversation(insertConversation: InsertConversation): Promise<Conversation> {
    const [conversation] = await db
      .insert(conversations)
      .values(insertConversation)
      .returning();
    return conversation;
  }

  async getDataSourcesByAgentConfigId(agentConfigId: number): Promise<DataSource[]> {
    return await db.select().from(dataSources).where(eq(dataSources.agentConfigId, agentConfigId));
  }

  async createDataSource(insertDataSource: InsertDataSource): Promise<DataSource> {
    const [dataSource] = await db
      .insert(dataSources)
      .values(insertDataSource)
      .returning();
    return dataSource;
  }

  async updateDataSource(id: number, updateData: Partial<InsertDataSource>): Promise<DataSource | undefined> {
    const [updated] = await db
      .update(dataSources)
      .set(updateData)
      .where(eq(dataSources.id, id))
      .returning();
    return updated || undefined;
  }

  async deleteDataSource(id: number): Promise<boolean> {
    const result = await db.delete(dataSources).where(eq(dataSources.id, id));
    return result.rowCount > 0;
  }

  async getMcpServersByUserId(userId: number): Promise<McpServer[]> {
    return await db.select().from(mcpServers).where(eq(mcpServers.userId, userId));
  }

  async createMcpServer(insertMcpServer: InsertMcpServer): Promise<McpServer> {
    const [mcpServer] = await db
      .insert(mcpServers)
      .values(insertMcpServer)
      .returning();
    return mcpServer;
  }

  async updateMcpServer(id: number, updateData: Partial<InsertMcpServer>): Promise<McpServer | undefined> {
    const [updated] = await db
      .update(mcpServers)
      .set(updateData)
      .where(eq(mcpServers.id, id))
      .returning();
    return updated || undefined;
  }

  async deleteMcpServer(id: number): Promise<boolean> {
    const result = await db.delete(mcpServers).where(eq(mcpServers.id, id));
    return result.rowCount > 0;
  }
}

export const storage = new DatabaseStorage();

    // Create default YouTube assistant agent config
    const defaultAgentConfig: AgentConfig = {
      id: 1,
      userId: 1,
      name: "Give Me the Mic Assistant",
      type: "youtube-assistant",
      systemPrompt: `You are a specialized AI assistant for the "Give Me the Mic" YouTube channel (484 subscribers, 249 videos).

Your primary responsibilities:
- Help subscribers and visitors understand the channel's content and mission
- Provide information about the channel's 249 videos and content library
- Share details from the official website (givemethemicofficial.com)
- Encourage engagement, subscriptions, and community participation
- Answer questions about the creator's background and content focus
- Guide users to relevant videos based on their interests

The channel has been active since January 2020 with over 62,000 total views. Be enthusiastic about the content and help viewers discover videos that match their interests.

Communication style:
- Be friendly, knowledgeable, and encouraging
- Highlight the channel's growing community (484+ subscribers)
- Mention specific video counts and engagement when relevant
- Always encourage viewers to subscribe and engage with content`,
      personality: "enthusiastic",
      voiceModel: "nova",
      responseLength: "moderate",
      temperature: 70,
      isActive: true,
      settings: {
        audioQuality: "high",
        bufferSize: 2048,
        enableLogging: true,
        autoReconnect: true,
        channelFocus: true,
        engagementPrompts: true
      },
      createdAt: new Date()
    };
    this.agentConfigs.set(1, defaultAgentConfig);
    this.currentAgentConfigId = 2;

    // Create default data sources
    const youtubeDataSource: DataSource = {
      id: 1,
      agentConfigId: 1,
      type: "youtube",
      name: "Give Me the Mic Channel",
      url: "https://www.youtube.com/channel/UCkFvVFwmpRRTC7Z9G-YzuOw",
      lastSynced: new Date(),
      isActive: true,
      metadata: {
        channelId: "UCkFvVFwmpRRTC7Z9G-YzuOw",
        channelHandle: "GiveMeTheMic",
        customUrl: "@givemethemicmusic",
        includeVideos: true,
        maxVideos: 10
      }
    };

    const websiteDataSource: DataSource = {
      id: 2,
      agentConfigId: 1,
      type: "website",
      name: "Official Website",
      url: "https://www.givemethemicofficial.com",
      lastSynced: new Date(),
      isActive: true,
      metadata: {
        crawlDepth: 3,
        lastCrawled: new Date().toISOString()
      }
    };

    this.dataSources.set(1, youtubeDataSource);
    this.dataSources.set(2, websiteDataSource);
    this.currentDataSourceId = 3;
  }

  // User methods
  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(user => user.username === username);
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.currentUserId++;
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  // Agent config methods
  async getAgentConfig(id: number): Promise<AgentConfig | undefined> {
    return this.agentConfigs.get(id);
  }

  async getAgentConfigsByUserId(userId: number): Promise<AgentConfig[]> {
    return Array.from(this.agentConfigs.values()).filter(config => config.userId === userId);
  }

  async getActiveAgentConfig(userId: number): Promise<AgentConfig | undefined> {
    return Array.from(this.agentConfigs.values()).find(
      config => config.userId === userId && config.isActive
    );
  }

  async createAgentConfig(insertConfig: InsertAgentConfig): Promise<AgentConfig> {
    const id = this.currentAgentConfigId++;
    const config: AgentConfig = { 
      id,
      userId: insertConfig.userId || 1,
      name: insertConfig.name,
      type: insertConfig.type,
      systemPrompt: insertConfig.systemPrompt,
      personality: insertConfig.personality || 'friendly',
      voiceModel: insertConfig.voiceModel || 'alloy',
      responseLength: insertConfig.responseLength || 'moderate',
      temperature: insertConfig.temperature || 70,
      isActive: insertConfig.isActive || false,
      settings: insertConfig.settings || {},
      createdAt: new Date() 
    };
    this.agentConfigs.set(id, config);
    return config;
  }

  async updateAgentConfig(id: number, updateData: Partial<InsertAgentConfig>): Promise<AgentConfig | undefined> {
    const existing = this.agentConfigs.get(id);
    if (!existing) return undefined;

    const updated: AgentConfig = { ...existing, ...updateData };
    this.agentConfigs.set(id, updated);
    return updated;
  }

  async deleteAgentConfig(id: number): Promise<boolean> {
    return this.agentConfigs.delete(id);
  }

  // Conversation methods
  async getConversationsBySessionId(sessionId: string): Promise<Conversation[]> {
    return Array.from(this.conversations.values()).filter(
      conv => conv.sessionId === sessionId
    );
  }

  async getConversationsByAgentConfigId(agentConfigId: number): Promise<Conversation[]> {
    return Array.from(this.conversations.values()).filter(
      conv => conv.agentConfigId === agentConfigId
    );
  }

  async createConversation(insertConversation: InsertConversation): Promise<Conversation> {
    const id = this.currentConversationId++;
    const conversation: Conversation = {
      ...insertConversation,
      id,
      agentConfigId: insertConversation.agentConfigId || 1,
      userMessage: insertConversation.userMessage || null,
      agentResponse: insertConversation.agentResponse || null,
      audioUrl: insertConversation.audioUrl || null,
      metadata: insertConversation.metadata || {},
      timestamp: new Date()
    };
    this.conversations.set(id, conversation);
    return conversation;
  }

  // Data source methods
  async getDataSourcesByAgentConfigId(agentConfigId: number): Promise<DataSource[]> {
    return Array.from(this.dataSources.values()).filter(
      source => source.agentConfigId === agentConfigId
    );
  }

  async createDataSource(insertDataSource: InsertDataSource): Promise<DataSource> {
    const id = this.currentDataSourceId++;
    const dataSource: DataSource = {
      id,
      agentConfigId: insertDataSource.agentConfigId || 1,
      type: insertDataSource.type,
      name: insertDataSource.name,
      url: insertDataSource.url || null,
      isActive: insertDataSource.isActive ?? true,
      metadata: insertDataSource.metadata || {},
      lastSynced: new Date()
    };
    this.dataSources.set(id, dataSource);
    return dataSource;
  }

  async updateDataSource(id: number, updateData: Partial<InsertDataSource>): Promise<DataSource | undefined> {
    const existing = this.dataSources.get(id);
    if (!existing) return undefined;

    const updated: DataSource = { ...existing, ...updateData };
    this.dataSources.set(id, updated);
    return updated;
  }

  async deleteDataSource(id: number): Promise<boolean> {
    return this.dataSources.delete(id);
  }
}

export const storage = new MemStorage();
