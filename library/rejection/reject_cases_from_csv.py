#!/usr/bin/env python3
"""
Script to reject cases from daily CSV files where both image_found and keyword_found are True.
Processes daily_claims_*.csv files and automatically rejects matching cases.
"""

import os
import sys
import argparse
from datetime import datetime
from library.unified_driver_utils import setup_driver
from library.rejection import (
    login_to_copytrack,
    reject_case_simple,
    extract_cases_to_reject_from_csv,
    get_daily_csv_files,
    RejectionTracker
)


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Reject cases with credits from daily CSV files'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--csv-file',
        type=str,
        help='Specific CSV file to process'
    )
    parser.add_argument(
        '--case-id',
        type=str,
        help='Reject a specific case ID (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List cases without rejecting'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of cases to process'
    )
    parser.add_argument(
        '--directory',
        type=str,
        default='.',
        help='Directory containing CSV files (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Handle single case ID (for testing)
    if args.case_id:
        print(f"[INFO] 🔴 Rejecting single case: {args.case_id}")
        print(f"[INFO] 🚀 Setting up Chrome driver...")
        
        driver = None
        try:
            driver = setup_driver(headless=True)
            
            if not login_to_copytrack(driver):
                print("[ERROR] ❌ Login failed, exiting")
                return 1
            
            # Reject the specific case
            if reject_case_simple(driver, args.case_id):
                print(f"\n[INFO] ✅ Case {args.case_id} rejected successfully!")
                return 0
            else:
                print(f"\n[ERROR] ❌ Failed to reject case {args.case_id}")
                return 1
                
        except Exception as e:
            print(f"[ERROR] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            if driver:
                driver.quit()
                print("\n[INFO] 🛑 Driver closed")
        return 0
    
    # Parse dates if provided
    start_date = None
    end_date = None
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    # Get CSV files to process
    if args.csv_file:
        csv_files = [args.csv_file] if os.path.exists(args.csv_file) else []
    else:
        csv_files = get_daily_csv_files(start_date, end_date, args.directory)
    
    if not csv_files:
        print("[ERROR] ❌ No CSV files found to process")
        return 1
    
    print(f"[INFO] 📁 Processing {len(csv_files)} CSV file(s)")
    
    # Extract all cases with credits
    all_cases = set()
    for csv_file in csv_files:
        cases = extract_cases_to_reject_from_csv(csv_file)
        all_cases.update(cases)
    
    if not all_cases:
        print("[INFO] ✅ No cases with credits found")
        return 0
    
    print(f"\n[INFO] 📊 Total cases to reject: {len(all_cases)}")
    
    # Initialize rejection tracker
    tracker = RejectionTracker()
    
    # Filter out already-rejected cases
    new_cases = [c for c in all_cases if not tracker.is_already_rejected(c)]
    skipped_count = len(all_cases) - len(new_cases)
    
    if skipped_count > 0:
        print(f"[INFO] ⏭️  Skipping {skipped_count} already-rejected case(s)")
    
    if not new_cases:
        print("[INFO] ✅ All cases were already rejected today")
        return 0
    
    print(f"[INFO] 🆕 New cases to reject: {len(new_cases)}")
    
    # Apply limit if specified
    cases_to_process = sorted(list(new_cases))
    if args.limit:
        cases_to_process = cases_to_process[:args.limit]
        print(f"[INFO] ⚠️  Limited to {args.limit} cases")
    
    # Dry run - just list cases
    if args.dry_run:
        print("\n[INFO] 🔍 DRY RUN - Cases that would be rejected:")
        for case_id in cases_to_process:
            print(f"  - {case_id}")
        print(f"\n[INFO] Total: {len(cases_to_process)} cases")
        return 0
    
    # Setup driver and login
    print("\n[INFO] 🚀 Setting up Chrome driver...")
    driver = None
    try:
        driver = setup_driver(headless=True)
        
        if not login_to_copytrack(driver):
            print("[ERROR] ❌ Login failed, exiting")
            return 1
        
        # Process each case
        successful = 0
        failed = 0
        
        for i, case_id in enumerate(cases_to_process, 1):
            print(f"\n[INFO] [{i}/{len(cases_to_process)}] Processing case {case_id}")
            
            if reject_case_simple(driver, case_id):
                successful += 1
                tracker.mark_as_rejected(case_id)
                print(f"[INFO] ✅ Progress: {successful} succeeded, {failed} failed")
            else:
                failed += 1
                print(f"[INFO] ⚠️  Progress: {successful} succeeded, {failed} failed")
            
            # Small delay between cases
            import time
            time.sleep(2)
        
        # Summary
        print("\n" + "="*60)
        print("[INFO] 📊 SUMMARY")
        print("="*60)
        print(f"[INFO] ✅ Successfully rejected: {successful}")
        print(f"[INFO] ❌ Failed to reject: {failed}")
        print(f"[INFO] 📋 Total processed: {successful + failed}")
        print("="*60)
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        print(f"[ERROR] ❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if driver:
            driver.quit()
            print("\n[INFO] 🛑 Driver closed")


if __name__ == "__main__":
    sys.exit(main())
