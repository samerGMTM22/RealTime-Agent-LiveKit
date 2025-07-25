# zapier_tool.py
import os
import json
import asyncio
import aiohttp
import logging
from livekit.agents.llm import function_tool

ZAPIER_MCP_URL = os.environ.get("ZAPIER_MCP_URL")

logger = logging.getLogger(__name__)

class ZapierTools:
    @function_tool
    async def send_email(self, to: str = "", subject: str = "", body: str = "") -> str:
        """
        Sends an email using Zapier integration.
        Use this tool to send emails to users or contacts.
        Provide 'to' (recipient email), 'subject', and 'body' parameters.
        """
        if not ZAPIER_MCP_URL:
            return "Zapier MCP URL is not configured."

        # Note: Latency management can be added later with agent context

        logger.info(f"Sending email via Zapier to: {to}")

        headers = {"Content-Type": "application/json"}

        try:
            # Prepare payload for Zapier
            payload = {"to": to, "subject": subject, "body": body}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ZAPIER_MCP_URL,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.info(f"Zapier email sent successfully")
                    return f"Email sent successfully to {to}"
                    
        except aiohttp.ClientError as e:
            logger.error(f"Error calling Zapier action: {e}")
            return f"I encountered an error while sending the email: {e}"
        except Exception as e:
            logger.error(f"An unexpected error occurred in Zapier tool: {e}")
            return "I encountered an unexpected error while sending the email."

    @function_tool
    async def execute_zapier_action(self, **kwargs) -> str:
        """
        Executes a predefined action via a Zapier MCP endpoint.
        Use this tool to trigger Zaps and interact with the thousands of apps
        connected to Zapier. The arguments to this function will be passed
        as a JSON object to Zapier.
        For example, to add a lead to a CRM, you might provide arguments like:
        'name', 'email', and 'company'.
        """
        if not ZAPIER_MCP_URL:
            return "Zapier MCP URL is not configured."

        # Note: Latency management can be added later with agent context

        logger.info(f"Executing Zapier action with data: {kwargs}")

        headers = {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ZAPIER_MCP_URL,
                    json=kwargs,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    logger.info(f"Zapier action completed with result: {result}")
                    return json.dumps(result)
        except Exception as e:
            logger.error(f"Error in Zapier tool: {e}")
            return f"An error occurred: {e}"