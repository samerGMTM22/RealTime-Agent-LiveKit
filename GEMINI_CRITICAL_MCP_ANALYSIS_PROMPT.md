# Critical MCP LiveKit Integration Analysis - Expert Consultation Request

## Problem Summary

Our LiveKit voice agent with MCP (Model Context Protocol) integration is experiencing critical failures that cause the agent to stop responding mid-conversation. While we successfully fixed the N8N search integration using your previous research, new issues have emerged that require expert analysis.

## Current Status

**✅ WORKING:**
- N8N MCP search integration (using `execute_web_search` tool name)
- Express API MCP proxy with proper "Accepted" response handling
- SSE connection establishment and session management
- Initial voice agent startup and configuration loading

**❌ FAILING:**
- Agent stops responding after function tool execution
- OpenAI Realtime API connection resets and timeouts
- Zapier MCP integration causes infinite connection loops
- Function tool execution triggers unwanted secondary function calls

## Detailed Error Analysis

### 1. Function Tool Execution Chain Issues

**Log Evidence:**
```
Agent: "FUNCTION ACTUALLY EXECUTED: search_web(healthy foods to eat in 2025)"
Agent: "Express API response: {'success': True, 'result': 'Search request accepted...'}"
Agent: "FUNCTION COMPLETED: Express API successful"
Agent: "FUNCTION ACTUALLY EXECUTED: send_email(to=[Placeholder Email], subject=Healthy Foods to Eat in 2025)"
```

**Problem:** After successfully executing the search function, the agent automatically triggers the email function without user request, creating an unwanted function chain.

### 2. Zapier MCP Connection Loop

**Log Evidence:**
```
Agent: "Establishing SSE connection to https://mcp.zapier.com/..."
[10 seconds later]
Agent: "Establishing SSE connection to https://mcp.zapier.com/..."
[10 seconds later]
Agent: "Establishing SSE connection to https://mcp.zapier.com/..."
```

**Problem:** The Zapier MCP client is stuck in an infinite connection retry loop, each attempt taking 10+ seconds and blocking the agent.

### 3. OpenAI Realtime API Failures

**Log Evidence:**
```
Error: "ClientConnectionResetError: Cannot write to closing transport"
Error: "RealtimeError: generate_reply timed out"
Error: "failed to update chat context before generating the function calls results"
```

**Problem:** The OpenAI Realtime API connection is being reset during function execution, causing the entire voice session to fail.

### 4. Agent Architecture Issues

**Current Implementation:**
```python
# agent.py - Current function tools
@function_tool
async def search_web(query: str) -> str:
    # Works correctly with Express API
    
@function_tool  
async def send_email(to: str, subject: str, body: str) -> str:
    # Causes SSE connection loops and blocks agent
```

## Technical Implementation Details

### Working N8N Integration
```typescript
// server/mcp_proxy.ts - WORKING
N8N MCP Proxy: Raw response: Accepted
N8N MCP Proxy: N8N workflow accepted the request - tool execution initiated
```

### Failing Zapier Integration
```python
# mcp_integration/simple_client.py - FAILING
def _handle_sse_mcp_call(self, tool_name: str, params: Dict[str, Any]):
    # Creates new SSE connection every call
    # No connection reuse or proper session management
    # Causes 10+ second delays per call
```

### Agent Configuration
```python
# Database agent config
{
    "name": "Voice Assistant",
    "type": "fitness-coach", 
    "instructions": "You are a certified fitness and wellness coach...",
    "voice": "echo",
    "temperature": 1.02
}
```

## Current Architecture

```
User Voice Input 
    ↓
LiveKit WebRTC
    ↓  
OpenAI Realtime API ←→ Function Tools
    ↓                      ↓
Voice Response         MCP Integration
                           ↓
                    Express API Proxy
                           ↓
                    N8N MCP (✅ Working)
                    Zapier MCP (❌ Failing)
```

## Specific Research Questions

### 1. Function Tool Execution Control
- How to prevent unwanted function call chains in OpenAI Realtime API?
- Should function tools be designed as single-shot operations?
- How to control when the agent decides to call multiple functions?

### 2. MCP Session Management Best Practices
- How should MCP SSE connections be pooled and reused in a voice agent context?
- What's the correct session lifecycle for Zapier MCP vs N8N MCP?
- Should we implement connection pooling at the Express API level?

### 3. OpenAI Realtime API Stability
- How to prevent connection resets during long-running function executions?
- What's the recommended timeout configuration for function tools?
- Should function execution be moved to a separate async context?

### 4. LiveKit Agent Error Recovery
- How to implement graceful error handling when MCP calls fail?
- Should the voice agent continue responding even if function tools fail?
- What's the best practice for handling partial function execution results?

## Expected Deliverables

1. **Corrected MCP integration architecture** that prevents connection loops
2. **Function tool execution strategy** that avoids unwanted call chains  
3. **Error handling patterns** for resilient voice agent operation
4. **Session management improvements** for both N8N and Zapier MCP servers
5. **OpenAI Realtime API configuration** that maintains stability during function execution

## Current Codebase Context

- **Express/Node.js backend** with working N8N MCP proxy
- **Python LiveKit agent** using OpenAI Realtime API
- **PostgreSQL database** with MCP server configurations
- **TypeScript/React frontend** for voice interface
- **Working N8N search** with `execute_web_search` tool name
- **Failing Zapier email** with SSE connection issues

The core challenge is maintaining voice agent responsiveness while executing potentially slow MCP function calls, especially when multiple tools are involved in a conversation flow.

Please provide specific code corrections and architectural improvements to resolve these critical issues while maintaining the working N8N search functionality.