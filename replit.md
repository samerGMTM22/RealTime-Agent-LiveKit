# LiveKit Voice Agent Platform with MCP Integration

## Project Overview

An advanced voice agent platform that integrates LiveKit WebRTC, OpenAI Realtime API, and Model Context Protocol (MCP) for intelligent, adaptive conversational experiences. The system provides real-time voice conversations with web search capabilities and extensible MCP server integration.

## Recent Changes (January 25, 2025)

### ✅ FINAL FIX: MCP Integration Working with HTTP Proxy Architecture

**Critical Discovery (2:17 PM)**:
- N8N and Zapier endpoints return 404/405 errors for MCP SSE protocol
- These are HTTP API endpoints, not standard MCP SSE servers
- Our backend HTTP proxy (working all along) successfully executes tools
- Voice agent properly calls tools, but SSE connection failures were causing confusion

**Root Cause Analysis**:
- **Wrong Protocol**: N8N/Zapier use custom HTTP APIs, not MCP SSE standard
- **Architecture Mismatch**: Attempted to force SSE protocol on HTTP-only endpoints  
- **Working Solution**: Backend proxy correctly translates to N8N/Zapier HTTP APIs
- **User Confirmation**: N8N workflows complete in 17 seconds (fast and working)

**Final Implementation**:

1. **Simplified MCP Client**: 
   - Removed failed SSE connection attempts
   - Direct HTTP proxy mode for N8N/Zapier compatibility
   - Clean error handling and logging

2. **Proven Architecture**:
   - Voice Agent → HTTP Proxy → N8N/Zapier HTTP APIs
   - 30-second timeouts (confirmed sufficient for 17s workflows)
   - Robust error handling with detailed logging

3. **Working Flow**:
   - User speaks: "Search for Emerson company"  
   - Agent calls: `execute_web_search("Emerson company")`
   - HTTP proxy: Executes N8N workflow (17s completion)
   - Agent receives: Search results for voice response

### ✅ Current Status (January 26, 2025 - 12:25 PM)

**UPDATE: Database-Driven MCP Integration Complete**

**Implementation Summary**:
- ✅ **Database Configuration**: All MCP servers loaded from database on startup
- ✅ **Dynamic URL Management**: Users can add/update/delete MCP servers via frontend
- ✅ **MCPToolExecutor**: Uses backend proxy with database-configured URLs
- ✅ **Server Detection**: Automatically finds N8N and Zapier servers by name
- ✅ **Protocol Routing**: Backend routes N8N to SSE proxy, Zapier to direct webhook
- ✅ **Error Handling**: Clear user-friendly messages when servers not configured

**Architecture**:
```
Database → Voice Agent → Function Tools → Backend Proxy → N8N/Zapier APIs
```

**Key Features**:
- No hardcoded URLs - everything from database
- Frontend can manage all MCP server configurations
- Voice agent dynamically loads server configs on startup
- Backend handles protocol differences transparently

**Current Issues**:
- N8N: 30-second timeout (workflow execution may need optimization)
- Zapier: Needs actual webhook URL configuration in database

## Project Architecture

### Core Technologies
- **LiveKit WebRTC**: Real-time audio communication
- **OpenAI Realtime API**: Direct voice-to-voice AI interaction
- **PostgreSQL**: Configuration and conversation storage
- **Node.js + Express**: Backend API server
- **React + Vite**: Frontend dashboard
- **Python**: LiveKit voice agent implementation

### Key Components

#### Voice Agent (`agents/voice_agent_realtime.py`)
- Pure OpenAI Realtime API integration (no STT-LLM-TTS fallback)
- Database configuration fetching
- MCP web search integration with result polling
- Proper LiveKit room audio subscription and bidirectional flow

#### Backend API (`server/`)
- LiveKit room and token management
- Agent configuration CRUD operations  
- MCP server management and execution endpoints
- Agent process spawning and monitoring

#### Frontend Dashboard (`client/`)
- Real-time voice conversation interface
- Agent configuration management
- MCP server setup and monitoring
- Conversation history and status tracking

### Database Schema (`shared/schema.ts`)
- Agent configurations with voice models and system prompts
- MCP server definitions with polling configuration
- Conversation history and session tracking
- User preferences and settings

## User Preferences

*None specified yet - will be documented here as user provides preferences*

## Current Status

### ✅ Working Features
- LiveKit + OpenAI Realtime API voice conversations
- Database configuration integration
- MCP web search with actual results (when services available)
- Voice-optimized response formatting
- Graceful error handling and fallbacks

### 🔄 Integration Points
- N8N workflow automation (configured)
- Zapier MCP server (configured)
- Internal web search MCP server (active)

### 📋 Next Development Priorities
1. **User Testing**: Validate voice conversation quality and search accuracy
2. **MCP Server Expansion**: Add more tool integrations as needed
3. **Performance Optimization**: Fine-tune polling intervals and timeouts
4. **Monitoring Dashboard**: Real-time agent and MCP server status

## Documentation References

### Implementation Guides
- `LIVEKIT_REALTIME_API_GUIDE.md`: Comprehensive implementation patterns and troubleshooting
- `MCP_POLLING_IMPLEMENTATION_SUMMARY.md`: Job polling architecture for async MCP operations

### Archive
- `archived_agents/`: Previous iterations documenting development progression
- `attached_assets/`: User-provided logs and implementation references

## Technical Notes

### Environment Requirements
- LiveKit server credentials (LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
- OpenAI API key with Realtime API access (Tier 5+ required)
- PostgreSQL database for configuration storage
- Optional: MCP server credentials for enhanced functionality

### Library Dependencies
- Python LiveKit agents with proper LD_LIBRARY_PATH configuration
- Node.js dependencies for backend and frontend
- PostgreSQL drivers and connection pooling

## Development Workflow

### Starting the Application
```bash
npm run dev  # Starts both backend and frontend
```

### Testing Voice Agent
1. Access frontend dashboard
2. Configure agent settings (voice, temperature, system prompt)
3. Start voice session - agent should connect and greet
4. Test search functionality: "Search for [topic]"
5. Verify bidirectional conversation flow

### Adding MCP Servers
1. Configure server in database via frontend
2. Test connection and tool discovery
3. Update agent prompt to utilize new capabilities
4. Validate search/tool execution results

*Last Updated: January 25, 2025*