"""MCP Tools integration for LiveKit agents"""
import inspect
import logging
from typing import Dict, List, Callable, Any
from livekit.agents import function_tool

from .manager import MCPManager

logger = logging.getLogger("mcp_tools")

class MCPToolsIntegration:
    """Convert MCP tools to LiveKit function tools"""
    
    @staticmethod
    async def build_livekit_tools(connected_servers: Dict[int, Any]) -> List[Callable]:
        """Convert all connected MCP tools to LiveKit function tools"""
        tools = []
        
        for server_id, server in connected_servers.items():
            try:
                mcp_tools = await server.list_tools()
                
                for mcp_tool in mcp_tools:
                    tool_name = mcp_tool.get("name")
                    tool_description = mcp_tool.get("description", "")
                    tool_schema = mcp_tool.get("inputSchema", {})
                    
                    if not tool_name:
                        continue
                    
                    # Create LiveKit function tool wrapper
                    livekit_tool = MCPToolsIntegration._create_tool_wrapper(
                        server_id, server, tool_name, tool_description, tool_schema
                    )
                    
                    if livekit_tool:
                        tools.append(livekit_tool)
                        logger.info(f"Added MCP tool: {tool_name} from {server.name}")
                        
            except Exception as e:
                logger.error(f"Failed to build tools from server {server_id}: {e}")
                
        return tools
    
    @staticmethod
    def _create_tool_wrapper(server_id: int, server: Any, tool_name: str, 
                           description: str, schema: Dict) -> Callable:
        """Create a LiveKit function tool wrapper for an MCP tool"""
        
        try:
            # Extract parameters from schema
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # Build function signature dynamically
            params = []
            annotations = {}
            
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                is_required = param_name in required
                
                # Convert JSON schema types to Python types
                if param_type == "string":
                    py_type = str
                elif param_type == "integer":
                    py_type = int
                elif param_type == "number":
                    py_type = float
                elif param_type == "boolean":
                    py_type = bool
                else:
                    py_type = str
                
                annotations[param_name] = py_type
                
                if not is_required:
                    params.append(f"{param_name}: {py_type.__name__} = None")
                else:
                    params.append(f"{param_name}: {py_type.__name__}")
            
            # Create the wrapper function
            async def mcp_tool_wrapper(**kwargs) -> str:
                """Dynamically created MCP tool wrapper"""
                try:
                    # Filter out None values for optional parameters
                    filtered_params = {k: v for k, v in kwargs.items() if v is not None}
                    
                    # Call the MCP tool
                    result = await server.call_tool(tool_name, filtered_params)
                    
                    if "error" in result:
                        return f"Error calling {tool_name}: {result['error']}"
                    
                    # Format the result
                    if "content" in result:
                        if isinstance(result["content"], list):
                            return "\n".join([
                                item.get("text", str(item)) 
                                for item in result["content"]
                            ])
                        else:
                            return str(result["content"])
                    else:
                        return str(result)
                        
                except Exception as e:
                    logger.error(f"Error in MCP tool {tool_name}: {e}")
                    return f"Error executing {tool_name}: {str(e)}"
            
            # Set function metadata
            mcp_tool_wrapper.__name__ = f"mcp_{tool_name}".replace("-", "_").replace(" ", "_")
            mcp_tool_wrapper.__doc__ = description or f"MCP tool: {tool_name}"
            mcp_tool_wrapper.__annotations__ = annotations
            mcp_tool_wrapper.__annotations__["return"] = str
            
            # Create the LiveKit function tool
            return function_tool(mcp_tool_wrapper)
            
        except Exception as e:
            logger.error(f"Failed to create wrapper for {tool_name}: {e}")
            return None