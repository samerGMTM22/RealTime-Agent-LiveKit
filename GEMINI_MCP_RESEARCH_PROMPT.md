# MCP Integration Research Request for Gemini AI

## Overview
We're developing a LiveKit voice agent platform with dynamic Model Context Protocol (MCP) integration. The system is designed to allow voice agents to dynamically connect to various MCP servers (like N8N workflows, Zapier integrations, etc.) and use their tools during conversations.

## Application Architecture
- **Frontend**: React with LiveKit client for real-time voice communication
- **Backend**: Node.js/Express server with PostgreSQL database
- **Voice Agent**: Python LiveKit agent using OpenAI Realtime API
- **MCP Integration**: Dynamic server connections with tool discovery and execution

## The Core Problem
Despite implementing multiple approaches, our MCP integration consistently fails to execute tools successfully. The voice agent connects to MCP servers, establishes sessions, but tool execution always fails with various protocol and session management issues.

## What We've Built So Far

### 1. Database-Driven MCP Configuration
```sql
-- MCP servers table stores server configurations
CREATE TABLE mcp_servers (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  api_key TEXT,
  capabilities TEXT[], -- JSON array of available tools
  status TEXT DEFAULT 'active'
);
```

### 2. Multiple MCP Client Implementations
We've created several MCP client approaches:

**A) Python MCP Integration (`mcp_integration/simple_client.py`)**
- Handles both standard HTTP and SSE-based MCP servers
- Implements concurrent session management for N8N
- Uses threading to maintain SSE connections during JSON-RPC calls

**B) Node.js N8N MCP Proxy (`server/mcp_proxy.ts`)**
- Dedicated proxy for handling N8N's SSE protocol
- Manages persistent EventSource connections
- Implements session discovery and tool execution

**C) Express API MCP Routes (`server/routes.ts`)**
- REST endpoints for MCP server management
- Tool execution proxy with protocol detection
- Health monitoring and status reporting

### 3. Voice Agent Integration
The Python voice agent (`agent_working_mcp.py`) includes:
- Dynamic MCP server loading from database
- Module-level function tools for LiveKit integration
- Fallback mechanisms when MCP tools fail

## Specific Issues We Keep Encountering

### Issue 1: N8N SSE Protocol Complexity
**Problem**: N8N MCP servers use Server-Sent Events (SSE) that require:
1. GET request to SSE endpoint to establish session
2. Extract session URL from SSE stream
3. Use session URL for JSON-RPC tool calls

**Error Pattern**:
```
N8N MCP Proxy: SSE endpoint event: /mcp/43a3ec6f-728e-489b-9456-45f9d41750b7/messages?sessionId=xxx
N8N MCP Proxy: Got session endpoint from endpoint event: https://n8n.srv755489.hstgr.cloud/mcp/xxx/messages?sessionId=xxx
N8N MCP Proxy: Making JSON-RPC call to session endpoint
{"jsonrpc":"2.0","id":"req_xxx","error":{"code":-32603,"message":"Tool not found"}}
```

### Issue 2: Tool Discovery and Naming
**Problem**: Different MCP servers use different tool names for similar functionality.
- We try: `search`, `web_search`, `google_search`, `internet_search`
- Server responds: "Tool not found" for all attempts

### Issue 3: Session Management
**Problem**: SSE sessions timeout between establishment and tool execution.
**Error Pattern**:
```
401 No transport found for sessionId
SyntaxError: Unexpected token 'A', "Accepted" is not valid JSON
```

### Issue 4: Protocol Mismatches
**Problem**: Some MCP servers expect different request formats or protocols than what we're implementing.

## Code Examples of Our Current Implementation

### N8N MCP Proxy (TypeScript)
```typescript
async callN8NTool(serverUrl: string, toolName: string, params: any, apiKey?: string): Promise<any> {
  // Establish SSE connection
  const connection = await this.createN8NConnection(serverUrl, apiKey);
  
  // Extract session URL from SSE stream
  const eventSource = new EventSource(serverUrl, { headers });
  eventSource.addEventListener('endpoint', (event) => {
    const messagesUrl = new URL(event.data, serverUrl).toString();
    // Make JSON-RPC call to session endpoint
  });
}
```

### Voice Agent Tool Integration (Python)
```python
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    try:
        # Use Express API as proxy to MCP servers
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:5000/api/mcp/execute",
                json={"tool": "search", "params": {"query": query}}
            ) as response:
                result = await response.json()
                
        if result.get("success"):
            return result.get("result", "Search completed")
        else:
            return f"Search failed: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Search error: {str(e)}"
```

## Recent Test Results
When testing the voice agent with internet search functionality:

1. **SSE Connection Success**: N8N MCP proxy successfully establishes SSE connections
2. **Session Discovery Success**: Successfully extracts session URLs from SSE streams  
3. **JSON-RPC Communication Success**: Can send/receive JSON-RPC messages
4. **Tool Execution Failure**: All tool calls result in "Tool not found" errors

## What We Need Research Help With

### Primary Questions:
1. **N8N MCP Protocol**: What is the exact protocol specification for N8N's MCP implementation? Are we missing required headers, authentication, or request formatting?

2. **Tool Discovery**: How should we properly discover available tools on N8N MCP servers? Is there a `tools/list` method, or do we need to query capabilities differently?

3. **Session Management**: How long do N8N MCP SSE sessions remain active? Do we need to keep the EventSource connection open during tool execution?

4. **Request Format**: Are we using the correct JSON-RPC request format for N8N MCP servers? Should parameters be nested differently?

### Secondary Questions:
5. **Authentication**: Are there specific authentication requirements for N8N MCP servers beyond bearer tokens?

6. **Error Handling**: What do common N8N MCP error codes mean, and how should we handle them?

7. **Alternative Approaches**: Should we consider using WebSocket connections instead of SSE for N8N MCP integration?

8. **Tool Naming**: Is there a standard naming convention for MCP tools, or do we need server-specific mapping?

### Technical Deep-Dive Questions:
9. **Protocol Compliance**: Are we correctly implementing the MCP specification, or are there N8N-specific extensions we're missing?

10. **Connection Lifecycle**: What's the proper lifecycle for SSE connections with N8N MCP servers?

11. **Debugging**: What debugging techniques can help us understand exactly what N8N MCP servers expect?

12. **Examples**: Are there working examples of N8N MCP client implementations we can reference?

## Current Codebase Status
- ✅ SSE connection establishment works
- ✅ Session discovery works  
- ✅ JSON-RPC communication works
- ❌ Tool execution consistently fails
- ❌ Tool discovery not working
- ❌ Session management needs improvement

## Request for Gemini
Please analyze this MCP integration challenge and provide:
1. Specific technical solutions for N8N MCP protocol handling
2. Correct request formats and session management approaches
3. Tool discovery and naming strategies
4. Code examples or corrections to our current implementation
5. Alternative approaches if our current direction is flawed

The goal is to achieve reliable tool execution through MCP servers so our voice agents can perform internet searches, send emails, and execute other external tools during conversations.