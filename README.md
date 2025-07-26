# LiveKit Voice Agent Platform with Webhook Integration

An advanced voice agent platform that integrates LiveKit WebRTC, OpenAI Realtime API, and external tool integration via webhooks for intelligent, adaptive conversational experiences.

## 🚀 Quick Start

### Prerequisites

1. **LiveKit Cloud Account** (or self-hosted LiveKit server)
   - Sign up at [LiveKit Cloud](https://cloud.livekit.io)
   - Get your API Key, Secret, and WebSocket URL

2. **OpenAI API Access** 
   - Requires Tier 5+ account for Realtime API access
   - Get your API key from [OpenAI Platform](https://platform.openai.com)

3. **PostgreSQL Database**
   - Can use cloud providers like Neon, Supabase, or self-hosted
   - Database URL connection string required

4. **External Tool Integration** (Optional)
   - N8N webhook for web search and automation
   - Alternative: Zapier or custom webhook endpoints

### Environment Setup

Create a `.env` file in the root directory:

```env
# Required - LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Required - OpenAI Configuration  
OPENAI_API_KEY=sk-your-openai-key

# Required - Database
DATABASE_URL=postgresql://user:password@host:port/database

# Optional - External Tools (N8N Webhook)
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-webhook-id

# Optional - Additional integrations
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/hooks/catch/your-hook-id
```

### Installation & Running

```bash
# Install dependencies
npm install

# Run database migrations (if needed)
npm run db:push

# Start the application
npm run dev
```

The application will be available at `http://localhost:5000`

## 🏗️ Architecture Overview

### Core Components

1. **Frontend Dashboard** (`client/`)
   - React + Vite application
   - Real-time voice conversation interface
   - Agent configuration management
   - Tool discovery and status monitoring

2. **Backend API** (`server/`)
   - Node.js + Express server
   - LiveKit room and token management
   - Agent configuration CRUD operations
   - External tool webhook integration
   - Database operations via Drizzle ORM

3. **Voice Agent** (`agents/voice_agent_webhook.py`)
   - Python-based LiveKit agent
   - OpenAI Realtime API integration with STT-LLM-TTS fallback
   - External tool execution via webhook calls
   - Database configuration loading
   - English-first responses (configurable)

4. **Database Schema** (`shared/schema.ts`)
   - Agent configurations and settings
   - Conversation history
   - External tool discovery metadata
   - User preferences

### External Tool Integration

The system uses a **webhook-based architecture** for external tool integration:

```
Voice Input → OpenAI Realtime API → Function Tools → N8N/Zapier Webhook → Results → Voice Output
```

**Benefits:**
- ✅ Simple HTTP integration (no complex protocols)
- ✅ Works with any webhook-capable system
- ✅ Reliable result retrieval
- ✅ Easy to extend and maintain

## 🔧 Configuration

### Agent Configuration

Configure your voice agent through the web interface:

1. **System Prompt**: Define the agent's personality and capabilities
2. **Voice Model**: Choose from OpenAI's voice options (coral, alloy, echo, etc.)
3. **Temperature**: Control response creativity (0-100)
4. **Language**: Default language for responses (English recommended)
5. **OpenAI Model**: Select the underlying language model

### External Tool Setup

#### N8N Integration

1. Create an N8N workflow with a webhook trigger
2. Add nodes for web search, email automation, etc.
3. Configure the webhook to return JSON responses
4. Add your webhook URL to the `N8N_WEBHOOK_URL` environment variable

**Expected Response Format:**
```json
{
  "tools": [
    {
      "name": "web_search",
      "description": "Search the internet for information",
      "category": "search"
    },
    {
      "name": "automation", 
      "description": "Execute automated tasks and workflows",
      "category": "workflow"
    }
  ]
}
```

#### Tool Discovery

The system automatically discovers available tools:
- **At interaction start**: Triggered when users join voice sessions
- **Background refresh**: Periodic discovery every 5 minutes
- **Manual refresh**: Available through the configuration interface

## 🎯 Key Features

### Voice Conversation
- **Real-time audio**: Low-latency LiveKit WebRTC
- **OpenAI Realtime API**: Direct voice-to-voice processing
- **Intelligent interruptions**: Natural conversation flow
- **Multi-language support**: Configurable default language

### External Tool Access
- **Web Search**: Real-time internet search capabilities
- **Automation**: Email sending, task creation, etc.
- **Extensible**: Add custom tools via webhook endpoints
- **Reliable**: Timeout handling and error recovery

### User Interface
- **Live conversation**: Real-time voice interaction
- **Configuration management**: Easy agent setup
- **Tool monitoring**: Real-time tool discovery status
- **Conversation history**: Track previous interactions

## 📁 Project Structure

```
├── agents/
│   └── voice_agent_webhook.py     # Active voice agent
├── client/                        # React frontend
│   ├── src/
│   │   ├── pages/                # Dashboard, configuration
│   │   ├── components/           # Reusable UI components
│   │   └── lib/                  # Utilities and API client
├── server/                       # Express backend
│   ├── lib/                      # Service integrations
│   ├── config/                   # Configuration management
│   └── routes.ts                 # API endpoints
├── shared/
│   └── schema.ts                 # Database schema (Drizzle)
├── docs/                         # Documentation
└── README.md                     # This file
```

## 🔍 Troubleshooting

### Common Issues

1. **Voice Agent Not Starting**
   - Verify all environment variables are set
   - Check OpenAI API key has Realtime API access (Tier 5+)
   - Ensure LiveKit credentials are correct

2. **External Tools Not Working**
   - Verify webhook URL is accessible
   - Check webhook returns proper JSON format
   - Review server logs for connection errors

3. **Database Connection Issues**
   - Verify DATABASE_URL format and credentials
   - Ensure database server is accessible
   - Run `npm run db:push` to sync schema

### Debug Mode

Enable detailed logging by setting:
```env
NODE_ENV=development
```

Check logs in:
- Browser console (frontend issues)
- Terminal output (backend and agent issues)
- PostgreSQL logs (database issues)

## 🚀 Production Deployment

### Using Replit Deployments

1. Configure all environment variables in Replit Secrets
2. Ensure database is accessible from Replit's IP ranges
3. Use the "Deploy" button in your Replit project
4. Your app will be available at `https://your-repl-name.your-username.replit.app`

### Alternative Deployments

The application can be deployed to any Node.js hosting platform:
- Vercel, Netlify (frontend + serverless functions)
- Railway, Render (full-stack)
- AWS, Google Cloud, Azure (container deployments)

## 📚 Documentation

- [`docs/LIVEKIT_REALTIME_API_GUIDE.md`](docs/LIVEKIT_REALTIME_API_GUIDE.md) - Implementation patterns and troubleshooting
- [`docs/MCP_POLLING_IMPLEMENTATION_SUMMARY.md`](docs/MCP_POLLING_IMPLEMENTATION_SUMMARY.md) - Legacy MCP implementation notes
- [`replit.md`](replit.md) - Project development history and architecture decisions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For support and questions:
1. Check the troubleshooting section above
2. Review the documentation in the `docs/` folder
3. Check issues in the project repository
4. Create a new issue with detailed information about your problem

---

**Built with:** LiveKit WebRTC, OpenAI Realtime API, React, Node.js, PostgreSQL, Python