#!/usr/bin/env python3
"""
Credit Checker Report Server
Combines report generation and static serving in one file
"""

import os
import csv
import glob
import sys
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json

def get_file_stats(filepath):
    """Get statistics for a CSV file"""
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        # Count valid data rows using proper CSV parsing
        data_lines = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if essential fields are present (very lenient validation)
                if (row.get('case_id') and
                    row.get('case_url') and
                    row.get('hit_number') and
                    row.get('image_found') and
                    row.get('keyword_found')):
                    data_lines += 1

        # Get file size
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)

        # Get modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))

        # Try to get keyword statistics if it's a data CSV - use proper CSV parsing
        keyword_stats = {}
        if data_lines > 0 and total_lines > 1:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    valid_rows = []

                    for row in reader:
                        # Check if essential fields are present (very lenient validation)
                        if (row.get('case_id') and
                            row.get('case_url') and
                            row.get('hit_number') and
                            row.get('image_found') and
                            row.get('keyword_found')):
                            valid_rows.append(row)

                    if valid_rows:
                        # Count keyword found cases
                        keyword_found = sum(1 for row in valid_rows if row.get('keyword_found', '').lower() == 'true')
                        no_keywords = sum(1 for row in valid_rows if row.get('keyword_found', '').lower() == 'false')

                        # Count image found cases
                        image_found = sum(1 for row in valid_rows if row.get('image_found', '').lower() == 'true')
                        no_images = sum(1 for row in valid_rows if row.get('image_found', '').lower() == 'false')

                        keyword_stats = {
                            'with_keywords': keyword_found,
                            'without_keywords': no_keywords,
                            'success_rate': (keyword_found / len(valid_rows) * 100) if len(valid_rows) > 0 else 0,
                            'with_images': image_found,
                            'without_images': no_images,
                            'image_success_rate': (image_found / len(valid_rows) * 100) if len(valid_rows) > 0 else 0
                        }
            except Exception as e:
                keyword_stats = {'error': str(e)}

        return {
            'total_lines': total_lines,
            'data_lines': data_lines,
            'file_size_mb': round(file_size_mb, 2),
            'mod_time': mod_time.strftime('%Y-%m-%d %H:%M:%S'),
            'keyword_stats': keyword_stats
        }
    except Exception as e:
        return {'error': str(e)}

def get_daily_csvs():
    """Get all daily CSV files"""
    daily_files = glob.glob('daily_claims_*.csv')
    daily_files.sort()
    return daily_files

def get_overall_csv():
    """Get overall CSV file"""
    return 'overall_checked_claims.csv'

def get_archived_csvs():
    """Get archived CSV files"""
    archived_files = glob.glob('logs/archive/*.csv')
    archived_files.sort()
    return archived_files

def get_recent_activity():
    """Get recent activity from logs"""
    try:
        log_files = glob.glob('logs/*.log')
        if not log_files:
            return []

        # Get the most recent log file
        latest_log = max(log_files, key=os.path.getmtime)

        with open(latest_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-20:]  # Get last 20 lines

        # Parse log lines for activity
        activities = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['scrape', 'check', 'upload', 'comment', 'error']):
                activities.append(line.strip())

        return activities[-10:]  # Return last 10 relevant activities
    except:
        return []

def generate_html_dashboard():
    """Generate HTML dashboard"""
    # Get file statistics
    daily_csvs = get_daily_csvs()
    overall_csv = get_overall_csv()
    archived_csvs = get_archived_csvs()

    # Collect statistics
    daily_stats = []
    for csv_file in daily_csvs[-7:]:  # Last 7 days
        stats = get_file_stats(csv_file)
        if stats:
            daily_stats.append({
                'filename': os.path.basename(csv_file),
                'stats': stats
            })

    overall_stats = get_file_stats(overall_csv)
    archived_stats = []
    for csv_file in archived_csvs[-5:]:  # Last 5 archived files
        stats = get_file_stats(csv_file)
        if stats:
            archived_stats.append({
                'filename': os.path.basename(csv_file),
                'stats': stats
            })

    # Get recent activity
    recent_activity = get_recent_activity()

    # Calculate totals
    total_cases = sum(stat['stats']['data_lines'] for stat in daily_stats) if daily_stats else 0
    total_overall = overall_stats['data_lines'] if overall_stats else 0
    total_archived = sum(stat['stats']['data_lines'] for stat in archived_stats) if archived_stats else 0

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Credit Checker Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }}

        .stat-card {{
            background: #f8fafc;
            border-radius: 8px;
            padding: 25px;
            border-left: 4px solid #4f46e5;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}

        .stat-card h3 {{
            color: #1e293b;
            margin-bottom: 15px;
            font-size: 1.2rem;
            font-weight: 600;
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #4f46e5;
            margin-bottom: 10px;
        }}

        .stat-detail {{
            color: #64748b;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }}

        .file-list {{
            margin-top: 20px;
        }}

        .file-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: white;
            border-radius: 6px;
            margin-bottom: 8px;
            border: 1px solid #e2e8f0;
        }}

        .file-name {{
            font-weight: 500;
            color: #334155;
        }}

        .file-stats {{
            font-size: 0.85rem;
            color: #64748b;
        }}

        .activity-section {{
            padding: 30px;
            background: #f8fafc;
        }}

        .activity-section h2 {{
            color: #1e293b;
            margin-bottom: 20px;
            font-size: 1.5rem;
            font-weight: 600;
        }}

        .activity-list {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}

        .activity-item {{
            padding: 15px 20px;
            border-bottom: 1px solid #e2e8f0;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85rem;
            color: #475569;
        }}

        .activity-item:last-child {{
            border-bottom: none;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            background: #f8fafc;
            color: #64748b;
            font-size: 0.9rem;
        }}

        .success-rate {{
            color: #10b981;
            font-weight: 600;
        }}

        .error-rate {{
            color: #ef4444;
            font-weight: 600;
        }}

        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}

            .header h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Credit Checker Dashboard</h1>
            <p>Real-time monitoring of credit checking operations</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>📊 Daily Cases (Last 7 Days)</h3>
                <div class="stat-value">{total_cases:,}</div>
                <div class="stat-detail">Total cases processed recently</div>
                <div class="file-list">
"""

    # Add daily file details
    for stat in daily_stats:
        html += f"""
                    <div class="file-item">
                        <span class="file-name">{stat['filename']}</span>
                        <span class="file-stats">{stat['stats']['data_lines']:,} cases • {stat['stats']['file_size_mb']:.1f}MB</span>
                    </div>"""

    html += f"""
                </div>
            </div>

            <div class="stat-card">
                <h3>📈 Overall Database</h3>
                <div class="stat-value">{total_overall:,}</div>
                <div class="stat-detail">Total cases in main database</div>"""

    if overall_stats and 'keyword_stats' in overall_stats and overall_stats['keyword_stats']:
        keyword_stats = overall_stats['keyword_stats']
        if 'success_rate' in keyword_stats:
            html += f"""
                <div class="stat-detail">Keyword detection: <span class="success-rate">{keyword_stats['success_rate']:.1f}%</span></div>
                <div class="stat-detail">Image detection: <span class="success-rate">{keyword_stats['image_success_rate']:.1f}%</span></div>"""

    html += f"""
            </div>

            <div class="stat-card">
                <h3>📚 Archived Data</h3>
                <div class="stat-value">{total_archived:,}</div>
                <div class="stat-detail">Cases in archived files</div>
                <div class="file-list">
"""

    # Add archived file details
    for stat in archived_stats:
        html += f"""
                    <div class="file-item">
                        <span class="file-name">{stat['filename']}</span>
                        <span class="file-stats">{stat['stats']['data_lines']:,} cases • {stat['stats']['file_size_mb']:.1f}MB</span>
                    </div>"""

    html += f"""
                </div>
            </div>
        </div>

        <div class="activity-section">
            <h2>🔄 Recent Activity</h2>
            <div class="activity-list">
"""

    # Add recent activity
    if recent_activity:
        for activity in recent_activity:
            html += f"""                <div class="activity-item">{activity}</div>
"""
    else:
        html += """                <div class="activity-item">No recent activity found</div>
"""

    html += f"""
            </div>
        </div>

        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Credit Checker System</p>
        </div>
    </div>
</body>
</html>"""

    return html

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
        print("🚀 Starting Simple Credit Checker Report Server...")
        print(f"📊 Generating report...")
        generate_and_save_report()
        print("🌐 Starting static server...")
        print(f"📊 Report available at: http://localhost:{port}")
        print(f"📊 Report available at: http://0.0.0.0:{port}")
        print(f"📄 Serving static HTML file: credit_checker_report.html")
        print("⏹️  Press Ctrl+C to stop")

        server.serve_forever()

    except KeyboardInterrupt:
        print("\n⏹️  Server stopped")
        print("✅ Static report server stopped!")
    except Exception as e:
        print(f"❌ Server error: {e}")

def generate_and_save_report():
    """Generate and save the HTML report"""
    try:
        html_content = generate_html_dashboard()
        with open('credit_checker_report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("✅ Report generated")
    except Exception as e:
        print(f"❌ Failed to generate report: {e}")
        raise

def main():
    """Main function"""
    port = 8080

    # Check if port is specified
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid port number. Using default port 8080")

    # Generate report
    generate_and_save_report()

    # Start server
    start_server(port)


if __name__ == "__main__":
    main()