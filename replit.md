# LiveKit Voice Agent Platform with MCP Integration

## Project Overview

An advanced voice agent platform that integrates LiveKit WebRTC, OpenAI Realtime API, and Model Context Protocol (MCP) for intelligent, adaptive conversational experiences. The system provides real-time voice conversations with web search capabilities and extensible MCP server integration.

## Recent Changes (January 25, 2025)

### ✅ Critical Fix: Restored Working LiveKit + OpenAI Realtime API Integration

**Issue Resolved**: The voice agent was connecting to OpenAI Realtime API but users couldn't speak to it due to broken LiveKit integration.

**Root Cause**: During MCP development, the proper LiveKit AgentSession integration was replaced with a standalone OpenAI client that had no connection to LiveKit room audio streams.

**Solution Implemented**:
- Created `agents/voice_agent_realtime.py` with proper LiveKit AgentSession pattern
- Restored bidirectional audio flow between LiveKit room and OpenAI Realtime API
- Integrated working MCP job polling system for actual search results
- Fixed library dependency issues with proper environment variables

**Key Technical Details**:
```python
# Proper LiveKit Integration Pattern Used:
await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

@ctx.room.on("track_published")
def on_track_published(publication, participant):
    if publication.kind == "audio":
        publication.set_subscribed(True)  # Critical for audio flow

session = AgentSession(
    llm=openai.realtime.RealtimeModel(
        model="gpt-4o-realtime-preview",
        voice=voice,
        temperature=realtime_temp,
        instructions=enhanced_prompt,
    ),
    allow_interruptions=True,
)

await session.start(room=ctx.room, agent=assistant)
```

### ✅ MCP Integration Status

**Working Components**:
- Job polling architecture for async MCP operations (35-second timeout)
- Database-driven MCP server configuration
- Voice-optimized search result formatting
- Graceful fallback when MCP services unavailable

**Search Function**: Provides real web search results instead of "Accepted" acknowledgments

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