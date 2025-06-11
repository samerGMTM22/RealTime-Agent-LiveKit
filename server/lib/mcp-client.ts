import WebSocket from 'ws';
import { EventEmitter } from 'events';

export interface MCPServer {
  id: string;
  name: string;
  url: string;
  status: 'connected' | 'disconnected' | 'error';
  capabilities?: string[];
  tools?: MCPTool[];
}

export interface MCPTool {
  name: string;
  description: string;
  parameters: Record<string, any>;
}

export interface MCPMessage {
  id: string;
  method: string;
  params?: any;
  result?: any;
  error?: any;
}

export class MCPClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private messageId = 0;
  private pendingRequests = new Map<string, { resolve: Function; reject: Function }>();
  
  constructor(
    public readonly server: MCPServer
  ) {
    super();
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.server.url);
        
        this.ws.on('open', () => {
          this.server.status = 'connected';
          this.emit('connected', this.server);
          this.initialize().then(resolve).catch(reject);
        });

        this.ws.on('message', (data: string) => {
          try {
            const message: MCPMessage = JSON.parse(data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse MCP message:', error);
          }
        });

        this.ws.on('error', (error) => {
          console.error('MCP WebSocket error:', error);
          this.server.status = 'error';
          this.emit('error', error);
          reject(error);
        });

        this.ws.on('close', () => {
          this.server.status = 'disconnected';
          this.emit('disconnected', this.server);
        });

        // Connection timeout
        setTimeout(() => {
          if (this.server.status !== 'connected') {
            reject(new Error('MCP connection timeout'));
          }
        }, 10000);

      } catch (error) {
        this.server.status = 'error';
        reject(error);
      }
    });
  }

  private async initialize(): Promise<void> {
    // Send initialization request
    const response = await this.sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {
        roots: { listChanged: true },
        sampling: {}
      },
      clientInfo: {
        name: 'VoiceAgent-MCP-Client',
        version: '1.0.0'
      }
    });

    if (response.capabilities) {
      this.server.capabilities = Object.keys(response.capabilities);
    }

    // Get available tools
    try {
      const toolsResponse = await this.sendRequest('tools/list', {});
      if (toolsResponse.tools) {
        this.server.tools = toolsResponse.tools;
      }
    } catch (error) {
      console.warn('Failed to get MCP tools:', error);
    }

    // Send initialized notification
    this.sendNotification('notifications/initialized', {});
  }

  async sendRequest(method: string, params?: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('MCP connection not open'));
        return;
      }

      const id = (++this.messageId).toString();
      const message: MCPMessage = { id, method, params };

      this.pendingRequests.set(id, { resolve, reject });

      try {
        this.ws.send(JSON.stringify(message));
        
        // Request timeout
        setTimeout(() => {
          if (this.pendingRequests.has(id)) {
            this.pendingRequests.delete(id);
            reject(new Error(`MCP request timeout: ${method}`));
          }
        }, 30000);

      } catch (error) {
        this.pendingRequests.delete(id);
        reject(error);
      }
    });
  }

  sendNotification(method: string, params?: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    const message = { method, params };
    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error('Failed to send MCP notification:', error);
    }
  }

  private handleMessage(message: MCPMessage): void {
    if (message.id && this.pendingRequests.has(message.id)) {
      const { resolve, reject } = this.pendingRequests.get(message.id)!;
      this.pendingRequests.delete(message.id);

      if (message.error) {
        reject(new Error(message.error.message || 'MCP request failed'));
      } else {
        resolve(message.result || {});
      }
    } else {
      // Handle notifications and other messages
      this.emit('message', message);
    }
  }

  async callTool(name: string, arguments_: Record<string, any>): Promise<any> {
    return this.sendRequest('tools/call', {
      name,
      arguments: arguments_
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.server.status = 'disconnected';
    this.pendingRequests.clear();
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export class MCPManager {
  private clients = new Map<string, MCPClient>();
  private servers = new Map<string, MCPServer>();

  async addServer(server: Omit<MCPServer, 'id' | 'status'>): Promise<MCPServer> {
    const id = `mcp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const mcpServer: MCPServer = {
      ...server,
      id,
      status: 'disconnected'
    };

    this.servers.set(id, mcpServer);
    return mcpServer;
  }

  async connectServer(serverId: string): Promise<void> {
    const server = this.servers.get(serverId);
    if (!server) {
      throw new Error(`MCP server not found: ${serverId}`);
    }

    if (this.clients.has(serverId)) {
      const client = this.clients.get(serverId)!;
      if (client.isConnected()) {
        return; // Already connected
      }
      client.disconnect();
    }

    const client = new MCPClient(server);
    this.clients.set(serverId, client);

    try {
      await client.connect();
      console.log(`Connected to MCP server: ${server.name}`);
    } catch (error) {
      console.error(`Failed to connect to MCP server ${server.name}:`, error);
      this.clients.delete(serverId);
      throw error;
    }
  }

  disconnectServer(serverId: string): void {
    const client = this.clients.get(serverId);
    if (client) {
      client.disconnect();
      this.clients.delete(serverId);
    }

    const server = this.servers.get(serverId);
    if (server) {
      server.status = 'disconnected';
    }
  }

  removeServer(serverId: string): boolean {
    this.disconnectServer(serverId);
    return this.servers.delete(serverId);
  }

  getServer(serverId: string): MCPServer | undefined {
    return this.servers.get(serverId);
  }

  getAllServers(): MCPServer[] {
    return Array.from(this.servers.values());
  }

  getConnectedServers(): MCPServer[] {
    return this.getAllServers().filter(server => server.status === 'connected');
  }

  async callTool(serverId: string, toolName: string, arguments_: Record<string, any>): Promise<any> {
    const client = this.clients.get(serverId);
    if (!client || !client.isConnected()) {
      throw new Error(`MCP server not connected: ${serverId}`);
    }

    return client.callTool(toolName, arguments_);
  }

  getAvailableTools(): Array<{ server: MCPServer; tool: MCPTool }> {
    const tools: Array<{ server: MCPServer; tool: MCPTool }> = [];
    
    for (const server of this.getConnectedServers()) {
      if (server.tools) {
        for (const tool of server.tools) {
          tools.push({ server, tool });
        }
      }
    }

    return tools;
  }
}

export const mcpManager = new MCPManager();