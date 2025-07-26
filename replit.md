# LiveKit Voice Agent Platform with MCP Integration

## Project Overview

An advanced voice agent platform that integrates LiveKit WebRTC, OpenAI Realtime API, and Model Context Protocol (MCP) for intelligent, adaptive conversational experiences. The system provides real-time voice conversations with web search capabilities and extensible MCP server integration.

## Recent Changes (January 26, 2025)

### ✅ COMPLETE ARCHITECTURE PIVOT: Webhook-Based External Tool Integration

**Major Decision (1:00 PM)**:
- **Abandoned MCP Integration**: Completely removed complex MCP protocol handling
- **Adopted Webhook Architecture**: Simple HTTP webhook calls for external tool execution
- **Simplified Integration**: Voice Agent → N8N Webhook → Tool Results → Voice Response

**Implementation Summary**:

1. **Removed All MCP Code**:
   - ✅ Archived MCP proxy files (`mcp_proxy.ts`, `test_direct_tools.py`)
   - ✅ Cleaned up `server/routes.ts` - removed all MCP endpoints and imports
   - ✅ Fixed application startup issues by eliminating MCP dependencies
   - ✅ Created new `ExternalToolHandler` with webhook-based execution

2. **New Webhook Architecture**:
   - ✅ Simple HTTP POST to N8N webhook: `https://n8n.srv755489.hstgr.cloud/webhook/5942b551-121e-4c21-a765-5eaa10563c5a`
   - ✅ Payload: `{ tool: "web_search", params: { query: "..." } }`
   - ✅ Direct response handling with 30-second timeout
   - ✅ Clean error handling and logging

3. **New Voice Agent** (`agents/voice_agent_webhook.py`):
   - ✅ **WebhookToolExecutor**: Direct webhook calls instead of MCP protocol
   - ✅ **Database Configuration**: Loads agent config from PostgreSQL
   - ✅ **External Functions**: `execute_web_search()` and `execute_automation()`
   - ✅ **Error Handling**: Graceful fallbacks when webhook unavailable

**Architecture Flow**:
```
Voice Input → OpenAI Realtime API → Function Tools → N8N Webhook → Results → Voice Output
```

**Key Benefits**:
- **Simplicity**: No complex protocol handling or session management
- **Reliability**: Direct HTTP calls with standard error handling  
- **Flexibility**: Any webhook-capable system can provide tools (N8N, Zapier, custom APIs)
- **Performance**: Eliminates connection overhead and polling complexity
- **Maintainability**: Standard HTTP patterns instead of experimental protocols

**Current Status**:
- ✅ Application running without MCP dependencies
- ✅ External tool handler with webhook integration ready
- ✅ New voice agent created with webhook tool execution
- 🔄 **Next**: Update frontend UI to remove MCP configuration pages
- 🔄 **Next**: Update database schema to remove MCP tables
- 🔄 **Next**: Test voice agent with actual webhook calls

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