# LiveKit MCP Integration Implementation Analysis

## Current Issue Summary

The expert consultation revealed the core problem and provided a solution, but implementation hit a LiveKit API compatibility issue.

### What We Learned from Expert Consultation

**Root Cause Identified**: Function tool conflicts between class method decorators and module-level definitions
- Agent was appearing to use tools but they weren't actually executing on MCP servers
- OpenAI Realtime API was using fallback implementations instead of actual MCP integration
- Mixed incompatible patterns: Agent class methods vs. module-level function tools

**Expert's Recommended Solution**: Use module-level function tools with global MCP manager access

### Implementation Attempt

Following expert advice, we implemented:
1. Module-level function tools with `@function_tool` decorator
2. Global `_mcp_manager` variable accessible by function tools  
3. Removed class method function tool duplicates
4. Updated entrypoint to use `assistant.add_function()` method

### Current Console Error Analysis

**Critical Error from Console**:
```
Agent stdout: {"message": "Realtime API failed: 'Assistant' object has no attribute 'add_function'", "level": "ERROR"}
```

**What's Working**:
- ✅ MCP server connections successful: "Connected to MCP server: Zapier send draft email" + "internet access"
- ✅ Global MCP manager initialization: "Initialized 2 MCP servers"
- ✅ System prompt loading correctly: "You are a professional customer service agent..."
- ✅ LiveKit worker registration and room connection
- ✅ Fallback to STT-LLM-TTS pipeline working: "STT-LLM-TTS pipeline started successfully"

**The Problem**: 
LiveKit's `Agent` class in version 1.0.23 doesn't have an `add_function()` method. The expert's solution assumed a different API structure.

## Current Architecture State

### Module-Level Function Tools (Correctly Implemented)
```python
@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    global _mcp_manager
    # Implementation with enhanced debugging logs
    
@function_tool  
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Zapier MCP integration."""
    global _mcp_manager
    # Implementation with enhanced debugging logs
```

### Global MCP Manager (Working)
- Successfully connects to 2 MCP servers (Zapier + internet access)
- Accessible via global `_mcp_manager` variable
- Enhanced debugging logs to trace actual execution

### Agent Class (API Issue)
```python
class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        super().__init__(instructions=system_prompt)
        self.config = config
```

**The `add_function()` method doesn't exist on this Agent class.**

## Questions for Expert Direction

### 1. LiveKit Agent API Compatibility
Given that `Agent.add_function()` doesn't exist in LiveKit 1.0.23, what is the correct method to register module-level function tools with an Agent instance?

### 2. Alternative Function Tool Registration Patterns
Should we:
- Pass function tools to the AgentSession instead of Agent?
- Use a different Agent class that supports function tools?
- Override the Agent class to add function tool support?
- Use a completely different integration pattern?

### 3. OpenAI Realtime API Function Tool Integration
The expert mentioned MultimodalAgent with FunctionContext, but that wasn't available in our LiveKit version. What's the correct pattern for registering external function tools with OpenAI Realtime API in LiveKit 1.0.23?

### 4. MCP Integration Architecture
Our current setup:
- Module-level function tools ✅
- Global MCP manager ✅  
- MCP server connections working ✅
- Function tool registration broken ❌

How should we bridge the gap between working MCP integration and LiveKit function tool system?

## Console Evidence

### Successful MCP Integration
```
Agent stdout: {"message": "MCP server Zapier send draft email marked as available"}
Agent stdout: {"message": "Connected to MCP server: Zapier send draft email"}
Agent stdout: {"message": "MCP server internet access marked as available"}
Agent stdout: {"message": "Connected to MCP server: internet access"}
Agent stdout: {"message": "Initialized 2 MCP servers"}
```

### Function Tool Registration Failure
```
Agent stdout: {"message": "Realtime API failed: 'Assistant' object has no attribute 'add_function'"}
Agent stdout: {"message": "Falling back to STT-LLM-TTS pipeline"}
```

### Fallback Working
```
Agent stdout: {"message": "STT-LLM-TTS pipeline started successfully"}
```

## Current Status

- **MCP Integration**: ✅ Working (2 servers connected)
- **Module-Level Function Tools**: ✅ Implemented correctly
- **Global MCP Manager**: ✅ Accessible by function tools
- **LiveKit Agent**: ❌ API incompatibility with function tool registration
- **Voice Conversation**: ✅ Working (fallback pipeline)
- **Tool Execution**: ❌ Blocked by registration issue

## Request for Expert Guidance

Please provide specific direction on the correct LiveKit 1.0.23 API pattern for:
1. Registering module-level function tools with Agent instances
2. Ensuring OpenAI Realtime API can access and execute these tools
3. Maintaining our working MCP integration architecture

The core function tool conflict issue has been resolved per your guidance, but we need the correct LiveKit API pattern to complete the implementation.