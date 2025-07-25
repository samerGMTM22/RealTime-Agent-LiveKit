"""Integration utilities for MCP tools with LiveKit agents."""
import logging
from typing import Any, List, Dict, Callable, Optional, TYPE_CHECKING
from livekit.agents import function_tool

if TYPE_CHECKING:
    from .server import MCPServer

logger = logging.getLogger("mcp-agent-tools")

class MCPToolsIntegration:
    """Helper class for integrating MCP tools with LiveKit agents."""
    
    @staticmethod
    async def create_function_tools(mcp_servers: List[Any]) -> List[Callable]:
        """
        Create LiveKit function tools from MCP servers.
        
        Args:
            mcp_servers: List of MCP server instances
            
        Returns:
            List of decorated function tools ready for LiveKit agent
        """
        function_tools = []
        
        # Connect to all servers
        for server in mcp_servers:
            if not server.connected:
                try:
                    await server.connect()
                except Exception as e:
                    logger.error(f"Failed to connect to {server.name}: {e}")
                    continue
        
        # Create function tools based on available MCP tools
        # For now, we'll create hardcoded tools that match our MCP servers
        
        # Web search tool
        @function_tool
        async def search_web(query: str) -> str:
            """Search the web for information."""
            logger.info(f"🔍 MCP web search for: {query}")
            
            # Find the internet access server
            for server in mcp_servers:
                if "internet" in server.name.lower():
                    try:
                        result = await server.call_tool("execute_web_search", {"query": query})
                        if "error" in result:
                            return f"Search failed: {result['error']}"
                        
                        # Format the result
                        content = result.get("content", "") or result.get("result", "")
                        if content:
                            return f"Here's what I found about {query}: {content}"
                        else:
                            return f"I searched for {query} but didn't find specific results."
                    except Exception as e:
                        logger.error(f"Search error: {e}")
                        return f"I encountered an error while searching for {query}."
            
            return f"Web search is not available right now."
        
        # Email tool  
        @function_tool
        async def send_email(to: str, subject: str, body: str) -> str:
            """Send an email using Zapier."""
            logger.info(f"📧 MCP email send to: {to}")
            
            # Find the Zapier server
            for server in mcp_servers:
                if "zapier" in server.name.lower():
                    try:
                        result = await server.call_tool("send_email", {
                            "to": to,
                            "subject": subject,
                            "body": body
                        })
                        
                        if "error" in result:
                            return f"Failed to send email: {result['error']}"
                        
                        return f"Email sent successfully to {to}!"
                    except Exception as e:
                        logger.error(f"Email error: {e}")
                        return f"I encountered an error while sending the email to {to}."
            
            return "Email service is not available right now."
        
        function_tools.extend([search_web, send_email])
        logger.info(f"Created {len(function_tools)} function tools from MCP servers")
        
        return function_tools