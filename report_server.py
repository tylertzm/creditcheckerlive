#!/usr/bin/env python3
"""
Credit Checker Report Server
Generates HTML matching dashboard structure for live updates
"""

import os
import csv
import glob
import sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

def get_file_stats(filepath):
    """Get statistics for a CSV file"""
    if not os.path.exists(filepath):
        return None

    csv.field_size_limit(sys.maxsize)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        data_lines = 0
        images_found = 0
        keywords_found = 0

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row.get('case_id') and row.get('case_url') and 'image_found' in row and 'keyword_found' in row):
                    data_lines += 1
                    if row.get('image_found', '').strip().lower() == 'true':
                        images_found += 1
                    if row.get('keyword_found', '').strip().lower() == 'true':
                        keywords_found += 1

        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))

        return {
            'total_lines': total_lines,
            'data_lines': data_lines,
            'file_size_mb': file_size_mb,
            'mod_time': mod_time,
            'images_found': images_found,
            'keywords_found': keywords_found
        }
    except:
        return None

def get_daily_csvs():
    """Get all daily CSV files"""
    daily_files = glob.glob('daily_claims_*.csv')
    daily_files.sort()
    return daily_files

def generate_html_dashboard():
    """Generate HTML dashboard matching the dashboard structure"""
    daily_csvs = get_daily_csvs()

    # Calculate overall statistics
    total_unique_cases = set()
    total_hits = 0
    total_images_found = 0
    total_keywords_found = 0

    for csv_file in daily_csvs:
        stats = get_file_stats(csv_file)
        if stats:
            total_hits += stats.get('data_lines', 0)
            total_images_found += stats.get('images_found', 0)
            total_keywords_found += stats.get('keywords_found', 0)
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        case_id = row.get('case_id')
                        if case_id:
                            total_unique_cases.add(case_id)
            except:
                pass

    unique_cases_count = len(total_unique_cases)
    image_success_rate = (total_images_found / total_hits * 100) if total_hits > 0 else 0
    keyword_success_rate = (total_keywords_found / total_hits * 100) if total_hits > 0 else 0

    # Today's statistics
    today = datetime.now().date()
    today_csv = f'daily_claims_{today}.csv'
    today_stats = get_file_stats(today_csv)
    today_total_claims = today_stats.get('data_lines', 0) if today_stats else 0
    today_unique_cases = set()
    today_images_found = today_stats.get('images_found', 0) if today_stats else 0
    today_keywords_found = today_stats.get('keywords_found', 0) if today_stats else 0
    try:
        with open(today_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                case_id = row.get('case_id')
                if case_id:
                    today_unique_cases.add(case_id)
    except:
        pass
    today_unique_count = len(today_unique_cases)
    today_image_rate = (today_images_found / today_total_claims * 100) if today_total_claims > 0 else 0
    today_keyword_rate = (today_keywords_found / today_total_claims * 100) if today_total_claims > 0 else 0

    # Generate daily files table
    daily_table_rows = ""
    for csv_file in sorted(daily_csvs, key=lambda x: os.path.getmtime(x), reverse=True)[:20]:
        stats = get_file_stats(csv_file)
        if stats:
            filename = os.path.basename(csv_file)
            mod_time = stats.get('mod_time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
            file_size_mb = stats.get('file_size_mb', 0)
            data_lines = stats.get('data_lines', 0)
            images_found = stats.get('images_found', 0)
            keywords_found = stats.get('keywords_found', 0)
            img_rate = (images_found / data_lines * 100) if data_lines > 0 else 0
            kw_rate = (keywords_found / data_lines * 100) if data_lines > 0 else 0
            daily_table_rows += f"""
                            <tr>
                                <td><a href="/{filename}" class="file-link">{filename}</a></td>
                                <td>{data_lines}</td>
                                <td>{file_size_mb:.2f} MB</td>
                                <td>{mod_time}</td>
                                <td>{images_found}</td>
                                <td>{keywords_found}</td>
                                <td>{img_rate:.1f}%</td>
                                <td>{kw_rate:.1f}%</td>
                            </tr>"""

    # Generate HTML matching dashboard structure
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Credit Checker Dashboard</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 20px;
            background-attachment: fixed;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-rows: auto 1fr;
            gap: 25px;
            min-height: calc(100vh - 40px);
        }}
        
        .header {{
            text-align: center;
            padding: 30px 20px;
            background: rgba(30, 41, 59, 0.8);
            border-radius: 16px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(148, 163, 184, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            font-weight: 700;
            background: linear-gradient(135deg, #60a5fa, #a78bfa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .header p {{
            color: #94a3b8;
            font-size: 1em;
            font-weight: 400;
            opacity: 0.9;
        }}
        
        .content {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 25px;
            height: 100%;
            overflow: hidden;
        }}
        
        .left-panel {{
            display: flex;
            flex-direction: column;
            gap: 25px;
            overflow: auto;
            scrollbar-width: thin;
            scrollbar-color: rgba(148, 163, 184, 0.3) transparent;
        }}
        
        .left-panel::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .left-panel::-webkit-scrollbar-track {{
            background: transparent;
        }}
        
        .left-panel::-webkit-scrollbar-thumb {{
            background: rgba(148, 163, 184, 0.3);
            border-radius: 3px;
        }}
        
        .right-panel {{
            background: rgba(30, 41, 59, 0.8);
            padding: 25px;
            border-radius: 16px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(148, 163, 184, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            overflow: auto;
            scrollbar-width: thin;
            scrollbar-color: rgba(148, 163, 184, 0.3) transparent;
        }}
        
        .right-panel::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .right-panel::-webkit-scrollbar-track {{
            background: transparent;
        }}
        
        .right-panel::-webkit-scrollbar-thumb {{
            background: rgba(148, 163, 184, 0.3);
            border-radius: 3px;
        }}
        
        .section {{
            background: rgba(30, 41, 59, 0.8);
            padding: 25px;
            border-radius: 16px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(148, 163, 184, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .section:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }}
        
        .section-title {{
            font-size: 1.2em;
            font-weight: 600;
            color: #f8fafc;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(96, 165, 250, 0.3);
        }}
        
        .section-title::before {{
            content: "📊";
            font-size: 1.1em;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
        }}
        
        .metric {{
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, rgba(51, 65, 85, 0.8), rgba(30, 41, 59, 0.8));
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .metric::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #60a5fa, #a78bfa, #34d399);
        }}
        
        .metric:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(96, 165, 250, 0.2);
            border-color: rgba(96, 165, 250, 0.4);
        }}
        
        .metric-value {{
            font-size: 2.2em;
            font-weight: 700;
            background: linear-gradient(135deg, #60a5fa, #a78bfa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .metric-label {{
            font-size: 0.85em;
            color: #94a3b8;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .table {{
            width: 100%;
        }}
        
        .table th {{
            text-align: left;
            padding: 8px 12px;
            color: #6b7280;
            font-size: 0.8em;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: rgba(30, 41, 59, 0.8);
        }}
        
        .table td {{
            padding: 10px 12px;
            color: #e2e8f0;
            background: rgba(30, 41, 59, 0.5);
            font-size: 0.9em;
        }}
        
        .table tr:hover {{
            background: rgba(96, 165, 250, 0.1);
        }}
        
        .file-link {{
            color: #60a5fa;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .file-link:hover {{
            color: #93c5fd;
        }}
        
        .status-active {{
            background: #065f46;
            color: #10b981;
            padding: 4px 8px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        
        .info-grid {{
            display: grid;
            gap: 12px;
        }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            color: #9ca3af;
            font-size: 0.9em;
            background: rgba(30, 41, 59, 0.5);
        }}
        
        .info-value {{
            color: #e2e8f0;
            font-weight: 600;
        }}
        
        .download-btn {{
            background: #065f46;
            color: #10b981;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8em;
            transition: all 0.3s ease;
        }}
        
        .download-btn:hover {{
            background: #10b981;
            color: #000000;
        }}
        
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.3); }}
            100% {{ transform: scale(1.2); }}
        }}
        
        @keyframes glow {{
            0% {{ text-shadow: 0 0 5px #10b981; }}
            50% {{ text-shadow: 0 0 20px #10b981, 0 0 30px #10b981; }}
            100% {{ text-shadow: 0 0 5px #10b981; }}
        }}
        
        @keyframes numberCount {{
            0% {{ transform: scale(0.8); opacity: 0.7; }}
            50% {{ transform: scale(1.1); opacity: 1; }}
            100% {{ transform: scale(1); opacity: 1; }}
        }}
        
        @keyframes slideInUp {{
            0% {{ transform: translateY(20px); opacity: 0; }}
            100% {{ transform: translateY(0); opacity: 1; }}
        }}
        
        @keyframes bounce {{
            0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
            40% {{ transform: translateY(-10px); }}
            60% {{ transform: translateY(-5px); }}
        }}
        
        @keyframes shimmer {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}
        
        .metric-value {{
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        .metric-value.updating {{
            animation: numberCount 0.6s ease-out, glow 1s ease-in-out;
            color: #10b981 !important;
            text-shadow: 0 0 15px #10b981;
        }}
        
        .metric-value.changed {{
            animation: bounce 0.8s ease-out;
            background: linear-gradient(45deg, #065f46, #10b981, #065f46);
            background-size: 200% 200%;
            animation: shimmer 1.5s ease-in-out, bounce 0.8s ease-out;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .metric-label {{
            transition: all 0.3s ease;
        }}
        
        .metric-label.updating {{
            color: #10b981;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>Credit Checker Dashboard</h1>
            <p>{datetime.now().strftime('%B %d, %Y • %H:%M:%S')} • Live updates every 10s</p>
        </div>

        <div class="content">
            <div class="left-panel">
                <!-- Overview Statistics -->
                <div class="section">
                    <div class="section-title">Overview Statistics (From Overall Data)</div>
                    <div class="metrics-grid">
                        <div class="metric">
                            <div class="metric-value">{unique_cases_count}</div>
                            <div class="metric-label">Unique Cases Processed</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{total_hits}</div>
                            <div class="metric-label">Total Hits Processed</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{len(daily_csvs)}</div>
                            <div class="metric-label">Daily CSV Files</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{total_images_found}</div>
                            <div class="metric-label">Images Found</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{total_keywords_found}</div>
                            <div class="metric-label">Keywords Found</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{image_success_rate:.1f}%</div>
                            <div class="metric-label">Image Success Rate</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{keyword_success_rate:.1f}%</div>
                            <div class="metric-label">Keyword Success Rate</div>
                        </div>
                    </div>
                </div>

                <!-- Today's Claims Statistics -->
                <div class="section">
                    <div class="section-title" style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Today's Claims Statistics ({today})</span>
                        <a href="/overall_checked_claims.csv" class="download-btn">
                            Download Overall Claims CSV
                        </a>
                    </div>
                    <div style="background: #1f2937; border-left: 4px solid #f59e0b; padding: 12px; margin-bottom: 20px; border-radius: 4px;">
                        <div style="color: #fbbf24; font-weight: 600; margin-bottom: 8px;">Data Accuracy Notice</div>
                        <div style="color: #d1d5db; font-size: 0.9em; line-height: 1.4;">
                            Today's statistics may contain processing errors and should be considered preliminary.
                            For accurate and reliable data, please refer to the overall dataset which undergoes
                            comprehensive validation and quality assurance processes.
                        </div>
                    </div>
                    <div class="metrics-grid" style="margin-bottom: 20px;">
                        <div class="metric">
                            <div class="metric-value">{today_total_claims}</div>
                            <div class="metric-label">Total Claims Processed</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{today_unique_count}</div>
                            <div class="metric-label">Unique Cases</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{today_images_found}</div>
                            <div class="metric-label">Images Found</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{today_keywords_found}</div>
                            <div class="metric-label">Keywords Found</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{today_image_rate:.1f}%</div>
                            <div class="metric-label">Image Success Rate</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{today_keyword_rate:.1f}%</div>
                            <div class="metric-label">Keyword Success Rate</div>
                        </div>
                    </div>
                </div>

                <!-- Daily CSV Files -->
                <div class="section">
                    <div class="section-title">Daily CSV Files</div>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>File</th>
                                <th>Total Processed Hits</th>
                                <th>File Size</th>
                                <th>Last Modified</th>
                                <th>Images Found</th>
                                <th>Keywords Found</th>
                                <th>Image Success Rate</th>
                                <th>Keyword Success Rate</th>
                            </tr>
                        </thead>
                        <tbody>
{daily_table_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="right-panel">
                <!-- System Status -->
                <div class="section-title">System Status</div>
                <div class="info-grid">
                    <div class="info-row">
                        <span>Active Daily Files</span>
                        <span class="info-value">{len(daily_csvs)}</span>
                    </div>
                    <div class="info-row">
                        <span>Locked Files</span>
                        <span class="info-value">0</span>
                    </div>
                    <div class="info-row">
                        <span>Archived Cases</span>
                        <span class="info-value">0</span>
                    </div>
                    <div class="info-row">
                        <span>Last Updated</span>
                        <span class="info-value">{datetime.now().strftime('%H:%M')}</span>
                    </div>
                </div>

                <button class="refresh-btn" onclick="location.reload()">Refresh Report</button>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html

class StaticReportHandler(SimpleHTTPRequestHandler):
    """Handler that serves static files"""

    def do_GET(self):
        if self.path == '/' or self.path == '/report':
            self.path = '/credit_checker_report.html'
        return super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        if self.path.endswith('.html') or self.path.endswith('.csv'):
            super().log_message(format, *args)

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
    """Main function - run as continuous server"""
    import time
    import threading
    
    # Generate initial report
    generate_and_save_report()
    
    # Start server in background thread
    def run_server():
        try:
            server = HTTPServer(('0.0.0.0', 5000), StaticReportHandler)
            print("📊 Report server started on http://0.0.0.0:5000")
            server.serve_forever()
        except Exception as e:
            print(f"❌ Report server error: {e}")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Update report every 30 seconds
    print("🔄 Report will update every 30 seconds...")
    while True:
        time.sleep(30)
        try:
            generate_and_save_report()
        except Exception as e:
            print(f"❌ Failed to update report: {e}")

if __name__ == "__main__":
    main()