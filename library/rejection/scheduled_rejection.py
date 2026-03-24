#!/usr/bin/env python3
"""
Scheduled rejection script that continuously monitors today's daily CSV
and rejects cases with found credits. Runs in an infinite loop with delays.
"""

import os
import sys
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from library.unified_driver_utils import setup_driver
from library.rejection import (
    login_to_copytrack,
    reject_case_simple,
    extract_cases_to_reject_from_csv,
    RejectionTracker
)


# Configuration
CHECK_INTERVAL_SECONDS = 300  # 5 minutes between checks
RETRY_DELAY_SECONDS = 60  # 1 minute before retrying on error


def get_today_csv_file(directory='/app/data'):
    """Get today's daily CSV file path"""
    today = datetime.now().strftime('%Y-%m-%d')
    csv_file = os.path.join(directory, f'daily_claims_{today}.csv')
    return csv_file if os.path.exists(csv_file) else None


def run_rejection_cycle(driver, tracker):
    """
    Run one rejection cycle: check today's CSV and reject new cases
    Returns: (successful_count, failed_count, skipped_count)
    """
    # Get today's CSV file
    csv_file = get_today_csv_file()
    
    if not csv_file:
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"[INFO] ⏳ No CSV file found for today ({today})")
        return 0, 0, 0
    
    print(f"[INFO] 📁 Checking {os.path.basename(csv_file)}")
    
    # Extract cases with credits (returns dict of case_id: credit_name)
    all_cases = extract_cases_to_reject_from_csv(csv_file)
    
    if not all_cases:
        print("[INFO] ✅ No cases with credits found in today's CSV")
        return 0, 0, 0
    
    # Filter out already-rejected cases
    new_cases = {case_id: credit for case_id, credit in all_cases.items() 
                 if not tracker.is_already_rejected(case_id)}
    skipped_count = len(all_cases) - len(new_cases)
    
    if skipped_count > 0:
        print(f"[INFO] ⏭️  Skipping {skipped_count} already-rejected case(s)")
    
    if not new_cases:
        print(f"[INFO] ✅ All {len(all_cases)} cases were already rejected today")
        return 0, 0, skipped_count
    
    print(f"[INFO] 🆕 Found {len(new_cases)} new case(s) to reject")
    
    # Process each new case
    successful = 0
    failed = 0
    
    for i, (case_id, credit_name) in enumerate(sorted(new_cases.items()), 1):
        print(f"\n[INFO] [{i}/{len(new_cases)}] Rejecting case {case_id} (Credit: {credit_name})")
        
        try:
            if reject_case_simple(driver, case_id, credit_name):
                successful += 1
                tracker.mark_as_rejected(case_id)
                print(f"[INFO] ✅ Success ({successful}/{len(new_cases)})")
            else:
                failed += 1
                print(f"[INFO] ❌ Failed ({failed}/{len(new_cases)})")
        except Exception as e:
            failed += 1
            print(f"[ERROR] ❌ Error rejecting {case_id}: {e}")
        
        # Small delay between cases
        time.sleep(2)
    
    return successful, failed, skipped_count


def main():
    """Main loop - continuously check and reject cases"""
    print("="*70)
    print("[INFO] 🚀 Starting Scheduled Rejection Service")
    print("="*70)
    print(f"[INFO] ⏰ Check interval: {CHECK_INTERVAL_SECONDS} seconds ({CHECK_INTERVAL_SECONDS//60} minutes)")
    print(f"[INFO] 📅 Today: {datetime.now().strftime('%Y-%m-%d')}")
    print("="*70)
    print()
    
    driver = None
    cycle_count = 0
    
    try:
        # Setup driver once
        print("[INFO] 🌐 Setting up Chrome driver...")
        driver = setup_driver(headless=True)
        
        # Login once at start
        print("[INFO] 🔐 Logging in to Copytrack...")
        if not login_to_copytrack(driver):
            print("[ERROR] ❌ Login failed, exiting")
            return 1
        
        print("[INFO] ✅ Login successful")
        print()
        
        # Main loop
        while True:
            cycle_count += 1
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print("="*70)
            print(f"[INFO] 🔄 Cycle #{cycle_count} - {now}")
            print("="*70)
            
            try:
                # Initialize/reload tracker (handles midnight cleanup)
                tracker = RejectionTracker()
                
                # Run rejection cycle
                successful, failed, skipped = run_rejection_cycle(driver, tracker)
                
                # Report summary
                if successful > 0 or failed > 0:
                    print("\n" + "-"*70)
                    print(f"[INFO] 📊 Cycle Summary:")
                    print(f"[INFO]    ✅ Rejected: {successful}")
                    print(f"[INFO]    ❌ Failed: {failed}")
                    print(f"[INFO]    ⏭️  Skipped: {skipped}")
                    print(f"[INFO]    📋 Total in tracker: {tracker.get_rejected_count()}")
                    print("-"*70)
                
                # Wait before next check
                next_check = datetime.fromtimestamp(time.time() + CHECK_INTERVAL_SECONDS)
                next_check_str = next_check.strftime('%H:%M:%S')
                print(f"\n[INFO] ⏰ Next check at {next_check_str}")
                print(f"[INFO] 😴 Sleeping for {CHECK_INTERVAL_SECONDS} seconds...")
                print()
                
                time.sleep(CHECK_INTERVAL_SECONDS)
                
            except Exception as e:
                print(f"\n[ERROR] ❌ Error in cycle: {e}")
                import traceback
                traceback.print_exc()
                
                # Try to recover - check if we need to re-login
                print(f"\n[INFO] 🔄 Attempting to recover in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
                
                try:
                    # Re-login
                    print("[INFO] 🔐 Re-logging in...")
                    if login_to_copytrack(driver):
                        print("[INFO] ✅ Re-login successful")
                    else:
                        print("[ERROR] ❌ Re-login failed, will retry next cycle")
                except Exception as re_login_error:
                    print(f"[ERROR] ❌ Re-login error: {re_login_error}")
                
                print()
    
    except KeyboardInterrupt:
        print("\n\n[INFO] ⚠️  Received shutdown signal")
        print("[INFO] 🛑 Shutting down gracefully...")
    
    except Exception as e:
        print(f"\n[ERROR] ❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if driver:
            driver.quit()
            print("[INFO] 🛑 Driver closed")
        
        print("\n" + "="*70)
        print(f"[INFO] 📊 Final Stats:")
        print(f"[INFO]    Total cycles completed: {cycle_count}")
        print("="*70)
        print("[INFO] ✅ Scheduled Rejection Service stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
