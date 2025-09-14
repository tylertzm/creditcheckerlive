#!/usr/bin/env python3
"""
Remove duplicate rows based on hit_number column, keeping only the first occurrence.
Uses only built-in Python libraries.
"""

import csv
import sys
from datetime import datetime

def remove_duplicate_hits(input_file, output_file):
    """Remove duplicate rows based on hit_number column."""
    
    print(f"📊 Loading data from {input_file}...")
    
    seen_hit_numbers = set()
    rows_processed = 0
    rows_written = 0
    duplicates_removed = 0
    
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        
        # Read header
        header = next(reader)
        rows_processed += 1
        
        # Find hit_number column index
        try:
            hit_number_index = header.index('hit_number')
        except ValueError:
            print("❌ Error: 'hit_number' column not found in CSV")
            return
        
        print(f"📈 Found hit_number column at index {hit_number_index}")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            
            # Write header
            writer.writerow(header)
            rows_written += 1
            
            # Process each row
            for row in reader:
                rows_processed += 1
                
                if len(row) > hit_number_index:
                    hit_number = row[hit_number_index]
                    
                    if hit_number not in seen_hit_numbers:
                        # First time seeing this hit_number
                        seen_hit_numbers.add(hit_number)
                        writer.writerow(row)
                        rows_written += 1
                    else:
                        # Duplicate hit_number
                        duplicates_removed += 1
                else:
                    # Malformed row, skip
                    print(f"⚠️  Skipping malformed row {rows_processed}")
                    continue
    
    print(f"\n📊 Summary:")
    print(f"   • Total rows processed: {rows_processed:,}")
    print(f"   • Rows written: {rows_written:,}")
    print(f"   • Duplicates removed: {duplicates_removed:,}")
    print(f"   • Unique hit numbers: {len(seen_hit_numbers):,}")
    print(f"   • Reduction: {(duplicates_removed / rows_processed * 100):.1f}%")

if __name__ == "__main__":
    input_file = "overall_checked_claims.csv"
    output_file = "overall_checked_claims_clean.csv"
    
    try:
        remove_duplicate_hits(input_file, output_file)
        print(f"\n✅ Deduplication completed successfully!")
        print(f"💾 Cleaned data saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)