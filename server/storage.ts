import { 
  users, agentConfigs, conversations, dataSources,
  type User, type InsertUser, 
  type AgentConfig, type InsertAgentConfig,
  type Conversation, type InsertConversation,
  type DataSource, type InsertDataSource
} from "@shared/schema";

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
}

export class MemStorage implements IStorage {
  private users: Map<number, User> = new Map();
  private agentConfigs: Map<number, AgentConfig> = new Map();
  private conversations: Map<number, Conversation> = new Map();
  private dataSources: Map<number, DataSource> = new Map();
  
  private currentUserId = 1;
  private currentAgentConfigId = 1;
  private currentConversationId = 1;
  private currentDataSourceId = 1;

  constructor() {
    this.initializeDefaultData();
  }

  private initializeDefaultData() {
    // Create default user
    const defaultUser: User = {
      id: 1,
      username: "admin",
      password: "admin123"
    };
    this.users.set(1, defaultUser);
    this.currentUserId = 2;

    // Create default YouTube assistant agent config
    const defaultAgentConfig: AgentConfig = {
      id: 1,
      userId: 1,
      name: "GiveMeTheMic Assistant",
      type: "youtube-assistant",
      systemPrompt: `You are a helpful AI assistant for the GiveMeTheMic YouTube channel (@GiveMeTheMic22). 
You help subscribers with information about the channel, website (givemethemicofficial.com), and content.
Be friendly, enthusiastic, and knowledgeable about the channel's content and community.
Always provide accurate information and encourage engagement with the channel.`,
      personality: "friendly",
      voiceModel: "alloy",
      responseLength: "moderate",
      temperature: 70,
      isActive: true,
      settings: {
        audioQuality: "high",
        bufferSize: 2048,
        enableLogging: true,
        autoReconnect: true
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
      name: "GiveMeTheMic Channel",
      url: "https://www.youtube.com/@GiveMeTheMic22",
      lastSynced: new Date(),
      isActive: true,
      metadata: {
        channelId: "@GiveMeTheMic22",
        apiKey: "YOUTUBE_API_KEY"
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
