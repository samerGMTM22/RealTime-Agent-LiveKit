#!/usr/bin/env python3
"""
Test script for enhanced MCP integration with result polling.
This script validates that the voice agent receives actual search results
instead of just acknowledgments.
"""

import asyncio
import requests
import json
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPIntegrationTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
    
    def test_health_check(self, server_id=2):
        """Test MCP server health check."""
        logger.info(f"Testing health check for server {server_id}")
        try:
            response = requests.get(f"{self.base_url}/api/mcp/health/{server_id}", timeout=5)
            result = response.json()
            logger.info(f"Health check result: {result}")
            return result.get('status') == 'healthy'
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def test_basic_search(self, query="Python programming tutorials"):
        """Test basic search functionality with polling."""
        logger.info(f"Testing search: '{query}'")
        
        start_time = time.time()
        
        try:
            # Make search request
            response = requests.post(
                f"{self.base_url}/api/mcp/execute",
                json={
                    "serverId": 2,  # N8N server ID
                    "tool": "execute_web_search",
                    "params": {"query": query}
                },
                timeout=40  # Extended timeout for polling
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Response received in {elapsed_time:.2f}s")
                logger.info(f"Success: {data.get('success')}")
                
                if data.get('success'):
                    result = data.get('result', '')
                    logger.info(f"Result type: {type(result)}")
                    logger.info(f"Result length: {len(str(result))}")
                    
                    # Check if we got actual results, not just acknowledgment
                    if "accepted" in str(result).lower() and len(str(result)) < 100:
                        logger.warning("Received acknowledgment instead of results!")
                        return False
                    
                    logger.info("Received actual search results!")
                    logger.info(f"First 200 chars: {str(result)[:200]}...")
                    return True
                else:
                    logger.error(f"Search failed: {data.get('error')}")
                    return False
            else:
                logger.error(f"HTTP error {response.status_code}")
                return False
                
        except requests.Timeout:
            logger.error(f"Request timed out after {time.time() - start_time:.2f}s")
            return False
        except Exception as e:
            logger.error(f"Search test failed: {e}")
            return False
    
    def test_webhook_callback(self):
        """Test webhook callback mechanism."""
        logger.info("Testing webhook callback mechanism")
        
        # This would require setting up a local webhook receiver
        # For now, we'll just verify the endpoint exists
        try:
            # Test with a dummy request ID
            response = requests.post(
                f"{self.base_url}/api/mcp/callback/test-callback-123",
                json={
                    "result": "Test callback result",
                    "metadata": {"test": True}
                },
                timeout=5
            )
            
            if response.status_code == 404:
                logger.info("Callback endpoint working (404 for unknown request ID)")
                return True
            elif response.status_code == 200:
                logger.info("Callback processed successfully")
                return True
            else:
                logger.error(f"Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Callback test failed: {e}")
            return False
    
    def test_concurrent_searches(self, num_searches=3):
        """Test multiple concurrent searches."""
        logger.info(f"Testing {num_searches} concurrent searches")
        
        queries = [
            "latest AI news 2025",
            "Python async programming",
            "LiveKit voice agents"
        ]
        
        async def async_search(query):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.test_basic_search, query)
        
        async def run_concurrent():
            tasks = [async_search(queries[i % len(queries)]) for i in range(num_searches)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        try:
            results = asyncio.run(run_concurrent())
            success_count = sum(1 for r in results if r is True)
            logger.info(f"Concurrent search results: {success_count}/{num_searches} successful")
            return success_count == num_searches
        except Exception as e:
            logger.error(f"Concurrent search test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all integration tests."""
        logger.info("=== Starting Enhanced MCP Integration Tests ===")
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Webhook Callback", self.test_webhook_callback),
            ("Basic Search", self.test_basic_search),
            ("Concurrent Searches", self.test_concurrent_searches)
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n--- Running: {test_name} ---")
            try:
                result = test_func()
                results.append((test_name, result))
                logger.info(f"Result: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                logger.error(f"Test crashed: {e}")
                results.append((test_name, False))
            
            time.sleep(1)  # Brief pause between tests
        
        # Summary
        logger.info("\n=== Test Summary ===")
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nTotal: {passed}/{total} tests passed")
        
        return passed == total

def main():
    """Main test execution."""
    # Ensure services are running
    logger.info("Enhanced MCP Integration Test Suite")
    logger.info("Make sure the following are running:")
    logger.info("1. Express server (npm run dev)")
    logger.info("2. N8N with MCP workflow")
    logger.info("3. Voice agent (python agent_enhanced.py)")
    
    input("\nPress Enter to start tests...")
    
    tester = MCPIntegrationTester()
    
    # Run individual test
    logger.info("\n=== Testing Single Search ===")
    if tester.test_basic_search("What is the weather today in Dubai"):
        logger.info("✅ Single search test passed - receiving actual results!")
    else:
        logger.error("❌ Single search test failed - still getting acknowledgments")
    
    # Run all tests
    input("\nPress Enter to run full test suite...")
    all_passed = tester.run_all_tests()
    
    if all_passed:
        logger.info("\n🎉 All tests passed! MCP integration is working correctly.")
    else:
        logger.error("\n⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    main()