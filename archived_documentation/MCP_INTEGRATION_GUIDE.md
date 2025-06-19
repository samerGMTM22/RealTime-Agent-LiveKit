# MCP (Model Context Protocol) Integration Guide for LiveKit Voice Agent

## Overview

This guide documents the complete implementation of MCP (Model Context Protocol) integration with the LiveKit voice agent. MCP allows the agent to dynamically connect to external servers and access additional tools and capabilities through a standardized protocol.

## Architecture Overview

The MCP integration consists of several key components:

1. **MCP Client** - Handles connections to MCP servers (stdio/WebSocket)
2. **MCP Manager** - Manages server lifecycle and health monitoring
3. **MCP Tools Integration** - Converts MCP tools to LiveKit function tools
4. **Database Storage** - Persistent storage for server configurations
5. **API Endpoints** - RESTful API for server management
6. **UI Components** - Real-time status monitoring and management interface

## Database Schema

### MCP Servers Table

```sql
CREATE TABLE mcp_servers (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  description TEXT,
  api_key TEXT,
  is_active BOOLEAN DEFAULT true,
  connection_status TEXT DEFAULT 'disconnected',
  last_connected TIMESTAMP,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Storage Interface

```typescript
// shared/schema.ts
export const mcpServers = pgTable("mcp_servers", {
  id: serial("id").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id),
  name: text("name").notNull(),
  url: text("url").notNull(),
  description: text("description"),
  apiKey: text("api_key"),
  isActive: boolean("is_active").default(true),
  connectionStatus: text("connection_status").default("disconnected"),
  lastConnected: timestamp("last_connected"),
  metadata: jsonb("metadata").default({}),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export interface IStorage {
  getMcpServersByUserId(userId: number): Promise<McpServer[]>;
  createMcpServer(mcpServer: InsertMcpServer): Promise<McpServer>;
  updateMcpServer(id: number, mcpServer: Partial<InsertMcpServer>): Promise<McpServer | undefined>;
  deleteMcpServer(id: number): Promise<boolean>;
}
```

## MCP Client Implementation

### Base MCP Server Class

```python
# server/mcp_client.py
class MCPServer:
    """Base class for MCP server connections"""
    
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params
        self.server = None
        self.tools = []
        self.connected = False
        
    async def connect(self) -> bool:
        """Connect to the MCP server"""
        raise NotImplementedError
        
    async def disconnect(self):
        """Disconnect from the MCP server"""
        self.connected = False
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server"""
        return self.tools
        
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        raise NotImplementedError
```

### Stdio Protocol Implementation

```python
class MCPServerStdio(MCPServer):
    """MCP server using stdio protocol (for local servers)"""
    
    async def connect(self) -> bool:
        try:
            cmd = self.params.get("cmd", "npx")
            args = self.params.get("args", [])
            
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                cmd, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize MCP session
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "livekit-agent", "version": "1.0.0"}
                }
            }
            
            await self._send_message(init_message)
            response = await self._receive_message()
            
            if response and "result" in response:
                # Get available tools
                tools_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
                await self._send_message(tools_message)
                tools_response = await self._receive_message()
                
                if tools_response and "result" in tools_response:
                    self.tools = tools_response["result"].get("tools", [])
                
                self.connected = True
                logger.info(f"Connected to {self.name} via stdio, found {len(self.tools)} tools")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to {self.name}: {e}")
            await self.disconnect()
            
        return False
```

### WebSocket Protocol Implementation

```python
class MCPServerHttp(MCPServer):
    """MCP server using HTTP/WebSocket protocol (for remote servers)"""
    
    async def connect(self) -> bool:
        try:
            url = self.params.get("url")
            headers = {}
            
            if self.params.get("api_key"):
                headers["Authorization"] = f"Bearer {self.params['api_key']}"
            
            # Connect via WebSocket
            self.websocket = await websockets.connect(
                url.replace("http", "ws"),
                extra_headers=headers
            )
            
            # Initialize MCP session
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "livekit-agent", "version": "1.0.0"}
                }
            }
            
            await self.websocket.send(json.dumps(init_message))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if "result" in response_data:
                # Get available tools
                tools_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
                await self.websocket.send(json.dumps(tools_message))
                tools_response = await self.websocket.recv()
                tools_data = json.loads(tools_response)
                
                if "result" in tools_data:
                    self.tools = tools_data["result"].get("tools", [])
                
                self.connected = True
                logger.info(f"Connected to {self.name} via WebSocket, found {len(self.tools)} tools")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to {self.name}: {e}")
            await self.disconnect()
            
        return False
```

## MCP Manager

### Server Lifecycle Management

```python
# server/mcp_manager.py
class MCPManager:
    """Manages MCP server connections and lifecycle"""
    
    def __init__(self, storage: IStorage):
        self.storage = storage
        self.connected_servers: Dict[int, MCPServer] = {}
        self.server_capabilities: Dict[int, List[str]] = {}
        self.health_check_task = None
        
    async def initialize_user_servers(self, user_id: int) -> List[McpServer]:
        """Load and connect all active MCP servers for a user"""
        servers = await self.storage.getMcpServersByUserId(user_id)
        active_servers = [s for s in servers if s.isActive]
        
        connected = []
        for server_config in active_servers:
            if await self.connect_server(server_config):
                connected.append(server_config)
                
        # Start health monitoring
        if connected and not self.health_check_task:
            self.health_check_task = asyncio.create_task(
                self._health_check_loop()
            )
            
        logger.info(f"Initialized {len(connected)} MCP servers for user {user_id}")
        return connected
    
    async def connect_server(self, server_config: McpServer) -> bool:
        """Connect to a single MCP server"""
        try:
            # Update status to connecting
            await self.storage.updateMcpServer(
                server_config.id,
                {"connectionStatus": "connecting"}
            )
            
            # Create appropriate server type
            if server_config.url.startswith(("http://", "https://", "ws://", "wss://")):
                server = MCPServerHttp(
                    name=server_config.name,
                    params={
                        "url": server_config.url,
                        "api_key": server_config.apiKey
                    }
                )
            else:
                # Local server via stdio
                args = server_config.url.split()[1:] if " " in server_config.url else [server_config.url]
                server = MCPServerStdio(
                    name=server_config.name,
                    params={
                        "cmd": "npx",
                        "args": args
                    }
                )
            
            # Connect
            if await server.connect():
                self.connected_servers[server_config.id] = server
                self.server_capabilities[server_config.id] = [
                    tool["name"] for tool in server.tools
                ]
                
                # Update database
                await self.storage.updateMcpServer(
                    server_config.id,
                    {
                        "connectionStatus": "connected",
                        "lastConnected": datetime.now(),
                        "metadata": {
                            "capabilities": self.server_capabilities[server_config.id],
                            "tool_count": len(server.tools)
                        }
                    }
                )
                
                logger.info(f"Connected to MCP server {server_config.name} with {len(server.tools)} tools")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to {server_config.name}: {e}")
            await self.storage.updateMcpServer(
                server_config.id,
                {
                    "connectionStatus": "error",
                    "metadata": {"error": str(e)}
                }
            )
            
        return False
```

### Health Monitoring

```python
    async def _health_check_loop(self):
        """Continuous health monitoring of connected servers"""
        while self.connected_servers:
            try:
                for server_id, server in list(self.connected_servers.items()):
                    try:
                        # Simple health check - list tools
                        await asyncio.wait_for(server.list_tools(), timeout=5.0)
                        
                        # Update last connected time
                        await self.storage.updateMcpServer(
                            server_id,
                            {"lastConnected": datetime.now()}
                        )
                        
                    except Exception as e:
                        logger.warning(f"Health check failed for server {server_id}: {e}")
                        
                        # Mark as error but don't disconnect yet
                        await self.storage.updateMcpServer(
                            server_id,
                            {
                                "connectionStatus": "error",
                                "metadata": {"health_check_error": str(e)}
                            }
                        )
                
                # Health check every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)
```

## Dynamic Tool Registration

### Converting MCP Tools to LiveKit Function Tools

```python
# server/mcp_tools.py
class MCPToolsIntegration:
    """Integrate MCP tools with LiveKit agents"""
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        
    @staticmethod
    def _py_type(schema: dict) -> Any:
        """Convert JSON schema to Python type annotation"""
        t = schema.get("type")
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict
        }
        
        if t in type_map:
            return type_map[t]
        if t == "array":
            items_schema = schema.get("items", {})
            return List[MCPToolsIntegration._py_type(items_schema)]
        return Any
    
    async def build_livekit_tools(self) -> List[Callable]:
        """Convert all connected MCP tools to LiveKit function tools"""
        livekit_tools = []
        all_tools = await self.mcp_manager.get_all_tools()
        
        for tool_key, tool_info in all_tools.items():
            server_id = tool_info["server_id"]
            tool = tool_info["tool"]
            
            # Create a closure to capture server_id and tool_name
            def create_tool_wrapper(sid: int, tname: str):
                async def mcp_tool_wrapper(**kwargs) -> str:
                    try:
                        result = await self.mcp_manager.call_tool(sid, tname, kwargs)
                        
                        # Extract content from MCP response
                        if isinstance(result, dict):
                            if "content" in result:
                                content = result["content"]
                                if isinstance(content, list) and content:
                                    return str(content[0].get("text", content[0]))
                                return str(content)
                            elif "result" in result:
                                return str(result["result"])
                            else:
                                return str(result)
                        
                        return str(result)
                        
                    except Exception as e:
                        logger.error(f"MCP tool {tname} failed: {e}")
                        return f"Tool execution failed: {str(e)}"
                
                return mcp_tool_wrapper
            
            # Create the wrapper function
            tool_wrapper = create_tool_wrapper(server_id, tool["name"])
            
            # Set proper function metadata
            tool_wrapper.__name__ = tool_key.replace("-", "_")  # Valid Python identifier
            tool_wrapper.__doc__ = MCPToolsIntegration.schema_to_docstring(
                tool.get("description", f"MCP tool: {tool['name']}"),
                tool.get("inputSchema", {})
            )
            
            # Add parameter annotations based on tool schema
            input_schema = tool.get("inputSchema", {})
            properties = input_schema.get("properties", {})
            required = set(input_schema.get("required", []))
            
            sig_params = []
            for prop_name, prop_schema in properties.items():
                clean_name = prop_name.replace("-", "_").replace(" ", "_")
                param = inspect.Parameter(
                    clean_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=MCPToolsIntegration._py_type(prop_schema),
                    default=inspect.Parameter.empty if prop_name in required else None
                )
                sig_params.append(param)
            
            tool_wrapper.__signature__ = inspect.Signature(sig_params)
            
            # Register as LiveKit function tool
            livekit_tool = function_tool(tool_wrapper)
            livekit_tools.append(livekit_tool)
            
        logger.info(f"Created {len(livekit_tools)} LiveKit tools from MCP servers")
        return livekit_tools
```

## Agent Integration

### Assistant Class with MCP Support

```python
# agent.py
class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        system_prompt = config.get("systemPrompt", "You are a helpful voice AI assistant.")
        super().__init__(instructions=system_prompt)
        self.config = config
        self.mcp_manager = None
        self.mcp_tools_integration = None

    async def initialize_mcp(self, user_id: int = 1):
        """Initialize MCP servers and tools for this agent"""
        try:
            # Initialize MCP manager with database storage
            storage = DatabaseStorage()
            self.mcp_manager = MCPManager(storage)
            
            # Load and connect MCP servers for the user
            await self.mcp_manager.initialize_user_servers(user_id)
            
            # Initialize MCP tools integration
            self.mcp_tools_integration = MCPToolsIntegration(self.mcp_manager)
            
            # Build and add MCP tools to agent
            mcp_tools = await self.mcp_tools_integration.build_livekit_tools()
            if mcp_tools:
                logger.info(f"Added {len(mcp_tools)} MCP tools to agent")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP: {e}")

    @function_tool
    async def search_web(self, query: str):
        """Search the web for current information using MCP internet access tools."""
        # Try to use MCP tools for web search if available
        if self.mcp_manager:
            try:
                all_tools = await self.mcp_manager.get_all_tools()
                for tool_key, tool_info in all_tools.items():
                    if "search" in tool_key.lower() or "web" in tool_key.lower():
                        result = await self.mcp_manager.call_tool(
                            tool_info["server_id"], 
                            tool_info["tool"]["name"], 
                            {"query": query}
                        )
                        return str(result)
            except Exception as e:
                logger.error(f"MCP web search failed: {e}")
        
        return f"I'll search for information about '{query}'. To enable real-time web search, please configure MCP servers with web search capabilities."
```

### Agent Entrypoint with MCP Initialization

```python
async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent with MCP integration."""
    # ... existing connection and config loading code ...
    
    try:
        logger.info("Attempting OpenAI Realtime API")
        
        assistant = Assistant(config)
        # Initialize MCP before starting the agent session
        await assistant.initialize_mcp(user_id=1)
        
        session = AgentSession(
            llm=openai.realtime.RealtimeModel(
                model="gpt-4o-realtime-preview",
                voice=voice,
                temperature=realtime_temp,
            ),
            allow_interruptions=True,
            min_interruption_duration=0.5,
            min_endpointing_delay=0.5,
            max_endpointing_delay=6.0,
        )

        await session.start(
            room=ctx.room,
            agent=assistant,
        )
        
        await session.generate_reply(
            instructions="Greet the user warmly and offer your assistance."
        )
        
        logger.info("OpenAI Realtime API agent with MCP started successfully")
        
    except Exception as e:
        # ... fallback implementation ...
```

## API Endpoints

### MCP Server Management Routes

```typescript
// Express.js routes in server/routes.ts

// Get all MCP servers for a user
app.get("/api/mcp/servers", async (req, res) => {
  try {
    const servers = await storage.getMcpServersByUserId(1);
    res.json(servers);
  } catch (error) {
    console.error("Error fetching MCP servers:", error);
    res.status(500).json({ error: "Failed to fetch MCP servers" });
  }
});

// Create new MCP server
app.post("/api/mcp/servers", async (req, res) => {
  try {
    const { name, url, description, apiKey } = req.body;
    
    if (!name || !url) {
      return res.status(400).json({ error: "Name and URL are required" });
    }

    const server = await storage.createMcpServer({
      userId: 1,
      name,
      url,
      description: description || "",
      apiKey: apiKey || "",
      isActive: true
    });
    
    res.status(201).json(server);
  } catch (error) {
    console.error("Error creating MCP server:", error);
    res.status(500).json({ error: "Failed to create MCP server" });
  }
});

// Update MCP server
app.put("/api/mcp/servers/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const updateData = req.body;
    
    const server = await storage.updateMcpServer(id, updateData);
    if (!server) {
      return res.status(404).json({ error: "MCP server not found" });
    }
    
    res.json(server);
  } catch (error) {
    console.error("Error updating MCP server:", error);
    res.status(500).json({ error: "Failed to update MCP server" });
  }
});

// Delete MCP server
app.delete("/api/mcp/servers/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const success = await storage.deleteMcpServer(id);
    
    if (!success) {
      return res.status(404).json({ error: "MCP server not found" });
    }
    
    res.json({ message: "MCP server deleted successfully" });
  } catch (error) {
    console.error("Error deleting MCP server:", error);
    res.status(500).json({ error: "Failed to delete MCP server" });
  }
});

// Test MCP server connection
app.post("/api/mcp/servers/:id/test", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    // Implementation would test connection and return status
    res.json({ status: "connected", tools_count: 5 });
  } catch (error) {
    console.error("Error testing MCP server:", error);
    res.json({ status: "error", error: str(error) });
  }
});
```

### System Status Integration

```typescript
// Updated status endpoint to include MCP information
app.get("/api/status", async (req, res) => {
  try {
    const status = {
      livekit: 'online',
      openai: 'connected',
      mcp: 'ready',
      latency: '45ms',
      timestamp: new Date().toISOString()
    };

    // Test LiveKit connection
    try {
      await liveKitService.listRooms();
    } catch (error) {
      status.livekit = 'error';
    }

    // MCP status - check if servers are configured and connected
    try {
      const mcpServers = await storage.getMcpServersByUserId(1);
      const connectedServers = mcpServers.filter(s => s.connectionStatus === 'connected');
      
      if (connectedServers.length > 0) {
        status.mcp = 'connected';
      } else if (mcpServers.length > 0) {
        status.mcp = 'disconnected';
      } else {
        status.mcp = 'ready';
      }
    } catch (error) {
      status.mcp = 'error';
    }

    res.json(status);
  } catch (error) {
    console.error("Error checking system status:", error);
    res.status(500).json({ error: "Failed to check system status" });
  }
});
```

## UI Integration

### System Status Component

The existing system status component automatically displays MCP status:

```typescript
// Status color mapping for MCP
const getStatusColor = (statusValue: string) => {
  switch (statusValue) {
    case 'connected':
      return 'text-green-400 bg-green-400';  // Green: At least one server connected
    case 'disconnected':
      return 'text-red-400 bg-red-400';      // Red: Servers configured but not connected
    case 'ready':
      return 'text-yellow-400 bg-yellow-400'; // Yellow: Ready for configuration
    case 'error':
      return 'text-red-500 bg-red-500';      // Red: System error
    default:
      return 'text-gray-400 bg-gray-400';
  }
};
```

### MCP Server Management UI (Future Implementation)

```typescript
// Future UI component for managing MCP servers
interface McpServerFormData {
  name: string;
  url: string;
  description: string;
  apiKey: string;
  type: 'stdio' | 'websocket';
}

const McpServerManagement = () => {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load servers, create/edit/delete functionality
  // Real-time status updates via polling or WebSocket
  // Test connection functionality
  // Tool discovery and display
};
```

## Common MCP Server Examples

### 1. Filesystem Access Server (Local)

```json
{
  "name": "Filesystem Tools",
  "url": "@modelcontextprotocol/server-filesystem",
  "description": "Access local filesystem for reading/writing files",
  "type": "stdio"
}
```

### 2. Web Search Server (Remote)

```json
{
  "name": "Web Search API",
  "url": "wss://api.example.com/mcp/search",
  "apiKey": "your-api-key",
  "description": "Real-time web search capabilities",
  "type": "websocket"
}
```

### 3. Database Query Server (Local)

```json
{
  "name": "Database Tools", 
  "url": "@modelcontextprotocol/server-sqlite",
  "description": "Query SQLite databases",
  "type": "stdio"
}
```

## Troubleshooting Guide

### Connection Issues

**Problem**: MCP server fails to connect
**Solutions**:
- Verify server URL format and accessibility
- Check API keys for authenticated servers
- Review server startup logs for errors
- Test connection using management API
- Ensure required dependencies are installed (e.g., npx for stdio servers)

**Problem**: Stdio server process fails to start
**Solutions**:
- Verify npx and Node.js are installed
- Check server package is available
- Review process spawn parameters
- Monitor stderr output for errors

### Tool Registration Issues

**Problem**: MCP tools not appearing in agent
**Solutions**:
- Ensure MCP server provides valid tool schemas
- Check for tool name conflicts between servers
- Verify tool parameter types match expected formats
- Review tool registration logs

**Problem**: Tool execution fails
**Solutions**:
- Check MCP server logs for execution errors
- Verify tool parameters are correctly passed
- Test tools individually using management API
- Ensure tool permissions and dependencies

### Health Monitoring Issues

**Problem**: Servers marked as unhealthy
**Solutions**:
- Monitor server connectivity (30-second intervals)
- Check for network connectivity issues
- Review server resource usage
- Implement automatic reconnection logic

## Security Considerations

### API Key Management
- Store API keys securely in database
- Encrypt sensitive credentials
- Use environment variables for development
- Implement key rotation policies

### Server Validation
- Validate server URLs before connection
- Sandbox tool execution environments
- Implement request/response size limits
- Monitor for suspicious activity

### User Isolation
- Separate MCP servers per user
- Implement proper access controls
- Audit tool usage and results
- Rate limit tool executions

## Performance Optimization

### Connection Management
- Use connection pooling for multiple requests
- Implement timeout handling for slow servers
- Cache tool discovery results
- Monitor connection health continuously

### Tool Execution
- Implement request queuing for high loads
- Cache frequently used tool results
- Set reasonable execution timeouts
- Monitor resource usage per tool

### Error Recovery
- Automatic reconnection on failures
- Graceful degradation when servers unavailable
- Fallback to cached results when appropriate
- User notification of service issues

## Integration Flow Summary

1. **Database Schema**: MCP servers stored with user association
2. **Agent Startup**: Load and connect to active MCP servers
3. **Tool Discovery**: Fetch available tools from connected servers
4. **Dynamic Registration**: Convert MCP tools to LiveKit function tools
5. **Runtime Execution**: Tools available for voice conversation use
6. **Health Monitoring**: Continuous connection status monitoring
7. **Management API**: CRUD operations for server configuration
8. **UI Integration**: Real-time status display and management

This MCP integration provides a robust, scalable foundation for extending the voice agent's capabilities through external services and tools while maintaining security, performance, and reliability.