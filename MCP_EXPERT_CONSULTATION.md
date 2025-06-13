# MCP (Model Context Protocol) Integration Expert Consultation

## Context & Objective

We have a working LiveKit OpenAI Realtime API voice agent and need to implement MCP (Model Context Protocol) server integration. The system should allow dynamic addition, deletion, and management of MCP servers through a persistent database, with real-time UI updates and automatic connection to the LiveKit agent.

## Current System Architecture

### Database Schema (Working)
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
```

### Storage Interface (Implemented)
```typescript
// server/storage.ts
export interface IStorage {
  getMcpServersByUserId(userId: number): Promise<McpServer[]>;
  createMcpServer(mcpServer: InsertMcpServer): Promise<McpServer>;
  updateMcpServer(id: number, mcpServer: Partial<InsertMcpServer>): Promise<McpServer | undefined>;
  deleteMcpServer(id: number): Promise<boolean>;
}
```

### Voice Agent Integration Point
```python
# agent.py - Current working voice agent
class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config
        # MCP servers should be loaded and connected here
```

## MCP Integration Requirements

### 1. Persistent MCP Server Management
- **Database Storage**: MCP servers stored in PostgreSQL with user association
- **CRUD Operations**: Full create, read, update, delete operations via API
- **Status Tracking**: Real-time connection status monitoring
- **Metadata Support**: Store server-specific configuration and capabilities

### 2. Dynamic Server Discovery and Connection
- **Auto-Discovery**: Detect available MCP servers at startup
- **Hot-Reload**: Add/remove servers without agent restart
- **Health Monitoring**: Continuous connection health checks
- **Error Recovery**: Automatic reconnection on failure

### 3. UI Integration Requirements
- **Real-time Status**: Live connection status indicators
- **Server Management**: Add/edit/delete MCP servers interface
- **Testing Interface**: Test server connections before activation
- **Capability Display**: Show available tools/functions per server

## Technical Questions for Expert

### A. MCP Protocol Implementation

**1. MCP Server Connection Pattern**
```python
# How should we implement MCP server connections in the LiveKit agent?
# Current agent structure:
class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config
        # Question: How to integrate MCP servers here?
        self.mcp_servers = []  # Load from database?
        
    @function_tool
    async def get_general_info(self):
        # Question: How to route function calls to appropriate MCP servers?
        pass
```

**Questions:**
- Should MCP servers be loaded in the `Assistant.__init__()` method?
- How do we handle dynamic server addition/removal during agent runtime?
- What's the recommended pattern for routing function calls to specific MCP servers?

**2. MCP Client Implementation**
```python
# How should we structure the MCP client manager?
class MCPManager:
    def __init__(self):
        self.connected_servers = {}
        self.server_capabilities = {}
    
    async def connect_server(self, server_config: dict):
        # Question: Proper MCP connection implementation?
        pass
    
    async def disconnect_server(self, server_id: int):
        # Question: Clean disconnect procedure?
        pass
    
    async def call_tool(self, server_id: int, tool_name: str, params: dict):
        # Question: How to make MCP tool calls?
        pass
```

**Questions:**
- What's the correct MCP client implementation pattern for Python?
- How do we handle MCP server authentication (API keys, tokens)?
- Should we use connection pooling or single connections per server?

### B. Database Integration Patterns

**3. Server State Synchronization**
```typescript
// How should we handle server state updates?
interface McpServerStatus {
  id: number;
  connectionStatus: 'connected' | 'disconnected' | 'error' | 'connecting';
  lastConnected: Date;
  capabilities: string[];
  errorMessage?: string;
}

// Questions:
// - How often should we update server status in database?
// - Should we use WebSocket for real-time UI updates?
// - How to handle concurrent status updates?
```

**4. User-Server Association**
```sql
-- Current schema allows user-specific MCP servers
-- Questions:
-- Should MCP servers be shared across users or user-specific?
-- How to handle permissions for shared servers?
-- Should we implement server groups or categories?
```

### C. LiveKit Agent Integration

**5. Function Tool Registration**
```python
# How to dynamically register MCP server functions as LiveKit function tools?
class Assistant(Agent):
    def __init__(self, config: dict) -> None:
        super().__init__()
        # Question: How to dynamically create @function_tool decorated methods?
        
    async def register_mcp_tools(self, mcp_servers: List[McpServer]):
        # Question: Dynamic tool registration pattern?
        for server in mcp_servers:
            for tool in server.capabilities:
                # How to create function_tool from MCP capability?
                pass
```

**Questions:**
- Can we dynamically register `@function_tool` methods at runtime?
- How do we handle tool name conflicts between different MCP servers?
- Should we prefix tool names with server identifiers?

**6. Agent Restart vs Hot-Reload**
```python
# When MCP servers are added/removed, should we:
# Option A: Restart the entire agent
# Option B: Hot-reload MCP connections only

# Question: Which approach is recommended for LiveKit agents?
# Question: How to implement hot-reload without breaking active conversations?
```

### D. UI/Frontend Integration

**7. Real-time Status Updates**
```typescript
// How should the frontend receive real-time MCP server status updates?
interface McpServerUI {
  id: number;
  name: string;
  url: string;
  status: 'connected' | 'disconnected' | 'error' | 'connecting';
  capabilities: string[];
  lastConnected: string;
  errorMessage?: string;
}

// Questions:
// - WebSocket connection for real-time updates?
// - Polling interval for status checks?
// - How to handle connection state changes in UI?
```

**8. Server Management Interface**
```typescript
// What should the MCP server management UI include?
interface McpServerForm {
  name: string;
  url: string;
  description?: string;
  apiKey?: string;
  authMethod: 'none' | 'api_key' | 'bearer_token';
  testConnection: boolean;
}

// Questions:
// - Should we test connections before saving?
// - How to handle different authentication methods?
// - Should we validate server capabilities during setup?
```

### E. Error Handling and Recovery

**9. Connection Failure Management**
```python
# How should we handle MCP server connection failures?
class MCPConnectionError(Exception):
    def __init__(self, server_id: int, error_message: str):
        self.server_id = server_id
        self.error_message = error_message

# Questions:
# - Retry policy for failed connections?
# - How to notify users of connection issues?
# - Should agent continue without failed MCP servers?
```

**10. Graceful Degradation**
```python
# When MCP servers are unavailable:
# - Should agent functions fall back to default responses?
# - How to communicate MCP unavailability to users?
# - Should we cache MCP responses for offline scenarios?
```

### F. Performance and Scalability

**11. Connection Management**
```python
# Questions about MCP connection performance:
# - Connection pooling strategies?
# - Timeout configurations for MCP calls?
# - How to handle slow MCP server responses?
# - Should we implement request queuing?
```

**12. Caching Strategy**
```python
# Should we cache MCP server responses?
# - Tool discovery results caching?
# - Function call result caching?
# - How to handle cache invalidation?
```

## Current Implementation Status

### ✅ Completed Components
- Database schema for MCP servers
- Storage interface for CRUD operations
- Basic API endpoints for server management
- Working LiveKit voice agent with OpenAI Realtime API

### ❌ Missing Components
- MCP client implementation in Python agent
- Dynamic tool registration from MCP servers
- Real-time status monitoring
- UI for MCP server management
- Connection health checking
- Error recovery mechanisms

### 🔧 Integration Points Needed
- MCP server loading in `Assistant.__init__()`
- Function tool registration from MCP capabilities
- Real-time status updates to database and UI
- WebSocket or polling for live status updates

## Specific Code Examples Needed

### 1. MCP Client Implementation
```python
# Need complete example of MCP client connection and tool calling
class MCPClient:
    async def connect(self, server_url: str, auth: dict) -> bool:
        # Complete implementation needed
        pass
    
    async def list_tools(self) -> List[dict]:
        # Get available tools from MCP server
        pass
    
    async def call_tool(self, tool_name: str, params: dict) -> dict:
        # Execute tool call on MCP server
        pass
```

### 2. Dynamic Tool Registration
```python
# How to convert MCP tool definitions to LiveKit function_tool decorators
def register_mcp_tool(self, mcp_tool_definition: dict):
    # Convert MCP tool to LiveKit function_tool
    # Need pattern for dynamic registration
    pass
```

### 3. Status Monitoring
```python
# Real-time connection status monitoring
class MCPStatusMonitor:
    async def monitor_servers(self, servers: List[McpServer]):
        # Continuous health checking
        # Database status updates
        # UI notification system
        pass
```

### 4. Frontend Integration
```typescript
// Real-time MCP server status component
const McpServerList = () => {
  // WebSocket connection for live updates
  // Server management interface
  // Connection testing functionality
};
```

## Request to Expert

Please provide specific guidance on:

1. **MCP Protocol Implementation**: Complete Python client implementation with authentication
2. **Dynamic Tool Registration**: Pattern for converting MCP tools to LiveKit function_tool
3. **Connection Management**: Best practices for MCP connection lifecycle
4. **Status Monitoring**: Real-time health checking and UI updates
5. **Error Recovery**: Robust error handling and reconnection strategies
6. **Performance Optimization**: Connection pooling, caching, and timeout strategies

Include working code examples that integrate with our existing LiveKit voice agent and database structure.

## Current Database Structure Reference

```sql
-- MCP Servers Table (Implemented)
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

-- Agent Configs Table (Working)
CREATE TABLE agent_configs (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  system_prompt TEXT,
  voice_model TEXT DEFAULT 'coral',
  temperature INTEGER DEFAULT 80,
  -- MCP integration fields needed here?
);
```

This consultation focuses on creating a production-ready MCP integration that works seamlessly with our existing LiveKit voice agent infrastructure.