#!/usr/bin/env python3
"""
Simple Static Credit Checker Report Server
Serves a single HTML file without regeneration
"""

import os
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser

class StaticReportHandler(SimpleHTTPRequestHandler):
    """Handler that serves static files"""

    def do_GET(self):
        # Redirect root to the report
        if self.path == '/' or self.path == '/report':
            self.path = '/credit_checker_report.html'

        return super().do_GET()

    def log_message(self, format, *args):
        """Override to reduce log noise - only show important requests"""
        if self.path.endswith('.html') or self.path.endswith('.csv'):
            super().log_message(format, *args)

def start_server(port=8080):
    """Start the web server"""
    try:
        server = HTTPServer(('0.0.0.0', port), StaticReportHandler)
        print(f"🌐 Credit Checker Report Server starting...")
        print(f"📊 Report available at: http://localhost:{port}")
        print(f"📊 Report available at: http://0.0.0.0:{port}")
        print(f"📄 Serving static HTML file: credit_checker_report.html")
        print(f"⏹️  Press Ctrl+C to stop")

        # Try to open browser (only works on local machines)
        try:
            webbrowser.open(f'http://localhost:{port}')
        except:
            pass  # Ignore browser opening errors

        server.serve_forever()

    except KeyboardInterrupt:
        print("\n⏹️  Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")

def main():
    """Main function"""
    port = 8080

    # Check if port is specified
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid port number. Using default port 8080")

    # Check if report file exists
    if not os.path.exists('credit_checker_report.html'):
        print("⚠️  Report file not found. Generating...")
        try:
            from generate_report import generate_html_dashboard
            html_content = generate_html_dashboard()
            with open('credit_checker_report.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print("✅ Report generated")
        except Exception as e:
            print(f"❌ Failed to generate report: {e}")
            sys.exit(1)

    # Start server
    start_server(port)

if __name__ == "__main__":
    main()