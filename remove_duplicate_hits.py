#!/usr/bin/env python3
"""
Remove rows that do not have more than 10 fields separated by commas, including empty ones.
Keeps only rows with 11 or more fields.
Uses only built-in Python libraries.
"""

import csv
import sys
from datetime import datetime

def filter_rows_by_field_count(input_file, output_file, min_fields=11):
    """Remove rows that have 10 or fewer fields, keeping only rows with 11+ fields."""
    
    print(f"📊 Loading data from {input_file}...")
    print(f"🎯 Filtering to keep only rows with {min_fields}+ fields...")
    
    rows_processed = 0
    rows_written = 0
    rows_filtered_out = 0
    
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            
            # Process each row
            for row in reader:
                rows_processed += 1
                
                field_count = len(row)
                
                if field_count >= min_fields:
                    # Row has enough fields, keep it
                    writer.writerow(row)
                    rows_written += 1
                else:
                    # Row has too few fields, filter it out
                    rows_filtered_out += 1
                    if rows_filtered_out <= 5:  # Show first 5 filtered rows as examples
                        print(f"⚠️  Filtered out row {rows_processed} (only {field_count} fields): {row[:3]}...")
                    elif rows_filtered_out == 6:
                        print("⚠️  ... (showing only first 5 filtered rows)")
    
    print(f"\n📊 Summary:")
    print(f"   • Total rows processed: {rows_processed:,}")
    print(f"   • Rows kept ({min_fields}+ fields): {rows_written:,}")
    print(f"   • Rows filtered out (≤{min_fields-1} fields): {rows_filtered_out:,}")
    print(f"   • Retention rate: {(rows_written / rows_processed * 100):.1f}%" if rows_processed > 0 else "   • Retention rate: 0%")

if __name__ == "__main__":
    input_file = "overall_checked_claims.csv"
    output_file = "overall_checked_claims_filtered.csv"
    
    try:
        filter_rows_by_field_count(input_file, output_file, min_fields=11)
        print(f"\n✅ Filtering completed successfully!")
        print(f"💾 Filtered data saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)