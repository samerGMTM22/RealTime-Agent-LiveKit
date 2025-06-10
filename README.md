# Voice Agent Platform - Give Me the Mic

A sophisticated voice agent application built with LiveKit Agents framework and OpenAI Realtime API, featuring a premium frontend and modular business customization capabilities.

## Architecture

### Backend (Node.js/TypeScript)
- **Frontend Server**: React/TypeScript with shadcn/ui components
- **API Server**: Express.js with LiveKit integration
- **Database**: In-memory storage with configurable agent templates
- **Real-time Communication**: LiveKit WebRTC for audio streaming

### Voice Agent (Python)
- **LiveKit Agents Framework**: Official Python framework for voice processing
- **OpenAI Realtime API**: Direct speech-to-speech processing
- **Custom Tools**: Channel information, music tips, content suggestions
- **Room Management**: Automatic connection to LiveKit rooms

## Features

### Voice Capabilities
- Real-time voice conversations with OpenAI Realtime API
- Automatic voice activity detection and turn-taking
- Natural speech processing with low latency
- Customizable voice models and personalities

### Business Intelligence
- YouTube channel integration (Give Me the Mic - 484 subscribers, 249 videos)
- Music-related advice and tips
- Content recommendations based on user interests
- Channel statistics and information

### Frontend Features
- Premium UI with dark/light mode support
- Real-time voice session management
- Agent configuration and customization
- Conversation history tracking
- System status monitoring

## Quick Start

### Prerequisites
- Node.js 20+ and Python 3.11+
- LiveKit Cloud account or self-hosted LiveKit server
- OpenAI API key with Realtime API access

### Environment Setup

1. Copy your API keys to `.env`:
```bash
OPENAI_API_KEY=your_openai_api_key
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret
LIVEKIT_URL=your_livekit_ws_url
YOUTUBE_API_KEY=your_youtube_api_key
```

### Running the Application

1. **Start the Node.js server**:
```bash
npm run dev
```

2. **Test the Python voice agent**:
```bash
python agent.py console
```

3. **Start a voice session**:
   - Open the web interface
   - Click "Start Session"
   - The Python agent will automatically join the room
   - Begin speaking to interact with the AI assistant

## System Components

### Python Voice Agent (`agent.py`)
- Implements proper LiveKit Agents framework
- Uses OpenAI Realtime API for speech processing
- Includes custom tools for channel information
- Handles room connections and voice interactions

### Node.js API Server
- Manages LiveKit room creation and tokens
- Provides agent configuration endpoints
- Handles conversation history
- Integrates with YouTube API for channel data

### React Frontend
- Voice interface with audio visualization
- Agent configuration and settings
- Real-time connection status
- Conversation history display

## Voice Agent Tools

The Python agent includes several specialized tools:

- **`get_channel_info()`**: Provides information about the Give Me the Mic channel
- **`get_music_tips(topic)`**: Offers music-related advice for singing, recording, instruments, etc.
- **`suggest_content(interest)`**: Recommends channel content based on user interests

## Deployment

### Development Mode
```bash
python agent.py dev
```

### Production Mode
```bash
python agent.py start
```

The agent automatically connects to LiveKit rooms created by the web application and provides voice responses using OpenAI's Realtime API.

## Customization

### Adding New Agent Types
1. Create templates in `server/config/agent-config.ts`
2. Define custom tools in the Python agent
3. Update the frontend configuration forms

### Business Templates
The system supports various business use cases:
- Music education and coaching
- Customer service automation
- Real estate assistance
- Fitness and wellness coaching

## Technical Details

### Voice Processing Pipeline
1. User speaks → LiveKit captures audio
2. Audio streams to Python agent
3. OpenAI Realtime API processes speech
4. AI generates response speech
5. Response streams back to user via LiveKit

### Integration Points
- **LiveKit WebRTC**: Real-time audio communication
- **OpenAI Realtime API**: Speech-to-speech processing
- **YouTube API**: Channel data integration
- **Custom Tools**: Business-specific functionality

## Troubleshooting

### Common Issues
1. **Agent not connecting**: Check LiveKit credentials in `.env`
2. **No voice response**: Verify OpenAI API key has Realtime API access
3. **Audio issues**: Ensure microphone permissions are granted

### Debug Mode
Run the Python agent with verbose logging:
```bash
python agent.py dev --verbose
```

## License

MIT License - See LICENSE file for details.