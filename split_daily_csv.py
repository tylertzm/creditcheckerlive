#!/usr/bin/env python3
"""
Split overall_checked_claims.csv into daily CSV files based on processed_at date.
Creates files with format: daily_claims_YYYY-MM-DD.csv
"""

import csv
import sys
import os
from datetime import datetime
from collections import defaultdict

OVERALL_CSV = "overall_checked_claims.csv"
OUTPUT_DIR = "."  # Current directory

def parse_date_from_timestamp(timestamp_str):
    """
    Extract date from processed_at timestamp.
    Expected format: "2025-09-12 16:50:13" or empty
    Returns: "2025-09-12" or None
    """
    if not timestamp_str or not timestamp_str.strip():
        return None
    
    try:
        # Parse the timestamp
        dt = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        # Try other common formats
        try:
            dt = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

def split_into_daily_files():
    """Read overall CSV and split into daily files"""
    
    if not os.path.exists(OVERALL_CSV):
        print(f"[ERROR] {OVERALL_CSV} not found!")
        sys.exit(1)
    
    print(f"[INFO] Reading {OVERALL_CSV}...")
    
    # Increase CSV field size limit
    csv.field_size_limit(sys.maxsize)
    
    # Dictionary to store rows by date
    daily_rows = defaultdict(list)
    rows_without_date = []
    total_rows = 0
    
    # Read the overall CSV
    with open(OVERALL_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        for row in reader:
            total_rows += 1
            
            # Extract date from processed_at column
            processed_at = row.get('processed_at', '')
            date = parse_date_from_timestamp(processed_at)
            
            if date:
                daily_rows[date].append(row)
            else:
                rows_without_date.append(row)
            
            # Progress indicator
            if total_rows % 10000 == 0:
                print(f"[INFO] Processed {total_rows} rows, found {len(daily_rows)} unique dates...")
    
    print(f"\n[INFO] Total rows processed: {total_rows}")
    print(f"[INFO] Rows without valid date: {len(rows_without_date)}")
    print(f"[INFO] Unique dates found: {len(daily_rows)}")
    
    # Write daily CSV files
    files_created = 0
    for date, rows in sorted(daily_rows.items()):
        filename = os.path.join(OUTPUT_DIR, f"daily_claims_{date}.csv")
        
        print(f"[INFO] Writing {filename} ({len(rows)} rows)...")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        
        files_created += 1
    
    # Optionally write rows without dates to a separate file
    if rows_without_date:
        no_date_file = os.path.join(OUTPUT_DIR, "daily_claims_no_date.csv")
        print(f"[INFO] Writing {no_date_file} ({len(rows_without_date)} rows without dates)...")
        
        with open(no_date_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows_without_date)
        
        files_created += 1
    
    print(f"\n[SUCCESS] ✅ Created {files_created} daily CSV files!")
    
    # Show summary of dates
    print("\n[INFO] Date summary:")
    for date in sorted(daily_rows.keys()):
        print(f"  - {date}: {len(daily_rows[date])} rows")

if __name__ == "__main__":
    split_into_daily_files()
