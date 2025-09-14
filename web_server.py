#!/usr/bin/env python3
"""
Dynamic Credit Checker Report Web Server
Regenerates the report on each request
"""

import os
import sys
from flask import Flask, render_template_string, send_file, request, Response
from generate_report import generate_html_dashboard
import base64

app = Flask(__name__)

# Password protection
PASSWORD = "ralphlauren7"

def check_auth(username, password):
    """Check if username/password combination is valid"""
    return username == "admin" and password == PASSWORD

def authenticate():
    """Send a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    """Decorator to require authentication"""
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route('/')
@requires_auth
def index():
    """Redirect to the report"""
    return '<script>window.location.href = "/credit_checker_report.html";</script>'

@app.route('/credit_checker_report.html')
@requires_auth
def credit_checker_report():
    """Generate and serve the credit checker report"""
    try:
        # Generate fresh report
        html_content = generate_html_dashboard()
        response = Response(html_content, mimetype='text/html')
        # Disable caching to ensure fresh content
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        return f"""
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error generating report</h1>
            <p>{str(e)}</p>
            <p><a href="/credit_checker_report.html">Try again</a></p>
        </body>
        </html>
        """, 500

@app.route('/overall_checked_claims.csv')
@requires_auth
def serve_overall_csv():
    """Serve the overall checked claims CSV file"""
    try:
        return send_file('overall_checked_claims.csv', 
                        as_attachment=True, 
                        download_name='overall_checked_claims.csv',
                        mimetype='text/csv')
    except FileNotFoundError:
        return "CSV file not found", 404

@app.route('/daily_claims_<date>.csv')
@requires_auth
def serve_daily_csv(date):
    """Serve daily claims CSV file"""
    try:
        filename = f'daily_claims_{date}.csv'
        return send_file(filename, 
                        as_attachment=True, 
                        download_name=filename,
                        mimetype='text/csv')
    except FileNotFoundError:
        return f"Daily CSV file for {date} not found", 404

@app.route('/status')
def status():
    """Simple status endpoint"""
    return {
        'status': 'running',
        'report': 'dynamic',
        'auto_refresh': True
    }

if __name__ == '__main__':
    print("🚀 Starting Dynamic Credit Checker Report Server...")
    print("📊 Report will regenerate on each request")
    print("🌐 Access at: http://localhost:5000/credit_checker_report.html")
    print("🔄 Auto-refresh: Every time you visit the page")
    
    # Kill any existing HTTP server on port 8000
    os.system("pkill -f 'python3 -m http.server 8000' 2>/dev/null || true")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
