#!/usr/bin/env python3
"""
Automated test for enhanced MCP integration - validates actual search results.
"""

import requests
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_enhanced_mcp_integration():
    """Test that MCP integration returns actual results, not acknowledgments."""
    base_url = "http://localhost:5000"
    
    logger.info("Testing Enhanced MCP Integration")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            logger.info(f"✅ System status: {status}")
        else:
            logger.error("❌ System not ready")
            return False
    except Exception as e:
        logger.error(f"❌ System check failed: {e}")
        return False
    
    # Test 2: Direct MCP search test
    logger.info("Testing direct MCP search...")
    try:
        start_time = time.time()
        
        search_response = requests.post(
            f"{base_url}/api/mcp/execute",
            json={
                "serverId": 9,
                "tool": "execute_web_search",
                "params": {"query": "Python programming best practices 2025"}
            },
            timeout=35
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Request completed in {elapsed_time:.2f}s")
        
        if search_response.status_code == 200:
            data = search_response.json()
            logger.info(f"Response success: {data.get('success')}")
            
            if data.get('success'):
                result = data.get('result', '')
                result_str = str(result)
                
                # Check if we got actual results vs acknowledgment
                if "accepted" in result_str.lower() and len(result_str) < 100:
                    logger.error("❌ Still receiving acknowledgments instead of results")
                    logger.error(f"Result: {result_str}")
                    return False
                
                logger.info("✅ Received actual search results!")
                logger.info(f"Result preview: {result_str[:200]}...")
                return True
            else:
                logger.error(f"❌ Search failed: {data.get('error')}")
                return False
        else:
            logger.error(f"❌ HTTP error {search_response.status_code}")
            return False
            
    except requests.Timeout:
        logger.error("❌ Search request timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Search test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_enhanced_mcp_integration()
    if success:
        print("\n🎉 Enhanced MCP integration is working correctly!")
        print("Voice agent will now receive actual search results instead of acknowledgments.")
    else:
        print("\n⚠️ Enhanced MCP integration needs attention.")
        print("Check the logs above for specific issues.")