interface AvailableTool {
  name: string;
  description: string;
  parameters?: Record<string, any>;
  category?: string;
}

interface WebhookDiscoveryResponse {
  success: boolean;
  availableTools?: AvailableTool[];
  error?: string;
  metadata?: Record<string, any>;
}

class WebhookToolDiscovery {
  private storage: any;
  private webhookUrl: string | null;
  private discoveryInterval: NodeJS.Timeout | null = null;

  constructor(storageInstance: any) {
    this.storage = storageInstance;
    this.webhookUrl = process.env.N8N_WEBHOOK_URL || null;
  }

  /**
   * Start automatic tool discovery in background
   * This runs parallel to the main application without user awareness
   */
  async startAutomaticDiscovery() {
    if (!this.webhookUrl) {
      console.log('[Tool Discovery] No webhook URL configured, skipping automatic discovery');
      return;
    }

    console.log('[Tool Discovery] Starting automatic tool discovery system');
    
    // Run initial discovery immediately
    await this.discoverAndUpdateTools();
    
    // Schedule periodic discovery every 5 minutes
    this.discoveryInterval = setInterval(async () => {
      await this.discoverAndUpdateTools();
    }, 5 * 60 * 1000); // 5 minutes
  }

  /**
   * Stop automatic discovery
   */
  stopAutomaticDiscovery() {
    if (this.discoveryInterval) {
      clearInterval(this.discoveryInterval);
      this.discoveryInterval = null;
      console.log('[Tool Discovery] Stopped automatic tool discovery');
    }
  }

  /**
   * Discover available tools via webhook and update database
   */
  private async discoverAndUpdateTools(): Promise<void> {
    try {
      console.log('[Tool Discovery] Discovering available tools...');
      
      const response = await this.callWebhookForDiscovery();
      
      if (response.success && response.availableTools) {
        await this.updateToolsInDatabase(response.availableTools);
        console.log(`[Tool Discovery] Updated ${response.availableTools.length} tools in database`);
      } else {
        console.log(`[Tool Discovery] Discovery failed: ${response.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('[Tool Discovery] Error during tool discovery:', error);
    }
  }

  /**
   * Call webhook to discover available tools
   */
  private async callWebhookForDiscovery(): Promise<WebhookDiscoveryResponse> {
    if (!this.webhookUrl) {
      return {
        success: false,
        error: 'No webhook URL configured'
      };
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

      const response = await fetch(this.webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'LiveKit-Voice-Agent/1.0'
        },
        body: JSON.stringify({
          tool: 'discovery',
          action: 'list_tools',
          timestamp: new Date().toISOString(),
          source: 'automatic_discovery'
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return {
          success: false,
          error: `HTTP ${response.status}: ${response.statusText}`
        };
      }

      const data = await response.json();
      
      return {
        success: true,
        availableTools: data.tools || [],
        metadata: {
          responseTime: Date.now(),
          webhookVersion: data.version,
          serverInfo: data.server
        }
      };
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return {
          success: false,
          error: 'Request timeout'
        };
      }
      
      return {
        success: false,
        error: error.message || 'Network error'
      };
    }
  }

  /**
   * Update tools in database
   */
  private async updateToolsInDatabase(tools: AvailableTool[]): Promise<void> {
    try {
      // Store discovered tools in a simple format
      const toolData = {
        discoveredAt: new Date().toISOString(),
        webhookUrl: this.webhookUrl,
        tools: tools.map(tool => ({
          name: tool.name,
          description: tool.description,
          parameters: tool.parameters || {},
          category: tool.category || 'general'
        })),
        count: tools.length
      };

      // You could extend this to store in a dedicated table
      // For now, we'll store in agent settings as discovered tools
      console.log('[Tool Discovery] Tools discovered:', JSON.stringify(toolData, null, 2));
      
      // Update any active agent configuration with available tools info
      const activeAgent = await this.storage.getActiveAgentConfig();
      if (activeAgent) {
        const updatedSettings = {
          ...activeAgent.settings,
          discoveredTools: toolData
        };
        
        await this.storage.updateAgentConfig(activeAgent.id, {
          settings: updatedSettings
        });
      }
    } catch (error) {
      console.error('[Tool Discovery] Error updating tools in database:', error);
    }
  }

  /**
   * Manual tool discovery for testing
   */
  async testDiscovery(): Promise<WebhookDiscoveryResponse> {
    console.log('[Tool Discovery] Manual discovery test initiated');
    return await this.callWebhookForDiscovery();
  }

  /**
   * Get last discovered tools from database
   */
  async getDiscoveredTools(): Promise<AvailableTool[]> {
    try {
      const activeAgent = await this.storage.getActiveAgentConfig();
      if (activeAgent?.settings?.discoveredTools?.tools) {
        return activeAgent.settings.discoveredTools.tools;
      }
      return [];
    } catch (error) {
      console.error('[Tool Discovery] Error getting discovered tools:', error);
      return [];
    }
  }
}

export { WebhookToolDiscovery, type AvailableTool, type WebhookDiscoveryResponse };