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
  type: text("type").notNull(), // 'youtube-assistant', 'customer-service', 'real-estate', 'custom'
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

// Types
export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;

export type AgentConfig = typeof agentConfigs.$inferSelect;
export type InsertAgentConfig = z.infer<typeof insertAgentConfigSchema>;

export type Conversation = typeof conversations.$inferSelect;
export type InsertConversation = z.infer<typeof insertConversationSchema>;

export type DataSource = typeof dataSources.$inferSelect;
export type InsertDataSource = z.infer<typeof insertDataSourceSchema>;

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
  youtube: 'active' | 'inactive' | 'error';
  latency: string;
}
