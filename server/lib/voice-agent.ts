// This file is deprecated - voice agent functionality is now handled by the Python LiveKit agent
// The Python agent.py file handles all voice processing with OpenAI Realtime API

export const voiceAgentManager = {
  async startAgent(sessionId: string, agentConfigId: number): Promise<void> {
    console.log(`Voice agent functionality moved to Python agent.py for session: ${sessionId}`);
    // Python agent is started by the routes.ts file
  },

  async stopAgent(sessionId: string): Promise<void> {
    console.log(`Voice agent stop for session: ${sessionId} - handled by Python process`);
  },

  getAgent(sessionId: string): undefined {
    return undefined;
  }
};