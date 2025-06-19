# LiveKit MCP Integration - Final Step Expert Consultation

## Current Development Status

We have successfully implemented a LiveKit OpenAI Realtime API voice agent with MCP (Model Context Protocol) integration for dynamic tool management. The agent is now very close to full functionality but has one remaining critical issue.

### What's Working ✅

1. **System Prompt Configuration**: Agent correctly loads and uses detailed system prompt from database ("professional customer service agent")
2. **MCP Server Detection**: Successfully connects to 2 MCP servers (Zapier email and internet access)
3. **Tool Registration**: MCP tools are properly registered as LiveKit function tools with `@function_tool` decorators
4. **Agent Initialization**: No import errors, clean startup, proper LiveKit worker registration
5. **Voice Conversation**: Agent can engage in voice conversations using OpenAI Realtime API

### Console Evidence from Latest Run

```
Agent stdout: {"message": "Connected to 2 MCP servers", "level": "INFO", "name": "voice-agent"}
Agent stdout: {"message": "Registering MCP tool: send_email from server Zapier send draft email", "level": "INFO", "name": "voice-agent"}
Agent stdout: {"message": "Registering MCP tool: search from server internet access", "level": "INFO", "name": "voice-agent"}
Agent stdout: {"message": "Stored 2 MCP tool mappings", "level": "INFO", "name": "voice-agent"}
Agent stdout: {"message": "Loaded and registered 2 MCP tools", "level": "INFO", "name": "voice-agent"}
Agent stdout: {"message": "OpenAI Realtime API agent started successfully", "level": "INFO", "name": "voice-agent"}
Agent stdout: {"message": "Searching web for: latest announcement by Anthropic", "level": "INFO", "name": "voice-agent"}
Agent stdout: {"message": "Sending email to: [Recipient's Email]", "level": "INFO", "name": "voice-agent"}
```

### Critical Issue ❌

**The agent appears to be using tools but they're not actually executing on the MCP servers.** The agent logs show it's "searching" and "sending emails" but there are no corresponding MCP API calls or tool executions on the server side. The agent seems to be hallucinating tool usage results.

## Current Implementation Architecture

### Agent Structure (agent.py)
```python
class Assistant(Agent):
    @function_tool
    async def search_web(self, query: str):
        """Search the web for current information using MCP internet access tools."""
        # Implementation with MCP manager calls
    
    @function_tool 
    async def send_email(self, to: str, subject: str, body: str):
        """Send an email via Zapier MCP integration."""
        # Implementation with MCP manager calls
```

### MCP Integration (mcp_integration/simple_client.py)
- SimpleMCPClient: Basic HTTP client for MCP servers
- SimpleMCPManager: Manages multiple MCP server connections
- Express API fallback: `/api/mcp/execute` endpoint for tool execution

## Expert Questions

Based on LiveKit official documentation and OpenAI Realtime API integration patterns:

1. **Function Tool Registration**: Are we correctly registering MCP tools as LiveKit function tools that the OpenAI Realtime API can properly invoke?

2. **Tool Execution Context**: When OpenAI Realtime API calls a `@function_tool` decorated method in a LiveKit agent, does the execution happen in the agent process context where MCP connections are available?

3. **Async Context Issues**: Could there be async context isolation preventing the function tools from accessing the agent's MCP manager instance?

4. **LiveKit Agent Framework**: What is the proper pattern for external tool integration in LiveKit agents using the OpenAI Realtime API according to official documentation?

5. **Debugging Tool Calls**: How can we verify that OpenAI is actually calling our function tools vs. generating responses that appear to use tools?

## Technical Context

- **LiveKit Version**: 1.0.23
- **Framework**: OpenAI Realtime API with LiveKit agents
- **Language**: Python 3.11
- **Integration**: MCP servers via HTTP/WebSocket
- **Platform**: Replit environment

## Request to Expert

Please search LiveKit's official documentation, GitHub repositories, and examples to provide guidance on:

1. The correct pattern for integrating external APIs/tools with LiveKit OpenAI Realtime API agents
2. Common pitfalls in function tool registration that could cause tools to appear available but not execute
3. Official examples of similar integrations in the LiveKit ecosystem
4. Debugging techniques for verifying actual tool execution vs. hallucinated responses

**Only provide solutions based on official LiveKit sources and documentation.**