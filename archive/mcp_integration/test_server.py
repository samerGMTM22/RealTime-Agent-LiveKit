"""Test MCP Server for Job Polling Demonstration"""
import asyncio
import json
import uuid
from typing import Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

class MCPTestServer:
    """A simple MCP server that demonstrates job polling with real results"""
    
    def __init__(self, port=8080):
        self.port = port
        self.jobs: Dict[str, Dict] = {}
        self.server = None
        self.server_thread = None
    
    def start(self):
        """Start the test MCP server"""
        handler = self._create_handler()
        self.server = HTTPServer(('localhost', self.port), handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        print(f"Test MCP server started on port {self.port}")
    
    def stop(self):
        """Stop the test MCP server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
    
    def _create_handler(self):
        jobs = self.jobs
        
        class TestMCPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/.well-known/mcp.json':
                    # MCP server capabilities
                    capabilities = {
                        "tools": [
                            {
                                "name": "web_search",
                                "description": "Search the web for information",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Search query"}
                                    },
                                    "required": ["query"]
                                }
                            }
                        ],
                        "protocols": ["http"],
                        "polling": {
                            "supported": True,
                            "interval": 2000
                        }
                    }
                    self._send_json_response(capabilities)
                
                elif self.path.startswith('/jobs/'):
                    # Get job result
                    job_id = self.path.split('/')[-1]
                    if job_id in jobs:
                        self._send_json_response(jobs[job_id])
                    else:
                        self._send_error(404, "Job not found")
                
                else:
                    self._send_error(404, "Not found")
            
            def do_POST(self):
                if self.path == '/tools/web_search':
                    # Execute search tool
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    params = json.loads(post_data.decode('utf-8'))
                    
                    job_id = str(uuid.uuid4())
                    query = params.get('query', '')
                    
                    # Create job with initial status
                    jobs[job_id] = {
                        "job_id": job_id,
                        "status": "processing",
                        "progress": 0,
                        "created_at": time.time()
                    }
                    
                    # Start async processing
                    asyncio.create_task(self._process_search(job_id, query))
                    
                    # Return job ID (not "Accepted")
                    response = {
                        "job_id": job_id,
                        "status": "processing",
                        "poll_url": f"/jobs/{job_id}"
                    }
                    self._send_json_response(response)
                
                else:
                    self._send_error(404, "Not found")
            
            async def _process_search(self, job_id: str, query: str):
                """Simulate search processing with real results"""
                await asyncio.sleep(1)  # Simulate processing time
                
                # Generate realistic search results
                search_results = f"""Based on your search for "{query}", here are the key findings:

1. Recent developments show significant progress in this area
2. Industry experts recommend focusing on practical applications
3. Current trends indicate growing adoption and improved efficiency
4. Best practices include thorough research and careful implementation

This information represents actual search results that would be useful for a voice agent to speak to users, demonstrating that the MCP job polling system successfully retrieves real content instead of just acknowledgment messages."""
                
                # Update job with final results
                jobs[job_id] = {
                    "job_id": job_id,
                    "status": "completed",
                    "progress": 100,
                    "result": search_results,
                    "completed_at": time.time()
                }
            
            def _send_json_response(self, data):
                response = json.dumps(data).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            
            def _send_error(self, code, message):
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = json.dumps({"error": message}).encode('utf-8')
                self.wfile.write(error_response)
            
            def log_message(self, format, *args):
                # Suppress default logging
                pass
        
        return TestMCPHandler

# Global test server instance
test_server = None

def start_test_server():
    """Start the test MCP server"""
    global test_server
    if not test_server:
        test_server = MCPTestServer(port=8080)
        test_server.start()
    return test_server

def stop_test_server():
    """Stop the test MCP server"""
    global test_server
    if test_server:
        test_server.stop()
        test_server = None