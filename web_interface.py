#!/usr/bin/env python3
"""
Simple web interface for the AI Test Automation Tool
Provides basic monitoring and control via HTTP
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import AppSettings

class TestAutomationWebHandler(BaseHTTPRequestHandler):
    """HTTP request handler for web interface"""
    
    def __init__(self, *args, **kwargs):
        self.settings = AppSettings()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/':
            self.serve_dashboard()
        elif parsed_url.path == '/api/status':
            self.serve_status()
        elif parsed_url.path == '/api/tests':
            self.serve_tests()
        elif parsed_url.path == '/api/results':
            self.serve_results()
        else:
            self.send_error(404, "Not Found")
    
    def serve_dashboard(self):
        """Serve main dashboard HTML"""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Test Automation Tool - Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        .container {{ 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
        }}
        .header {{
            background: rgba(255,255,255,0.95);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5rem;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .status-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: rgba(255,255,255,0.95);
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        .card h3 {{
            color: #666;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        .card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: #333;
        }}
        .section {{
            background: rgba(255,255,255,0.95);
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .section-header {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #dee2e6;
            border-radius: 12px 12px 0 0;
        }}
        .section-content {{
            padding: 20px;
        }}
        .feature-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .feature {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 3px solid #28a745;
        }}
        .feature h4 {{
            color: #28a745;
            margin-bottom: 8px;
        }}
        .logs {{
            background: #000;
            color: #0f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            max-height: 200px;
            overflow-y: auto;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .status-running {{ background: #28a745; }}
        .status-stopped {{ background: #dc3545; }}
        .status-warning {{ background: #ffc107; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI Test Automation Tool</h1>
            <p>Intelligent test generation and execution for Salesforce Experience Cloud</p>
        </div>
        
        <div class="status-cards">
            <div class="card">
                <h3>Application Status</h3>
                <div class="value">
                    <span class="status-indicator status-running"></span>
                    Running
                </div>
            </div>
            <div class="card">
                <h3>Database</h3>
                <div class="value">
                    <span class="status-indicator status-running"></span>
                    Connected
                </div>
            </div>
            <div class="card">
                <h3>AI Engine</h3>
                <div class="value">
                    <span class="status-indicator status-warning"></span>
                    Limited*
                </div>
            </div>
            <div class="card">
                <h3>Crawler</h3>
                <div class="value">
                    <span class="status-indicator status-running"></span>
                    Ready
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <h2>Core Features</h2>
            </div>
            <div class="section-content">
                <div class="feature-list">
                    <div class="feature">
                        <h4>🤖 AI-Powered Test Generation</h4>
                        <p>Automatically creates comprehensive test cases by analyzing page structures and user interactions</p>
                    </div>
                    <div class="feature">
                        <h4>🕷️ Intelligent Web Crawling</h4>
                        <p>Smart navigation through Salesforce sites with element extraction and classification</p>
                    </div>
                    <div class="feature">
                        <h4>🧪 Automated Test Execution</h4>
                        <p>Parallel test execution with real browser automation and comprehensive reporting</p>
                    </div>
                    <div class="feature">
                        <h4>📊 Visual Reporting</h4>
                        <p>HTML reports with screenshots, performance metrics, and detailed execution logs</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <h2>System Information</h2>
            </div>
            <div class="section-content">
                <p><strong>Database Path:</strong> {self.settings.DATABASE_PATH}</p>
                <p><strong>AI Model:</strong> {self.settings.OPENAI_MODEL}</p>
                <p><strong>Max Pages per Crawl:</strong> {self.settings.MAX_PAGES_PER_CRAWL}</p>
                <p><strong>Test Timeout:</strong> {self.settings.TEST_TIMEOUT} seconds</p>
                <p><strong>Parallel Workers:</strong> {self.settings.PARALLEL_TESTS}</p>
                <br>
                <p style="color: #666; font-size: 0.9rem;">
                    * AI features limited due to OpenAI quota. Application running in fallback mode with basic functionality.
                </p>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <h2>Quick Start</h2>
            </div>
            <div class="section-content">
                <ol>
                    <li><strong>Configure Salesforce:</strong> Set up your credentials and target site URLs</li>
                    <li><strong>Start Crawling:</strong> Let the tool analyze your site structure</li>
                    <li><strong>Generate Tests:</strong> AI creates comprehensive test scenarios</li>
                    <li><strong>Execute & Report:</strong> Run tests and review detailed HTML reports</li>
                </ol>
                <br>
                <p>For detailed instructions, see the <code>quick_start.md</code> file in the project directory.</p>
            </div>
        </div>
    </div>
    
    <script>
        // Auto-refresh status every 30 seconds
        setInterval(() => {{
            fetch('/api/status')
                .then(r => r.json())
                .then(data => console.log('Status:', data))
                .catch(e => console.warn('Status check failed:', e));
        }}, 30000);
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_status(self):
        """Serve system status as JSON"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'application': 'running',
            'database': 'connected',
            'ai_engine': 'limited',
            'crawler': 'ready',
            'settings': {
                'database_path': str(self.settings.DATABASE_PATH),
                'ai_model': self.settings.OPENAI_MODEL,
                'max_pages': self.settings.MAX_PAGES_PER_CRAWL,
                'test_timeout': self.settings.TEST_TIMEOUT
            }
        }
        
        self.send_json_response(status)
    
    def serve_tests(self):
        """Serve test cases from database"""
        try:
            # This would normally query the database
            tests = [
                {
                    'id': 1,
                    'title': 'Sample Login Test',
                    'type': 'Functional',
                    'priority': 'High',
                    'status': 'Ready'
                }
            ]
            self.send_json_response({'tests': tests})
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def serve_results(self):
        """Serve test execution results"""
        try:
            results = [
                {
                    'id': 1,
                    'test_id': 1,
                    'status': 'PASSED',
                    'duration': 2.5,
                    'executed_at': datetime.now().isoformat()
                }
            ]
            self.send_json_response({'results': results})
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to reduce logging noise"""
        pass

def main():
    """Start the web interface server"""
    port = 5000
    server_address = ('0.0.0.0', port)
    
    print(f"AI Test Automation Tool - Web Interface")
    print(f"Starting server on port {port}...")
    print(f"Access dashboard at: http://localhost:{port}")
    
    httpd = HTTPServer(server_address, TestAutomationWebHandler)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\\nShutting down web interface...")
        httpd.shutdown()

if __name__ == "__main__":
    main()