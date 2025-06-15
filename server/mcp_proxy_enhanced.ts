import { EventSource } from 'eventsource';
import fetch from 'node-fetch';
import { v4 as uuidv4 } from 'uuid';

interface PendingResult {
  requestId: string;
  toolName: string;
  params: any;
  timestamp: number;
  status: 'pending' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

export class EnhancedN8NMCPProxy {
  // Store active connections to reuse them
  private activeConnections = new Map<string, {
    eventSource: EventSource;
    messagesUrl: string;
    lastActivity: number;
    isReady: Promise<void>;
  }>();

  // Store pending results for polling
  private pendingResults = new Map<string, PendingResult>();
  
  // Result storage with TTL
  private resultCache = new Map<string, {
    result: any;
    timestamp: number;
    ttl: number;
  }>();

  async callN8NToolWithPolling(
    serverUrl: string, 
    toolName: string, 
    params: any, 
    apiKey?: string,
    options: { pollInterval?: number; maxWaitTime?: number } = {}
  ): Promise<any> {
    const requestId = uuidv4();
    const pollInterval = options.pollInterval || 1000; // 1 second default
    const maxWaitTime = options.maxWaitTime || 30000; // 30 seconds default

    try {
      // First, make the initial MCP call
      const connection = await this.getOrCreateConnection(serverUrl, apiKey);
      
      const mcpRequest = {
        jsonrpc: "2.0",
        id: requestId,
        method: "tools/call",
        params: {
          name: toolName,
          arguments: {
            ...params,
            _requestId: requestId, // Include request ID for tracking
            _callbackUrl: `http://localhost:5000/api/mcp/callback/${requestId}` // Webhook URL
          }
        }
      };

      const headers: any = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      };
      if (apiKey) {
        headers['Authorization'] = `Bearer ${apiKey}`;
      }

      // Store pending request
      this.pendingResults.set(requestId, {
        requestId,
        toolName,
        params,
        timestamp: Date.now(),
        status: 'pending'
      });

      // Make initial request
      const response = await fetch(connection.messagesUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(mcpRequest),
        signal: AbortSignal.timeout(15000)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const responseText = await response.text();
      
      // If we get immediate results (synchronous tools), return them
      if (responseText !== "Accepted" && response.status !== 202) {
        try {
          const result = JSON.parse(responseText);
          if (result.result) {
            this.pendingResults.delete(requestId);
            return { success: true, result: this.formatMCPResult(result.result) };
          }
        } catch (e) {
          // Continue to polling if not valid JSON
        }
      }

      // For async workflows, start polling
      console.log(`MCP Proxy: Workflow accepted, starting result polling for request ${requestId}`);
      
      return await this.pollForResult(requestId, pollInterval, maxWaitTime);

    } catch (error: any) {
      this.pendingResults.delete(requestId);
      console.error('Enhanced MCP Proxy error:', error);
      return { success: false, error: error.message || 'Unknown proxy error' };
    }
  }

  private async pollForResult(
    requestId: string, 
    pollInterval: number, 
    maxWaitTime: number
  ): Promise<any> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < maxWaitTime) {
      // Check if result is in cache (from webhook callback)
      const cached = this.resultCache.get(requestId);
      if (cached && Date.now() - cached.timestamp < cached.ttl) {
        this.pendingResults.delete(requestId);
        this.resultCache.delete(requestId);
        return { success: true, result: cached.result };
      }

      // Check pending result status
      const pending = this.pendingResults.get(requestId);
      if (pending) {
        if (pending.status === 'completed' && pending.result) {
          this.pendingResults.delete(requestId);
          return { success: true, result: pending.result };
        } else if (pending.status === 'failed') {
          this.pendingResults.delete(requestId);
          return { success: false, error: pending.error || 'Workflow execution failed' };
        }
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    // Timeout reached
    this.pendingResults.delete(requestId);
    return { 
      success: false, 
      error: 'Workflow execution timeout - no results received within ' + (maxWaitTime / 1000) + ' seconds' 
    };
  }

  // Webhook endpoint to receive async results
  handleWebhookCallback(requestId: string, data: any): boolean {
    console.log(`MCP Proxy: Received webhook callback for request ${requestId}`);
    
    const pending = this.pendingResults.get(requestId);
    if (pending) {
      if (data.error) {
        pending.status = 'failed';
        pending.error = data.error;
      } else {
        pending.status = 'completed';
        pending.result = this.formatMCPResult(data.result || data);
      }
      
      // Also store in cache for immediate retrieval
      this.resultCache.set(requestId, {
        result: pending.result || data,
        timestamp: Date.now(),
        ttl: 60000 // 1 minute TTL
      });
      
      return true;
    }
    
    return false;
  }

  // Get or create connection (from existing proxy)
  private getOrCreateConnection(serverUrl: string, apiKey?: string): Promise<{ eventSource: EventSource; messagesUrl: string; lastActivity: number; }> {
    if (this.activeConnections.has(serverUrl)) {
        const existingConn = this.activeConnections.get(serverUrl)!;
        // Check if connection is still active
        if (Date.now() - existingConn.lastActivity < 60000) { // 1-minute timeout
            return existingConn.isReady.then(() => existingConn);
        }
        this.closeConnection(serverUrl); // Close expired connection
    }

    console.log(`MCP Proxy: Creating new SSE connection to ${serverUrl}`);
    
    let connectionResolve: () => void;
    let connectionReject: (error: Error) => void;
    
    const connectionPromise = new Promise<void>((resolve, reject) => {
        connectionResolve = resolve;
        connectionReject = reject;
    });

    const headers: any = { 'Cache-Control': 'no-cache', Connection: 'keep-alive' };
    if (apiKey) {
        headers['Authorization'] = `Bearer ${apiKey}`;
    }

    const eventSource = new EventSource(serverUrl);
    const connection = { 
        eventSource, 
        messagesUrl: '', 
        lastActivity: Date.now(), 
        isReady: connectionPromise 
    };
    
    // Setup enhanced event handlers
    this.setupEnhancedEventHandlers(eventSource, serverUrl);
    
    const timeout = setTimeout(() => {
        eventSource.close();
        connectionReject(new Error('SSE connection timed out after 10 seconds.'));
    }, 10000);

    eventSource.addEventListener('message', (event: any) => {
        const data = event.data;
        if (data && data.includes('/messages?sessionId=')) {
            connection.messagesUrl = new URL(data, serverUrl).toString();
            console.log(`MCP Proxy: Got session endpoint: ${connection.messagesUrl}`);
            clearTimeout(timeout);
            connectionResolve();
        }
    });

    eventSource.addEventListener('endpoint', (event: any) => {
        const data = event.data;
        if (data && data.includes('/messages?sessionId=')) {
            connection.messagesUrl = new URL(data, serverUrl).toString();
            console.log(`MCP Proxy: Got session endpoint from endpoint event: ${connection.messagesUrl}`);
            clearTimeout(timeout);
            connectionResolve();
        }
    });

    eventSource.addEventListener('error', (err: any) => {
        console.error('MCP Proxy: SSE connection error:', err);
        clearTimeout(timeout);
        eventSource.close();
        connectionReject(new Error('SSE connection failed. Check N8N workflow is active and URL is correct.'));
    });
    
    this.activeConnections.set(serverUrl, connection);
    return connectionPromise.then(() => connection);
  }

  // Enhanced SSE handler to listen for results
  private setupEnhancedEventHandlers(eventSource: EventSource, serverUrl: string) {
    // Listen for tool results
    eventSource.addEventListener('tool-result', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        if (data.requestId) {
          console.log(`MCP Proxy: Received tool result via SSE for request ${data.requestId}`);
          this.handleWebhookCallback(data.requestId, data);
        }
      } catch (e) {
        console.error('Failed to parse tool result:', e);
      }
    });

    // Listen for workflow completion events
    eventSource.addEventListener('workflow-complete', (event: any) => {
      try {
        const data = JSON.parse(event.data);
        if (data.requestId) {
          console.log(`MCP Proxy: Workflow completed for request ${data.requestId}`);
          this.handleWebhookCallback(data.requestId, data);
        }
      } catch (e) {
        console.error('Failed to parse workflow completion:', e);
      }
    });
  }

  private closeConnection(serverUrl: string) {
      if (this.activeConnections.has(serverUrl)) {
          console.log(`MCP Proxy: Closing connection to ${serverUrl}`);
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
    console.log('Enhanced MCP Proxy: Cleaning up all connections');
    const serverUrls = Array.from(this.activeConnections.keys());
    for (const serverUrl of serverUrls) {
      this.closeConnection(serverUrl);
    }
  }
}

export const enhancedN8NMCPProxy = new EnhancedN8NMCPProxy();