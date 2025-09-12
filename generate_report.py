#!/usr/bin/env python3
"""
Credit Checker Report Generator
Generates an HTML report showing statistics for all CSV files
"""

import os
import csv
import glob
from datetime import datetime, timedelta
import json

def get_file_stats(filepath):
    """Get statistics for a CSV file"""
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        data_lines = total_lines - 1 if total_lines > 0 else 0  # Subtract header
        
        # Get file size
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        
        # Get modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        # Try to get keyword statistics if it's a data CSV
        keyword_stats = {}
        if data_lines > 0 and total_lines > 1:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                
                if rows:
                    # Count keyword found cases
                    keyword_found = sum(1 for row in rows if row.get('keyword_found', '').lower() == 'true')
                    no_keywords = sum(1 for row in rows if row.get('keyword_found', '').lower() == 'false')
                    
                    # Count image found cases
                    image_found = sum(1 for row in rows if row.get('image_found', '').lower() == 'true')
                    no_images = sum(1 for row in rows if row.get('image_found', '').lower() == 'false')
                    
                    keyword_stats = {
                        'with_keywords': keyword_found,
                        'without_keywords': no_keywords,
                        'success_rate': (keyword_found / len(rows) * 100) if len(rows) > 0 else 0,
                        'with_images': image_found,
                        'without_images': no_images,
                        'image_success_rate': (image_found / len(rows) * 100) if len(rows) > 0 else 0
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
    archived_files = []
    if os.path.exists('logs/archive'):
        archived_files = glob.glob('logs/archive/*.csv')
    return sorted(archived_files)

def generate_html_report():
    """Generate the HTML report"""
    
    # Get current time
    now = datetime.now()
    
    # Get file statistics
    overall_csv = get_overall_csv()
    daily_csvs = get_daily_csvs()
    archived_csvs = get_archived_csvs()
    
    # Get statistics
    overall_stats = get_file_stats(overall_csv)
    daily_stats = {f: get_file_stats(f) for f in daily_csvs}
    archived_stats = {f: get_file_stats(f) for f in archived_csvs}
    
    # Calculate totals from daily CSVs only
    total_daily_rows = sum(stats['data_lines'] for stats in daily_stats.values() if stats and 'data_lines' in stats)
    total_archived_cases = sum(stats['data_lines'] for stats in archived_stats.values() if stats and 'data_lines' in stats)
    
    # Calculate unique case IDs and combined statistics from all daily CSVs
    unique_case_ids = set()
    total_images_found = 0
    total_no_images = 0
    total_keywords_found = 0
    total_no_keywords = 0
    
    for filename, stats in daily_stats.items():
        if stats and 'error' not in stats:
            # Count unique case IDs from this file
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        case_id = row.get('case_id', '').strip()
                        if case_id:
                            unique_case_ids.add(case_id)
            except Exception as e:
                print(f"Warning: Could not read {filename} for case ID counting: {e}")
            
            # Get statistics from the stats
            if 'keyword_stats' in stats and 'error' not in stats.get('keyword_stats', {}):
                keyword_stats = stats['keyword_stats']
                total_images_found += keyword_stats.get('with_images', 0)
                total_no_images += keyword_stats.get('without_images', 0)
                total_keywords_found += keyword_stats.get('with_keywords', 0)
                total_no_keywords += keyword_stats.get('without_keywords', 0)
    
    total_unique_cases = len(unique_case_ids)
    total_hits = total_images_found + total_no_images
    image_success_rate = (total_images_found / total_hits * 100) if total_hits > 0 else 0
    keyword_success_rate = (total_keywords_found / total_hits * 100) if total_hits > 0 else 0
    
    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Credit Checker Report - {now.strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 1.1em;
        }}
        .file-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .file-table th, .file-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        .file-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        .file-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .status-good {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-warning {{
            color: #ffc107;
            font-weight: bold;
        }}
        .status-error {{
            color: #dc3545;
            font-weight: bold;
        }}
        .keyword-stats {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
        }}
        .keyword-stats h4 {{
            margin: 0 0 10px 0;
            color: #1976d2;
        }}
        .keyword-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }}
        .keyword-item {{
            text-align: center;
            padding: 10px;
            background: white;
            border-radius: 5px;
        }}
        .keyword-number {{
            font-size: 1.5em;
            font-weight: bold;
            color: #1976d2;
        }}
        .keyword-label {{
            font-size: 0.9em;
            color: #666;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }}
        .refresh-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
            margin: 20px 0;
        }}
        .refresh-btn:hover {{
            background: #5a6fd8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Credit Checker Report</h1>
            <p>Generated on {now.strftime('%A, %B %d, %Y at %I:%M %p')}</p>
            <p style="opacity: 0.8; font-size: 0.9em;">🔄 Auto-refreshes every 30 seconds</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📊 Overview Statistics (From Daily CSVs)</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_unique_cases}</div>
                        <div class="stat-label">Unique Cases Processed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_hits}</div>
                        <div class="stat-label">Total Hits Processed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len(daily_csvs)}</div>
                        <div class="stat-label">Daily CSV Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_images_found}</div>
                        <div class="stat-label">Images Found</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_keywords_found}</div>
                        <div class="stat-label">Keywords Found</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{image_success_rate:.1f}%</div>
                        <div class="stat-label">Image Success Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{keyword_success_rate:.1f}%</div>
                        <div class="stat-label">Keyword Success Rate</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📈 Overall Checked Claims</h2>
                <table class="file-table">
                    <thead>
                        <tr>
                            <th>File</th>
                            <th>File Size</th>
                            <th>Last Modified</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong><a href="http://localhost:8000/{overall_csv}" target="_blank" style="color: #667eea; text-decoration: none;">{overall_csv}</a></strong></td>
                            <td>{overall_stats['file_size_mb'] if overall_stats else 'N/A'} MB</td>
                            <td>{overall_stats['mod_time'] if overall_stats else 'N/A'}</td>
                            <td class="status-good">✓ Active</td>
                        </tr>
                    </tbody>
                </table>
"""
    
    # Add combined daily CSV statistics
    if total_unique_cases > 0:
        html += f"""
                <div class="keyword-stats">
                    <h4>🎯 Combined Daily CSV Analysis</h4>
                    <div class="keyword-grid">
                        <div class="keyword-item">
                            <div class="keyword-number">{total_keywords_found}</div>
                            <div class="keyword-label">Keywords Found</div>
                        </div>
                        <div class="keyword-item">
                            <div class="keyword-number">{total_no_keywords}</div>
                            <div class="keyword-label">No Keywords</div>
                        </div>
                        <div class="keyword-item">
                            <div class="keyword-number">{keyword_success_rate:.1f}%</div>
                            <div class="keyword-label">Keyword Success Rate</div>
                        </div>
                        <div class="keyword-item">
                            <div class="keyword-number">{total_images_found}</div>
                            <div class="keyword-label">Images Found</div>
                        </div>
                        <div class="keyword-item">
                            <div class="keyword-number">{total_no_images}</div>
                            <div class="keyword-label">No Images</div>
                        </div>
                        <div class="keyword-item">
                            <div class="keyword-number">{image_success_rate:.1f}%</div>
                            <div class="keyword-label">Image Success Rate</div>
                        </div>
                    </div>
                </div>
            """
    
    html += """
            </div>
            
            <div class="section">
                <h2>📅 Daily CSV Files</h2>
                <table class="file-table">
                    <thead>
                        <tr>
                            <th>File</th>
                            <th>File Size</th>
                            <th>Last Modified</th>
                            <th>Images Found</th>
                            <th>Keywords Found</th>
                            <th>Image Success Rate</th>
                            <th>Keyword Success Rate</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # Add daily CSV rows
    for filename in daily_csvs:
        stats = daily_stats.get(filename, {})
        if stats and 'error' not in stats:
            keyword_stats = stats.get('keyword_stats', {})
            success_rate = keyword_stats.get('success_rate', 0) if 'error' not in keyword_stats else 0
            keywords_found = keyword_stats.get('with_keywords', 0) if 'error' not in keyword_stats else 0
            images_found = keyword_stats.get('with_images', 0) if 'error' not in keyword_stats else 0
            image_success_rate = keyword_stats.get('image_success_rate', 0) if 'error' not in keyword_stats else 0
            
            status_class = "status-good" if success_rate > 0 else "status-warning"
            image_status_class = "status-good" if image_success_rate > 0 else "status-warning"
            
            html += f"""
                        <tr>
                            <td><strong><a href="http://localhost:8000/{filename}" target="_blank" style="color: #667eea; text-decoration: none;">{filename}</a></strong></td>
                            <td>{stats.get('file_size_mb', 'N/A')} MB</td>
                            <td>{stats.get('mod_time', 'N/A')}</td>
                            <td class="{image_status_class}">{images_found}</td>
                            <td class="{status_class}">{keywords_found}</td>
                            <td class="{image_status_class}">{image_success_rate:.1f}%</td>
                            <td class="{status_class}">{success_rate:.1f}%</td>
                        </tr>
            """
        else:
            html += f"""
                        <tr>
                            <td><strong><a href="http://localhost:8000/{filename}" target="_blank" style="color: #667eea; text-decoration: none;">{filename}</a></strong></td>
                            <td colspan="6" class="status-error">Error reading file</td>
                        </tr>
            """
    
    html += """
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>📁 Archived CSV Files</h2>
                <table class="file-table">
                    <thead>
                        <tr>
                            <th>File</th>
                            <th>Total Lines</th>
                            <th>Data Rows</th>
                            <th>File Size</th>
                            <th>Last Modified</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # Add archived CSV rows
    for filename in archived_csvs:
        stats = archived_stats.get(filename, {})
        if stats and 'error' not in stats:
            html += f"""
                        <tr>
                            <td><strong><a href="http://localhost:8000/{filename}" target="_blank" style="color: #667eea; text-decoration: none;">{os.path.basename(filename)}</a></strong></td>
                            <td>{stats.get('file_size_mb', 'N/A')} MB</td>
                            <td>{stats.get('mod_time', 'N/A')}</td>
                        </tr>
            """
        else:
            html += f"""
                        <tr>
                            <td><strong><a href="http://localhost:8000/{filename}" target="_blank" style="color: #667eea; text-decoration: none;">{os.path.basename(filename)}</a></strong></td>
                            <td colspan="2" class="status-error">Error reading file</td>
                        </tr>
            """
    
    html += f"""
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>🔄 System Status</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{len([f for f in daily_csvs if os.path.exists(f)])}</div>
                        <div class="stat-label">Active Daily Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len([f for f in daily_csvs if os.path.exists(f + '.lock')])}</div>
                        <div class="stat-label">Locked Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_archived_cases}</div>
                        <div class="stat-label">Archived Cases</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{now.strftime('%H:%M')}</div>
                        <div class="stat-label">Last Updated</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Credit Checker System Report | Generated by generate_report.py</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Report</button>
        </div>
    </div>
</body>
</html>
"""
    
    return html

def main():
    """Main function"""
    print("🔍 Generating Credit Checker Report...")
    
    # Generate HTML report
    html_content = generate_html_report()
    
    # Write to file
    output_file = 'credit_checker_report.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Report generated: {output_file}")
    print(f"🌐 Open in browser: file://{os.path.abspath(output_file)}")
    print(f"📊 Or run: open {output_file}")

if __name__ == "__main__":
    main()
