#!/usr/bin/env python3
"""
Credit Checker Dashboard Generator
Generates a clean viewport-contained dashboard HTML report
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
        # Count only rows with exactly 13 fields (valid data rows)
        data_lines = 0
        for line in lines[1:]:  # Skip header
            parts = line.strip().split(',')
            if len(parts) == 13:
                data_lines += 1
        
        # Get file size
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        
        # Get modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        # Try to get keyword statistics if it's a data CSV - only count rows with 7 fields
        keyword_stats = {}
        if data_lines > 0 and total_lines > 1:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        header = lines[0].strip().split(',')
                        valid_rows = []
                        
                        # Only process rows with exactly 13 fields
                        for line in lines[1:]:
                            parts = line.strip().split(',')
                            if len(parts) == 13:
                                valid_rows.append(parts)
                        
                        if valid_rows:
                            # Count keyword found cases (column 7, index 6)
                            keyword_found = sum(1 for row in valid_rows if len(row) > 6 and row[6].lower() == 'true')
                            no_keywords = sum(1 for row in valid_rows if len(row) > 6 and row[6].lower() == 'false')
                            
                            # Count image found cases (column 6, index 5)
                            image_found = sum(1 for row in valid_rows if len(row) > 5 and row[5].lower() == 'true')
                            no_images = sum(1 for row in valid_rows if len(row) > 5 and row[5].lower() == 'false')
                            
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
    archived_files = []
    if os.path.exists('logs/archive'):
        archived_files = glob.glob('logs/archive/*.csv')
    return sorted(archived_files)

def get_overall_statistics():
    """Get comprehensive statistics from the overall CSV file"""
    overall_csv = get_overall_csv()
    if not os.path.exists(overall_csv):
        return None
    
    try:
        with open(overall_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return None
        
        # Calculate statistics
        total_claims = len(rows)
        images_found = sum(1 for row in rows if row.get('image_found', '').lower() == 'true')
        keywords_found = sum(1 for row in rows if row.get('keyword_found', '').lower() == 'true')
        success_cases = sum(1 for row in rows if row.get('error_status', '').lower() == 'success')
        error_cases = sum(1 for row in rows if row.get('error_status', '').lower() not in ['success', ''])
        
        # Calculate success rates
        image_success_rate = (images_found / total_claims * 100) if total_claims > 0 else 0
        keyword_success_rate = (keywords_found / total_claims * 100) if total_claims > 0 else 0
        overall_success_rate = (success_cases / total_claims * 100) if total_claims > 0 else 0
        
        # Get date range
        processed_dates = []
        for row in rows:
            processed_at = row.get('processed_at', '')
            if processed_at:
                try:
                    # Extract date from timestamp
                    date_str = processed_at.split(' ')[0]
                    processed_dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
                except:
                    continue
        
        date_range = "N/A"
        if processed_dates:
            min_date = min(processed_dates)
            max_date = max(processed_dates)
            date_range = f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        
        # Get unique case IDs
        unique_cases = len(set(row.get('case_id', '') for row in rows if row.get('case_id')))
        
        return {
            'total_claims': total_claims,
            'unique_cases': unique_cases,
            'images_found': images_found,
            'keywords_found': keywords_found,
            'success_cases': success_cases,
            'error_cases': error_cases,
            'image_success_rate': image_success_rate,
            'keyword_success_rate': keyword_success_rate,
            'overall_success_rate': overall_success_rate,
            'date_range': date_range
        }
        
    except Exception as e:
        return {'error': str(e)}

def generate_html_dashboard():
    """Generate the clean viewport dashboard HTML"""
    
    # Get current time in local timezone
    from datetime import timezone, timedelta
    local_tz = timezone(timedelta(hours=2))  # UTC+2 timezone
    now = datetime.now(local_tz)
    
    # Get file statistics
    overall_csv = get_overall_csv()
    daily_csvs = get_daily_csvs()
    archived_csvs = get_archived_csvs()
    
    # Get statistics
    overall_stats = get_file_stats(overall_csv)
    overall_statistics = get_overall_statistics()
    daily_stats = {f: get_file_stats(f) for f in daily_csvs}
    archived_stats = {f: get_file_stats(f) for f in archived_csvs}
    
    # Calculate totals from TODAY'S daily CSV only - count only rows with 13 fields
    today = now.strftime('%Y-%m-%d')
    today_csv = f'daily_claims_{today}.csv'
    total_daily_rows = 0
    
    if os.path.exists(today_csv):
        try:
            with open(today_csv, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    # Count only rows with exactly 13 fields
                    for line in lines[1:]:
                        parts = line.strip().split(',')
                        if len(parts) == 13:
                            total_daily_rows += 1
        except Exception as e:
            print(f"Warning: Could not count valid rows in {today_csv}: {e}")
    # Calculate archived cases using the same robust parsing
    total_archived_cases = 0
    for filename, stats in archived_stats.items():
        if stats and 'error' not in stats:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        # Count only rows with exactly 13 fields
                        valid_rows = 0
                        for line in lines[1:]:
                            parts = line.strip().split(',')
                            if len(parts) == 13:
                                valid_rows += 1
                        total_archived_cases += valid_rows
            except Exception as e:
                print(f"Warning: Could not count valid rows in {filename}: {e}")
    
    # Calculate TODAY'S statistics for the "Today's Claims Statistics" section
    today_unique_cases = 0
    today_images_found = 0
    today_no_images = 0
    today_keywords_found = 0
    today_no_keywords = 0
    
    # Only process today's CSV file
    if os.path.exists(today_csv):
        try:
            with open(today_csv, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) > 1:  # Skip if only header
                    unique_case_ids = set()
                    for line_num, line in enumerate(lines[1:], 2):
                        try:
                            # Split by comma and check if we have exactly 13 fields
                            parts = line.strip().split(',')
                            if len(parts) == 13:
                                case_id = parts[0].strip()
                                if case_id and case_id.isdigit():
                                    unique_case_ids.add(case_id)
                                
                                # Count images and keywords from today's data
                                if len(parts) > 5 and parts[5].lower() == 'true':
                                    today_images_found += 1
                                elif len(parts) > 5 and parts[5].lower() == 'false':
                                    today_no_images += 1
                                    
                                if len(parts) > 6 and parts[6].lower() == 'true':
                                    today_keywords_found += 1
                                elif len(parts) > 6 and parts[6].lower() == 'false':
                                    today_no_keywords += 1
                        except Exception as e:
                            # Skip malformed lines
                            continue
                    today_unique_cases = len(unique_case_ids)
        except Exception as e:
            print(f"Warning: Could not read {today_csv} for statistics: {e}")
    
    # Calculate today's success rates
    today_processed_images = today_images_found + today_no_images
    today_processed_keywords = today_keywords_found + today_no_keywords
    today_image_success_rate = (today_images_found / today_processed_images * 100) if today_processed_images > 0 else 0
    today_keyword_success_rate = (today_keywords_found / today_processed_keywords * 100) if today_processed_keywords > 0 else 0
    
    # Use overall statistics for the main overview section
    if overall_statistics and 'error' not in overall_statistics:
        total_unique_cases = overall_statistics['unique_cases']
        total_hits = overall_statistics['total_claims']
        total_images_found = overall_statistics['images_found']
        total_keywords_found = overall_statistics['keywords_found']
        image_success_rate = overall_statistics['image_success_rate']
        keyword_success_rate = overall_statistics['keyword_success_rate']
    else:
        # Fallback to daily CSV calculation if overall stats unavailable
        unique_case_ids = set()
        total_images_found = 0
        total_no_images = 0
        total_keywords_found = 0
        total_no_keywords = 0
        
        for filename, stats in daily_stats.items():
            if stats and 'error' not in stats:
                # Count unique case IDs from this file - only count rows with 13 fields
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # Skip if only header
                            for line_num, line in enumerate(lines[1:], 2):
                                try:
                                    # Split by comma and check if we have exactly 13 fields
                                    parts = line.strip().split(',')
                                    if len(parts) == 13:
                                        case_id = parts[0].strip()
                                        if case_id and case_id.isdigit():
                                            unique_case_ids.add(case_id)
                                except Exception as e:
                                    # Skip malformed lines
                                    continue
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
        # Calculate actual processed rows (those with True/False values)
        total_processed_images = total_images_found + total_no_images
        total_processed_keywords = total_keywords_found + total_no_keywords
        total_hits = total_daily_rows  # Total data rows
        image_success_rate = (total_images_found / total_processed_images * 100) if total_processed_images > 0 else 0
        keyword_success_rate = (total_keywords_found / total_processed_keywords * 100) if total_processed_keywords > 0 else 0
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Credit Checker Dashboard</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background: #000000;
            color: #e2e8f0;
            height: 100vh;
            overflow: hidden;
            padding: 20px;
        }}
        
        .dashboard {{
            height: 100%;
            display: grid;
            grid-template-rows: auto 1fr;
            gap: 20px;
        }}
        
        .header {{
            text-align: center;
            padding: 10px 0;
        }}
        
        .header h1 {{
            font-size: 1.8em;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 4px;
        }}
        
        .header p {{
            color: #94a3b8;
            font-size: 0.9em;
        }}
        
        .content {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            height: 100%;
            overflow: hidden;
        }}
        
        .left-panel {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            overflow: auto;
        }}
        
        .right-panel {{
            background: #000000;
            padding: 20px;
            overflow: auto;
        }}
        
        .section {{
            background: #000000;
            padding: 20px;
        }}
        
        .section-title {{
            font-size: 1.1em;
            font-weight: 600;
            color: #f8fafc;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 15px;
        }}
        
        .metric {{
            text-align: center;
            padding: 15px;
            background: #000000;
        }}
        
        .metric-value {{
            font-size: 1.8em;
            font-weight: 700;
            color: #9CAF88;
            margin-bottom: 4px;
        }}
        
        .metric-label {{
            font-size: 0.8em;
            color: #9ca3af;
            font-weight: 500;
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
            background: #000000;
        }}
        
        .table td {{
            padding: 10px 12px;
            color: #e2e8f0;
            background: #000000;
            font-size: 0.9em;
        }}
        
        .table tr:hover {{
            background: #000000;
        }}
        
        .file-link {{
            color: #9CAF88;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .file-link:hover {{
            color: #87A96B;
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
            background: #000000;
        }}
        
        .info-value {{
            color: #e2e8f0;
            font-weight: 600;
        }}
        
        .refresh-btn {{
            width: 100%;
            padding: 10px;
            background: #000000;
            color: white;
            font-weight: 500;
            cursor: pointer;
            margin-top: 15px;
        }}
        
        .refresh-btn:hover {{
            background: #000000;
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
            <p>{now.strftime('%B %d, %Y • %H:%M')} • Live updates every 3s</p>
        </div>
        
        <div class="content">
            <div class="left-panel">
                <!-- Overview Statistics -->
                <div class="section">
                    <div class="section-title">Overview Statistics (From Overall Data)</div>
                    <div class="metrics-grid">
                        <div class="metric">
                            <div class="metric-value">{total_unique_cases}</div>
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
                        <a href="/overall_checked_claims.csv" class="download-btn" style="
                            background: #065f46;
                            color: #10b981;
                            padding: 8px 16px;
                            text-decoration: none;
                            border-radius: 4px;
                            font-weight: 600;
                            font-size: 0.8em;
                            transition: all 0.3s ease;
                        " onmouseover="this.style.background='#10b981'; this.style.color='#000000';" onmouseout="this.style.background='#065f46'; this.style.color='#10b981';">
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
                            <div class="metric-value">{total_daily_rows}</div>
                            <div class="metric-label">Total Claims Processed</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{today_unique_cases}</div>
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
                            <div class="metric-value">{today_image_success_rate:.1f}%</div>
                            <div class="metric-label">Image Success Rate</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{today_keyword_success_rate:.1f}%</div>
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
                        <tbody>"""

    # Add daily CSV files
    for filename in daily_csvs:
        stats = daily_stats.get(filename, {})
        if stats and 'error' not in stats:
            keyword_stats = stats.get('keyword_stats', {})
            success_rate = keyword_stats.get('success_rate', 0) if 'error' not in keyword_stats else 0
            keywords_found = keyword_stats.get('with_keywords', 0) if 'error' not in keyword_stats else 0
            images_found = keyword_stats.get('with_images', 0) if 'error' not in keyword_stats else 0
            image_success_rate_daily = keyword_stats.get('image_success_rate', 0) if 'error' not in keyword_stats else 0
            
            # Get total processed hits for this file
            total_processed_hits = stats.get('data_lines', 0)
            
            html += f"""
                            <tr>
                                <td><a href="/{filename}" class="file-link">{filename}</a></td>
                                <td>{total_processed_hits}</td>
                                <td>{stats.get('file_size_mb', 'N/A')} MB</td>
                                <td>{stats.get('mod_time', 'N/A')}</td>
                                <td>{images_found}</td>
                                <td>{keywords_found}</td>
                                <td>{image_success_rate_daily:.1f}%</td>
                                <td>{success_rate:.1f}%</td>
                            </tr>"""

    html += f"""
                        </tbody>
                    </table>
                </div>
                
                <!-- Archived Files -->
                <div class="section">
                    <div class="section-title">Archived CSV Files</div>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>File</th>
                                <th>Total Lines</th>
                                <th>Data Rows</th>
                                <th>File Size</th>
                                <th>Last Modified</th>
                            </tr>
                        </thead>
                        <tbody>"""

    # Add archived CSV files (if any)
    if not archived_csvs:
        html += """
                            <tr>
                                <td colspan="5" style="text-align: center; color: #6b7280; font-style: italic;">No archived files</td>
                            </tr>"""
    else:
        for filename in archived_csvs:
            stats = archived_stats.get(filename, {})
            if stats and 'error' not in stats:
                html += f"""
                            <tr>
                                <td><a href="/{filename}" class="file-link">{os.path.basename(filename)}</a></td>
                                <td>{stats.get('total_lines', 'N/A')}</td>
                                <td>{stats.get('data_lines', 'N/A')}</td>
                                <td>{stats.get('file_size_mb', 'N/A')} MB</td>
                                <td>{stats.get('mod_time', 'N/A')}</td>
                            </tr>"""

    html += f"""
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
                        <span class="info-value">{len([f for f, s in daily_stats.items() if s and 'error' not in s])}</span>
                    </div>
                    <div class="info-row">
                        <span>Locked Files</span>
                        <span class="info-value">{len([f for f in daily_csvs if os.path.exists(f + '.lock')])}</span>
                    </div>
                    <div class="info-row">
                        <span>Archived Cases</span>
                        <span class="info-value">{len(archived_csvs)}</span>
                    </div>
                    <div class="info-row">
                        <span>Last Updated</span>
                        <span class="info-value">{now.strftime('%H:%M')}</span>
                    </div>
                </div>
                
                <button class="refresh-btn" onclick="location.reload()">Refresh Report</button>
            </div>
        </div>
    </div>
    
    <script>
        // Real-time data updates
        let updateInterval;
        
        // Smooth number counting animation
        function animateNumber(element, startValue, endValue, duration = 1000) {{
            const startTime = performance.now();
            const isPercentage = endValue.toString().includes('%');
            const numericEndValue = parseFloat(endValue.replace('%', ''));
            const numericStartValue = parseFloat(startValue.replace('%', ''));
            
            function updateNumber(currentTime) {{
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Easing function for smooth animation
                const easeOutCubic = 1 - Math.pow(1 - progress, 3);
                const currentValue = numericStartValue + (numericEndValue - numericStartValue) * easeOutCubic;
                
                if (isPercentage) {{
                    element.textContent = currentValue.toFixed(1) + '%';
                }} else {{
                    element.textContent = Math.round(currentValue).toLocaleString();
                }}
                
                if (progress < 1) {{
                    requestAnimationFrame(updateNumber);
                }} else {{
                    element.textContent = endValue;
                }}
            }}
            
            requestAnimationFrame(updateNumber);
        }}
        
        function updateDashboard() {{
            // Add loading indicator with animation
            const header = document.querySelector('.header p');
            if (header) {{
                const originalText = header.textContent.replace(' • UPDATING', '').replace(' • LIVE', '');
                header.innerHTML = originalText + ' • <span style="color: #10b981; animation: pulse 1s infinite;">UPDATING</span>';
            }}
            
            fetch('/credit_checker_report.html', {{
                credentials: 'include',
                headers: {{
                    'Authorization': 'Basic ' + btoa('admin:ralphlauren7')
                }}
            }})
            .then(response => response.text())
            .then(html => {{
                // Parse the new HTML
                const parser = new DOMParser();
                const newDoc = parser.parseFromString(html, 'text/html');
                
                // Update metric values with enhanced animations
                const metrics = document.querySelectorAll('.metric-value');
                const newMetrics = newDoc.querySelectorAll('.metric-value');
                const metricLabels = document.querySelectorAll('.metric-label');
                let hasChanges = false;
                
                metrics.forEach((metric, index) => {{
                    if (newMetrics[index]) {{
                        const oldValue = metric.textContent.trim();
                        const newValue = newMetrics[index].textContent.trim();
                        
                        if (oldValue !== newValue) {{
                            hasChanges = true;
                            
                            // Add updating class for visual feedback
                            metric.classList.add('updating');
                            if (metricLabels[index]) {{
                                metricLabels[index].classList.add('updating');
                            }}
                            
                            // Animate the number change
                            setTimeout(() => {{
                                animateNumber(metric, oldValue, newValue, 800);
                                
                                // Add changed class for final effect
                                setTimeout(() => {{
                                    metric.classList.remove('updating');
                                    metric.classList.add('changed');
                                    if (metricLabels[index]) {{
                                        metricLabels[index].classList.remove('updating');
                                    }}
                                    
                                    // Remove changed class after animation
                                    setTimeout(() => {{
                                        metric.classList.remove('changed');
                                    }}, 1500);
                                }}, 400);
                            }}, 100);
                        }}
                    }}
                }});
                
                // Show update indicator with enhanced feedback
                if (hasChanges) {{
                    console.log('Dashboard updated with changes!');
                    
                    // Add a subtle notification
                    const notification = document.createElement('div');
                    notification.style.cssText = `
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        background: #065f46;
                        color: #10b981;
                        padding: 10px 15px;
                        border-radius: 5px;
                        font-weight: 600;
                        z-index: 1000;
                        animation: slideInUp 0.5s ease-out;
                        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                    `;
                    notification.textContent = 'Data Updated!';
                    document.body.appendChild(notification);
                    
                    setTimeout(() => {{
                        notification.style.animation = 'slideInUp 0.5s ease-out reverse';
                        setTimeout(() => notification.remove(), 500);
                    }}, 2000);
                }}
                
                // Update table data with enhanced animations
                const tableRows = document.querySelectorAll('.table tbody tr');
                const newTableRows = newDoc.querySelectorAll('.table tbody tr');
                
                tableRows.forEach((row, index) => {{
                    if (newTableRows[index]) {{
                        const cells = row.querySelectorAll('td');
                        const newCells = newTableRows[index].querySelectorAll('td');
                        
                        cells.forEach((cell, cellIndex) => {{
                            if (newCells[cellIndex]) {{
                                const oldValue = cell.textContent.trim();
                                const newValue = newCells[cellIndex].textContent.trim();
                                
                                if (oldValue !== newValue) {{
                                    // Enhanced cell animation
                                    cell.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
                                    cell.style.backgroundColor = '#065f46';
                                    cell.style.transform = 'scale(1.02)';
                                    cell.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.3)';
                                    
                                    setTimeout(() => {{
                                        cell.textContent = newValue;
                                        cell.style.backgroundColor = '#000000';
                                        cell.style.transform = 'scale(1)';
                                        cell.style.boxShadow = 'none';
                                    }}, 300);
                                }}
                            }}
                        }});
                    }}
                }});
                
                // Update timestamp with animation
                const timestamp = document.querySelector('.header p');
                const newTimestamp = newDoc.querySelector('.header p');
                if (timestamp && newTimestamp) {{
                    timestamp.style.transition = 'all 0.3s ease';
                    timestamp.style.opacity = '0.7';
                    setTimeout(() => {{
                        timestamp.innerHTML = newTimestamp.innerHTML;
                        timestamp.style.opacity = '1';
                    }}, 150);
                }}
                
                // Remove loading indicator
                if (header) {{
                const originalText = header.textContent.replace(' • UPDATING', '').replace(' • LIVE', '');
                header.innerHTML = originalText + ' • <span style="color: #10b981;">LIVE</span>';
                }}
            }})
            .catch(error => {{
                console.log('Update failed:', error);
                // Remove loading indicator on error
                if (header) {{
                const originalText = header.textContent.replace(' • UPDATING', '').replace(' • LIVE', '');
                header.innerHTML = originalText + ' • <span style="color: #ef4444;">ERROR</span>';
                }}
            }});
        }}
        
        // Start auto-updates every 3 seconds
        function startAutoUpdate() {{
            updateInterval = setInterval(updateDashboard, 3000);
        }}
        
        // Stop auto-updates
        function stopAutoUpdate() {{
            if (updateInterval) {{
                clearInterval(updateInterval);
            }}
        }}
        
        // Start updates when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            startAutoUpdate();
            
            // Add visual indicator for live updates
            const header = document.querySelector('.header p');
            if (header) {{
                header.innerHTML += ' • <span style="color: #10b981;">LIVE</span>';
            }}
        }});
        
        // Pause updates when page is not visible
        document.addEventListener('visibilitychange', function() {{
            if (document.hidden) {{
                stopAutoUpdate();
            }} else {{
                startAutoUpdate();
            }}
        }});
    </script>
</body>
</html>"""
    
    return html

def main():
    """Main function"""
    print("Generating Credit Checker Dashboard...")
    
    # Generate HTML dashboard
    html_content = generate_html_dashboard()
    
    # Write to file
    output_file = 'credit_checker_dashboard.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Dashboard generated: {output_file}")
    print(f"Open in browser: file://{os.path.abspath(output_file)}")
    print(f"Or run: open {output_file}")

if __name__ == "__main__":
    main()