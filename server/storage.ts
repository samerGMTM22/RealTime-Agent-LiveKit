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
    return (result.rowCount || 0) > 0;
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
    return (result.rowCount || 0) > 0;
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
    return (result.rowCount || 0) > 0;
  }
}

export const storage = new DatabaseStorage();