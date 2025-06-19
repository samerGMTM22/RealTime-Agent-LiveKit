# LiveKit MCP Integration - Final Expert Consultation

## Current Status Summary

We have successfully implemented a LiveKit OpenAI Realtime API voice agent with MCP integration that shows function tools are executing, but the actual MCP server communication is failing. The agent is returning fallback success messages instead of real MCP responses.

## Console Evidence of Issue

### ✅ What's Working
```
Agent stdout: {"message": "MCP server Zapier send draft email marked as available"}
Agent stdout: {"message": "Connected to MCP server: Zapier send draft email"}
Agent stdout: {"message": "MCP server internet access marked as available"}
Agent stdout: {"message": "Connected to MCP server: internet access"}
Agent stdout: {"message": "Initialized 2 MCP servers"}
Agent stdout: {"message": "OpenAI Realtime API agent started successfully"}
```

### ✅ Function Tools Are Executing
```
Agent stdout: {"message": "FUNCTION ACTUALLY EXECUTED: search_web(breaking news from yesterday)"}
Agent stdout: {"message": "FUNCTION COMPLETED at 1749884416.1538794: MCP search successful"}
Agent stdout: {"message": "FUNCTION ACTUALLY EXECUTED: send_email(to=, subject=[Draft] Summary...)"}
Agent stdout: {"message": "FUNCTION COMPLETED at 1749884566.4416132: MCP email successful"}
```

### ❌ The Problem
The functions return generic success messages instead of actual MCP server responses. This indicates the global MCP manager is not properly accessible to the function tools.

## Code Architecture Analysis

### Current Module-Level Function Tools Implementation
```python
# Global MCP manager variable
_mcp_manager = None

@function_tool
async def search_web(query: str) -> str:
    """Search the web for current information using MCP internet access tools."""
    global _mcp_manager
    logger.info(f"FUNCTION ACTUALLY EXECUTED: search_web({query})")
    
    if _mcp_manager is None:
        logger.error("MCP manager not initialized")
        return "MCP integration not available. Please try again later."
    
    try:
        result = await _mcp_manager.execute_tool(
            server_name="internet access",
            tool_name="search",
            arguments={"query": query}
        )
        logger.info(f"Web search result: {result}")
        return result.get("content", "No results found")
    except Exception as e:
        logger.error(f"MCP search failed: {e}")
        return f"Search failed: {str(e)}"

@function_tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Zapier MCP integration."""
    global _mcp_manager
    logger.info(f"FUNCTION ACTUALLY EXECUTED: send_email(to={to})")
    
    if _mcp_manager is None:
        logger.error("MCP manager not initialized")
        return "Email service not available. Please try again later."
    
    try:
        result = await _mcp_manager.execute_tool(
            server_name="Zapier send draft email",
            tool_name="send_email",
            arguments={"to": to, "subject": subject, "body": body}
        )
        logger.info(f"Email send result: {result}")
        return "Email sent successfully"
    except Exception as e:
        logger.error(f"MCP email send failed: {e}")
        return f"Email send failed: {str(e)}"
```

### Current MCP Manager Initialization
```python
async def entrypoint(ctx: JobContext):
    # Initialize global MCP manager for module-level function tools
    global _mcp_manager
    logger.info("Initializing MCP integration...")
    _mcp_manager = SimpleMCPManager()
    
    try:
        mcp_servers = await _mcp_manager.initialize_user_servers(user_id=1)
        connected_count = len([s for s in mcp_servers if s.get("status") == "connected"])
        logger.info(f"Connected to {connected_count} MCP servers")
    except Exception as e:
        logger.error(f"Failed to initialize MCP servers: {e}")
        _mcp_manager = None

    # Create assistant with function tools passed to constructor
    assistant = Assistant(
        config=config, 
        tools=[search_web, send_email]  # Pass module-level function tools
    )
```

### MCP Manager Implementation (SimpleMCPManager)
```python
class SimpleMCPManager:
    def __init__(self):
        self.connected_servers = {}
        self.storage = None

    async def initialize_user_servers(self, user_id: int) -> List[Dict]:
        """Load and connect MCP servers for user"""
        try:
            # Connect to Express API to get MCP servers
            response = requests.get(f'http://localhost:5000/api/mcp/servers', timeout=10)
            if response.status_code == 200:
                servers_data = response.json()
                results = []
                
                for server_data in servers_data:
                    server_name = server_data.get("name", "Unknown")
                    logger.info(f"MCP server {server_name} marked as available")
                    
                    # Mock connection for now - this is the issue!
                    self.connected_servers[server_data["id"]] = {
                        "name": server_name,
                        "status": "connected"
                    }
                    logger.info(f"Connected to MCP server: {server_name}")
                    results.append({"status": "connected", "name": server_name})
                
                logger.info(f"Initialized {len(results)} MCP servers")
                return results
        except Exception as e:
            logger.error(f"Failed to initialize MCP servers: {e}")
            return []

    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool on a specific MCP server"""
        try:
            # This is returning mock responses instead of actual MCP calls!
            logger.info(f"FUNCTION COMPLETED at {time.time()}: MCP {tool_name} successful")
            return {"content": f"MCP {tool_name} successful", "success": True}
        except Exception as e:
            logger.error(f"MCP tool execution failed: {e}")
            return {"error": str(e), "success": False}
```

## Critical Issues Identified

### 1. Mock MCP Implementation
The `SimpleMCPManager.execute_tool()` method is returning hardcoded mock responses instead of making actual MCP server calls. This explains why we see "MCP search successful" instead of real search results.

### 2. Missing Actual MCP Protocol Implementation
The current implementation doesn't use the actual MCP protocol (JSON-RPC over stdio/HTTP). It needs to:
- Connect to real MCP servers using the Model Context Protocol
- Send properly formatted JSON-RPC requests
- Parse MCP server responses correctly

### 3. Server Connection Gap
While the logs show "Connected to MCP server", this is a mock connection. Real MCP servers (like the Zapier and internet access tools) are not being invoked.

## Questions for Expert

### 1. MCP Protocol Implementation
Given our current architecture, what is the correct way to implement actual MCP server communication in Python? Should we:
- Use the official MCP Python SDK?
- Implement JSON-RPC directly?
- Use existing MCP client libraries?

### 2. LiveKit Agent + MCP Integration Pattern
The current pattern is:
```
LiveKit Agent -> Global MCP Manager -> Module-Level Function Tools
```

Is this the recommended approach, or should we:
- Integrate MCP tools directly into the Agent class?
- Use a different design pattern for external tool integration?
- Implement MCP as a separate service?

### 3. Actual MCP Server Connection
Our current `SimpleMCPManager` is a mock. How should we:
- Connect to real MCP servers (Zapier, internet access)?
- Handle MCP server discovery and capabilities?
- Manage MCP server lifecycle within LiveKit agent context?

### 4. Code Samples Request
Could you provide a working code example of:
- Connecting to an MCP server from Python
- Executing an MCP tool and parsing the response
- Integrating this with LiveKit agent function tools

## Environment Details

- **LiveKit Agents**: 1.0.23
- **OpenAI Realtime API**: Working correctly
- **Function Tools**: Executing successfully (but with mock MCP responses)
- **MCP Servers**: Zapier (email) and Internet Access
- **Architecture**: Python agent with Express.js backend

## Request

Please provide specific guidance on replacing our mock `SimpleMCPManager` with actual MCP protocol implementation that can connect to real MCP servers and return genuine responses to the LiveKit agent function tools.

The agent framework is working perfectly - we just need the final piece to make real MCP calls instead of mock responses.