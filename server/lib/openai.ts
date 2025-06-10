import OpenAI from "openai";

// the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
const openai = new OpenAI({ 
  apiKey: process.env.OPENAI_API_KEY || process.env.OPENAI_API_KEY_ENV_VAR || "default_key"
});

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface VoiceGenerationOptions {
  model?: string;
  voice?: 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer';
  speed?: number;
}

export class OpenAIService {
  async generateChatResponse(
    messages: ChatMessage[], 
    temperature: number = 0.7,
    maxTokens: number = 500
  ): Promise<string> {
    try {
      const response = await openai.chat.completions.create({
        model: "gpt-4o",
        messages,
        temperature,
        max_tokens: maxTokens,
      });

      return response.choices[0].message.content || "";
    } catch (error) {
      console.error("OpenAI chat completion error:", error);
      throw new Error(`Failed to generate chat response: ${error.message}`);
    }
  }

  async generateVoiceResponse(
    text: string, 
    options: VoiceGenerationOptions = {}
  ): Promise<Buffer> {
    try {
      const response = await openai.audio.speech.create({
        model: "tts-1",
        voice: options.voice || 'alloy',
        input: text,
        speed: options.speed || 1.0,
      });

      return Buffer.from(await response.arrayBuffer());
    } catch (error) {
      console.error("OpenAI voice generation error:", error);
      throw new Error(`Failed to generate voice response: ${error.message}`);
    }
  }

  async transcribeAudio(audioBuffer: Buffer): Promise<string> {
    try {
      // Create a temporary file for the audio data
      const file = new File([audioBuffer], "audio.webm", { type: "audio/webm" });
      
      const response = await openai.audio.transcriptions.create({
        file,
        model: "whisper-1",
      });

      return response.text;
    } catch (error) {
      console.error("OpenAI transcription error:", error);
      throw new Error(`Failed to transcribe audio: ${error.message}`);
    }
  }

  async processChannelQuery(
    query: string, 
    channelData: any, 
    websiteData: any
  ): Promise<string> {
    const systemPrompt = `You are a helpful AI assistant for the GiveMeTheMic YouTube channel.
Channel Information: ${JSON.stringify(channelData)}
Website Information: ${JSON.stringify(websiteData)}

Provide accurate, helpful responses about the channel, its content, and related information.
Be friendly and enthusiastic while staying factual.`;

    const response = await this.generateChatResponse([
      { role: 'system', content: systemPrompt },
      { role: 'user', content: query }
    ]);

    return response;
  }
}

export const openaiService = new OpenAIService();
