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

**Root Cause Analysis**:
- **Known Bug**: OpenAI Realtime API + function tools has compatibility issue (GitHub #2383)
- **WebSocket Timeouts**: Realtime API designed for low-latency, not 30+ second MCP operations
- **Connection Instability**: "keepalive ping timeout" occurs during long function calls

**Solutions Implemented**:

1. **Switched to Reliable Voice Pipeline**:
   - Created `voice_agent_reliable.py` using traditional STT-LLM-TTS
   - Uses Deepgram STT + OpenAI GPT-4o + OpenAI TTS
   - Function tools work reliably without WebSocket crashes

2. **Reduced MCP Timeouts**: 
   - All timeouts reduced from 30s → 15s to prevent connection drops
   - Web search timeout: 15 seconds
   - Email send timeout: 15 seconds
   - SSE connection timeout: 15 seconds

3. **Enhanced Error Handling**:
   - Graceful fallbacks when MCP services are slow
   - Clear user feedback for timeout scenarios
   - Test mode available (`MCP_TEST_MODE=true`)

4. **Server Configuration**:
   - Updated routes.ts to use reliable agent
   - Proper environment variable handling
   - Comprehensive logging for debugging

### ✅ Current Status (January 25, 2025 - 12:31 PM)

**Working Features**:
- ✅ **Reliable Voice Agent**: Uses Silero VAD + OpenAI Whisper STT + GPT-4o + TTS
- ✅ **Voice Conversations**: Agent connects, responds to voice input, clear TTS output
- ✅ **MCP Server Connectivity**: Both internet access (ID 9) and Zapier (ID 15) servers connected
- ✅ **Direct MCP Integration**: New agent (voice_agent_mcp.py) connects to MCP servers directly
- ✅ **Error Handling**: Graceful fallbacks with 20-second timeouts
- ✅ **Console Cleanup**: Reduced audio stream debug clutter

**Latest Implementation**:
- 🔄 **Hybrid Approach**: MCP client module with backend proxy fallback for reliability
- 🔄 **Extended Timeouts**: Increased to 20 seconds to prevent premature cutoffs
- 🔄 **Simplified Architecture**: Using hardcoded tool definitions for stability

**Technical Architecture**:
- **Voice Pipeline**: Silero VAD → OpenAI Whisper → GPT-4o → OpenAI TTS
- **MCP Integration**: Direct client module with backend proxy for execution
- **Function Tools**: Web search (server ID 9) + Email sending (server ID 15)
- **Timeout Strategy**: 20-second limits with graceful fallback messages

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