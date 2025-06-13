"""MCP Tools integration for LiveKit agents"""

import inspect
import logging
from typing import Any, List, Callable, Dict, get_origin
from livekit.agents.llm import function_tool
from .mcp_manager import MCPManager

logger = logging.getLogger("mcp_tools")

class MCPToolsIntegration:
    """Integrate MCP tools with LiveKit agents"""
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        
    @staticmethod
    def _py_type(schema: dict) -> Any:
        """Convert JSON schema to Python type annotation"""
        t = schema.get("type")
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict
        }
        
        if t in type_map:
            return type_map[t]
        if t == "array":
            items_schema = schema.get("items", {})
            return List[MCPToolsIntegration._py_type(items_schema)]
        return Any
    
    @staticmethod
    def schema_to_docstring(description: str, schema: dict) -> str:
        """Generate docstring from JSON schema"""
        lines = [description, "", "Args:"]
        
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get("type", "any")
            prop_desc = prop_schema.get("description", "")
            lines.append(f"    {prop_name} ({prop_type}): {prop_desc}")
            
        return "\n".join(lines)
    
    async def build_livekit_tools(self) -> List[Callable]:
        """Convert all connected MCP tools to LiveKit function tools"""
        livekit_tools = []
        all_tools = await self.mcp_manager.get_all_tools()
        
        for tool_key, tool_info in all_tools.items():
            server_id = tool_info["server_id"]
            tool = tool_info["tool"]
            
            # Create a closure to capture server_id and tool_name
            def create_tool_wrapper(sid: int, tname: str):
                async def mcp_tool_wrapper(**kwargs) -> str:
                    try:
                        result = await self.mcp_manager.call_tool(sid, tname, kwargs)
                        
                        # Extract content from MCP response
                        if isinstance(result, dict):
                            if "content" in result:
                                content = result["content"]
                                if isinstance(content, list) and content:
                                    return str(content[0].get("text", content[0]))
                                return str(content)
                            elif "result" in result:
                                return str(result["result"])
                            else:
                                return str(result)
                        
                        return str(result)
                        
                    except Exception as e:
                        logger.error(f"MCP tool {tname} failed: {e}")
                        return f"Tool execution failed: {str(e)}"
                
                return mcp_tool_wrapper
            
            # Create the wrapper function
            tool_wrapper = create_tool_wrapper(server_id, tool["name"])
            
            # Set proper function metadata
            tool_wrapper.__name__ = tool_key.replace("-", "_")  # Valid Python identifier
            tool_wrapper.__doc__ = MCPToolsIntegration.schema_to_docstring(
                tool.get("description", f"MCP tool: {tool['name']}"),
                tool.get("inputSchema", {})
            )
            
            # Add parameter annotations
            sig_params = []
            
            input_schema = tool.get("inputSchema", {})
            properties = input_schema.get("properties", {})
            required = set(input_schema.get("required", []))
            
            for prop_name, prop_schema in properties.items():
                # Clean property name for Python parameter
                clean_name = prop_name.replace("-", "_").replace(" ", "_")
                
                param = inspect.Parameter(
                    clean_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=MCPToolsIntegration._py_type(prop_schema),
                    default=inspect.Parameter.empty if prop_name in required else None
                )
                sig_params.append(param)
            
            tool_wrapper.__signature__ = inspect.Signature(sig_params)
            
            # Register as LiveKit function tool
            livekit_tool = function_tool(tool_wrapper)
            livekit_tools.append(livekit_tool)
            
        logger.info(f"Created {len(livekit_tools)} LiveKit tools from MCP servers")
        return livekit_tools