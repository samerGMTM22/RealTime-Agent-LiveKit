# LiveKit Voice Agent Platform with MCP Integration

## Project Overview

An advanced voice agent platform that integrates LiveKit WebRTC, OpenAI Realtime API, and Model Context Protocol (MCP) for intelligent, adaptive conversational experiences. The system provides real-time voice conversations with web search capabilities and extensible MCP server integration.

## Recent Changes (January 25, 2025)

### ✅ Major Fix: Resolved Voice Cutting Off & MCP Integration Issues

**Issues Resolved**:
1. **Voice Cutting Off**: Agent was interrupting itself and cutting off mid-sentence
2. **System Prompt Confusion**: System prompts were being treated as user inputs
3. **MCP Timeouts**: Both web search and email functions were timing out
4. **Function Tools Type Error**: Fixed LiveKit agents type compatibility

**Root Causes Identified**:
- OpenAI Realtime API's Voice Activity Detection (VAD) was too sensitive (default threshold 0.5)
- System prompts passed via `generate_reply` were confusing the conversation context
- MCP proxy timeouts were too short (10 seconds for SSE connections)
- Known bug with OpenAI Realtime Model + function tools in LiveKit agents

**Solutions Implemented**:

1. **Turn Detection Optimization**:
```python
turn_detection=TurnDetection(
    type="server_vad",
    threshold=0.7,  # Increased from 0.5 (less sensitive)
    prefix_padding_ms=400,  # More padding before speech
    silence_duration_ms=1000,  # Wait 1 second vs 500ms default
    create_response=True,
    interrupt_response=True,
)
# Also increased interruption delays to 0.8s and max endpointing to 8.0s
```

2. **MCP Timeout Fixes**:
- SSE connection timeout: 10s → 30s
- Web search timeout: 35s → 45s  
- Email send timeout: 30s → 45s

3. **System Prompt Isolation**:
- Removed automatic greeting via `generate_reply(instructions=...)`
- Agent now waits for user to speak first
- System prompts properly isolated in Agent constructor

4. **Improved Error Handling**:
- Created `voice_agent_realtime_improved.py` with comprehensive fallbacks
- Added test mode for MCP functions (set `MCP_TEST_MODE=true`)
- Graceful degradation when MCP services unavailable

### ✅ Current Status

**Working Features**:
- Voice conversations without cutting off or self-interruption
- Proper turn detection for natural conversation flow
- MCP function tools registered correctly with Agent
- Fallback responses when MCP services timeout
- Test mode for validating voice + function integration

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