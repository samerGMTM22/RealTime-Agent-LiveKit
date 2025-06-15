import { EventSource } from 'eventsource';
import fetch from 'node-fetch';

export class N8NMCPProxy {
  // Store active connections to reuse them and keep them alive
  private activeConnections = new Map<string, {
    eventSource: EventSource;
    messagesUrl: string;
    lastActivity: number;
    isReady: Promise<void>;
  }>();



  // Call this method from your /api/mcp/execute route
  async callN8NTool(serverUrl: string, toolName: string, params: any, apiKey?: string): Promise<any> {
    try {
      console.log(`N8N MCP Proxy: Calling tool '${toolName}' on ${serverUrl}`);

      // Get or create a persistent connection
      const connection = await this.getOrCreateConnection(serverUrl, apiKey);

      // Make the MCP JSON-RPC call using the session's messagesUrl
      const mcpRequest = {
        jsonrpc: "2.0",
        id: `req_${Date.now()}`,
        method: "tools/call",
        params: {
          name: toolName, // Use the exact internal name from N8N
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
      console.log(`N8N MCP Proxy: Request body: ${JSON.stringify(mcpRequest)}`);

      const response = await fetch(connection.messagesUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(mcpRequest),
        signal: AbortSignal.timeout(15000) // 15-second timeout
      });

      // Update activity timestamp to keep connection alive
      connection.lastActivity = Date.now();

      if (response.ok) {
        const result: any = await response.json();
        console.log(`N8N MCP Proxy: Success response:`, JSON.stringify(result).substring(0, 200));

        if (result.result) {
            return { success: true, result: this.formatMCPResult(result.result) };
        } else if (result.error) {
            console.error(`N8N MCP Proxy: JSON-RPC error: ${result.error.message}`);
            // If tool not found, it's a configuration issue
            if (result.error.code === -32603 || result.error.message.includes("Tool not found")) {
                 return { success: false, error: `Tool '${toolName}' not found on the N8N server. Check the 'Internal Name' in your N8N workflow.` };
            }
            return { success: false, error: result.error.message || 'MCP server error' };
        }
      } else {
        const errorText = await response.text();
        console.error(`N8N MCP Proxy: HTTP error ${response.status}: ${errorText}`);
        // If session is invalid, close the connection
        if (response.status === 404 || errorText.includes('sessionId')) {
            this.closeConnection(serverUrl);
        }
        return { success: false, error: `HTTP ${response.status}: ${errorText}` };
      }

    } catch (error: any) {
      console.error('N8N MCP Proxy error:', error);
      return { success: false, error: error.message || 'Unknown proxy error' };
    }
    
    return { success: false, error: 'No valid response from MCP server' };
  }
  
  private getOrCreateConnection(serverUrl: string, apiKey?: string): Promise<{ eventSource: EventSource; messagesUrl: string; lastActivity: number; }> {
    if (this.activeConnections.has(serverUrl)) {
        const existingConn = this.activeConnections.get(serverUrl)!;
        // Check if connection is still active, otherwise create new
        if (Date.now() - existingConn.lastActivity < 60000) { // 1-minute timeout
            return existingConn.isReady.then(() => existingConn);
        }
        this.closeConnection(serverUrl); // Close expired connection
    }

    console.log(`N8N MCP Proxy: Creating new SSE connection to ${serverUrl}`);
    const promise = new Promise<void>((resolve, reject) => {
        const headers: any = { 'Cache-Control': 'no-cache', Connection: 'keep-alive' };
        if (apiKey) {
            headers['Authorization'] = `Bearer ${apiKey}`;
        }

        const eventSource = new EventSource(serverUrl);
        const connection = { eventSource, messagesUrl: '', lastActivity: Date.now(), isReady: null as any };
        connection.isReady = promise; // Add the promise to the connection object
        
        const timeout = setTimeout(() => {
            eventSource.close();
            reject(new Error('SSE connection timed out after 10 seconds.'));
        }, 10000);

        eventSource.addEventListener('message', (event: any) => {
            const data = event.data;
            if (data && data.includes('/messages?sessionId=')) {
                connection.messagesUrl = new URL(data, serverUrl).toString();
                console.log(`N8N MCP Proxy: Got session endpoint: ${connection.messagesUrl}`);
                clearTimeout(timeout);
                resolve();
            }
        });

        eventSource.addEventListener('endpoint', (event: any) => {
            const data = event.data;
            if (data && data.includes('/messages?sessionId=')) {
                connection.messagesUrl = new URL(data, serverUrl).toString();
                console.log(`N8N MCP Proxy: Got session endpoint from endpoint event: ${connection.messagesUrl}`);
                clearTimeout(timeout);
                resolve();
            }
        });

        eventSource.addEventListener('error', (err: any) => {
            console.error('N8N MCP Proxy: SSE connection error:', err);
            clearTimeout(timeout);
            eventSource.close();
            reject(new Error('SSE connection failed. Check N8N workflow is active and URL is correct.'));
        });
        
        this.activeConnections.set(serverUrl, connection);
    });

    return promise.then(() => this.activeConnections.get(serverUrl)!);
  }

  private closeConnection(serverUrl: string) {
      if (this.activeConnections.has(serverUrl)) {
          console.log(`N8N MCP Proxy: Closing connection to ${serverUrl}`);
          this.activeConnections.get(serverUrl)!.eventSource.close();
          this.activeConnections.delete(serverUrl);
      }
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
    console.log('N8N MCP Proxy: Cleaning up all connections');
    const serverUrls = Array.from(this.activeConnections.keys());
    for (const serverUrl of serverUrls) {
      this.closeConnection(serverUrl);
    }
  }
}

export const n8nMCPProxy = new N8NMCPProxy();