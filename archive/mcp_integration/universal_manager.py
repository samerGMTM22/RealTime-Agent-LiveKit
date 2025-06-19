"""Universal MCP Dispatcher with Job Polling Architecture"""
import asyncio
import time
from typing import Dict, Any, List
from mcp_integration.protocols import BaseProtocolHandler, HTTPProtocolHandler, SSEProtocolHandler, WebSocketProtocolHandler, StdioProtocolHandler
from mcp_integration.storage import PostgreSQLStorage

class UniversalMCPDispatcher:
    def __init__(self, storage: PostgreSQLStorage):
        self.storage = storage
        self.tool_registry: Dict[str, Dict] = {}
        self.protocol_handlers: Dict[str, BaseProtocolHandler] = {
            "http": HTTPProtocolHandler(),
            "sse": SSEProtocolHandler(),
            "websocket": WebSocketProtocolHandler(),
            "stdio": StdioProtocolHandler(),
        }
        print("UniversalMCPDispatcher initialized with job polling architecture.")

    async def initialize_tools(self, user_id: int = 1):
        """Initialize tools from all active MCP servers in the database."""
        print("Initializing MCP tools...")
        active_servers = await self.storage.get_active_mcp_servers(user_id)
        if not active_servers:
            print("No active MCP servers found.")
            return

        for server in active_servers:
            protocol_type = server.get('protocol_type', 'http')
            handler = self.protocol_handlers.get(protocol_type)
            
            if not handler:
                print(f"Warning: No handler for protocol '{protocol_type}' on server '{server['name']}'")
                continue

            try:
                # Try to discover tools from server
                discovered = await handler.discover_tools(server)
                tools = discovered.get('tools', [])
                
                # If no tools discovered, use stored tools from database
                if not tools:
                    tools = server.get('tools', [])

                # Register each tool with a prefixed name
                for tool in tools:
                    tool_name = tool.get('name')
                    if tool_name:
                        prefixed_tool_name = f"{server['name'].replace(' ', '_')}_{tool_name}"
                        self.tool_registry[prefixed_tool_name] = {
                            "server_config": server,
                            "tool_config": tool,
                        }
                        print(f"Registered tool: {prefixed_tool_name}")

                # Update server status to connected if tools were found
                if tools:
                    await self.storage.update_server_status(server['id'], 'connected')
                else:
                    print(f"No tools found for server '{server['name']}'")

            except Exception as e:
                print(f"Error discovering tools for server '{server['name']}': {e}")
                await self.storage.update_server_status(server['id'], 'error')
        
        print(f"Tool initialization complete. Registered tools: {list(self.tool_registry.keys())}")

    async def execute_tool(self, tool_name: str, params: Dict[str, Any], timeout: int = 30) -> Any:
        """Execute a tool using job polling architecture."""
        if tool_name not in self.tool_registry:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")

        registry_entry = self.tool_registry[tool_name]
        server_config = registry_entry['server_config']
        tool_config = registry_entry['tool_config']
        
        protocol_type = server_config.get('protocol_type', 'http')
        handler = self.protocol_handlers.get(protocol_type)

        if not handler:
            raise ValueError(f"No protocol handler found for type '{protocol_type}'")

        print(f"Executing tool '{tool_name}' via server '{server_config['name']}'...")

        try:
            # Step 1: Execute the tool to get a Job ID
            exec_response = await handler.execute_tool(server_config, tool_config.get('name'), params)
            
            job_id = exec_response.get('job_id')
            if not job_id:
                # Handle immediate results if the server supports it
                if exec_response.get('status') == 'completed':
                    return exec_response.get('data')
                elif exec_response.get('status') == 'accepted':
                    # Some servers might return accepted without job_id - this is an error
                    raise ValueError("MCP server returned 'accepted' status but no job_id for polling.")
                else:
                    # Return the response as-is if it's not async
                    return exec_response

            print(f"Tool execution accepted. Job ID: {job_id}. Starting to poll for results.")

            # Step 2: Poll for the result
            start_time = time.time()
            poll_interval_seconds = server_config.get('poll_interval', 1000) / 1000.0

            while time.time() - start_time < timeout:
                await asyncio.sleep(poll_interval_seconds)
                print(f"Polling for result of job_id: {job_id}")
                
                try:
                    result_response = await handler.get_result(server_config, job_id)
                    status = result_response.get('status')

                    if status == 'completed':
                        print(f"Result received for job_id: {job_id}")
                        return result_response.get('data')
                    elif status == 'failed':
                        error_msg = result_response.get('error', 'Unknown error')
                        raise RuntimeError(f"Tool execution failed for job_id: {job_id}. Reason: {error_msg}")
                    elif status == 'pending':
                        # Continue polling
                        continue
                    else:
                        print(f"Warning: Unknown status '{status}' for job_id: {job_id}")
                        
                except Exception as poll_error:
                    print(f"Polling error for job_id {job_id}: {poll_error}")
                    # Continue polling unless it's a timeout
                    if time.time() - start_time >= timeout:
                        break

            raise asyncio.TimeoutError(f"Polling for tool '{tool_name}' timed out after {timeout} seconds.")

        except Exception as e:
            print(f"An error occurred during tool execution for '{tool_name}': {e}")
            raise

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools."""
        tools = []
        for tool_name, registry_entry in self.tool_registry.items():
            tool_config = registry_entry['tool_config']
            server_config = registry_entry['server_config']
            
            tools.append({
                "name": tool_name,
                "description": tool_config.get('description', 'No description available'),
                "parameters": tool_config.get('parameters', {}),
                "server": server_config['name'],
                "protocol": server_config.get('protocol_type', 'http')
            })
        
        return tools

    async def health_check_all_servers(self) -> Dict[str, bool]:
        """Check health of all registered servers."""
        health_status = {}
        
        for tool_name, registry_entry in self.tool_registry.items():
            server_config = registry_entry['server_config']
            server_name = server_config['name']
            
            if server_name not in health_status:
                protocol_type = server_config.get('protocol_type', 'http')
                handler = self.protocol_handlers.get(protocol_type)
                
                if handler:
                    try:
                        is_healthy = await handler.health_check(server_config)
                        health_status[server_name] = is_healthy
                        
                        # Update database status
                        new_status = 'connected' if is_healthy else 'disconnected'
                        await self.storage.update_server_status(server_config['id'], new_status)
                        
                    except Exception as e:
                        print(f"Health check failed for {server_name}: {e}")
                        health_status[server_name] = False
                        await self.storage.update_server_status(server_config['id'], 'error')
                else:
                    health_status[server_name] = False
        
        return health_status

    async def cleanup(self):
        """Cleanup resources."""
        await self.storage.cleanup()
        print("UniversalMCPDispatcher cleanup completed.")