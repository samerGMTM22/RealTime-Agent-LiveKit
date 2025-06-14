import { EventSource } from 'eventsource';
import fetch from 'node-fetch';

export class N8NMCPProxy {
  private activeConnections = new Map<string, {
    eventSource: EventSource;
    messagesUrl: string;
    lastActivity: number;
  }>();

  async callN8NTool(serverUrl: string, toolName: string, params: any, apiKey?: string): Promise<any> {
    try {
      console.log(`N8N MCP Proxy: Calling tool ${toolName} on ${serverUrl}`);
      
      // Check if we have an active connection
      const connectionKey = `${serverUrl}_${toolName}`;
      let connection = this.activeConnections.get(connectionKey);
      
      if (!connection || Date.now() - connection.lastActivity > 30000) {
        // Create new connection
        connection = await this.createN8NConnection(serverUrl, apiKey);
        if (connection) {
          this.activeConnections.set(connectionKey, connection);
        }
      }
      
      if (!connection || !connection.messagesUrl) {
        throw new Error('Failed to establish N8N MCP session');
      }
      
      // Update activity timestamp
      connection.lastActivity = Date.now();
      
      // Make the MCP JSON-RPC call
      const mcpRequest = {
        jsonrpc: "2.0",
        id: `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        method: "tools/call",
        params: {
          name: toolName,
          arguments: params
        }
      };
      
      const headers: any = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      };
      
      if (apiKey) {
        headers['Authorization'] = `Bearer ${apiKey}`;
      }
      
      console.log(`N8N MCP Proxy: Making JSON-RPC call to ${connection.messagesUrl}`);
      
      const response = await fetch(connection.messagesUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(mcpRequest)
      });
      
      if (response.ok) {
        const result: any = await response.json();
        console.log(`N8N MCP Proxy: Success response:`, JSON.stringify(result).substring(0, 200));
        
        if (result.result) {
          return {
            success: true,
            result: this.formatMCPResult(result.result),
            server: 'N8N MCP'
          };
        } else if (result.error) {
          return {
            success: false,
            error: result.error.message || 'MCP server error'
          };
        }
      } else {
        const errorText = await response.text();
        console.error(`N8N MCP Proxy: HTTP error ${response.status}: ${errorText}`);
        
        // If we get a session error, remove the connection and retry once
        if (response.status === 401 && errorText.includes('sessionId')) {
          this.activeConnections.delete(connectionKey);
          console.log('N8N MCP Proxy: Session expired, retrying with new connection...');
          return this.callN8NTool(serverUrl, toolName, params, apiKey);
        }
        
        return {
          success: false,
          error: `HTTP ${response.status}: ${errorText}`
        };
      }
      
    } catch (error) {
      console.error('N8N MCP Proxy error:', error);
      return {
        success: false,
        error: error.message || 'Unknown error'
      };
    }
    
    return {
      success: false,
      error: 'No valid response from MCP server'
    };
  }
  
  private async createN8NConnection(serverUrl: string, apiKey?: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        eventSource?.close();
        reject(new Error('SSE connection timeout'));
      }, 10000);
      
      const headers: any = {};
      if (apiKey) {
        headers['Authorization'] = `Bearer ${apiKey}`;
      }
      
      console.log(`N8N MCP Proxy: Establishing SSE connection to ${serverUrl}`);
      
      const eventSource = new EventSource(serverUrl, { headers });
      let messagesUrl = '';
      
      eventSource.addEventListener('message', (event: any) => {
        const data = event.data;
        console.log(`N8N MCP Proxy: SSE message: ${data}`);
        
        if (data && data.includes('/messages?sessionId=')) {
          messagesUrl = new URL(data, serverUrl).toString();
          console.log(`N8N MCP Proxy: Got session endpoint: ${messagesUrl}`);
          
          clearTimeout(timeout);
          resolve({
            eventSource,
            messagesUrl,
            lastActivity: Date.now()
          });
        }
      });
      
      eventSource.addEventListener('error', (error: any) => {
        console.error('N8N MCP Proxy: SSE error:', error);
        clearTimeout(timeout);
        eventSource.close();
        reject(new Error('SSE connection failed'));
      });
      
      // Also listen for the 'endpoint' event type that N8N might use
      eventSource.addEventListener('endpoint', (event: any) => {
        const data = event.data;
        console.log(`N8N MCP Proxy: SSE endpoint event: ${data}`);
        
        if (data && data.includes('/messages?sessionId=')) {
          messagesUrl = new URL(data, serverUrl).toString();
          console.log(`N8N MCP Proxy: Got session endpoint from endpoint event: ${messagesUrl}`);
          
          clearTimeout(timeout);
          resolve({
            eventSource,
            messagesUrl,
            lastActivity: Date.now()
          });
        }
      });
    });
  }
  
  private formatMCPResult(result: any): string {
    if (typeof result === 'string') {
      return result;
    } else if (Array.isArray(result)) {
      return result.map((item: any) => 
        typeof item === 'string' ? item : 
        item.text || item.content || JSON.stringify(item)
      ).join('\n');
    } else if (result && typeof result === 'object') {
      if (result.content) {
        return result.content;
      } else if (result.text) {
        return result.text;
      } else {
        return JSON.stringify(result);
      }
    } else {
      return String(result);
    }
  }
  
  cleanup() {
    console.log('N8N MCP Proxy: Cleaning up connections');
    for (const [key, connection] of this.activeConnections.entries()) {
      connection.eventSource.close();
    }
    this.activeConnections.clear();
  }
}

export const n8nMCPProxy = new N8NMCPProxy();