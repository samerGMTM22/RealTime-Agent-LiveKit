# n8n_tool.py
import os
import json
import asyncio
import aiohttp
import logging
from livekit.agents.llm import function_tool

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "https://n8n.srv755489.hstgr.cloud/mcp/43a3ec6f-728e-489b-9456-45f9d41750b7")
N8N_BEARER_TOKEN = os.environ.get("N8N_BEARER_TOKEN")

logger = logging.getLogger(__name__)

class N8NTools:
    @function_tool
    async def execute_web_search(self, query: str = "") -> str:
        """
        Executes a web search using N8N workflow.
        Use this tool to search the internet for current information, news, or research.
        Provide a search query as the 'query' parameter.
        """
        if not N8N_WEBHOOK_URL:
            return "N8N webhook URL is not configured."

        # Note: Latency management can be added later with agent context

        logger.info(f"Executing N8N web search with query: {query}")

        headers = {"Content-Type": "application/json"}
        if N8N_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {N8N_BEARER_TOKEN}"

        try:
            # Prepare payload for N8N workflow
            payload = {"query": query}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    N8N_WEBHOOK_URL,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)  # Set a reasonable timeout
                ) as response:
                    response.raise_for_status()  # Raises an exception for 4xx/5xx status codes
                    result = await response.json()
                    logger.info(f"N8N web search completed successfully")
                    
                    # Extract meaningful content from result
                    if isinstance(result, dict):
                        # Look for common result fields
                        content = result.get('content') or result.get('result') or result.get('data') or str(result)
                    else:
                        content = str(result)
                    
                    return content
                    
        except aiohttp.ClientError as e:
            logger.error(f"Error calling N8N workflow: {e}")
            return f"I encountered an error while searching: {e}"
        except Exception as e:
            logger.error(f"An unexpected error occurred in N8N tool: {e}")
            return "I encountered an unexpected error while searching. Let me help with what I know instead."

    @function_tool
    async def execute_n8n_workflow(self, **kwargs) -> str:
        """
        Executes a predefined N8N workflow.
        Use this tool to perform complex automations, connect to other services,
        or process data via N8N. The arguments to this function will be passed
        as a JSON object to the N8N workflow.
        """
        if not N8N_WEBHOOK_URL:
            return "N8N webhook URL is not configured."

        # Note: Latency management can be added later with agent context

        logger.info(f"Executing N8N workflow with data: {kwargs}")
        headers = {"Content-Type": "application/json"}
        if N8N_BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {N8N_BEARER_TOKEN}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    N8N_WEBHOOK_URL, 
                    json=kwargs, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.info(f"N8N workflow completed with result: {result}")
                    # Return the result as a JSON string for the LLM
                    return json.dumps(result)
        except Exception as e:
            logger.error(f"Error in N8N tool: {e}")
            return f"An error occurred: {e}"