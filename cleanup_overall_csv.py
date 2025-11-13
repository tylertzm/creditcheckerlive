#!/usr/bin/env python3
"""
Clean up overall_checked_claims.csv by:
1. Moving misplaced dates from screenshot_path to processed_at
2. Moving misplaced screenshot paths from error_status to screenshot_path
3. Removing rows that only have one or two fields populated (incomplete rows)
"""

import csv
import sys
import os
import re
from datetime import datetime

OVERALL_CSV = "overall_checked_claims.csv"
TEMP_CSV = "overall_checked_claims.tmp"

# Regex patterns for date detection
DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}')
DATETIME_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}')
SCREENSHOT_PATTERN = re.compile(r'screenshot_\d{8}_\d{6}\.png')

def count_populated_fields(row):
    """Count how many fields in the row have non-empty values"""
    count = 0
    for key, value in row.items():
        if value and str(value).strip():
            count += 1
    return count

def is_date_string(s):
    """Check if string contains a date pattern"""
    if not s or not isinstance(s, str):
        return False
    return bool(DATETIME_PATTERN.search(s) or DATE_PATTERN.search(s))

def is_screenshot_path(s):
    """Check if string looks like a screenshot path"""
    if not s or not isinstance(s, str):
        return False
    return bool(SCREENSHOT_PATTERN.search(s))

def clean_row(row):
    """
    Clean a single row by moving misplaced fields.
    Returns (cleaned_row, was_modified)
    """
    modified = False
    
    # Check if processed_at is empty but screenshot_path contains a date
    if (not row.get('processed_at') or not row.get('processed_at').strip()) and is_date_string(row.get('screenshot_path', '')):
        # Move date from screenshot_path to processed_at
        row['processed_at'] = row['screenshot_path']
        row['screenshot_path'] = ''
        modified = True
        
    # Check if screenshot_path is empty but error_status contains a screenshot path
    if (not row.get('screenshot_path') or not row.get('screenshot_path').strip()) and is_screenshot_path(row.get('error_status', '')):
        # Move screenshot from error_status to screenshot_path
        row['screenshot_path'] = row['error_status']
        row['error_status'] = 'Success'  # Assume success if screenshot exists
        modified = True
    
    return row, modified

def cleanup_overall_csv():
    """Main cleanup function"""
    
    if not os.path.exists(OVERALL_CSV):
        print(f"[ERROR] {OVERALL_CSV} not found!")
        sys.exit(1)
    
    print(f"[INFO] Reading {OVERALL_CSV}...")
    
    # Increase CSV field size limit
    csv.field_size_limit(sys.maxsize)
    
    # Statistics
    total_rows = 0
    modified_rows = 0
    removed_rows = 0
    removed_no_comma = 0
    dates_moved = 0
    screenshots_moved = 0
    cleaned_rows = []
    
    # First pass: Read raw lines to detect rows with no commas
    print(f"[INFO] First pass: detecting rows without commas...")
    raw_lines = []
    with open(OVERALL_CSV, 'r', encoding='utf-8') as f:
        header_line = f.readline()
        raw_lines.append(header_line)
        
        line_num = 1
        for line in f:
            line_num += 1
            # Check if line has commas (CSV separator)
            if ',' not in line.strip():
                removed_no_comma += 1
                if line_num % 10000 == 0:
                    print(f"[INFO] Scanned {line_num} lines, found {removed_no_comma} without commas...")
                continue
            raw_lines.append(line)
    
    print(f"[INFO] Found {removed_no_comma} rows without commas, removing them...")
    
    # Write cleaned lines to temp file
    temp_raw = OVERALL_CSV + ".raw_cleaned"
    with open(temp_raw, 'w', encoding='utf-8') as f:
        f.writelines(raw_lines)
    
    # Second pass: Read CSV and clean fields
    print(f"[INFO] Second pass: cleaning CSV fields...")
    with open(temp_raw, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        for row in reader:
            total_rows += 1
            
            # Count populated fields (excluding case_id, case_url, hit_number which are required)
            populated = count_populated_fields(row)
            
            # Remove rows with very few fields populated (likely incomplete/corrupt)
            # We need at least case_id, case_url, hit_number + some other data
            required_fields = ['case_id', 'case_url', 'hit_number']
            has_required = all(row.get(field, '').strip() for field in required_fields)
            
            if not has_required or populated < 4:
                removed_rows += 1
                if total_rows % 10000 == 0:
                    print(f"[INFO] Processed {total_rows} rows, removed {removed_rows} incomplete rows...")
                continue
            
            # Track original values for comparison
            original_processed_at = row.get('processed_at', '')
            original_screenshot = row.get('screenshot_path', '')
            
            # Clean the row
            cleaned_row, was_modified = clean_row(row)
            
            if was_modified:
                modified_rows += 1
                if original_processed_at != cleaned_row.get('processed_at', ''):
                    dates_moved += 1
                if original_screenshot != cleaned_row.get('screenshot_path', ''):
                    screenshots_moved += 1
            
            cleaned_rows.append(cleaned_row)
            
            # Progress indicator
            if total_rows % 10000 == 0:
                print(f"[INFO] Processed {total_rows} rows, modified {modified_rows}, removed {removed_rows}...")
    
    # Remove temp raw file
    os.remove(temp_raw)
    
    print(f"\n[INFO] Writing cleaned data back to {OVERALL_CSV}...")
    
    # Write to temp file first
    with open(TEMP_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(cleaned_rows)
    
    # Replace original file with temp file
    os.replace(TEMP_CSV, OVERALL_CSV)
    
    print(f"\n[SUCCESS] ✅ Cleanup complete!")
    print(f"[INFO] Statistics:")
    print(f"  - Total rows processed: {total_rows}")
    print(f"  - Rows removed (no commas): {removed_no_comma}")
    print(f"  - Rows removed (incomplete): {removed_rows}")
    print(f"  - Rows modified: {modified_rows}")
    print(f"  - Rows kept: {len(cleaned_rows)}")
    print(f"  - Dates moved from screenshot_path to processed_at: {dates_moved}")
    print(f"  - Screenshots moved from error_status to screenshot_path: {screenshots_moved}")

if __name__ == "__main__":
    cleanup_overall_csv()
