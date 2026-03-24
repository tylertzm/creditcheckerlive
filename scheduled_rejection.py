#!/usr/bin/env python3
"""
Scheduled rejection service that checks today's daily CSV every 10 minutes
and automatically rejects cases where both image_found and keyword_found are True.
"""

import os
import sys
import time
from datetime import datetime
from library.unified_driver_utils import setup_driver
from library.rejection import (
    login_to_copytrack,
    reject_case_simple,
    extract_cases_to_reject_from_csv
)


def get_todays_csv_file(directory='.'):
    """Get today's daily CSV file path"""
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'daily_claims_{today}.csv'
    filepath = os.path.join(directory, filename)
    return filepath if os.path.exists(filepath) else None


def process_rejections(driver, processed_cases):
    """
    Process rejections for today's CSV file.
    
    Args:
        driver: Selenium WebDriver instance (reused across runs)
        processed_cases: Set of case IDs already processed
        
    Returns:
        tuple: (newly_rejected_count, failed_count)
    """
    # Get today's CSV file
    csv_file = get_todays_csv_file('/app/data')
    
    if not csv_file:
        print(f"[INFO] ⚠️  No CSV file found for today ({datetime.now().strftime('%Y-%m-%d')})")
        return 0, 0
    
    print(f"[INFO] 📋 Checking CSV file: {csv_file}")
    
    # Extract cases that need rejection
    cases_to_reject = extract_cases_to_reject_from_csv(csv_file)
    
    # Filter out already processed cases
    new_cases = cases_to_reject - processed_cases
    
    if not new_cases:
        print(f"[INFO] ✅ No new cases to reject (found {len(cases_to_reject)} cases, all already processed)")
        return 0, 0
    
    print(f"[INFO] 🔴 Found {len(new_cases)} new cases to reject")
    
    # Process each new case
    successful = 0
    failed = 0
    
    for i, case_id in enumerate(sorted(new_cases), 1):
        print(f"\n[INFO] [{i}/{len(new_cases)}] Processing case {case_id}")
        
        try:
            if reject_case_simple(driver, case_id):
                successful += 1
                processed_cases.add(case_id)
                print(f"[INFO] ✅ Case {case_id} rejected successfully")
            else:
                failed += 1
                print(f"[WARN] ⚠️  Failed to reject case {case_id}")
            
            # Small delay between cases
            time.sleep(2)
            
        except Exception as e:
            failed += 1
            print(f"[ERROR] ❌ Error rejecting case {case_id}: {e}")
            continue
    
    return successful, failed


def main():
    """Main scheduled rejection loop"""
    print("\n" + "="*70)
    print("[INFO] 🚀 Starting Scheduled Rejection Service")
    print("="*70)
    print(f"[INFO] ⏱️  Interval: Every 10 minutes")
    print(f"[INFO] 📂 Data directory: /app/data")
    print(f"[INFO] 🔍 Monitoring file pattern: daily_claims_YYYY-MM-DD.csv")
    print("="*70 + "\n")
    
    # Keep track of processed cases (persists across runs)
    processed_cases = set()
    
    # Setup driver once and reuse it
    driver = None
    last_login_time = None
    LOGIN_REFRESH_INTERVAL = 3600  # Re-login every hour
    
    cycle = 0
    total_rejected = 0
    total_failed = 0
    
    try:
        while True:
            cycle += 1
            current_time = time.time()
            
            print(f"\n[INFO] ===== Cycle {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
            
            # Setup driver and login if needed
            if driver is None or last_login_time is None or (current_time - last_login_time) > LOGIN_REFRESH_INTERVAL:
                if driver is not None:
                    print("[INFO] 🔄 Refreshing browser session...")
                    try:
                        driver.quit()
                    except:
                        pass
                
                print("[INFO] 🚀 Setting up Chrome driver...")
                driver = setup_driver(headless=True)
                
                if not login_to_copytrack(driver):
                    print("[ERROR] ❌ Login failed, will retry in 10 minutes")
                    driver.quit()
                    driver = None
                    last_login_time = None
                else:
                    last_login_time = current_time
                    print("[INFO] ✅ Browser session ready")
            
            if driver is not None:
                try:
                    # Process rejections
                    rejected, failed = process_rejections(driver, processed_cases)
                    total_rejected += rejected
                    total_failed += failed
                    
                    if rejected > 0 or failed > 0:
                        print(f"\n[INFO] 📊 Cycle {cycle} summary: {rejected} rejected, {failed} failed")
                    
                    print(f"[INFO] 📈 Total stats: {total_rejected} rejected, {total_failed} failed, {len(processed_cases)} tracked")
                    
                except Exception as e:
                    print(f"[ERROR] ❌ Error during processing: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Wait 10 minutes before next cycle
            print(f"\n[INFO] ⏸️  Waiting 10 minutes until next check...")
            print(f"[INFO] 🕐 Next check at: {datetime.fromtimestamp(time.time() + 600).strftime('%H:%M:%S')}")
            time.sleep(600)  # 10 minutes
            
    except KeyboardInterrupt:
        print("\n\n[INFO] 🛑 Shutting down scheduled rejection service...")
        print(f"[INFO] 📊 Final stats: {total_rejected} rejected, {total_failed} failed")
    except Exception as e:
        print(f"\n[ERROR] ❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
                print("[INFO] 🛑 Browser closed")
            except:
                pass


if __name__ == "__main__":
    main()
