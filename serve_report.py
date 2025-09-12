#!/usr/bin/env python3
"""
Credit Checker Report Server
Serves the HTML report on a local web server
"""

import os
import sys
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from generate_report import generate_html_report
import webbrowser

class ReportHandler(SimpleHTTPRequestHandler):
    """Custom handler that regenerates the report on each request"""
    
    def do_GET(self):
        if self.path == '/' or self.path == '/report':
            # Generate fresh report
            print("🔄 Regenerating report...")
            html_content = generate_html_report()
            
            # Write to file
            with open('credit_checker_report.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Serve the report
            self.path = '/credit_checker_report.html'
        
        return super().do_GET()
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        pass

def start_server(port=8080):
    """Start the web server"""
    try:
        server = HTTPServer(('0.0.0.0', port), ReportHandler)
        print(f"🌐 Credit Checker Report Server starting...")
        print(f"📊 Report available at: http://localhost:{port}")
        print(f"📊 Report available at: http://0.0.0.0:{port}")
        print(f"🔄 Report auto-refreshes on each visit")
        print(f"⏹️  Press Ctrl+C to stop")
        
        # Try to open browser (only works on local machines)
        try:
            webbrowser.open(f'http://localhost:{port}')
        except:
            pass
        
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped")
        server.shutdown()
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    """Main function"""
    port = 8080
    
    # Check if port is specified
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid port number. Using default port 8080")
    
    # Generate initial report
    print("🔍 Generating initial report...")
    html_content = generate_html_report()
    with open('credit_checker_report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("✅ Initial report generated")
    
    # Start server
    start_server(port)

if __name__ == "__main__":
    main()
