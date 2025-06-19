import { pgTable, text, serial, integer, boolean, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const agentConfigs = pgTable("agent_configs", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id),
  name: text("name").notNull(),
  type: text("type").notNull(), // 'voice-assistant', 'customer-service', 'real-estate', 'custom'
  systemPrompt: text("system_prompt").notNull(),
  personality: text("personality").notNull().default("friendly"),
  voiceModel: text("voice_model").notNull().default("alloy"),
  responseLength: text("response_length").notNull().default("moderate"),
  temperature: integer("temperature").notNull().default(70), // stored as int (0-100)
  isActive: boolean("is_active").notNull().default(false),
  settings: jsonb("settings").notNull().default('{}'),
  createdAt: timestamp("created_at").defaultNow(),
});

export const conversations = pgTable("conversations", {
  id: serial("id").primaryKey(),
  agentConfigId: integer("agent_config_id").references(() => agentConfigs.id),
  sessionId: text("session_id").notNull(),
  userMessage: text("user_message"),
  agentResponse: text("agent_response"),
  timestamp: timestamp("timestamp").defaultNow(),
  audioUrl: text("audio_url"),
  metadata: jsonb("metadata").default('{}'),
});

export const dataSources = pgTable("data_sources", {
  id: serial("id").primaryKey(),
  agentConfigId: integer("agent_config_id").references(() => agentConfigs.id),
  type: text("type").notNull(), // 'youtube', 'website', 'document', 'api'
  name: text("name").notNull(),
  url: text("url"),
  lastSynced: timestamp("last_synced"),
  isActive: boolean("is_active").notNull().default(true),
  metadata: jsonb("metadata").default('{}'),
});

export const mcpServers = pgTable("mcp_servers", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").references(() => users.id).notNull(),
  name: text("name").notNull(),
  url: text("url").notNull(), // base_url for the MCP server
  protocolType: text("protocol_type").notNull().default("sse"), // 'http', 'sse', 'websocket', 'stdio'
  discoveryEndpoint: text("discovery_endpoint").default("/.well-known/mcp.json"), // endpoint for tool discovery
  resultEndpoint: text("result_endpoint").default("/mcp/results"), // endpoint for result polling
  pollInterval: integer("poll_interval").default(1000), // polling interval in milliseconds
  description: text("description"),
  apiKey: text("api_key"),
  isActive: boolean("is_active").default(true),
  connectionStatus: text("connection_status").default("disconnected"), // 'connected', 'disconnected', 'error', 'testing'
  capabilities: jsonb("capabilities").default([]),
  tools: jsonb("tools").default([]),
  lastConnected: timestamp("last_connected"),
  metadata: jsonb("metadata").default({}),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// Insert schemas
export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export const insertAgentConfigSchema = createInsertSchema(agentConfigs).omit({
  id: true,
  createdAt: true,
});

export const insertConversationSchema = createInsertSchema(conversations).omit({
  id: true,
  timestamp: true,
});

export const insertDataSourceSchema = createInsertSchema(dataSources).omit({
  id: true,
  lastSynced: true,
});

export const insertMcpServerSchema = createInsertSchema(mcpServers).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
  lastConnected: true,
});

// Types
export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;

export type AgentConfig = typeof agentConfigs.$inferSelect;
export type InsertAgentConfig = z.infer<typeof insertAgentConfigSchema>;

export type Conversation = typeof conversations.$inferSelect;
export type InsertConversation = z.infer<typeof insertConversationSchema>;

export type DataSource = typeof dataSources.$inferSelect;
export type InsertDataSource = z.infer<typeof insertDataSourceSchema>;

export type McpServer = typeof mcpServers.$inferSelect;
export type InsertMcpServer = z.infer<typeof insertMcpServerSchema>;

// Voice session types
export interface VoiceSessionData {
  sessionId: string;
  isActive: boolean;
  isMuted: boolean;
  latency: number;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
}

export interface SystemStatus {
  livekit: 'online' | 'offline' | 'error';
  openai: 'connected' | 'disconnected' | 'error';
  mcp: 'connected' | 'disconnected' | 'error';
  latency: string;
}
