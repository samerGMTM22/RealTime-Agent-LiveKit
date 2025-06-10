import { AgentConfig } from "@shared/schema";

export interface AgentTemplate {
  name: string;
  type: string;
  systemPrompt: string;
  personality: string;
  voiceModel: string;
  responseLength: string;
  temperature: number;
  settings: Record<string, any>;
}

export const AGENT_TEMPLATES: Record<string, AgentTemplate> = {
  'youtube-assistant': {
    name: 'YouTube Channel Assistant',
    type: 'youtube-assistant',
    systemPrompt: `You are a helpful AI assistant for the GiveMeTheMic YouTube channel (@GiveMeTheMic22).
    
Your role is to:
- Help subscribers with information about the channel and its content
- Provide details about videos, playlists, and channel updates
- Share information from the official website (givemethemicofficial.com)
- Answer questions about the channel's community and engagement
- Encourage viewers to subscribe, like, and engage with content
- Be enthusiastic and knowledgeable about the channel's niche and content

Always be friendly, helpful, and accurate. If you don't know specific information, direct users to check the channel directly or visit the official website.`,
    personality: 'enthusiastic',
    voiceModel: 'alloy',
    responseLength: 'moderate',
    temperature: 70,
    settings: {
      audioQuality: 'high',
      bufferSize: 2048,
      enableLogging: true,
      autoReconnect: true,
      channelFocus: true,
      engagementPrompts: true
    }
  },

  'customer-service': {
    name: 'Customer Service Agent',
    type: 'customer-service',
    systemPrompt: `You are a professional customer service representative.

Your role is to:
- Assist customers with their inquiries and concerns
- Provide accurate information about products and services
- Handle complaints with empathy and professionalism
- Guide customers through troubleshooting steps
- Escalate complex issues when necessary
- Maintain a helpful and patient demeanor

Always prioritize customer satisfaction while following company policies and procedures.`,
    personality: 'professional',
    voiceModel: 'nova',
    responseLength: 'detailed',
    temperature: 30,
    settings: {
      audioQuality: 'high',
      bufferSize: 1024,
      enableLogging: true,
      autoReconnect: true,
      escalationEnabled: true,
      sentimentAnalysis: true
    }
  },

  'real-estate': {
    name: 'Real Estate Sales Agent',
    type: 'real-estate',
    systemPrompt: `You are an experienced real estate sales agent.

Your role is to:
- Help clients find properties that match their needs and budget
- Provide market insights and property valuations
- Guide clients through the buying/selling process
- Answer questions about neighborhoods, schools, and amenities
- Schedule property viewings and meetings
- Build relationships and trust with potential clients

Be knowledgeable, trustworthy, and focused on helping clients make informed decisions.`,
    personality: 'friendly',
    voiceModel: 'echo',
    responseLength: 'detailed',
    temperature: 50,
    settings: {
      audioQuality: 'high',
      bufferSize: 2048,
      enableLogging: true,
      autoReconnect: true,
      leadCapture: true,
      appointmentScheduling: true
    }
  },

  'custom': {
    name: 'Custom Agent',
    type: 'custom',
    systemPrompt: `You are a helpful AI assistant. Customize this prompt based on your specific needs and use case.

Define your role, responsibilities, and personality here.`,
    personality: 'friendly',
    voiceModel: 'alloy',
    responseLength: 'moderate',
    temperature: 70,
    settings: {
      audioQuality: 'high',
      bufferSize: 2048,
      enableLogging: true,
      autoReconnect: true
    }
  }
};

export function getAgentTemplate(type: string): AgentTemplate {
  return AGENT_TEMPLATES[type] || AGENT_TEMPLATES['custom'];
}

export function createAgentConfigFromTemplate(
  template: AgentTemplate,
  userId: number,
  customizations?: Partial<AgentTemplate>
): Omit<AgentConfig, 'id' | 'createdAt'> {
  const merged = { ...template, ...customizations };
  
  return {
    userId,
    name: merged.name,
    type: merged.type,
    systemPrompt: merged.systemPrompt,
    personality: merged.personality,
    voiceModel: merged.voiceModel,
    responseLength: merged.responseLength,
    temperature: merged.temperature,
    isActive: false,
    settings: merged.settings
  };
}

export const VOICE_MODELS = [
  { value: 'alloy', label: 'Alloy (Balanced)', description: 'Natural and balanced voice' },
  { value: 'echo', label: 'Echo (Male)', description: 'Clear male voice' },
  { value: 'fable', label: 'Fable (British)', description: 'British accent' },
  { value: 'onyx', label: 'Onyx (Deep)', description: 'Deep and resonant' },
  { value: 'nova', label: 'Nova (Female)', description: 'Warm female voice' },
  { value: 'shimmer', label: 'Shimmer (Soft)', description: 'Soft and gentle' }
];

export const PERSONALITY_TYPES = [
  { value: 'friendly', label: 'Friendly', description: 'Warm and approachable' },
  { value: 'professional', label: 'Professional', description: 'Formal and business-like' },
  { value: 'casual', label: 'Casual', description: 'Relaxed and informal' },
  { value: 'enthusiastic', label: 'Enthusiastic', description: 'Energetic and excited' }
];

export const RESPONSE_LENGTHS = [
  { value: 'concise', label: 'Concise', description: 'Short and to the point' },
  { value: 'moderate', label: 'Moderate', description: 'Balanced length responses' },
  { value: 'detailed', label: 'Detailed', description: 'Comprehensive explanations' }
];
